"""
Execution Service

Handles order placement, broker integration, fill tracking,
slippage monitoring, and order state machine.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import aiosqlite
from loguru import logger

from src.config import Config
from ..core.state_models import OrderCommand, ExecutionReport
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..mcp.broker import ZerodhaBroker


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PLACED = "placed"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderState:
    """Order state tracking."""
    order_id: str
    broker_order_id: Optional[str]
    status: OrderStatus
    symbol: str
    quantity: int
    filled_quantity: int = 0
    remaining_quantity: int = 0
    average_price: Optional[float] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.remaining_quantity:
            self.remaining_quantity = self.quantity


class ExecutionService(EventHandler):
    """
    Execution Service - handles order lifecycle and broker integration.

    Responsibilities:
    - Order placement and management
    - Broker API integration
    - Fill tracking and reconciliation
    - Slippage monitoring
    - Order state machine
    """

    def __init__(self, config: Config, event_bus: EventBus, broker: ZerodhaBroker):
        self.config = config
        self.event_bus = event_bus
        self.broker = broker
        self.db_path = config.state_dir / "execution.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Order tracking
        self._active_orders: Dict[str, OrderState] = {}

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)
        self.event_bus.subscribe(EventType.RISK_BREACH, self)

    async def initialize(self) -> None:
        """Initialize the execution service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            await self._load_active_orders()
            logger.info("Execution service initialized")

    async def _create_tables(self) -> None:
        """Create execution database tables."""
        schema = """
        -- Orders
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            broker_order_id TEXT,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            order_type TEXT NOT NULL,
            product TEXT NOT NULL,
            price REAL,
            trigger_price REAL,
            status TEXT NOT NULL,
            filled_quantity INTEGER DEFAULT 0,
            remaining_quantity INTEGER,
            average_price REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Order commands
        CREATE TABLE IF NOT EXISTS order_commands (
            id INTEGER PRIMARY KEY,
            order_id TEXT NOT NULL,
            command_type TEXT NOT NULL,
            command_data TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        -- Execution reports
        CREATE TABLE IF NOT EXISTS execution_reports (
            id INTEGER PRIMARY KEY,
            order_id TEXT NOT NULL,
            broker_order_id TEXT,
            status TEXT NOT NULL,
            fills TEXT,
            avg_price REAL,
            slippage_bps REAL,
            received_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_broker_id ON orders(broker_order_id);
        CREATE INDEX IF NOT EXISTS idx_reports_order_id ON execution_reports(order_id);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _load_active_orders(self) -> None:
        """Load active orders from database."""
        cursor = await self._db_connection.execute("""
            SELECT id, broker_order_id, symbol, quantity, order_type, product, price,
                   trigger_price, status, filled_quantity, remaining_quantity, average_price,
                   created_at, updated_at
            FROM orders
            WHERE status IN ('pending', 'placed', 'partial_fill')
        """)

        async for row in cursor:
            order_state = OrderState(
                order_id=row[0],
                broker_order_id=row[1],
                symbol=row[2],
                quantity=row[3],
                status=OrderStatus(row[8]),
                filled_quantity=row[9] or 0,
                remaining_quantity=row[10] or row[3],
                average_price=row[11],
                created_at=row[12]
            )
            order_state.updated_at = row[13]
            self._active_orders[row[0]] = order_state

    async def place_order(self, order_command: OrderCommand) -> str:
        """Place an order through the broker."""
        async with self._lock:
            # Generate internal order ID
            order_id = f"order_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{order_command.symbol}"

            # Create order state
            order_state = OrderState(
                order_id=order_id,
                broker_order_id=None,
                status=OrderStatus.PENDING,
                symbol=order_command.symbol,
                quantity=order_command.qty or 0
            )
            self._active_orders[order_id] = order_state

            # Save to database
            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute("""
                INSERT INTO orders
                (id, symbol, quantity, order_type, product, price, trigger_price, status,
                 remaining_quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                order_command.symbol,
                order_command.qty,
                order_command.order_type,
                order_command.product,
                order_command.price,
                order_command.trigger_price,
                order_state.status.value,
                order_state.remaining_quantity,
                now,
                now
            ))

            # Save order command
            await self._db_connection.execute("""
                INSERT INTO order_commands (order_id, command_type, command_data, executed_at)
                VALUES (?, ?, ?, ?)
            """, (
                order_id,
                order_command.type,
                json.dumps(order_command.to_dict()),
                now
            ))

            await self._db_connection.commit()

            # Publish order placed event
            await self.event_bus.publish(Event(
                id=f"order_placed_{order_id}",
                type=EventType.EXECUTION_ORDER_PLACED,
                timestamp=now,
                source="execution_service",
                data={
                    "order_id": order_id,
                    "symbol": order_command.symbol,
                    "quantity": order_command.qty,
                    "order_type": order_command.order_type,
                    "price": order_command.price
                }
            ))

            # Submit to broker (async)
            asyncio.create_task(self._submit_to_broker(order_id, order_command))

            logger.info(f"Order placed: {order_id} for {order_command.symbol}")
            return order_id

    async def _submit_to_broker(self, order_id: str, order_command: OrderCommand) -> None:
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
                        order_state = self._active_orders[order_id]
                        order_state.broker_order_id = broker_order_id
                        order_state.status = OrderStatus.PLACED
                        order_state.updated_at = datetime.now(timezone.utc).isoformat()

                        # Update database
                        await self._db_connection.execute("""
                            UPDATE orders SET broker_order_id = ?, status = ?, updated_at = ?
                            WHERE id = ?
                        """, (broker_order_id, order_state.status.value, order_state.updated_at, order_id))
                        await self._db_connection.commit()

                logger.info(f"Order {order_id} submitted to broker: {broker_order_id}")
            else:
                await self._handle_order_rejection(order_id, broker_response.get("message", "Unknown error"))

        except Exception as e:
            logger.error(f"Failed to submit order {order_id} to broker: {e}")
            await self._handle_order_rejection(order_id, str(e))

    def _convert_to_broker_format(self, order_command: OrderCommand) -> Dict[str, Any]:
        """Convert internal order command to broker API format."""
        # This would map internal format to Zerodha API format
        return {
            "tradingsymbol": order_command.symbol,
            "exchange": "NSE",  # Default
            "transaction_type": order_command.side,
            "order_type": order_command.order_type,
            "quantity": order_command.qty,
            "product": order_command.product,
            "price": order_command.price,
            "trigger_price": order_command.trigger_price,
            "validity": order_command.tif,
            "variety": order_command.variety
        }

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        async with self._lock:
            if order_id not in self._active_orders:
                return False

            order_state = self._active_orders[order_id]

            if order_state.broker_order_id:
                # Cancel with broker
                try:
                    cancel_result = await self.broker.cancel_order(
                        order_id=order_state.broker_order_id,
                        variety="regular"  # Default
                    )

                    if cancel_result.get("status") == "success":
                        await self._update_order_status(order_id, OrderStatus.CANCELLED)
                        return True
                    else:
                        logger.error(f"Failed to cancel order {order_id}: {cancel_result}")
                        return False

                except Exception as e:
                    logger.error(f"Error cancelling order {order_id}: {e}")
                    return False
            else:
                # Cancel locally if not submitted to broker yet
                await self._update_order_status(order_id, OrderStatus.CANCELLED)
                return True

    async def _update_order_status(self, order_id: str, status: OrderStatus) -> None:
        """Update order status."""
        async with self._lock:
            if order_id in self._active_orders:
                order_state = self._active_orders[order_id]
                order_state.status = status
                order_state.updated_at = datetime.now(timezone.utc).isoformat()

                await self._db_connection.execute("""
                    UPDATE orders SET status = ?, updated_at = ? WHERE id = ?
                """, (status.value, order_state.updated_at, order_id))
                await self._db_connection.commit()

                # Publish status change event
                await self.event_bus.publish(Event(
                    id=f"order_status_{order_id}_{status.value}",
                    type=EventType.EXECUTION_ORDER_CANCELLED if status == OrderStatus.CANCELLED
                         else EventType.EXECUTION_ORDER_REJECTED if status == OrderStatus.REJECTED
                         else EventType.EXECUTION_ORDER_FILLED,
                    timestamp=order_state.updated_at,
                    source="execution_service",
                    data={
                        "order_id": order_id,
                        "broker_order_id": order_state.broker_order_id,
                        "status": status.value,
                        "symbol": order_state.symbol
                    }
                ))

    async def _handle_order_rejection(self, order_id: str, reason: str) -> None:
        """Handle order rejection."""
        await self._update_order_status(order_id, OrderStatus.REJECTED)

        # Create execution report for rejection
        report = ExecutionReport(
            broker_order_id=None,
            status="REJECTED",
            received_at=datetime.now(timezone.utc).isoformat()
        )

        await self._save_execution_report(order_id, report)
        logger.warning(f"Order {order_id} rejected: {reason}")

    async def _save_execution_report(self, order_id: str, report: ExecutionReport) -> None:
        """Save execution report to database."""
        await self._db_connection.execute("""
            INSERT INTO execution_reports
            (order_id, broker_order_id, status, fills, avg_price, slippage_bps, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            report.broker_order_id,
            report.status,
            json.dumps(report.fills) if report.fills else None,
            report.avg_price,
            report.slippage_bps,
            report.received_at
        ))
        await self._db_connection.commit()

    async def get_order_status(self, order_id: str) -> Optional[OrderState]:
        """Get order status."""
        async with self._lock:
            return self._active_orders.get(order_id)

    async def get_active_orders(self) -> List[OrderState]:
        """Get all active orders."""
        async with self._lock:
            return list(self._active_orders.values())

    async def check_order_updates(self) -> None:
        """Check for order status updates from broker."""
        # This would poll the broker API for order status updates
        # In a real implementation, this would be called periodically
        pass

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.EXECUTION_ORDER_PLACED:
            # Order placement confirmation
            pass
        elif event.type == EventType.RISK_BREACH:
            # Handle risk breach - might need to cancel orders
            data = event.data
            if data.get("severity") == "high":
                logger.warning("High severity risk breach - checking for order cancellation needs")

    async def close(self) -> None:
        """Close the execution service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None