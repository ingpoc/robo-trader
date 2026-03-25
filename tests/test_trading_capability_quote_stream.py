from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.models.trading_capabilities import CapabilityStatus
from src.services.quote_stream_adapter import QuoteStreamStatus
from src.services.trading_capability_service import TradingCapabilityService


@pytest.mark.asyncio
async def test_paper_mode_automation_can_run_with_live_quotes_even_when_broker_is_degraded(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(
        "src.services.trading_capability_service.get_claude_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=True,
                checked_at=now,
                account_info={"auth_method": "claude_code_cli"},
                error=None,
            )
        ),
    )

    market_data_service = SimpleNamespace(
        get_quote_stream_status=AsyncMock(
            return_value=QuoteStreamStatus(
                provider="upstox",
                configured=True,
                connected=True,
                status="ready",
                summary="Upstox quote stream is serving live quotes.",
                last_tick_at=now,
                active_symbols=3,
                mode="ltpc",
                instrument_cache_ready=True,
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={"INFY": SimpleNamespace(), "RELIANCE": SimpleNamespace()}),
        _market_data={
            "INFY": SimpleNamespace(timestamp=now, provider="upstox"),
            "RELIANCE": SimpleNamespace(timestamp=now, provider="upstox"),
        },
    )
    account = SimpleNamespace(account_id="paper_main")
    account_manager = SimpleNamespace(
        get_all_accounts=AsyncMock(return_value=[account]),
        get_account=AsyncMock(return_value=account),
    )
    container = SimpleNamespace(
        config=SimpleNamespace(
            integration=SimpleNamespace(
                zerodha_api_key=None,
                zerodha_api_secret=None,
            )
        ),
        get=AsyncMock(
            side_effect=lambda name: {
                "market_data_service": market_data_service,
                "paper_trading_account_manager": account_manager,
                "kite_connect_service": None,
            }[name]
        ),
    )

    snapshot = await TradingCapabilityService(container).get_snapshot(account_id="paper_main")

    broker_check = next(check for check in snapshot.checks if check.key == "broker_auth")
    quote_stream_check = next(check for check in snapshot.checks if check.key == "quote_stream")

    assert snapshot.automation_allowed is True
    assert snapshot.overall_status == CapabilityStatus.DEGRADED
    assert snapshot.blockers == []
    assert broker_check.blocking is False
    assert broker_check.status == CapabilityStatus.DEGRADED
    assert quote_stream_check.status == CapabilityStatus.READY


@pytest.mark.asyncio
async def test_claude_runtime_is_degraded_when_usage_is_exhausted(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(
        "src.services.trading_capability_service.get_claude_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=True,
                checked_at=now,
                account_info={"auth_method": "claude.ai"},
                error=None,
                rate_limit_info={
                    "status": "exhausted",
                    "code": "rate_limit",
                    "message": "You're out of extra usage · resets 5:30pm (Asia/Calcutta)",
                },
            )
        ),
    )

    market_data_service = SimpleNamespace(
        get_quote_stream_status=AsyncMock(
            return_value=QuoteStreamStatus(
                provider="upstox",
                configured=True,
                connected=True,
                status="ready",
                summary="Upstox quote stream is serving live quotes.",
                last_tick_at=now,
                active_symbols=1,
                mode="ltpc",
                instrument_cache_ready=True,
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={}),
        _market_data={},
    )
    account = SimpleNamespace(account_id="paper_main")
    account_manager = SimpleNamespace(
        get_all_accounts=AsyncMock(return_value=[account]),
        get_account=AsyncMock(return_value=account),
    )
    container = SimpleNamespace(
        config=SimpleNamespace(
            integration=SimpleNamespace(
                zerodha_api_key=None,
                zerodha_api_secret=None,
            )
        ),
        get=AsyncMock(
            side_effect=lambda name: {
                "market_data_service": market_data_service,
                "paper_trading_account_manager": account_manager,
                "kite_connect_service": None,
            }[name]
        ),
    )

    snapshot = await TradingCapabilityService(container).get_snapshot(account_id="paper_main")

    claude_check = next(check for check in snapshot.checks if check.key == "claude_runtime")
    assert claude_check.status == CapabilityStatus.DEGRADED
    assert "usage-limited" in claude_check.summary
    assert "resets 5:30pm" in (claude_check.detail or "")


@pytest.mark.asyncio
async def test_market_data_capability_accepts_naive_cached_timestamps(monkeypatch):
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        "src.services.trading_capability_service.get_claude_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=True,
                checked_at=now.isoformat(),
                account_info={"auth_method": "claude_code_cli"},
                error=None,
            )
        ),
    )

    market_data_service = SimpleNamespace(
        get_quote_stream_status=AsyncMock(
            return_value=QuoteStreamStatus(
                provider="zerodha_kite",
                configured=True,
                connected=True,
                status="degraded",
                summary="KiteTicker subscriptions updated.",
                detail="Streaming 3 active symbol(s).",
                active_symbols=3,
                mode="ltp",
                instrument_cache_ready=True,
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={"RELIANCE": SimpleNamespace()}),
        _market_data={
            "RELIANCE": SimpleNamespace(
                timestamp=now.replace(tzinfo=None).isoformat(timespec="seconds"),
                provider="zerodha_kite",
            )
        },
    )
    account = SimpleNamespace(account_id="paper_main")
    account_manager = SimpleNamespace(
        get_all_accounts=AsyncMock(return_value=[account]),
        get_account=AsyncMock(return_value=account),
    )
    container = SimpleNamespace(
        config=SimpleNamespace(
            integration=SimpleNamespace(
                zerodha_api_key="key",
                zerodha_api_secret="secret",
            )
        ),
        get=AsyncMock(
            side_effect=lambda name: {
                "market_data_service": market_data_service,
                "paper_trading_account_manager": account_manager,
                "kite_connect_service": SimpleNamespace(is_authenticated=AsyncMock(return_value=True), is_mock=False),
            }[name]
        ),
    )

    snapshot = await TradingCapabilityService(container).get_snapshot(account_id="paper_main")

    market_data_check = next(check for check in snapshot.checks if check.key == "market_data")
    assert market_data_check.status == CapabilityStatus.READY


@pytest.mark.asyncio
async def test_missing_quote_stream_blocks_autonomous_paper_mode(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(
        "src.services.trading_capability_service.get_claude_status",
        AsyncMock(
            return_value=SimpleNamespace(
                is_valid=True,
                checked_at=now,
                account_info={"auth_method": "claude_code_cli"},
                error=None,
            )
        ),
    )

    market_data_service = SimpleNamespace(
        get_quote_stream_status=AsyncMock(
            return_value=QuoteStreamStatus(
                provider="none",
                configured=False,
                connected=False,
                status="blocked",
                summary="Quote stream is not configured.",
                detail="Set QUOTE_STREAM_PROVIDER and provider credentials.",
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={}),
        _market_data={},
    )
    account = SimpleNamespace(account_id="paper_main")
    account_manager = SimpleNamespace(
        get_all_accounts=AsyncMock(return_value=[account]),
        get_account=AsyncMock(return_value=account),
    )
    container = SimpleNamespace(
        config=SimpleNamespace(
            integration=SimpleNamespace(
                zerodha_api_key=None,
                zerodha_api_secret=None,
            )
        ),
        get=AsyncMock(
            side_effect=lambda name: {
                "market_data_service": market_data_service,
                "paper_trading_account_manager": account_manager,
                "kite_connect_service": None,
            }[name]
        ),
    )

    snapshot = await TradingCapabilityService(container).get_snapshot(account_id="paper_main")

    assert snapshot.automation_allowed is False
    assert snapshot.overall_status == CapabilityStatus.BLOCKED
    assert any("quote stream provider" in blocker.lower() for blocker in snapshot.blockers)
