"""
Portfolio Service

Manages current positions, cash, and portfolio calculations.
Provides portfolio snapshots, P&L calculations, and exposure tracking.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiosqlite
from loguru import logger

from src.config import Config

from ..core.event_bus import Event, EventBus, EventHandler, EventType
from ..core.state_models import PortfolioState


@dataclass
class PortfolioUpdate:
    """Portfolio update data."""

    symbol: str
    quantity_change: float
    price: float
    transaction_type: str  # "BUY", "SELL"
    timestamp: str


class PortfolioService(EventHandler):
    """
    Portfolio Service - manages portfolio state and calculations.

    Responsibilities:
    - Portfolio state management
    - P&L calculations
    - Exposure tracking
    - Position updates
    - Portfolio event publishing
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "portfolio.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.PORTFOLIO_CASH_CHANGE, self)

    async def initialize(self) -> None:
        """Initialize the portfolio service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            logger.info("Portfolio service initialized")

    async def _create_tables(self) -> None:
        """Create portfolio database tables."""
        schema = """
        -- Portfolio snapshots
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY,
            as_of TEXT NOT NULL,
            cash TEXT NOT NULL,
            holdings TEXT NOT NULL,
            exposure_total REAL NOT NULL,
            risk_aggregates TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Portfolio transactions
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            order_id TEXT,
            created_at TEXT NOT NULL
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_snapshots_as_of ON portfolio_snapshots(as_of);
        CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON portfolio_transactions(symbol);
        CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON portfolio_transactions(timestamp);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        async with self._lock:
            cursor = await self._db_connection.execute(
                """
                SELECT as_of, cash, holdings, exposure_total, risk_aggregates
                FROM portfolio_snapshots
                ORDER BY created_at DESC LIMIT 1
            """
            )
            row = await cursor.fetchone()

            if row:
                return PortfolioState(
                    as_of=row[0],
                    cash=json.loads(row[1]),
                    holdings=json.loads(row[2]),
                    exposure_total=row[3],
                    risk_aggregates=json.loads(row[4]),
                )
            return None

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute(
                """
                INSERT INTO portfolio_snapshots
                (as_of, cash, holdings, exposure_total, risk_aggregates, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    portfolio.as_of,
                    json.dumps(portfolio.cash),
                    json.dumps(portfolio.holdings),
                    portfolio.exposure_total,
                    json.dumps(portfolio.risk_aggregates),
                    now,
                ),
            )
            await self._db_connection.commit()

            # Publish portfolio update event
            await self.event_bus.publish(
                Event(
                    id=f"portfolio_update_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.PORTFOLIO_PNL_UPDATE,
                    timestamp=now,
                    source="portfolio_service",
                    data={
                        "portfolio": portfolio.to_dict(),
                        "exposure_total": portfolio.exposure_total,
                    },
                )
            )

            logger.info(f"Portfolio updated as of {portfolio.as_of}")

    async def record_transaction(self, update: PortfolioUpdate) -> None:
        """Record a portfolio transaction."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute(
                """
                INSERT INTO portfolio_transactions
                (symbol, quantity, price, transaction_type, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    update.symbol,
                    update.quantity_change,
                    update.price,
                    update.transaction_type,
                    update.timestamp,
                    now,
                ),
            )
            await self._db_connection.commit()

            logger.debug(
                f"Recorded transaction: {update.symbol} {update.transaction_type} {update.quantity_change}"
            )

    async def calculate_pnl(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Calculate P&L for portfolio or specific symbol."""
        async with self._lock:
            if symbol:
                # Calculate P&L for specific symbol
                cursor = await self._db_connection.execute(
                    """
                    SELECT
                        SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE 0 END) as buy_qty,
                        SUM(CASE WHEN transaction_type = 'SELL' THEN quantity ELSE 0 END) as sell_qty,
                        AVG(CASE WHEN transaction_type = 'BUY' THEN price END) as avg_buy_price,
                        AVG(CASE WHEN transaction_type = 'SELL' THEN price END) as avg_sell_price
                    FROM portfolio_transactions
                    WHERE symbol = ?
                """,
                    (symbol,),
                )

                row = await cursor.fetchone()
                if row:
                    buy_qty, sell_qty, avg_buy_price, avg_sell_price = row
                    net_qty = (buy_qty or 0) - (sell_qty or 0)

                    return {
                        "symbol": symbol,
                        "net_quantity": net_qty,
                        "avg_buy_price": avg_buy_price,
                        "avg_sell_price": avg_sell_price,
                        "unrealized_pnl": 0.0,  # Would need current price
                    }
            else:
                # Calculate total portfolio P&L
                cursor = await self._db_connection.execute(
                    """
                    SELECT symbol, SUM(quantity) as net_qty
                    FROM portfolio_transactions
                    GROUP BY symbol
                    HAVING net_qty != 0
                """
                )

                positions = {}
                async for row in cursor:
                    positions[row[0]] = row[1]

                return {
                    "total_positions": len(positions),
                    "positions": positions,
                    "total_pnl": 0.0,  # Would need current prices
                }

            return {}

    async def get_exposure(self) -> Dict[str, Any]:
        """Get current portfolio exposure."""
        portfolio = await self.get_portfolio()
        if not portfolio:
            return {"total_exposure": 0.0, "exposure_breakdown": {}}

        return {
            "total_exposure": portfolio.exposure_total,
            "exposure_breakdown": portfolio.risk_aggregates,
            "as_of": portfolio.as_of,
        }

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.EXECUTION_ORDER_FILLED:
            await self._handle_order_fill(event)
        elif event.type == EventType.PORTFOLIO_CASH_CHANGE:
            await self._handle_cash_change(event)

    async def _handle_order_fill(self, event: Event) -> None:
        """Handle order fill event."""
        data = event.data
        symbol = data.get("symbol")
        quantity = data.get("quantity", 0)
        price = data.get("price", 0)
        side = data.get("side", "BUY")

        if symbol and quantity and price:
            # Record the transaction
            transaction = PortfolioUpdate(
                symbol=symbol,
                quantity_change=quantity if side == "BUY" else -quantity,
                price=price,
                transaction_type=side,
                timestamp=event.timestamp,
            )
            await self.record_transaction(transaction)

            # Update portfolio (this would be more complex in real implementation)
            # For now, just log the event
            logger.info(f"Portfolio updated for {symbol} {side} {quantity} @ {price}")

    async def _handle_cash_change(self, event: Event) -> None:
        """Handle cash change event."""
        data = event.data
        amount = data.get("amount", 0)
        reason = data.get("reason", "unknown")

        logger.info(f"Cash change: {amount} for {reason}")

        # Update portfolio cash balance
        # This would require getting current portfolio and updating cash

    async def close(self) -> None:
        """Close the portfolio service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
