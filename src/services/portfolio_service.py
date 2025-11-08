"""
Portfolio Service

Manages current positions, cash, and portfolio calculations.
Provides portfolio snapshots, P&L calculations, and exposure tracking.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import aiosqlite
from loguru import logger

from src.config import Config
from ..core.state_models import PortfolioState
from ..core.event_bus import EventBus, Event, EventType, EventHandler


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
            cursor = await self._db_connection.execute("""
                SELECT as_of, cash, holdings, exposure_total, risk_aggregates
                FROM portfolio_snapshots
                ORDER BY created_at DESC LIMIT 1
            """)
            row = await cursor.fetchone()

            if row:
                return PortfolioState(
                    as_of=row[0],
                    cash=json.loads(row[1]),
                    holdings=json.loads(row[2]),
                    exposure_total=row[3],
                    risk_aggregates=json.loads(row[4])
                )
            return None

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute("""
                INSERT INTO portfolio_snapshots
                (as_of, cash, holdings, exposure_total, risk_aggregates, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                portfolio.as_of,
                json.dumps(portfolio.cash),
                json.dumps(portfolio.holdings),
                portfolio.exposure_total,
                json.dumps(portfolio.risk_aggregates),
                now
            ))
            await self._db_connection.commit()

            # Publish portfolio update event
            await self.event_bus.publish(Event(
                id=f"portfolio_update_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.PORTFOLIO_PNL_UPDATE,
                timestamp=now,
                source="portfolio_service",
                data={
                    "portfolio": portfolio.to_dict(),
                    "exposure_total": portfolio.exposure_total
                }
            ))

            logger.info(f"Portfolio updated as of {portfolio.as_of}")

    async def record_transaction(self, update: PortfolioUpdate) -> None:
        """Record a portfolio transaction."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute("""
                INSERT INTO portfolio_transactions
                (symbol, quantity, price, transaction_type, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                update.symbol,
                update.quantity_change,
                update.price,
                update.transaction_type,
                update.timestamp,
                now
            ))
            await self._db_connection.commit()

            logger.debug(f"Recorded transaction: {update.symbol} {update.transaction_type} {update.quantity_change}")

    async def calculate_pnl(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Calculate P&L for portfolio or specific symbol."""
        async with self._lock:
            if symbol:
                # Calculate P&L for specific symbol
                cursor = await self._db_connection.execute("""
                    SELECT
                        SUM(CASE WHEN transaction_type = 'BUY' THEN quantity ELSE 0 END) as buy_qty,
                        SUM(CASE WHEN transaction_type = 'SELL' THEN quantity ELSE 0 END) as sell_qty,
                        AVG(CASE WHEN transaction_type = 'BUY' THEN price END) as avg_buy_price,
                        AVG(CASE WHEN transaction_type = 'SELL' THEN price END) as avg_sell_price
                    FROM portfolio_transactions
                    WHERE symbol = ?
                """, (symbol,))

                row = await cursor.fetchone()
                if row:
                    buy_qty, sell_qty, avg_buy_price, avg_sell_price = row
                    net_qty = (buy_qty or 0) - (sell_qty or 0)

                    return {
                        "symbol": symbol,
                        "net_quantity": net_qty,
                        "avg_buy_price": avg_buy_price,
                        "avg_sell_price": avg_sell_price,
                        "unrealized_pnl": 0.0  # Would need current price
                    }
            else:
                # Calculate total portfolio P&L
                cursor = await self._db_connection.execute("""
                    SELECT symbol, SUM(quantity) as net_qty
                    FROM portfolio_transactions
                    GROUP BY symbol
                    HAVING net_qty != 0
                """)

                positions = {}
                async for row in cursor:
                    positions[row[0]] = row[1]

                return {
                    "total_positions": len(positions),
                    "positions": positions,
                    "total_pnl": 0.0  # Would need current prices
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
            "as_of": portfolio.as_of
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
                timestamp=event.timestamp
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

    async def sync_account_balances(self) -> Dict[str, Any]:
        """Synchronize account balances from broker API."""
        try:
            logger.info("Syncing account balances from broker")

            # For now, return placeholder implementation
            # In production, this would:
            # 1. Call broker API for current balances
            # 2. Update portfolio state with new data
            # 3. Emit balance change events

            result = {
                "status": "completed",
                "cash_balance": 100000.0,  # placeholder value
                "margin_used": 0.0,
                "margin_available": 100000.0,
                "collateral": 0.0,
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                "broker": "placeholder"  # Would use actual broker name
            }

            # Emit event for balance change
            await self.event_bus.publish(Event(
                id=f"balance_sync_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.PORTFOLIO_CASH_CHANGE,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source=self.__class__.__name__,
                data={
                    "amount": result["cash_balance"],
                    "reason": "sync_account_balances"
                }
            ))

            logger.info(f"Account balance sync completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error syncing account balances: {e}")
            from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
            raise TradingError(
                f"Account balance sync failed: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=60
            )

    async def validate_portfolio_risks(self) -> Dict[str, Any]:
        """Validate current portfolio risk levels."""
        try:
            logger.info("Processing portfolio risk validation")

            # Get current portfolio
            portfolio = await self.get_portfolio()
            if not portfolio:
                return {"status": "skipped", "reason": "no_portfolio"}

            # Calculate current exposure
            total_exposure = sum(
                pos.quantity * pos.current_price
                for pos in portfolio.positions.values()
            )

            # Risk validation logic
            risk_assessment = {
                "status": "completed",
                "total_exposure": total_exposure,
                "sector_concentration": {},  # Calculate sector concentration
                "position_size_risk": {},    # Check position sizes
                "liquidity_risk": {},        # Assess liquidity
                "overall_risk_score": 0.0,   # Calculate risk score (0-100)
                "risk_warnings": [],         # List of risk warnings
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Simple risk calculations (placeholder)
            if total_exposure > 50000:  # Example threshold
                risk_assessment["risk_warnings"].append("High portfolio exposure")
                risk_assessment["overall_risk_score"] = min(80, total_exposure / 1000)

            if total_exposure > 100000:  # Critical threshold
                risk_assessment["risk_warnings"].append("Critical portfolio exposure")
                risk_assessment["overall_risk_score"] = min(95, total_exposure / 500)

            # Check position concentrations
            large_positions = [
                pos for pos in portfolio.positions.values()
                if abs(pos.quantity * pos.current_price) > 10000
            ]
            if large_positions:
                risk_assessment["risk_warnings"].append(f"{len(large_positions)} large positions")
                risk_assessment["position_size_risk"] = True

            logger.info(f"Portfolio risk validation completed: {risk_assessment}")
            return risk_assessment

        except Exception as e:
            logger.error(f"Error validating portfolio risks: {e}")
            from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
            raise TradingError(
                f"Portfolio risk validation failed: {e}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def close(self) -> None:
        """Close the portfolio service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None