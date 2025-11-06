"""
Market monitoring service.

Tracks market hours and status (IST timezone aware).
"""

from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from loguru import logger


class MarketMonitor:
    """Monitors market status and market hours."""

    IST_MARKET_OPEN = time(9, 15)
    IST_MARKET_CLOSE = time(15, 30)

    def __init__(self):
        """Initialize market monitor."""
        self.market_open = False
        self.last_check = None
        self._on_market_open: Optional[Callable] = None
        self._on_market_close: Optional[Callable] = None

    def set_market_open_callback(self, callback: Callable) -> None:
        """Set callback for market open event.

        Args:
            callback: Async callable to invoke on market open
        """
        self._on_market_open = callback

    def set_market_close_callback(self, callback: Callable) -> None:
        """Set callback for market close event.

        Args:
            callback: Async callable to invoke on market close
        """
        self._on_market_close = callback

    def is_market_open(self) -> bool:
        """Check if market is currently open.

        Returns:
            True if market is open, False otherwise
        """
        return self.market_open

    async def check_market_status(self) -> Dict[str, Any]:
        """Check market status and trigger events if status changed.

        Returns:
            Dictionary with market status information
        """
        now = datetime.now(timezone.utc)
        ist_time = now + timedelta(hours=5, minutes=30)
        current_time = ist_time.time()

        was_open = self.market_open
        self.market_open = (
            ist_time.weekday() < 5
            and self.IST_MARKET_OPEN <= current_time <= self.IST_MARKET_CLOSE
        )

        self.last_check = now

        if self.market_open and not was_open:
            logger.info("Market opened")
            if self._on_market_open:
                await self._on_market_open()

        elif not self.market_open and was_open:
            logger.info("Market closed")
            if self._on_market_close:
                await self._on_market_close()

        return {
            "market_open": self.market_open,
            "ist_time": ist_time.isoformat(),
            "last_check": now.isoformat(),
            "market_open_time": self.IST_MARKET_OPEN.isoformat(),
            "market_close_time": self.IST_MARKET_CLOSE.isoformat(),
        }

    def get_next_market_open(self) -> datetime:
        """Get the next market open time (IST).

        Returns:
            datetime of next market open
        """
        now = datetime.now(timezone.utc)
        ist_time = now + timedelta(hours=5, minutes=30)

        next_open = ist_time.replace(
            hour=self.IST_MARKET_OPEN.hour,
            minute=self.IST_MARKET_OPEN.minute,
            second=0,
            microsecond=0,
        )

        if ist_time.time() >= self.IST_MARKET_OPEN:
            next_open += timedelta(days=1)

        while next_open.weekday() >= 5:
            next_open += timedelta(days=1)

        return next_open - timedelta(hours=5, minutes=30)

    def get_next_market_close(self) -> datetime:
        """Get the next market close time (IST).

        Returns:
            datetime of next market close
        """
        now = datetime.now(timezone.utc)
        ist_time = now + timedelta(hours=5, minutes=30)

        next_close = ist_time.replace(
            hour=self.IST_MARKET_CLOSE.hour,
            minute=self.IST_MARKET_CLOSE.minute,
            second=0,
            microsecond=0,
        )

        if ist_time.time() >= self.IST_MARKET_CLOSE:
            next_close += timedelta(days=1)

        while next_close.weekday() >= 5:
            next_close += timedelta(days=1)

        return next_close - timedelta(hours=5, minutes=30)

    def get_market_hours_remaining(self) -> int:
        """Get minutes remaining until market close.

        Returns:
            Minutes remaining until market close, or -1 if market is closed
        """
        if not self.market_open:
            return -1

        now = datetime.now(timezone.utc)
        ist_time = now + timedelta(hours=5, minutes=30)

        close_time = ist_time.replace(
            hour=self.IST_MARKET_CLOSE.hour,
            minute=self.IST_MARKET_CLOSE.minute,
            second=0,
            microsecond=0,
        )

        diff = (close_time - ist_time).total_seconds() / 60
        return int(max(0, diff))

    def is_trading_day(self) -> bool:
        """Check if today is a trading day (not weekend).

        Returns:
            True if today is a trading day, False otherwise
        """
        now = datetime.now(timezone.utc)
        ist_time = now + timedelta(hours=5, minutes=30)
        return ist_time.weekday() < 5
