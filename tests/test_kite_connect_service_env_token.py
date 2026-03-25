import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.kite_connect_service import KiteConnectService


class _DummyKite:
    def __init__(self) -> None:
        self.access_token = None

    def set_access_token(self, access_token: str) -> None:
        self.access_token = access_token

    def quote(self, instruments):
        return {
            "NSE:RELIANCE": {
                "instrument_token": 738561,
                "timestamp": "2026-03-23 16:54:25",
                "last_trade_time": "2026-03-23 15:54:56",
                "last_price": 1407.8,
                "last_quantity": 5,
                "buy_quantity": 36,
                "sell_quantity": 0,
                "volume": 18979554,
                "average_price": 1404.45,
                "net_change": 0.0,
                "ohlc": {
                    "open": 1400.0,
                    "high": 1415.6,
                    "low": 1391.0,
                    "close": 1414.4,
                },
            }
        }


@pytest.mark.asyncio
async def test_set_access_token_creates_active_session_from_account_context(monkeypatch):
    monkeypatch.setenv("ZERODHA_USER_ID", "WH6407")
    monkeypatch.delenv("PAPER_TRADING_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("ZERODHA_ACCOUNT_ID", raising=False)

    service = object.__new__(KiteConnectService)
    service.logger = logging.getLogger("kite-connect-test")
    service.kite = _DummyKite()
    service._active_session = None

    result = await service._set_access_token("token-123")

    assert result is True
    assert service.kite.access_token == "token-123"
    assert service._active_session is not None
    assert service._active_session.account_id == "WH6407"
    assert service._active_session.user_id == "WH6407"
    assert service._active_session.access_token == "token-123"
    assert service._active_session.expires_at


@pytest.mark.asyncio
async def test_is_authenticated_accepts_timezone_aware_env_session(monkeypatch):
    monkeypatch.setenv("ZERODHA_USER_ID", "WH6407")
    monkeypatch.delenv("PAPER_TRADING_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("ZERODHA_ACCOUNT_ID", raising=False)

    service = object.__new__(KiteConnectService)
    service.logger = logging.getLogger("kite-connect-test")
    service.kite = _DummyKite()
    service._active_session = None

    result = await service._set_access_token("token-123")

    assert result is True
    assert await service.is_authenticated() is True


@pytest.mark.asyncio
async def test_get_quotes_supports_kite_net_change_payload(monkeypatch):
    monkeypatch.setenv("ZERODHA_USER_ID", "WH6407")

    service = object.__new__(KiteConnectService)
    service.logger = logging.getLogger("kite-connect-test")
    service.kite = _DummyKite()
    service._active_session = SimpleNamespace(expires_at="2026-03-24T11:11:11.192506+00:00")
    service._last_api_call = {}
    service._min_interval = 0
    service.real_time_state = SimpleNamespace(store_real_time_quote=AsyncMock())

    quotes = await service.get_quotes(["RELIANCE"])

    assert list(quotes.keys()) == ["RELIANCE"]
    assert quotes["RELIANCE"].change == 0.0
    assert quotes["RELIANCE"].change_percent == 0.0
    assert quotes["RELIANCE"].timestamp == "2026-03-23T11:24:25+00:00"
    service.real_time_state.store_real_time_quote.assert_awaited_once()
