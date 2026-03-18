"""Regression tests for the mission-cut dashboard operator view."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.trading_capabilities import CapabilityCheck, CapabilityStatus, TradingCapabilitySnapshot
from src.web.routes.dashboard import api_dashboard


@pytest.mark.asyncio
async def test_dashboard_uses_paper_trading_truth_instead_of_legacy_portfolio_state():
    """The active dashboard should build from paper-trading services, not orchestrator portfolio state."""
    container = MagicMock()
    account_manager = AsyncMock()
    capability_service = AsyncMock()
    config = SimpleNamespace(claude_agent=SimpleNamespace(daily_token_budget=15000))

    account_manager.get_all_accounts.return_value = [
        SimpleNamespace(
            account_id="paper_main",
            initial_balance=100000.0,
            current_balance=82000.0,
            buying_power=80000.0,
        )
    ]
    account_manager.get_open_positions.return_value = [
        SimpleNamespace(
            symbol="INFY",
            quantity=10,
            current_price=120.0,
            current_value=1200.0,
            unrealized_pnl=200.0,
            unrealized_pnl_pct=20.0,
            stop_loss=110.0,
            target_price=130.0,
            trade_type="BUY",
        )
    ]
    account_manager.get_closed_trades.return_value = [
        SimpleNamespace(
            exit_date="2026-03-18T09:30:00+00:00",
            realized_pnl=150.0,
        )
    ]

    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="claude_runtime",
                label="Claude Runtime",
                status=CapabilityStatus.READY,
                summary="Claude runtime is authenticated.",
            ),
            CapabilityCheck(
                key="market_data",
                label="Market Data",
                status=CapabilityStatus.DEGRADED,
                summary="Market data is available with blockers.",
                detail="Broker-backed quotes are still limited.",
            ),
        ],
    )

    async def get_service(name):
        if name == "paper_trading_account_manager":
            return account_manager
        if name == "trading_capability_service":
            return capability_service
        if name == "config":
            return config
        raise ValueError(name)

    container.get = AsyncMock(side_effect=get_service)
    container.get_orchestrator = AsyncMock()

    payload = await api_dashboard(request=MagicMock(), container=container)

    assert payload["portfolio"]["holdings"][0]["symbol"] == "INFY"
    assert payload["portfolio"]["cash"]["free"] == pytest.approx(80000.0)
    assert payload["portfolio"]["summary"]["active_positions"] == 1
    assert payload["analytics"]["paper_trading"]["portfolio_value"] == pytest.approx(83200.0)
    assert payload["analytics"]["paper_trading"]["capability_status"] == "degraded"
    assert payload["ai_status"]["daily_api_limit"] == 15000
    assert payload["alerts"][0]["id"] == "capability-market_data"
    container.get_orchestrator.assert_not_called()
