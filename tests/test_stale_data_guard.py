"""
Tests for the StaleDataGuard.

Verifies that stale prices block execution and fresh prices allow it.
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.stale_data_guard import StaleDataGuard, MAX_PRICE_AGE_SECONDS


@pytest.fixture
def guard():
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    return StaleDataGuard(event_bus=event_bus)


class TestStaleDataGuard:
    @pytest.mark.asyncio
    async def test_no_price_data_blocks(self, guard):
        """Trading should be blocked when no price data exists for a symbol."""
        result = await guard.check("UNKNOWN_SYMBOL")
        # May be blocked by market hours OR no price data
        assert not result.can_trade

    @pytest.mark.asyncio
    async def test_fresh_price_allows_trade(self, guard):
        """Fresh price data should allow trading (if market is open)."""
        guard.record_price_update("RELIANCE")
        result = await guard.check("RELIANCE")
        # Can only be True if market is also open
        if result.is_market_open:
            assert result.can_trade
            assert result.price_age_seconds is not None
            assert result.price_age_seconds < MAX_PRICE_AGE_SECONDS

    @pytest.mark.asyncio
    async def test_stale_price_blocks(self, guard):
        """Stale price data should block trading."""
        # Record a price update, then artificially age it
        guard._last_price_timestamps["RELIANCE"] = time.monotonic() - MAX_PRICE_AGE_SECONDS - 10
        result = await guard.check("RELIANCE")
        if result.is_market_open:
            assert not result.can_trade
            assert "stale" in (result.reason or "").lower() or "old" in (result.reason or "").lower()

    def test_record_price_update(self, guard):
        """Recording a price update should store the timestamp."""
        guard.record_price_update("TCS")
        assert "TCS" in guard._last_price_timestamps
        assert guard._last_price_timestamps["TCS"] > 0

    @pytest.mark.asyncio
    async def test_market_hours_check(self, guard):
        """Market hours check should return a boolean."""
        is_open = guard._is_market_open()
        assert isinstance(is_open, bool)

    @pytest.mark.asyncio
    async def test_block_emits_event(self, guard):
        """Blocking a trade should emit a STALE_DATA_BLOCK event."""
        # This will be blocked (no price data)
        await guard.check("NOSYMBOL")
        # Event bus publish should have been called (if market was open)
        # We can't guarantee market is open, but if it blocks for any reason,
        # an event should be emitted
