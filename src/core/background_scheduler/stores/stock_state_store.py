"""Track per-stock scheduler state (last run times for each scheduler type)."""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class StockSchedulerState:
    """State for a single stock across all scheduler types."""
    symbol: str
    last_news_check: Optional[date] = None
    last_earnings_check: Optional[date] = None
    last_fundamentals_check: Optional[date] = None
    last_portfolio_update: Optional[datetime] = None
    last_analysis_check: Optional[datetime] = None  # For comprehensive stock analysis
    needs_fundamentals_recheck: bool = False
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "symbol": self.symbol,
            "last_news_check": self.last_news_check.isoformat() if self.last_news_check else None,
            "last_earnings_check": self.last_earnings_check.isoformat() if self.last_earnings_check else None,
            "last_fundamentals_check": self.last_fundamentals_check.isoformat() if self.last_fundamentals_check else None,
            "last_portfolio_update": self.last_portfolio_update.isoformat() if self.last_portfolio_update else None,
            "last_analysis_check": self.last_analysis_check.isoformat() if self.last_analysis_check else None,
            "needs_fundamentals_recheck": self.needs_fundamentals_recheck,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "StockSchedulerState":
        """Create from JSON dict."""
        return StockSchedulerState(
            symbol=data.get("symbol"),
            last_news_check=date.fromisoformat(data["last_news_check"]) if data.get("last_news_check") else None,
            last_earnings_check=date.fromisoformat(data["last_earnings_check"]) if data.get("last_earnings_check") else None,
            last_fundamentals_check=date.fromisoformat(data["last_fundamentals_check"]) if data.get("last_fundamentals_check") else None,
            last_portfolio_update=datetime.fromisoformat(data["last_portfolio_update"]) if data.get("last_portfolio_update") else None,
            last_analysis_check=datetime.fromisoformat(data["last_analysis_check"]) if data.get("last_analysis_check") else None,
            needs_fundamentals_recheck=data.get("needs_fundamentals_recheck", False),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class StockStateStore:
    """Persistent store for per-stock scheduler state."""

    def __init__(self, db_connection):
        """Initialize store with database connection.

        Args:
            db_connection: Active database connection
        """
        self.db = db_connection
        self._state: Dict[str, StockSchedulerState] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load state from database."""
        if self._initialized:
            return

        try:
            query = "SELECT * FROM stock_scheduler_state"
            cursor = await self.db.execute(query)
            rows = await cursor.fetchall()

            self._state = {}
            for row in rows:
                state = StockSchedulerState(
                    symbol=row[0],
                    last_news_check=row[1],
                    last_earnings_check=row[2],
                    last_fundamentals_check=row[3],
                    last_portfolio_update=row[4],
                    needs_fundamentals_recheck=row[5],
                    updated_at=row[6] or datetime.now().isoformat()
                )
                self._state[state.symbol] = state

            logger.info(f"Loaded stock scheduler state for {len(self._state)} stocks from database")
        except Exception as e:
            logger.error(f"Failed to load stock scheduler state from database: {e}")
            self._state = {}

        self._initialized = True

    async def get_state(self, symbol: str) -> StockSchedulerState:
        """Get state for a stock, create if doesn't exist."""
        if symbol not in self._state:
            self._state[symbol] = StockSchedulerState(symbol=symbol)
            await self._save_state(symbol)

        return self._state[symbol]

    async def update_news_check(self, symbol: str, check_date: Optional[date] = None) -> None:
        """Update last news check date for a stock."""
        state = await self.get_state(symbol)
        state.last_news_check = check_date or date.today()
        state.updated_at = datetime.now().isoformat()
        await self._save_state(symbol)
        logger.debug(f"Updated news check for {symbol}: {state.last_news_check}")

    async def update_earnings_check(self, symbol: str, check_date: Optional[date] = None) -> None:
        """Update last earnings check date for a stock."""
        state = await self.get_state(symbol)
        state.last_earnings_check = check_date or date.today()
        state.updated_at = datetime.now().isoformat()
        await self._save_state(symbol)
        logger.debug(f"Updated earnings check for {symbol}: {state.last_earnings_check}")

    async def update_fundamentals_check(self, symbol: str, check_date: Optional[date] = None) -> None:
        """Update last fundamentals check date for a stock."""
        state = await self.get_state(symbol)
        state.last_fundamentals_check = check_date or date.today()
        state.needs_fundamentals_recheck = False
        state.updated_at = datetime.now().isoformat()
        await self._save_state(symbol)
        logger.debug(f"Updated fundamentals check for {symbol}: {state.last_fundamentals_check}")

    async def flag_fundamentals_recheck(self, symbol: str) -> None:
        """Flag that fundamentals need rechecking due to material news."""
        state = await self.get_state(symbol)
        state.needs_fundamentals_recheck = True
        state.updated_at = datetime.now().isoformat()
        await self._save_state(symbol)
        logger.info(f"Flagged fundamentals recheck for {symbol} due to material news")

    async def update_analysis_check(self, symbol: str, check_time: Optional[datetime] = None) -> None:
        """Update last comprehensive analysis check time for a stock.

        Args:
            symbol: Stock symbol
            check_time: Analysis check time (defaults to current UTC time)
        """
        state = await self.get_state(symbol)
        state.last_analysis_check = check_time or datetime.now()
        state.updated_at = datetime.now().isoformat()
        await self._save_state(symbol)
        logger.debug(f"Updated analysis check for {symbol}: {state.last_analysis_check}")

    async def needs_news_fetch(self, symbol: str) -> bool:
        """Check if news needs fetching for this stock today."""
        state = await self.get_state(symbol)
        return state.last_news_check != date.today()

    async def needs_earnings_fetch(self, symbol: str) -> bool:
        """Check if earnings needs fetching for this stock."""
        state = await self.get_state(symbol)
        # First-run always needs fetch, then weekly
        if state.last_earnings_check is None:
            return True
        # Check if week has passed (7 days)
        days_since = (date.today() - state.last_earnings_check).days
        return days_since >= 7

    async def needs_fundamentals_check(self, symbol: str) -> bool:
        """Check if fundamentals need rechecking."""
        state = await self.get_state(symbol)
        # Recheck if flagged or weekly refresh
        if state.needs_fundamentals_recheck:
            return True
        if state.last_fundamentals_check is None:
            return True
        # Weekly refresh
        days_since = (date.today() - state.last_fundamentals_check).days
        return days_since >= 7

    async def get_stocks_needing_news(self, symbols: list) -> list:
        """Get list of stocks that need news fetch today."""
        result = []
        for symbol in symbols:
            if await self.needs_news_fetch(symbol):
                result.append(symbol)
        return result

    async def get_stocks_needing_earnings(self, symbols: list) -> list:
        """Get list of stocks that need earnings check."""
        result = []
        for symbol in symbols:
            if await self.needs_earnings_fetch(symbol):
                result.append(symbol)
        return result

    async def get_oldest_news_stocks(self, symbols: list, limit: int = 5) -> list:
        """Get stocks with oldest last_news_check date (prioritize by oldest first).
        
        None (never checked) stocks come first, then sorted by oldest date.
        """
        stocks_with_dates = []
        for symbol in symbols:
            state = await self.get_state(symbol)
            # Use date.min as sentinel for None to enable proper sorting
            check_date = state.last_news_check if state.last_news_check else date.min
            stocks_with_dates.append((symbol, state.last_news_check, check_date))

        # Sort: None first (check_date == date.min), then oldest dates (ascending)
        stocks_with_dates.sort(key=lambda x: (x[2] != date.min, x[2]))

        # Return top N symbols
        return [symbol for symbol, _, _ in stocks_with_dates[:limit]]

    async def get_oldest_earnings_stocks(self, symbols: list, limit: int = 5) -> list:
        """Get stocks with oldest last_earnings_check date (prioritize by oldest first).
        
        None (never checked) stocks come first, then sorted by oldest date.
        """
        stocks_with_dates = []
        for symbol in symbols:
            state = await self.get_state(symbol)
            # Use date.min as sentinel for None to enable proper sorting
            check_date = state.last_earnings_check if state.last_earnings_check else date.min
            stocks_with_dates.append((symbol, state.last_earnings_check, check_date))

        # Sort: None first (check_date == date.min), then oldest dates (ascending)
        stocks_with_dates.sort(key=lambda x: (x[2] != date.min, x[2]))

        # Return top N symbols
        return [symbol for symbol, _, _ in stocks_with_dates[:limit]]

    async def get_oldest_fundamentals_stocks(self, symbols: list, limit: int = 5) -> list:
        """Get stocks with oldest last_fundamentals_check date (prioritize by oldest first).
        
        None (never checked) stocks come first, then sorted by oldest date.
        """
        stocks_with_dates = []
        for symbol in symbols:
            state = await self.get_state(symbol)
            # Use date.min as sentinel for None to enable proper sorting
            check_date = state.last_fundamentals_check if state.last_fundamentals_check else date.min
            stocks_with_dates.append((symbol, state.last_fundamentals_check, check_date))

        # Sort: None first (check_date == date.min), then oldest dates (ascending)
        stocks_with_dates.sort(key=lambda x: (x[2] != date.min, x[2]))

        # Return top N symbols
        return [symbol for symbol, _, _ in stocks_with_dates[:limit]]

    async def _save_state(self, symbol: str) -> None:
        """Persist state for a symbol to database."""
        try:
            state = self._state[symbol]
            query = """
                INSERT INTO stock_scheduler_state (
                    symbol, last_news_check, last_earnings_check,
                    last_fundamentals_check, last_portfolio_update,
                    needs_fundamentals_recheck, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol) DO UPDATE SET
                    last_news_check = excluded.last_news_check,
                    last_earnings_check = excluded.last_earnings_check,
                    last_fundamentals_check = excluded.last_fundamentals_check,
                    last_portfolio_update = excluded.last_portfolio_update,
                    needs_fundamentals_recheck = excluded.needs_fundamentals_recheck,
                    updated_at = excluded.updated_at
            """

            await self.db.execute(
                query,
                (
                    state.symbol,
                    state.last_news_check,
                    state.last_earnings_check,
                    state.last_fundamentals_check,
                    state.last_portfolio_update,
                    state.needs_fundamentals_recheck,
                    state.updated_at
                ),
            )
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to save stock scheduler state for {symbol}: {e}")
            await self.db.rollback()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass