"""
Live Order Service

Handles live order execution, management, and broker integration.
Provides focused order lifecycle management with proper dependency injection.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import aiosqlite
from loguru import logger

from ..config import Config
from ..core.state_models import OrderCommand
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError, APIError, ValidationError
from ..mcp.broker import ZerodhaBroker


class LiveOrderStatus(Enum):
    """Live order status enumeration."""
    PENDING = "pending"
    PLACED = "placed"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class LiveOrder:
    """Live order tracking."""
    order_id: str
    broker_order_id: Optional[str]
    symbol: str
    side: str
    quantity: int
    filled_quantity: int = 0
    remaining_quantity: int = 0
    price: Optional[float] = None
    status: LiveOrderStatus = LiveOrderStatus.PENDING
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.remaining_quantity:
            self.remaining_quantity = self.quantity


class LiveOrderService(EventHandler):
    """
    Live Order Service - Focused order execution and management.

    Responsibilities:
    - Order placement and cancellation
    - Broker API integration
    - Order status tracking
    - Risk validation before execution
    """

    def __init__(self, config: Config, event_bus: EventBus, broker: ZerodhaBroker, db_connection: aiosqlite.Connection):
        self.config = config
        self.event_bus = event_bus
        self.broker = broker
        self.db = db_connection
        self._lock = asyncio.Lock()

        # Order state
        self._active_orders: Dict[str, LiveOrder] = {}

        # Risk limits
        self._max_single_order = config.get("trading", {}).get("max_single_order", 50000)

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)

    async def initialize(self) -> None:
        """Initialize the order service."""
        async with self._lock:
            await self._load_active_orders()
            logger.info("Live order service initialized")

    async def _load_active_orders(self) -> None:
        """Load active orders from database."""
        cursor = await self.db.execute("""
            SELECT order_id, broker_order_id, symbol, side, quantity, filled_quantity,
                   remaining_quantity, price, status, created_at, updated_at
            FROM live_orders
            WHERE status IN ('pending', 'placed', 'partial_fill')
        """)

        async for row in cursor:
            order = LiveOrder(
                order_id=row[0],
                broker_order_id=row[1],
                symbol=row[2],
                side=row[3],
                quantity=row[4],
                filled_quantity=row[5] or 0,
                remaining_quantity=row[6] or row[4],
                price=row[7],
                status=LiveOrderStatus(row[8]),
                created_at=row[9]
            )
            order.updated_at = row[10]
            self._active_orders[row[0]] = order

    async def place_order(self, order_command: OrderCommand, correlation_id: str) -> str:
        """Place a live order through the broker."""
        async with self._lock:
            # Validate order
            await self._validate_order(order_command)

            # Generate internal order ID
            order_id = f"live_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{order_command.symbol}"

            # Create live order
            live_order = LiveOrder(
                order_id=order_id,
                broker_order_id=None,
                symbol=order_command.symbol,
                side=order_command.side,
                quantity=order_command.qty or 0,
                price=order_command.price,
                status=LiveOrderStatus.PENDING
            )
            self._active_orders[order_id] = live_order

            # Save to database
            now = datetime.now(timezone.utc).isoformat()
            await self.db.execute("""
                INSERT INTO live_orders
                (order_id, symbol, side, quantity, remaining_quantity, price, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                order_command.symbol,
                order_command.side,
                order_command.qty,
                order_command.qty,
                order_command.price,
                live_order.status.value,
                now,
                now
            ))
            await self.db.commit()

            # Submit to broker asynchronously
            asyncio.create_task(self._submit_to_broker(order_id, order_command, correlation_id))

            # Emit event with correlation ID
            await self.event_bus.publish(Event(
                id=f"order_placed_{order_id}",
                type=EventType.EXECUTION_ORDER_PLACED,
                timestamp=now,
                source="live_order_service",
                correlation_id=correlation_id,
                data={
                    "order_id": order_id,
                    "symbol": order_command.symbol,
                    "quantity": order_command.qty,
                    "side": order_command.side,
                    "price": order_command.price
                }
            ))

            logger.info(f"Live order placed: {order_id} for {order_command.symbol}")
            return order_id

    async def _validate_order(self, order_command: OrderCommand) -> None:
        """Validate order against risk limits."""
        if not order_command.price or not order_command.qty:
            raise ValidationError("Order must have price and quantity", recoverable=False)

        order_value = order_command.price * order_command.qty

        # Check single order limit
        if order_value > self._max_single_order:
            raise ValidationError(
                f"Order value {order_value:.2f} exceeds single order limit {self._max_single_order:.2f}",
                recoverable=True
            )

    async def _submit_to_broker(self, order_id: str, order_command: OrderCommand, correlation_id: str) -> None:
        """Submit order to broker."""
        try:
            # Convert to broker format
            broker_params = self._convert_to_broker_format(order_command)

            # Place order with broker
            broker_response = await self.broker.place_order(**broker_params)

            if broker_response.get("status") == "success":
                broker_order_id = broker_response.get("order_id")

                # Update order state
                async with self._lock:
                    if order_id in self._active_orders:
                        order = self._active_orders[order_id]
                        order.broker_order_id = broker_order_id
                        order.status = LiveOrderStatus.PLACED
                        order.updated_at = datetime.now(timezone.utc).isoformat()

                        # Update database
                        await self.db.execute("""
                            UPDATE live_orders SET broker_order_id = ?, status = ?, updated_at = ?
                            WHERE order_id = ?
                        """, (broker_order_id, order.status.value, order.updated_at, order_id))
                        await self.db.commit()

                await self.event_bus.publish(Event(
                    id=f"order_submitted_{order_id}",
                    type=EventType.EXECUTION_ORDER_FILLED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="live_order_service",
                    correlation_id=correlation_id,
                    data={
                        "order_id": order_id,
                        "broker_order_id": broker_order_id,
                        "status": "placed"
                    }
                ))

                logger.info(f"Order {order_id} submitted to broker: {broker_order_id}")
            else:
                await self._handle_order_rejection(order_id, broker_response.get("message", "Unknown error"), correlation_id)

        except Exception as e:
            logger.error(f"Failed to submit order {order_id} to broker: {e}")
            await self._handle_order_rejection(order_id, str(e), correlation_id)

    def _convert_to_broker_format(self, order_command: OrderCommand) -> Dict[str, Any]:
        """Convert internal order command to broker API format."""
        return {
            "tradingsymbol": order_command.symbol,
            "exchange": "NSE",
            "transaction_type": order_command.side,
            "order_type": order_command.order_type,
            "quantity": order_command.qty,
            "product": order_command.product,
            "price": order_command.price,
            "trigger_price": order_command.trigger_price,
            "validity": order_command.tif,
            "variety": order_command.variety
        }

    async def cancel_order(self, order_id: str, correlation_id: str) -> bool:
        """Cancel a live order."""
        async with self._lock:
            if order_id not in self._active_orders:
                return False

            order = self._active_orders[order_id]

            if order.broker_order_id and order.status in [LiveOrderStatus.PENDING, LiveOrderStatus.PLACED]:
                # Cancel with broker
                try:
                    cancel_result = await self.broker.cancel_order(
                        order_id=order.broker_order_id,
                        variety="regular"
                    )

                    if cancel_result.get("status") == "success":
                        await self._update_order_status(order_id, LiveOrderStatus.CANCELLED, correlation_id)
                        return True
                    else:
                        logger.error(f"Failed to cancel order {order_id}: {cancel_result}")
                        return False

                except Exception as e:
                    logger.error(f"Error cancelling order {order_id}: {e}")
                    return False
            else:
                # Cancel locally
                await self._update_order_status(order_id, LiveOrderStatus.CANCELLED, correlation_id)
                return True

    async def _update_order_status(self, order_id: str, status: LiveOrderStatus, correlation_id: str) -> None:
        """Update order status."""
        async with self._lock:
            if order_id in self._active_orders:
                order = self._active_orders[order_id]
                order.status = status
                order.updated_at = datetime.now(timezone.utc).isoformat()

                await self.db.execute("""
                    UPDATE live_orders SET status = ?, updated_at = ? WHERE order_id = ?
                """, (status.value, order.updated_at, order_id))
                await self.db.commit()

                # Emit status update event
                await self.event_bus.publish(Event(
                    id=f"order_status_{order_id}",
                    type=EventType.EXECUTION_ORDER_FILLED,
                    timestamp=order.updated_at,
                    source="live_order_service",
                    correlation_id=correlation_id,
                    data={
                        "order_id": order_id,
                        "status": status.value
                    }
                ))

    async def _handle_order_rejection(self, order_id: str, reason: str, correlation_id: str) -> None:
        """Handle order rejection."""
        await self._update_order_status(order_id, LiveOrderStatus.REJECTED, correlation_id)

        await self.event_bus.publish(Event(
            id=f"order_rejected_{order_id}",
            type=EventType.EXECUTION_ORDER_FILLED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="live_order_service",
            correlation_id=correlation_id,
            data={
                "order_id": order_id,
                "status": "rejected",
                "reason": reason
            }
        ))

        logger.warning(f"Order {order_id} rejected: {reason}")

    async def get_active_orders(self) -> Dict[str, LiveOrder]:
        """Get active live orders."""
        async with self._lock:
            return {k: v for k, v in self._active_orders.items()
                   if v.status in [LiveOrderStatus.PENDING, LiveOrderStatus.PLACED, LiveOrderStatus.PARTIAL_FILL]}

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        # Handle order status updates from broker feeds
        if event.type == EventType.EXECUTION_ORDER_FILLED:
            order_data = event.data
            if "order_id" in order_data and "status" in order_data:
                order_id = order_data["order_id"]
                new_status = order_data["status"]

                # Update local order status
                status_enum = LiveOrderStatus(new_status)
                await self._update_order_status(order_id, status_enum, event.correlation_id or "")

    async def close(self) -> None:
        """Close the order service."""
        # Cancel any pending broker operations
        pass