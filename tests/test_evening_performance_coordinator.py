from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.coordinators.paper_trading.evening_performance_coordinator import EveningPerformanceCoordinator


@pytest.mark.asyncio
async def test_evening_performance_generates_claude_insights(monkeypatch):
    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query_with_timeout(client, prompt, timeout):
        return '{"insights":["Cut losers faster when confirmation fails.","Momentum setup quality was strongest in one strategy bucket."]}'

    monkeypatch.setattr(
        "src.core.coordinators.paper_trading.evening_performance_coordinator.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.core.coordinators.paper_trading.evening_performance_coordinator.query_with_timeout",
        _query_with_timeout,
    )

    state_manager = MagicMock()
    state_manager.paper_trading = AsyncMock()
    container = MagicMock()

    async def _get(name):
        if name == "state_manager":
            return state_manager
        if name == "autonomous_trading_safeguards":
            return AsyncMock()
        raise ValueError(name)

    container.get = AsyncMock(side_effect=_get)

    coordinator = EveningPerformanceCoordinator(config=MagicMock(), event_bus=AsyncMock(), container=container)
    await coordinator.initialize()
    insights = await coordinator.generate_trading_insights(
        {
            "daily_pnl": 1250.0,
            "daily_pnl_percent": 1.5,
            "win_rate": 66.0,
            "trades_reviewed": [{"symbol": "INFY", "side": "BUY"}],
            "strategy_performance": {"momentum": {"total_pnl": 1250.0, "win_rate": 66.0, "trades": 3}},
        },
        [],
    )

    assert insights == [
        "Cut losers faster when confirmation fails.",
        "Momentum setup quality was strongest in one strategy bucket.",
    ]
    manager.cleanup_client.assert_awaited_once()
