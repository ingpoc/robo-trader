import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.config import Config
from src.services.quote_stream_adapter import KiteInstrumentResolver, KiteTickerQuoteStreamAdapter, UpstoxQuoteStreamAdapter


class _FakeKiteTicker:
    MODE_LTP = "ltp"
    MODE_QUOTE = "quote"
    MODE_FULL = "full"

    def __init__(self, api_key, access_token):
        self.api_key = api_key
        self.access_token = access_token
        self.on_ticks = None
        self.on_connect = None
        self.on_close = None
        self.on_error = None
        self.on_reconnect = None
        self.on_noreconnect = None
        self.subscribe_calls = []
        self.set_mode_calls = []
        self.connect_calls = []

    def connect(self, threaded=False, disable_ssl_verification=False, proxy=None):
        self.connect_calls.append(
            {
                "threaded": threaded,
                "disable_ssl_verification": disable_ssl_verification,
                "proxy": proxy,
            }
        )
        if self.on_connect:
            self.on_connect(self, {"status": "ok"})

    def subscribe(self, instrument_tokens):
        self.subscribe_calls.append(list(instrument_tokens))

    def set_mode(self, mode, instrument_tokens):
        self.set_mode_calls.append((mode, list(instrument_tokens)))

    def close(self):
        return None


@pytest.mark.asyncio
async def test_kite_quote_stream_adapter_uses_on_ticks_callback_and_ltp_mode(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setitem(sys.modules, "kiteconnect", SimpleNamespace(KiteTicker=_FakeKiteTicker))

    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )
    config.integration.zerodha_api_key = "test-key"
    config.integration.zerodha_access_token = "test-token"

    adapter = KiteTickerQuoteStreamAdapter(config, AsyncMock())
    await adapter.initialize()

    await adapter._create_ticker([408065])

    assert isinstance(adapter._ticker, _FakeKiteTicker)
    assert adapter._ticker.on_ticks == adapter._handle_tick
    assert getattr(adapter._ticker, "on_tick", None) is None
    assert adapter._ticker.connect_calls == [
        {
            "threaded": True,
            "disable_ssl_verification": False,
            "proxy": None,
        }
    ]
    assert adapter._ticker.subscribe_calls == [[408065]]
    assert adapter._ticker.set_mode_calls == [("ltp", [408065])]
    assert adapter._connected is True
    assert adapter._current_mode == "ltp"


@pytest.mark.asyncio
async def test_kite_instrument_resolver_reads_fresh_cache_without_blocking_network(tmp_path):
    resolver = KiteInstrumentResolver("test-key", "test-token", tmp_path / "state")
    resolver._cache_path.write_text(
        "instrument_token,exchange,tradingsymbol\n408065,NSE,INFY\n",
        encoding="utf-8",
    )

    token = await resolver.resolve_instrument_token("INFY")

    assert token == 408065
    assert resolver.cache_ready is True


@pytest.mark.asyncio
async def test_upstox_handle_message_ignores_malformed_feed(monkeypatch, tmp_path):
    config = Config(
        state_dir=tmp_path / "state",
        logs_dir=tmp_path / "logs",
        project_dir=tmp_path,
    )
    on_quote_update = AsyncMock()
    adapter = UpstoxQuoteStreamAdapter(config, on_quote_update)
    adapter._loop = asyncio.get_running_loop()
    adapter._key_to_symbol = {"NSE_EQ|INE009A01021": "INFY"}

    monkeypatch.setattr(
        adapter,
        "_normalize_feed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad feed")),
    )
    run_coroutine_threadsafe = AsyncMock()
    monkeypatch.setattr(
        "src.services.quote_stream_adapter.asyncio.run_coroutine_threadsafe",
        run_coroutine_threadsafe,
    )

    adapter._handle_message(
        {
            "currentTs": "1712044800000",
            "feeds": {"NSE_EQ|INE009A01021": {"ltpc": {"ltp": "broken"}}},
        }
    )

    run_coroutine_threadsafe.assert_not_called()
