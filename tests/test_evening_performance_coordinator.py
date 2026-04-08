from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.coordinators.paper_trading.evening_performance_coordinator import (
    EveningPerformanceCoordinator,
)


@pytest.mark.asyncio
async def test_evening_performance_generates_claude_insights(tmp_path):
    runtime_client = AsyncMock()
    runtime_client.run_structured.return_value = {
        "output": {
            "insights": [
                "Cut losers faster when confirmation fails.",
                "Momentum setup quality was strongest in one strategy bucket.",
            ]
        }
    }
    state_manager = MagicMock()
    state_manager.paper_trading = AsyncMock()
    container = MagicMock()

    async def _get(name):
        if name == "state_manager":
            return state_manager
        if name == "autonomous_trading_safeguards":
            return AsyncMock()
        if name == "codex_runtime_client":
            return runtime_client
        raise ValueError(name)

    container.get = AsyncMock(side_effect=_get)
    config = SimpleNamespace(
        ai_runtime=SimpleNamespace(
            codex_model="gpt-5.4",
            codex_reasoning_deep="medium",
        ),
        project_dir=tmp_path,
    )

    coordinator = EveningPerformanceCoordinator(
        config=config, event_bus=AsyncMock(), container=container
    )
    await coordinator.initialize()
    insights = await coordinator.generate_trading_insights(
        {
            "daily_pnl": 1250.0,
            "daily_pnl_percent": 1.5,
            "win_rate": 66.0,
            "trades_reviewed": [{"symbol": "INFY", "side": "BUY"}],
            "strategy_performance": {
                "momentum": {"total_pnl": 1250.0, "win_rate": 66.0, "trades": 3}
            },
        },
        [],
    )

    assert insights == [
        "Cut losers faster when confirmation fails.",
        "Momentum setup quality was strongest in one strategy bucket.",
    ]
    runtime_client.run_structured.assert_awaited_once()
