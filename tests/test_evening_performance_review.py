"""Contract tests for the evening review coordinator."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.core.coordinators.paper_trading.evening_session_coordinator import (
    EveningSessionCoordinator,
)
from src.core.errors import TradingError


@pytest.fixture
async def container():
    """Create a container with store-backed evening review dependencies."""
    container = MagicMock()

    state_manager = Mock()
    state_manager.paper_trading = AsyncMock()
    state_manager.news_earnings_state = AsyncMock()

    store = AsyncMock()
    account_manager = AsyncMock()
    market_data_service = AsyncMock()
    safeguards = AsyncMock()
    event_bus = AsyncMock()

    services = {
        "state_manager": state_manager,
        "paper_trading_store": store,
        "paper_trading_account_manager": account_manager,
        "kite_connect_service": AsyncMock(),
        "market_data_service": market_data_service,
        "autonomous_trading_safeguards": safeguards,
    }

    async def get_service(name):
        if name in services:
            return services[name]
        raise ValueError(f"Service '{name}' not registered")

    container.get = AsyncMock(side_effect=get_service)
    container._services = services
    container._event_bus = event_bus
    return container


@pytest.fixture
async def coordinator(container):
    """Initialize the evening coordinator with mocked services."""
    coordinator = EveningSessionCoordinator(
        config=Mock(),
        event_bus=container._event_bus,
        container=container,
    )
    await coordinator.initialize()
    return coordinator


@pytest.mark.asyncio
async def test_evening_review_uses_store_backed_metrics(coordinator, container):
    """The coordinator should source execution-adjacent truth from the store path."""
    review_date = "2026-03-17"
    state_manager = await container.get("state_manager")
    store = await container.get("paper_trading_store")
    account_manager = await container.get("paper_trading_account_manager")
    market_data_service = await container.get("market_data_service")

    account_manager.get_all_accounts.return_value = [
        SimpleNamespace(account_id="paper_main")
    ]
    account_manager.get_open_positions.return_value = [SimpleNamespace(symbol="TCS")]
    market_data_service.get_multiple_market_data.return_value = {}
    store.get_open_trades.return_value = []
    store.calculate_daily_performance_metrics.return_value = {
        "trades_reviewed": [
            {
                "id": "trade_1",
                "symbol": "TCS",
                "side": "BUY",
                "quantity": 10,
                "entry_price": 100.0,
                "exit_price": 110.0,
                "strategy_tag": "momentum",
                "status": "CLOSED",
            }
        ],
        "daily_pnl": 100.0,
        "daily_pnl_percent": 0.1,
        "open_positions_count": 1,
        "closed_positions_count": 1,
        "win_rate": 100.0,
        "strategy_performance": {
            "momentum": {
                "trades": 1,
                "winning_trades": 1,
                "total_pnl": 100.0,
                "win_rate": 100.0,
            }
        },
        "winning_trades": 1,
        "losing_trades": 0,
    }
    state_manager.paper_trading.get_discovery_watchlist.return_value = []
    state_manager.paper_trading.store_evening_performance_review.return_value = True
    state_manager.news_earnings_state.get_recent_news.return_value = None

    result = await coordinator.run_evening_review(
        trigger_source="MANUAL", review_date=review_date
    )

    assert result["success"] is True
    assert result["account_id"] == "paper_main"
    assert result["daily_pnl"] == 100.0
    store.calculate_daily_performance_metrics.assert_awaited_once_with(
        account_id="paper_main",
        review_date=review_date,
        current_prices={},
    )
    state_manager.paper_trading.calculate_daily_performance_metrics.assert_not_called()
    state_manager.paper_trading.get_open_trades.assert_not_called()
    state_manager.paper_trading.store_evening_performance_review.assert_awaited_once()
    container._event_bus.publish.assert_awaited()


@pytest.mark.asyncio
async def test_evening_review_fails_loud_when_account_selection_is_ambiguous(
    coordinator, container
):
    """The evening review should not guess an account when more than one exists."""
    state_manager = await container.get("state_manager")
    account_manager = await container.get("paper_trading_account_manager")

    account_manager.get_all_accounts.return_value = [
        SimpleNamespace(account_id="paper_main"),
        SimpleNamespace(account_id="paper_alt"),
    ]
    state_manager.paper_trading.store_evening_performance_review.return_value = True

    with pytest.raises(TradingError, match="explicit paper trading account selection"):
        await coordinator.run_evening_review(review_date="2026-03-17")

    state_manager.paper_trading.store_evening_performance_review.assert_awaited_once()
