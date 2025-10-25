"""
Portfolio state management for Robo Trader.

Handles portfolio CRUD operations with database persistence and caching.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from src.core.state_models import PortfolioState
from src.core.event_bus import EventBus, Event, EventType
from .base import DatabaseConnection


class PortfolioStateManager:
    """
    Manages portfolio state with database persistence and event emissions.

    Responsibilities:
    - Get/update portfolio state
    - Cache portfolio in memory for performance
    - Emit events on portfolio changes
    - Thread-safe operations with async locks
    """

    def __init__(self, db: DatabaseConnection, event_bus: Optional[EventBus] = None):
        """
        Initialize portfolio state manager.

        Args:
            db: Database connection manager
            event_bus: Optional event bus for emitting portfolio changes
        """
        self.db = db
        self.event_bus = event_bus
        self._portfolio: Optional[PortfolioState] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load initial portfolio state from database."""
        await self._load_portfolio()

    async def _load_portfolio(self) -> None:
        """Load portfolio from database into memory cache."""
        async with self._lock:
            async with self.db.connection.execute(
                "SELECT * FROM portfolio ORDER BY updated_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    self._portfolio = PortfolioState(
                        as_of=row[1],
                        cash=json.loads(row[2]),
                        holdings=json.loads(row[3]),
                        exposure_total=row[4],
                        risk_aggregates=json.loads(row[5])
                    )
                    logger.info(f"Portfolio loaded: {len(self._portfolio.holdings)} holdings")

    async def get_portfolio(self) -> Optional[PortfolioState]:
        """
        Get current portfolio state.

        Returns:
            PortfolioState if available, None otherwise
        """
        async with self._lock:
            return self._portfolio

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """
        Update portfolio state in database and cache.

        Emits PORTFOLIO_UPDATED event if event bus is available.

        Args:
            portfolio: New portfolio state to save
        """
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self._portfolio = portfolio

            # Save to database
            async with self.db.connection.execute("""
                INSERT OR REPLACE INTO portfolio
                (id, as_of, cash, holdings, exposure_total, risk_aggregates, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio.as_of,
                json.dumps(portfolio.cash),
                json.dumps(portfolio.holdings),
                portfolio.exposure_total,
                json.dumps(portfolio.risk_aggregates),
                now,
                now
            )):
                await self.db.connection.commit()

            logger.info(f"Portfolio updated as of {portfolio.as_of}")

            # Emit event if event bus available
            if self.event_bus:
                await self._emit_portfolio_updated(portfolio)

    async def _emit_portfolio_updated(self, portfolio: PortfolioState) -> None:
        """
        Emit portfolio updated event.

        Args:
            portfolio: Portfolio state that was updated
        """
        try:
            event = Event(
                type=EventType.PORTFOLIO_UPDATED,
                source="PortfolioStateManager",
                data={
                    "as_of": portfolio.as_of,
                    "exposure_total": portfolio.exposure_total,
                    "holdings_count": len(portfolio.holdings),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await self.event_bus.emit(event)
            logger.debug("Portfolio updated event emitted")
        except Exception as e:
            logger.warning(f"Failed to emit portfolio updated event: {e}")
