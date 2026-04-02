from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.config import Config
from src.core.event_bus import EventBus
from src.models.market_data import MarketData, MarketDataProvider, SubscriptionMode
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


class _FakeKiteQuoteStreamAdapter(_FakeQuoteStreamAdapter):
    provider = MarketDataProvider.ZERODHA_KITE


class _FakeAuthenticatedKiteBroker:
    def __init__(self):
        self.get_quotes = AsyncMock(
            return_value={
                "HDFCBANK": SimpleNamespace(
                    last_price=744.15,
                    volume=123456,
                    timestamp="2026-03-23T16:51:24+00:00",
                    ohlc={
                        "open": 742.0,
                        "high": 746.5,
                        "low": 739.2,
                        "close": 740.8,
                    },
                )
            }
        )

    async def is_authenticated(self):
        return True


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


@pytest.mark.asyncio
async def test_market_data_service_normalizes_legacy_hdfc_subscription_on_write(tmp_path: Path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )
    event_bus = EventBus(config)
    await event_bus.initialize()

    adapter = _FakeKiteQuoteStreamAdapter()
    service = MarketDataService(
        config,
        event_bus,
        broker=None,
        quote_stream_adapter=adapter,
        default_provider=MarketDataProvider.ZERODHA_KITE,
    )
    await service.initialize()

    try:
        subscribed = await service.subscribe_market_data("HDFC", mode=SubscriptionMode.LTP)

        assert subscribed is True
        assert "HDFCBANK" in service._subscriptions
        assert "HDFC" not in service._subscriptions
        assert adapter.subscribe_calls[0][0].symbol == "HDFCBANK"

        conn = sqlite3.connect(service.db_path)
        try:
            rows = conn.execute("SELECT symbol FROM market_subscriptions").fetchall()
        finally:
            conn.close()
        assert rows == [("HDFCBANK",)]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_market_data_service_migrates_legacy_hdfc_subscription_on_load(tmp_path: Path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )

    market_db = config.state_dir / "market_data.db"
    market_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(market_db)
    try:
        conn.execute(
            """
            CREATE TABLE market_subscriptions (
                symbol TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                last_update TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO market_subscriptions (symbol, mode, provider, active, last_update, created_at)
            VALUES ('HDFC', 'ltp', 'zerodha_kite', 1, '2026-03-23T09:21:03.282190+00:00', '2026-03-23T09:21:03.282190+00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    event_bus = EventBus(config)
    await event_bus.initialize()

    adapter = _FakeKiteQuoteStreamAdapter()
    service = MarketDataService(
        config,
        event_bus,
        broker=None,
        quote_stream_adapter=adapter,
        default_provider=MarketDataProvider.ZERODHA_KITE,
    )
    await service.initialize()

    try:
        assert "HDFCBANK" in service._subscriptions
        assert "HDFC" not in service._subscriptions
        assert adapter.subscribe_calls[0][0].symbol == "HDFCBANK"

        conn = sqlite3.connect(service.db_path)
        try:
            rows = conn.execute("SELECT symbol FROM market_subscriptions").fetchall()
        finally:
            conn.close()
        assert rows == [("HDFCBANK",)]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_market_data_service_seeds_zerodha_cache_from_broker_quote_on_subscribe(tmp_path: Path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )
    event_bus = EventBus(config)
    await event_bus.initialize()

    adapter = _FakeKiteQuoteStreamAdapter()
    broker = _FakeAuthenticatedKiteBroker()
    service = MarketDataService(
        config,
        event_bus,
        broker=broker,
        quote_stream_adapter=adapter,
        default_provider=MarketDataProvider.ZERODHA_KITE,
    )
    await service.initialize()

    try:
        subscribed = await service.subscribe_market_data("HDFC", mode=SubscriptionMode.LTP)

        assert subscribed is True
        broker.get_quotes.assert_awaited_once_with(["HDFCBANK"])
        assert service._market_data["HDFCBANK"].ltp == 744.15

        conn = sqlite3.connect(service.db_path)
        try:
            rows = conn.execute(
                "SELECT symbol, ltp, provider FROM market_data_cache ORDER BY symbol"
            ).fetchall()
        finally:
            conn.close()

        assert rows == [("HDFCBANK", 744.15, "zerodha_kite")]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_market_data_service_resolves_legacy_aliases_on_read(tmp_path: Path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )
    event_bus = EventBus(config)
    await event_bus.initialize()

    adapter = _FakeKiteQuoteStreamAdapter()
    broker = _FakeAuthenticatedKiteBroker()
    service = MarketDataService(
        config,
        event_bus,
        broker=broker,
        quote_stream_adapter=adapter,
        default_provider=MarketDataProvider.ZERODHA_KITE,
    )
    await service.initialize()

    try:
        await service.subscribe_market_data("HDFC", mode=SubscriptionMode.LTP)

        single = await service.get_market_data("HDFC")
        multiple = await service.get_multiple_market_data(["HDFC"])

        assert single is not None
        assert single.ltp == 744.15
        assert "HDFC" in multiple
        assert multiple["HDFC"].ltp == 744.15
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_market_data_service_emits_unique_event_ids_for_rapid_updates(tmp_path: Path):
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
        first = MarketData(
            symbol="INFY",
            ltp=1520.0,
            volume=1000,
            timestamp="2026-03-24T06:36:00+00:00",
            provider="upstox",
        )
        second = MarketData(
            symbol="INFY",
            ltp=1521.5,
            volume=1200,
            timestamp="2026-03-24T06:36:01+00:00",
            provider="upstox",
        )

        await service._update_market_data(first)
        await service._update_market_data(second)

        conn = sqlite3.connect(event_bus.db_path)
        try:
            rows = conn.execute(
                "SELECT id FROM events WHERE type = 'market.price_update' ORDER BY rowid"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) == 2
        assert rows[0][0] != rows[1][0]
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_market_data_service_seeds_zerodha_cache_for_restored_subscriptions_on_initialize(tmp_path: Path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )

    market_db = config.state_dir / "market_data.db"
    market_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(market_db)
    try:
        conn.execute(
            """
            CREATE TABLE market_subscriptions (
                symbol TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                last_update TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO market_subscriptions (symbol, mode, provider, active, last_update, created_at)
            VALUES ('HDFC', 'ltp', 'zerodha_kite', 1, '2026-03-23T09:21:03.282190+00:00', '2026-03-23T09:21:03.282190+00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    event_bus = EventBus(config)
    await event_bus.initialize()

    adapter = _FakeKiteQuoteStreamAdapter()
    broker = _FakeAuthenticatedKiteBroker()
    service = MarketDataService(
        config,
        event_bus,
        broker=broker,
        quote_stream_adapter=adapter,
        default_provider=MarketDataProvider.ZERODHA_KITE,
    )
    await service.initialize()

    try:
        broker.get_quotes.assert_awaited_once_with(["HDFCBANK"])
        assert service._market_data["HDFCBANK"].ltp == 744.15

        conn = sqlite3.connect(service.db_path)
        try:
            rows = conn.execute(
                "SELECT symbol, ltp, provider FROM market_data_cache ORDER BY symbol"
            ).fetchall()
        finally:
            conn.close()

        assert rows == [("HDFCBANK", 744.15, "zerodha_kite")]
    finally:
        await service.close()
