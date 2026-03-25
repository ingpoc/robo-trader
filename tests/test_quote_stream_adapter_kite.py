import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.config import Config
from src.services.quote_stream_adapter import KiteTickerQuoteStreamAdapter


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
