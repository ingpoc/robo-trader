from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import Config
from src.core.event_bus import EventBus
from src.models.market_data import MarketDataProvider, SubscriptionMode
from src.services.market_data_service import MarketDataService
from src.services.quote_stream_adapter import QuoteStreamStatus


class _FakeQuoteStreamAdapter:
    provider = MarketDataProvider.UPSTOX

    def __init__(self):
        self.subscribe_calls = []
        self.unsubscribe_calls = []
        self.callback = None

    async def initialize(self):
        return None

    async def subscribe(self, requests):
        self.subscribe_calls.append(list(requests))

    async def unsubscribe(self, symbols):
        self.unsubscribe_calls.append(list(symbols))

    async def get_status(self):
        return QuoteStreamStatus(
            provider="upstox",
            configured=True,
            connected=True,
            status="ready",
            summary="Streaming",
            active_symbols=1,
            mode="ltpc",
            instrument_cache_ready=True,
        )

    async def close(self):
        return None

    def set_quote_update_callback(self, callback):
        self.callback = callback


@pytest.mark.asyncio
async def test_market_data_service_routes_upstox_subscriptions_to_quote_stream(tmp_path: Path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )
    event_bus = EventBus(config)
    await event_bus.initialize()

    adapter = _FakeQuoteStreamAdapter()
    service = MarketDataService(
        config,
        event_bus,
        broker=None,
        quote_stream_adapter=adapter,
        default_provider=MarketDataProvider.UPSTOX,
    )
    await service.initialize()

    try:
        subscribed = await service.subscribe_market_data("INFY", mode=SubscriptionMode.LTP)

        assert subscribed is True
        assert len(adapter.subscribe_calls) == 1
        assert adapter.subscribe_calls[0][0].symbol == "INFY"
        assert adapter.subscribe_calls[0][0].mode == SubscriptionMode.LTP

        unsubscribed = await service.unsubscribe_market_data("INFY")

        assert unsubscribed is True
        assert adapter.unsubscribe_calls == [["INFY"]]
    finally:
        await service.close()
