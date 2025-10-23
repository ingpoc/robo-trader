"""
Live Position Service

Handles live position tracking, P&L calculation, and market data integration.
Provides focused position management with proper dependency injection.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiosqlite
from loguru import logger

from ..config import Config
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError, APIError
from ..mcp.broker import ZerodhaBroker


@dataclass
class LivePosition:
    """Live position tracking."""
    symbol: str
    quantity: int
    average_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    market_value: float = 0.0
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now(timezone.utc).isoformat()


class LivePositionService(EventHandler):
    """
    Live Position Service - Focused position tracking and P&L management.

    Responsibilities:
    - Position tracking and updates
    - Real-time P&L calculation
    - Market data integration
    - Position synchronization with broker
    """

    def __init__(self, config: Config, event_bus: EventBus, broker: ZerodhaBroker, db_connection: aiosqlite.Connection):
        self.config = config
        self.event_bus = event_bus
        self.broker = broker
        self.db = db_connection
        self._lock = asyncio.Lock()

        # Position state
        self._positions: Dict[str, LivePosition] = {}

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)

    async def initialize(self) -> None:
        """Initialize the position service."""
        async with self._lock:
            await self._load_positions()
            logger.info("Live position service initialized")

    async def _load_positions(self) -> None:
        """Load positions from database."""
        cursor = await self.db.execute("""
            SELECT symbol, quantity, average_price, current_price, unrealized_pnl,
                   realized_pnl, market_value, last_updated
            FROM live_positions
        """)

        async for row in cursor:
            position = LivePosition(
                symbol=row[0],
                quantity=row[1],
                average_price=row[2],
                current_price=row[3],
                unrealized_pnl=row[4] or 0.0,
                realized_pnl=row[5] or 0.0,
                market_value=row[6] or 0.0,
                last_updated=row[7]
            )
            self._positions[row[0]] = position

    async def update_positions_from_broker(self, correlation_id: str) -> None:
        """Update positions from broker API."""
        try:
            if not self.broker.is_authenticated():
                logger.warning("Broker not authenticated, skipping position update")
                return

            # Get positions from broker
            positions_data = await self.broker.get_portfolio()

            async with self._lock:
                updated_positions = []

                for position_data in positions_data.get("positions", []):
                    symbol = position_data.get("tradingsymbol")
                    if not symbol:
                        continue

                    quantity = position_data.get("quantity", 0)
                    average_price = position_data.get("average_price", 0)

                    # Update or create position
                    if symbol in self._positions:
                        position = self._positions[symbol]
                        position.quantity = quantity
                        position.average_price = average_price
                        position.last_updated = datetime.now(timezone.utc).isoformat()
                    else:
                        position = LivePosition(
                            symbol=symbol,
                            quantity=quantity,
                            average_price=average_price
                        )
                        self._positions[symbol] = position

                    # Update database
                    await self.db.execute("""
                        INSERT OR REPLACE INTO live_positions
                        (symbol, quantity, average_price, last_updated)
                        VALUES (?, ?, ?, ?)
                    """, (symbol, quantity, average_price, position.last_updated))

                    updated_positions.append(symbol)

                await self.db.commit()

                # Emit position update event
                await self.event_bus.publish(Event(
                    id=f"positions_updated_{datetime.now(timezone.utc).timestamp()}",
                    type=EventType.MARKET_PRICE_UPDATE,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="live_position_service",
                    correlation_id=correlation_id,
                    data={
                        "updated_positions": updated_positions,
                        "total_positions": len(self._positions)
                    }
                ))

            logger.info(f"Updated {len(updated_positions)} positions from broker")

        except Exception as e:
            logger.error(f"Failed to update positions from broker: {e}")
            await self.event_bus.publish(Event(
                id=f"position_update_error_{datetime.now(timezone.utc).timestamp()}",
                type=EventType.SYSTEM_ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="live_position_service",
                correlation_id=correlation_id,
                data={"error": str(e), "operation": "position_update"}
            ))

    async def update_market_prices(self, price_updates: Dict[str, float], correlation_id: str) -> None:
        """Update market prices and recalculate P&L."""
        async with self._lock:
            updated_positions = []

            for symbol, price in price_updates.items():
                if symbol in self._positions:
                    position = self._positions[symbol]
                    position.current_price = price
                    position.market_value = position.quantity * price
                    position.unrealized_pnl = (price - position.average_price) * position.quantity
                    position.last_updated = datetime.now(timezone.utc).isoformat()

                    # Update database
                    await self.db.execute("""
                        UPDATE live_positions SET
                        current_price = ?, market_value = ?, unrealized_pnl = ?, last_updated = ?
                        WHERE symbol = ?
                    """, (price, position.market_value, position.unrealized_pnl,
                          position.last_updated, symbol))

                    updated_positions.append(symbol)

            if updated_positions:
                await self.db.commit()

                # Emit P&L update event
                await self.event_bus.publish(Event(
                    id=f"pnl_updated_{datetime.now(timezone.utc).timestamp()}",
                    type=EventType.MARKET_PRICE_UPDATE,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="live_position_service",
                    correlation_id=correlation_id,
                    data={
                        "updated_positions": updated_positions,
                        "total_unrealized_pnl": sum(p.unrealized_pnl for p in self._positions.values())
                    }
                ))

                logger.debug(f"Updated prices for {len(updated_positions)} positions")

    async def get_positions(self) -> Dict[str, LivePosition]:
        """Get current live positions."""
        async with self._lock:
            return self._positions.copy()

    async def get_position(self, symbol: str) -> Optional[LivePosition]:
        """Get position for a specific symbol."""
        async with self._lock:
            return self._positions.get(symbol)

    async def update_position_from_fill(self, symbol: str, quantity: int, price: float,
                                      side: str, correlation_id: str) -> None:
        """Update position based on order fill."""
        async with self._lock:
            if symbol not in self._positions:
                # Create new position
                self._positions[symbol] = LivePosition(
                    symbol=symbol,
                    quantity=quantity if side == "BUY" else -quantity,
                    average_price=price
                )
            else:
                # Update existing position
                position = self._positions[symbol]

                if side == "BUY":
                    # Calculate new average price for buy
                    total_value = (position.quantity * position.average_price) + (quantity * price)
                    total_quantity = position.quantity + quantity
                    position.average_price = total_value / total_quantity if total_quantity != 0 else price
                    position.quantity = total_quantity
                else:
                    # For sell, update realized P&L
                    realized_pnl = (price - position.average_price) * min(quantity, abs(position.quantity))
                    position.realized_pnl += realized_pnl
                    position.quantity -= quantity

                    # Remove position if fully closed
                    if position.quantity == 0:
                        del self._positions[symbol]
                        await self.db.execute("DELETE FROM live_positions WHERE symbol = ?", (symbol,))
                    else:
                        await self.db.execute("""
                            UPDATE live_positions SET quantity = ?, realized_pnl = ?, last_updated = ?
                            WHERE symbol = ?
                        """, (position.quantity, position.realized_pnl,
                              datetime.now(timezone.utc).isoformat(), symbol))

                await self.db.commit()

                # Emit position change event
                await self.event_bus.publish(Event(
                    id=f"position_changed_{symbol}_{datetime.now(timezone.utc).timestamp()}",
                    type=EventType.EXECUTION_ORDER_FILLED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="live_position_service",
                    correlation_id=correlation_id,
                    data={
                        "symbol": symbol,
                        "quantity": position.quantity if symbol in self._positions else 0,
                        "average_price": position.average_price if symbol in self._positions else 0,
                        "realized_pnl": position.realized_pnl if symbol in self._positions else 0
                    }
                ))

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with total P&L."""
        async with self._lock:
            total_unrealized_pnl = sum(p.unrealized_pnl for p in self._positions.values())
            total_realized_pnl = sum(p.unrealized_pnl for p in self._positions.values())
            total_market_value = sum(p.market_value for p in self._positions.values())

            return {
                "total_positions": len(self._positions),
                "total_market_value": total_market_value,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_realized_pnl": total_realized_pnl,
                "total_pnl": total_unrealized_pnl + total_realized_pnl,
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "average_price": p.average_price,
                        "current_price": p.current_price,
                        "market_value": p.market_value,
                        "unrealized_pnl": p.unrealized_pnl,
                        "realized_pnl": p.realized_pnl
                    }
                    for p in self._positions.values()
                ]
            }

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.MARKET_PRICE_UPDATE:
            # Update market prices
            prices = event.data.get("prices", {})
            await self.update_market_prices(prices, event.correlation_id or "")

        elif event.type == EventType.EXECUTION_ORDER_FILLED:
            # Update position from order fill
            order_data = event.data
            if all(k in order_data for k in ["symbol", "quantity", "price", "side"]):
                await self.update_position_from_fill(
                    order_data["symbol"],
                    order_data["quantity"],
                    order_data["price"],
                    order_data["side"],
                    event.correlation_id or ""
                )

    async def close(self) -> None:
        """Close the position service."""
        pass