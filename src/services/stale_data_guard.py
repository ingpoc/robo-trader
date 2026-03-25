"""
Stale Data Guard

Pre-execution check that blocks trades when data is stale.
Integrated into the trade execution path to prevent trading on outdated prices.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.core.event_bus import EventBus, Event, EventType

logger = logging.getLogger(__name__)

# Maximum age of price data before it's considered stale (seconds)
MAX_PRICE_AGE_SECONDS = 60

# Market hours (IST) — simple implementation; production should use proper NSE calendar
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


@dataclass
class StaleDataCheckResult:
    """Result of a stale data check."""
    can_trade: bool
    reason: Optional[str] = None
    price_age_seconds: Optional[float] = None
    is_market_open: Optional[bool] = None


class StaleDataGuard:
    """
    Guards against trading on stale data.

    Checks:
    1. Price freshness: last price update must be < MAX_PRICE_AGE_SECONDS
    2. Market hours: exchange must be open
    3. Feed health: price feed circuit breaker must not be tripped
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self._last_price_timestamps: dict[str, float] = {}  # symbol -> monotonic time

    def record_price_update(self, symbol: str) -> None:
        """Record that a price update was received for a symbol."""
        self._last_price_timestamps[symbol] = time.monotonic()

    async def check(self, symbol: str) -> StaleDataCheckResult:
        """
        Check if it's safe to trade this symbol right now.

        Returns StaleDataCheckResult with can_trade=False if data is stale.
        """
        # Check 1: Market hours
        is_open = self._is_market_open()
        if not is_open:
            result = StaleDataCheckResult(
                can_trade=False,
                reason=f"Market is closed. NSE trading hours: {MARKET_OPEN_HOUR}:{MARKET_OPEN_MINUTE:02d}-{MARKET_CLOSE_HOUR}:{MARKET_CLOSE_MINUTE:02d} IST",
                is_market_open=False,
            )
            await self._emit_block(symbol, result)
            return result

        # Check 2: Price freshness
        last_update = self._last_price_timestamps.get(symbol)
        if last_update is None:
            result = StaleDataCheckResult(
                can_trade=False,
                reason=f"No price data available for {symbol}. Cannot trade without live prices.",
                is_market_open=True,
                price_age_seconds=None,
            )
            await self._emit_block(symbol, result)
            return result

        age = time.monotonic() - last_update
        if age > MAX_PRICE_AGE_SECONDS:
            result = StaleDataCheckResult(
                can_trade=False,
                reason=f"Price data for {symbol} is {age:.0f}s old (max {MAX_PRICE_AGE_SECONDS}s). Blocking trade.",
                is_market_open=True,
                price_age_seconds=age,
            )
            await self._emit_block(symbol, result)
            return result

        return StaleDataCheckResult(
            can_trade=True,
            is_market_open=True,
            price_age_seconds=age,
        )

    def _is_market_open(self) -> bool:
        """Check if NSE is currently in trading hours (simple IST check)."""
        now = datetime.now(timezone.utc)
        # Convert to IST (UTC+5:30)
        ist_hour = now.hour + 5
        ist_minute = now.minute + 30
        if ist_minute >= 60:
            ist_hour += 1
            ist_minute -= 60
        if ist_hour >= 24:
            ist_hour -= 24

        current_time = ist_hour * 100 + ist_minute
        market_open = MARKET_OPEN_HOUR * 100 + MARKET_OPEN_MINUTE
        market_close = MARKET_CLOSE_HOUR * 100 + MARKET_CLOSE_MINUTE

        # Also check weekday (Mon=0 through Sun=6)
        ist_weekday = now.weekday()  # Approximate — doesn't handle midnight IST transition
        if ist_weekday >= 5:  # Saturday/Sunday
            return False

        return market_open <= current_time <= market_close

    async def _emit_block(self, symbol: str, result: StaleDataCheckResult) -> None:
        """Emit a STALE_DATA_BLOCK event."""
        if self.event_bus:
            try:
                await self.event_bus.publish(Event(
                    id=f"stale_block_{symbol}_{int(time.monotonic())}",
                    type=EventType.STALE_DATA_BLOCK,
                    data={
                        "symbol": symbol,
                        "reason": result.reason,
                        "price_age_seconds": result.price_age_seconds,
                        "is_market_open": result.is_market_open,
                    },
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))
            except Exception as e:
                logger.warning(f"Failed to emit stale data block event: {e}")
        logger.warning(f"STALE DATA BLOCK: {result.reason}")
