from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.coordinators.core.session_authentication_coordinator import (
    SessionAuthenticationCoordinator,
)
from src.core.coordinators.paper_trading.morning_session_coordinator import (
    MorningSessionCoordinator,
)
from src.services.claude_agent_service import ClaudeAgentService
from src.services.prompt_optimization_service import PromptOptimizationService


@pytest.mark.asyncio
async def test_session_authentication_uses_runtime_aware_status(monkeypatch):
    expected = SimpleNamespace(
        is_valid=True,
        api_key_present=True,
        account_info={"auth_method": "chatgpt_codex_local_runtime"},
    )
    runtime_status = AsyncMock(return_value=expected)
    monkeypatch.setattr(
        "src.core.coordinators.core.session_authentication_coordinator.get_claude_sdk_status",
        runtime_status,
    )

    coordinator = SessionAuthenticationCoordinator(config=MagicMock())
    status = await coordinator.validate_authentication()

    assert status is expected
    runtime_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_morning_session_auto_run_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AUTO_RUN_MORNING_SESSION", raising=False)
    event_bus = MagicMock()
    coordinator = MorningSessionCoordinator(
        config=MagicMock(),
        event_bus=event_bus,
        container=MagicMock(),
    )
    coordinator.premarket.initialize = AsyncMock()
    coordinator.research.initialize = AsyncMock()
    coordinator.trade_ideas.initialize = AsyncMock()
    coordinator.safeguards.initialize = AsyncMock()
    coordinator.execution.initialize = AsyncMock()

    await coordinator.initialize()

    event_bus.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_prompt_optimization_real_time_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_REAL_TIME_PROMPT_OPTIMIZATION", raising=False)
    event_bus = MagicMock()
    service = PromptOptimizationService(
        config={},
        event_bus=event_bus,
        container=MagicMock(),
        market_research_service=AsyncMock(),
    )

    await service.initialize()

    event_bus.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_legacy_claude_agent_automation_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_LEGACY_CLAUDE_AGENT_AUTOMATION", raising=False)

    class _DummyMCPServer:
        def __init__(self, container):
            self.container = container

        async def initialize(self):
            return None

        async def cleanup(self):
            return None

    monkeypatch.setattr(
        "src.services.claude_agent_service.ClaudeAgentMCPServer",
        _DummyMCPServer,
    )

    event_bus = MagicMock()
    container = MagicMock()
    container.get = AsyncMock(return_value=MagicMock())
    service = ClaudeAgentService(
        config={},
        event_bus=event_bus,
        container=container,
        strategy_store=MagicMock(),
    )

    await service.initialize()

    event_bus.subscribe.assert_not_called()
