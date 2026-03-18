from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.models.agent_artifacts import ResearchPacket
from src.models.trading_capabilities import CapabilityCheck, CapabilityStatus, TradingCapabilitySnapshot
from src.services.claude_agent.agent_artifact_service import AgentArtifactService


class _Container:
    def __init__(self, services):
        self._services = services

    async def get(self, name):
        if name not in self._services:
            raise KeyError(name)
        return self._services[name]


@pytest.mark.asyncio
async def test_discovery_view_uses_watchlist_and_excludes_held_symbols():
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")
    account_manager.get_open_positions.return_value = [SimpleNamespace(symbol="INFY")]

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = [
        {
            "id": "cand-1",
            "symbol": "INFY",
            "company_name": "Infosys",
            "sector": "Technology",
            "discovery_source": "watchlist",
            "confidence_score": 0.9,
            "discovery_reason": "Already held",
        },
        {
            "id": "cand-2",
            "symbol": "TCS",
            "company_name": "TCS",
            "sector": "Technology",
            "discovery_source": "watchlist",
            "confidence_score": 0.72,
            "discovery_reason": "Strong trend and earnings momentum",
        },
    ]

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
            }
        )
    )

    envelope = await service.get_discovery_view("paper_main")

    assert envelope.status == "ready"
    assert envelope.artifact_count == 1
    assert envelope.candidates[0].symbol == "TCS"


@pytest.mark.asyncio
async def test_decision_view_blocks_when_claude_runtime_is_invalid(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
            }
        )
    )

    async def _invalid_status():
        return SimpleNamespace(is_valid=False)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status_cached",
        _invalid_status,
    )

    envelope = await service.get_decision_view("paper_main")

    assert envelope.status == "blocked"
    assert "Claude runtime" in envelope.blockers[0]


@pytest.mark.asyncio
async def test_research_view_blocks_when_claude_runtime_is_invalid(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = [
        {
            "id": "cand-1",
            "symbol": "INFY",
            "company_name": "Infosys",
            "discovery_source": "watchlist",
            "confidence_score": 0.7,
            "discovery_reason": "Momentum remains intact.",
        }
    ]

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
            }
        )
    )

    async def _invalid_status():
        return SimpleNamespace(is_valid=False)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status_cached",
        _invalid_status,
    )

    envelope = await service.get_research_view("paper_main")

    assert envelope.status == "blocked"
    assert envelope.research is None
    assert "Claude runtime" in envelope.blockers[0]


@pytest.mark.asyncio
async def test_research_view_uses_top_candidate_when_no_candidate_id_is_provided(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(
        account_id="paper_main",
        current_balance=100000.0,
        buying_power=100000.0,
        monthly_pnl=0.0,
    )
    account_manager.get_open_positions.return_value = []
    account_manager.get_closed_trades.return_value = []
    account_manager.get_performance_metrics.return_value = {"win_rate": 0.0, "profit_factor": 0.0}

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = [
        {
            "id": "cand-1",
            "symbol": "TCS",
            "company_name": "TCS",
            "sector": "Technology",
            "discovery_source": "watchlist",
            "confidence_score": 0.82,
            "discovery_reason": "Trend and earnings strength remain aligned.",
        }
    ]

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="claude_runtime",
                label="Claude Runtime",
                status=CapabilityStatus.READY,
                summary="Claude runtime is ready.",
            )
        ],
        account_id="paper_main",
    )

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "trading_capability_service": capability_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    async def _fake_run(**kwargs):
        assert "TCS" in kwargs["prompt"]
        return kwargs["output_model"](
            research_id="research-1",
            symbol="TCS",
            thesis="Trend and post-earnings momentum remain constructive.",
            evidence=["Relative strength is holding above sector peers."],
            risks=["Breakout could fail if volume dries up."],
            invalidation="Daily close below the recent base low.",
            confidence=0.74,
            next_step="Promote to a decision packet only if the breakout holds.",
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status_cached",
        _valid_status,
    )
    monkeypatch.setattr(service, "_run_structured_role", _fake_run)

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "ready"
    assert envelope.research is not None
    assert envelope.research.symbol == "TCS"
    assert envelope.research.candidate_id == "cand-1"
    assert envelope.research.account_id == "paper_main"


@pytest.mark.asyncio
async def test_research_view_returns_empty_when_no_candidates_exist(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")
    account_manager.get_open_positions.return_value = []

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = []

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status_cached",
        _valid_status,
    )

    envelope = await service.get_research_view("paper_main")

    assert envelope.status == "empty"
    assert envelope.research is None


@pytest.mark.asyncio
async def test_review_view_returns_empty_without_positions_or_trades(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(
        account_id="paper_main",
        current_balance=100000.0,
        buying_power=100000.0,
        monthly_pnl=0.0,
    )
    account_manager.get_open_positions.return_value = []
    account_manager.get_closed_trades.return_value = []
    account_manager.get_performance_metrics.return_value = {"win_rate": 0.0, "profit_factor": 0.0}

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="claude_runtime",
                label="Claude Runtime",
                status=CapabilityStatus.READY,
                summary="Claude runtime is ready.",
            )
        ],
        account_id="paper_main",
    )

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "trading_capability_service": capability_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status_cached",
        _valid_status,
    )

    envelope = await service.get_review_view("paper_main")

    assert envelope.status == "empty"
    assert envelope.review is None


@pytest.mark.asyncio
async def test_run_structured_role_recreates_and_cleans_up_client(monkeypatch):
    service = AgentArtifactService(_Container({}))

    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query(client, prompt, timeout):
        return (
            '{"research_id":"r-1","candidate_id":"cand-1","account_id":"paper_main",'
            '"symbol":"TCS","thesis":"test","evidence":[],"risks":[],"invalidation":"x",'
            '"confidence":0.5,"next_step":"y"}'
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.query_with_timeout",
        _query,
    )

    result = await service._run_structured_role(
        client_type="agent_research_paper_main",
        role_name="research",
        system_prompt="system",
        prompt="prompt",
        output_model=ResearchPacket,
        allowed_tools=[],
        session_id="research:paper_main",
    )

    assert result.symbol == "TCS"
    manager.get_client.assert_awaited_once()
    _, kwargs = manager.get_client.await_args
    assert kwargs["force_recreate"] is True
    manager.cleanup_client.assert_awaited_once_with("agent_research_paper_main")


@pytest.mark.asyncio
async def test_run_structured_role_cleans_up_client_after_sdk_error(monkeypatch):
    service = AgentArtifactService(_Container({}))

    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query(client, prompt, timeout):
        raise TradingError(
            "Claude SDK error: Claude SDK session ended with error",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.query_with_timeout",
        _query,
    )

    with pytest.raises(TradingError):
        await service._run_structured_role(
            client_type="agent_research_paper_main",
            role_name="research",
            system_prompt="system",
            prompt="prompt",
            output_model=ResearchPacket,
            allowed_tools=[],
            session_id="research:paper_main",
        )

    manager.cleanup_client.assert_awaited_once_with("agent_research_paper_main")
