import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.models.agent_artifacts import Candidate, DecisionPacket, ResearchPacket, ReviewReport, StrategyProposal
from src.models.trading_capabilities import CapabilityCheck, CapabilityStatus, TradingCapabilitySnapshot
from src.services.claude_agent.agent_artifact_service import AgentArtifactService
from src.services.codex_runtime_client import CodexRuntimeError


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
async def test_discovery_view_ignores_stale_watchlist_candidates():
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")
    account_manager.get_open_positions.return_value = []

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = [
        {
            "id": "cand-1",
            "symbol": "RELIANCE",
            "company_name": "Reliance Industries",
            "sector": "Energy",
            "discovery_source": "watchlist",
            "confidence_score": 0.72,
            "discovery_reason": "Old stale discovery row",
            "last_analyzed": "2025-12-23T17:09:21.514794+00:00",
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

    envelope = await service.get_discovery_view("paper_main")

    assert envelope.status == "empty"
    assert envelope.artifact_count == 0
    assert envelope.candidates == []
    assert envelope.blockers == ["No active discovery candidates cleared the confidence threshold in the watchlist."]


@pytest.mark.asyncio
async def test_discovery_view_keeps_low_confidence_candidates_out_of_auto_research_promotion():
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")
    account_manager.get_open_positions.return_value = []

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = [
        {
            "id": "cand-1",
            "symbol": "SBIN",
            "company_name": "State Bank of India",
            "sector": "Financials",
            "discovery_source": "watchlist",
            "confidence_score": 0.55,
            "discovery_reason": "Setup is emerging, but confirmation remains incomplete.",
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

    discovery = await service.get_discovery_view("paper_main")

    assert discovery.status == "ready"
    assert discovery.candidates[0].symbol == "SBIN"
    assert "promotion confidence threshold" in discovery.blockers[0]
    assert (
        service._resolve_research_candidate(
            discovery=discovery,
            candidate_id=None,
            symbol=None,
        )
        is None
    )


@pytest.mark.asyncio
async def test_decision_view_blocks_when_ai_runtime_is_invalid(monkeypatch):
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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _invalid_status,
    )

    envelope = await service.get_decision_view("paper_main")

    assert envelope.status == "blocked"
    assert "AI runtime" in envelope.blockers[0]


@pytest.mark.asyncio
async def test_decision_view_blocks_when_position_marks_are_stale(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")
    account_manager.get_open_positions.return_value = [
        SimpleNamespace(
            symbol="INFY",
            market_price_status="stale_entry",
            market_price_timestamp="2026-03-28T00:00:00+00:00",
        )
    ]

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True, rate_limit_info={})

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )

    envelope = await service.get_decision_view("paper_main", refresh=True)

    assert envelope.status == "blocked"
    assert "fresh" in envelope.blockers[0].lower()
    assert "INFY" in envelope.blockers[0]


@pytest.mark.asyncio
async def test_decision_view_downgrades_low_confidence_packets(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")
    account_manager.get_open_positions.return_value = [
        SimpleNamespace(
            symbol="INFY",
            market_price_status="live",
            market_price_timestamp=datetime.now(timezone.utc).isoformat(),
        )
    ]

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True, rate_limit_info={})

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        service,
        "_build_prompt_context",
        AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda mode="json": {},
                positions=[],
                recent_trades=[],
                capability_summary={},
                learning_summary={},
                improvement_report={},
                account_summary={},
            )
        ),
    )
    monkeypatch.setattr(
        service,
        "_run_structured_role",
        AsyncMock(
                return_value=(
                    SimpleNamespace(
                        decisions=[
                            DecisionPacket(
                                decision_id="decision-1",
                                symbol="INFY",
                                action="tighten_stop",
                                confidence=0.52,
                                thesis="Momentum remains positive.",
                                invalidation="Close below support.",
                                next_step="Tighten the stop today.",
                                risk_note="Fresh quote is available.",
                            )
                        ]
                    ),
                    {"provider": "codex"},
            )
        ),
    )

    envelope = await service.get_decision_view("paper_main", refresh=True)

    assert envelope.status == "blocked"
    assert envelope.decisions[0].action == "review_exit"
    assert "deterministic promotion threshold" in envelope.blockers[0]
    assert "operator review is required" in envelope.decisions[0].risk_note.lower()


@pytest.mark.asyncio
async def test_research_view_blocks_when_ai_runtime_is_invalid(monkeypatch):
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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _invalid_status,
    )

    envelope = await service.get_research_view("paper_main")

    assert envelope.status == "blocked"
    assert envelope.research is None
    assert "AI runtime" in envelope.blockers[0]


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
                key="ai_runtime",
                label="AI Runtime",
                status=CapabilityStatus.READY,
                summary="AI runtime is ready.",
            )
        ],
        account_id="paper_main",
    )
    learning_service = AsyncMock()
    learning_service.get_learning_summary.return_value = SimpleNamespace(
        model_dump=lambda mode="json": {
            "account_id": "paper_main",
            "wins": 2,
            "losses": 1,
            "top_lessons": ["TCS: prior profitable breakout respected the thesis."],
        }
    )
    learning_service.get_symbol_learning_context.return_value = {
        "symbol": "TCS",
        "recent_lessons": ["TCS: prior profitable breakout respected the thesis."],
        "recent_improvements": ["TCS: keep demanding confirmation volume before entry."],
        "recent_outcomes": ["win"],
    }

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "trading_capability_service": capability_service,
                "paper_trading_learning_service": learning_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    async def _fake_run(**kwargs):
        assert "TCS" in kwargs["prompt"]
        assert "recent_lessons" in kwargs["prompt"]
        assert "top_lessons" in kwargs["prompt"]
        assert kwargs["allowed_tools"] == []
        assert kwargs["model"] == "haiku"
        assert kwargs["timeout_seconds"] == service.FOCUSED_RESEARCH_SYNTHESIS_TIMEOUT_SECONDS
        return (
            kwargs["output_model"](
                thesis="Trend and post-earnings momentum remain constructive.",
                evidence=["Relative strength is holding above sector peers."],
                risks=["Breakout could fail if volume dries up."],
                invalidation="Daily close below the recent base low.",
                confidence=0.74,
                next_step="Promote to a decision packet only if the breakout holds.",
            ),
            {"provider": "codex", "model": "gpt-5.4", "reasoning": "medium"},
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(service, "_run_structured_role", _fake_run)
    monkeypatch.setattr(
        service,
        "_build_focused_research_inputs",
        AsyncMock(
            return_value={
                "screening_snapshot": {
                    "candidate_confidence": 0.82,
                    "candidate_priority": "high",
                    "candidate_rationale": "Trend and earnings strength remain aligned.",
                    "watchlist": {"id": "cand-1", "symbol": "TCS"},
                    "research_ledger": {"symbol": "TCS", "score": 0.82},
                },
                "source_summary": [
                    {
                        "source_type": "research_ledger",
                        "label": "Structured screening ledger",
                        "timestamp": "2026-03-23T09:00:00+00:00",
                        "freshness": "fresh",
                        "detail": "Action BUY at score 0.78",
                    },
                    {
                        "source_type": "technical_context",
                        "label": "OHLCV technical state",
                        "timestamp": "2026-03-23T09:08:00+00:00",
                        "freshness": "fresh",
                        "detail": "TCS is trending higher with strong volume support.",
                    },
                    {
                        "source_type": "codex_web_research",
                        "label": "Fresh external news",
                        "timestamp": "2026-03-23T09:05:00+00:00",
                        "freshness": "fresh",
                        "detail": "Codex web research found a fresh catalyst update.",
                    },
                ],
                "evidence_citations": [
                    {
                        "source_type": "research_ledger",
                        "label": "Structured screening ledger",
                        "reference": "ledger:entry-1",
                        "freshness": "fresh",
                        "timestamp": "2026-03-23T09:00:00+00:00",
                    },
                    {
                        "source_type": "codex_web_research",
                        "label": "Fresh external news",
                        "reference": "https://example.com/tcs-news",
                        "freshness": "fresh",
                        "timestamp": "2026-03-23T09:05:00+00:00",
                    }
                ],
                "market_data_freshness": {
                    "status": "fresh",
                    "summary": "Intraday quote is current enough for operator review.",
                    "timestamp": "2026-03-23T09:10:00+00:00",
                    "age_seconds": 60.0,
                    "provider": "zerodha_kite",
                    "has_intraday_quote": True,
                    "has_historical_data": True,
                },
            }
        ),
    )

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "ready"
    assert envelope.research is not None
    assert envelope.research.symbol == "TCS"
    assert envelope.research.candidate_id == "cand-1"
    assert envelope.research.account_id == "paper_main"
    assert envelope.research.analysis_mode == "fresh_evidence"
    assert envelope.research.actionability == "watch_only"
    assert envelope.research.external_evidence_status == "fresh"
    assert envelope.research.screening_confidence == 0.82
    assert envelope.research.thesis_confidence == 0.57
    assert envelope.research.source_summary[0].source_type == "research_ledger"
    assert any(item.source_type == "codex_web_research" for item in envelope.research.source_summary)
    assert any(item.reference == "ledger:entry-1" for item in envelope.research.evidence_citations)
    assert any(item.reference == "https://example.com/tcs-news" for item in envelope.research.evidence_citations)
    learning_service.record_research_packet.assert_awaited_once()


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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )

    envelope = await service.get_research_view("paper_main")

    assert envelope.status == "empty"
    assert envelope.research is None


@pytest.mark.asyncio
async def test_research_view_blocks_when_ai_runtime_is_usage_limited(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(account_id="paper_main")

    discovery_service = AsyncMock()
    discovery_service.get_watchlist.return_value = [
        {
            "id": "cand-1",
            "symbol": "TCS",
            "company_name": "TCS",
            "discovery_source": "watchlist",
            "confidence_score": 0.8,
            "discovery_reason": "Momentum remains intact.",
        }
    ]
    learning_service = AsyncMock()

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "paper_trading_learning_service": learning_service,
            }
        )
    )

    async def _limited_status():
        return SimpleNamespace(
            is_valid=True,
            rate_limit_info={
                "status": "exhausted",
                "message": "You're out of extra usage · resets 5:30pm (Asia/Calcutta)",
            },
        )

    run_structured_role = AsyncMock()

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _limited_status,
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _limited_status,
    )
    monkeypatch.setattr(service, "_run_structured_role", run_structured_role)

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "blocked"
    assert envelope.research is None
    assert envelope.blockers == [
        "AI runtime is usage-limited for research generation. You're out of extra usage · resets 5:30pm (Asia/Calcutta)"
    ]
    run_structured_role.assert_not_awaited()
    learning_service.record_research_packet.assert_awaited_once()
    assert learning_service.record_research_packet.await_args.args[2].actionability == "blocked"
    assert learning_service.record_research_packet.await_args.args[2].symbol == "TCS"


@pytest.mark.asyncio
async def test_research_view_degrades_when_sdk_rate_limit_hits_mid_run(monkeypatch):
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
            "discovery_source": "watchlist",
            "confidence_score": 0.8,
            "discovery_reason": "Momentum remains intact.",
        }
    ]

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[],
        account_id="paper_main",
    )
    learning_service = AsyncMock()
    learning_service.get_learning_summary.return_value = SimpleNamespace(model_dump=lambda mode="json": {})
    learning_service.get_symbol_learning_context.return_value = {}

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "trading_capability_service": capability_service,
                "paper_trading_learning_service": learning_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        service,
        "_build_focused_research_inputs",
        AsyncMock(
            return_value={
                "screening_snapshot": {"candidate_confidence": 0.8, "watchlist": {"id": "cand-1"}},
                "source_summary": [],
                "evidence_citations": [],
                "market_data_freshness": {},
                "fresh_external_research": {},
            }
        ),
    )

    async def _limited_run(**kwargs):
        raise TradingError(
            "Research agent did not return valid JSON.",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            response="You're out of extra usage · resets 6:30pm (Asia/Calcutta)",
        )

    monkeypatch.setattr(service, "_run_structured_role", _limited_run)

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "blocked"
    assert envelope.research is None
    assert envelope.blockers == [
        "AI runtime is usage-limited for research generation. You're out of extra usage · resets 6:30pm (Asia/Calcutta)"
    ]
    learning_service.record_research_packet.assert_awaited_once()
    assert learning_service.record_research_packet.await_args.args[2].actionability == "blocked"
    assert learning_service.record_research_packet.await_args.args[2].symbol == "TCS"


@pytest.mark.asyncio
async def test_research_view_degrades_when_sdk_spending_cap_hits_mid_run(monkeypatch):
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
            "symbol": "INFY",
            "company_name": "Infosys",
            "discovery_source": "watchlist",
            "confidence_score": 0.8,
            "discovery_reason": "Momentum remains intact.",
        }
    ]

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[],
        account_id="paper_main",
    )
    learning_service = AsyncMock()
    learning_service.get_learning_summary.return_value = SimpleNamespace(model_dump=lambda mode="json": {})
    learning_service.get_symbol_learning_context.return_value = {}

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "trading_capability_service": capability_service,
                "paper_trading_learning_service": learning_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        service,
        "_build_focused_research_inputs",
        AsyncMock(
            return_value={
                "screening_snapshot": {"candidate_confidence": 0.8, "watchlist": {"id": "cand-1"}},
                "source_summary": [],
                "evidence_citations": [],
                "market_data_freshness": {},
                "fresh_external_research": {},
            }
        ),
    )

    async def _limited_run(**kwargs):
        raise TradingError(
            "Research agent did not return valid JSON.",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            response="Spending cap reached resets 11:30pm",
        )

    monkeypatch.setattr(service, "_run_structured_role", _limited_run)

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "blocked"
    assert envelope.research is None
    assert envelope.blockers == [
        "AI runtime is usage-limited for research generation. Spending cap reached resets 11:30pm"
    ]
    learning_service.record_research_packet.assert_awaited_once()
    assert learning_service.record_research_packet.await_args.args[2].actionability == "blocked"
    assert learning_service.record_research_packet.await_args.args[2].symbol == "INFY"


@pytest.mark.asyncio
async def test_research_view_blocks_when_runtime_times_out_mid_run(monkeypatch):
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
            "symbol": "INFY",
            "company_name": "Infosys",
            "discovery_source": "watchlist",
            "confidence_score": 0.8,
            "discovery_reason": "Momentum remains intact.",
        }
    ]

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[],
        account_id="paper_main",
    )
    learning_service = AsyncMock()
    learning_service.get_learning_summary.return_value = SimpleNamespace(model_dump=lambda mode="json": {})
    learning_service.get_symbol_learning_context.return_value = {}

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "trading_capability_service": capability_service,
                "paper_trading_learning_service": learning_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        service,
        "_build_focused_research_inputs",
        AsyncMock(
            return_value={
                "screening_snapshot": {"candidate_confidence": 0.8, "watchlist": {"id": "cand-1"}},
                "source_summary": [],
                "evidence_citations": [],
                "market_data_freshness": {},
                "fresh_external_research": {},
            }
        ),
    )

    async def _timed_out_run(**kwargs):
        raise TradingError(
            "AI runtime timed out during research generation.",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            metadata={
                "runtime_state": "timed_out",
                "provider_error": "Codex runtime timed out after 45.0s.",
            },
        )

    monkeypatch.setattr(service, "_run_structured_role", _timed_out_run)

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "blocked"
    assert envelope.research is None
    assert envelope.blockers == [
        "AI runtime timed out during research generation. Codex runtime timed out after 45.0s."
    ]
    learning_service.record_research_packet.assert_awaited_once()
    assert learning_service.record_research_packet.await_args.args[2].actionability == "blocked"
    assert learning_service.record_research_packet.await_args.args[2].symbol == "INFY"


@pytest.mark.asyncio
async def test_research_view_degrades_when_evidence_is_stale(monkeypatch):
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
            "symbol": "INFY",
            "company_name": "Infosys",
            "sector": "Technology",
            "discovery_source": "watchlist",
            "confidence_score": 0.78,
            "discovery_reason": "Stored setup still looks interesting.",
        }
    ]

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="quote_stream",
                label="Quote Stream",
                status=CapabilityStatus.DEGRADED,
                summary="Live quote stream is delayed.",
            )
        ],
        account_id="paper_main",
    )
    learning_service = AsyncMock()
    learning_service.get_learning_summary.return_value = SimpleNamespace(model_dump=lambda mode="json": {})
    learning_service.get_symbol_learning_context.return_value = {"symbol": "INFY"}

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
                "trading_capability_service": capability_service,
                "paper_trading_learning_service": learning_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    async def _fake_run(**kwargs):
        return (
            kwargs["output_model"](
                research_id="research-2",
                symbol="INFY",
                thesis="The setup remains interesting, but current confirmation is weak.",
                evidence=["Stored discovery context remains constructive."],
                risks=[],
                invalidation="Close below support.",
                confidence=0.88,
            ),
            {"provider": "codex", "model": "gpt-5.4", "reasoning": "medium"},
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(service, "_run_structured_role", _fake_run)
    monkeypatch.setattr(
        service,
        "_build_focused_research_inputs",
        AsyncMock(
            return_value={
                "screening_snapshot": {
                    "candidate_confidence": 0.78,
                    "candidate_priority": "medium",
                    "candidate_rationale": "Stored setup still looks interesting.",
                    "watchlist": {"id": "cand-1", "symbol": "INFY"},
                    "research_ledger": {},
                },
                "source_summary": [
                    {
                        "source_type": "stored_external_research",
                        "label": "Stored discovery research",
                        "timestamp": "2026-03-20T09:00:00+00:00",
                        "freshness": "stale",
                        "detail": "Using stored discovery-time external research for historical context.",
                    },
                    {
                        "source_type": "technical_context",
                        "label": "OHLCV technical state",
                        "timestamp": "2026-03-20T09:00:00+00:00",
                        "freshness": "stale",
                        "detail": "INFY is range-bound with weakening volume.",
                    }
                ],
                "evidence_citations": [],
                "market_data_freshness": {
                    "status": "stale",
                    "summary": "Current market data is stale or unavailable; any thesis should stay watch-only.",
                    "timestamp": "2026-03-20T09:00:00+00:00",
                    "age_seconds": 250000.0,
                    "provider": "zerodha_kite",
                    "has_intraday_quote": False,
                    "has_historical_data": True,
                },
            }
        ),
    )

    envelope = await service.get_research_view("paper_main", refresh=True)

    assert envelope.status == "ready"
    assert "Current market data is stale or unavailable; any thesis should stay watch-only." in envelope.blockers
    assert envelope.research is not None
    assert envelope.research.actionability == "watch_only"
    assert envelope.research.analysis_mode == "stale_evidence"
    assert envelope.research.thesis_confidence <= 0.58


@pytest.mark.asyncio
async def test_collect_focused_research_runtime_inputs_degrades_external_timeout():
    service = AgentArtifactService(_Container({}))
    service.FOCUSED_RESEARCH_EXTERNAL_TIMEOUT_SECONDS = 0.01
    service.FOCUSED_RESEARCH_MARKET_CONTEXT_TIMEOUT_SECONDS = 0.05

    async def _slow_external(symbol: str, *, company_name=None):
        del symbol, company_name
        await asyncio.sleep(0.05)
        return {"evidence": ["should not arrive"]}

    async def _fast_market(symbol: str):
        return {
            "market_data": {"ltp": 100.0, "provider": "zerodha_kite"},
            "market_data_freshness": {
                "status": "fresh",
                "summary": "Intraday quote is current enough for operator review.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "age_seconds": 1.0,
                "provider": "zerodha_kite",
                "has_intraday_quote": True,
                "has_historical_data": True,
            },
            "technical_state": {},
            "historical_data": [],
        }

    service._load_fresh_external_research = _slow_external
    service._load_market_context = _fast_market

    runtime_inputs = await service._collect_focused_research_runtime_inputs(
        symbol="INFY",
        company_name="Infosys",
    )

    assert runtime_inputs["external_research"]["errors"] == ["Codex runtime timed out after 0.0s."]
    assert runtime_inputs["market_context"]["market_data"]["ltp"] == 100.0


@pytest.mark.asyncio
async def test_load_market_context_fetches_fresh_broker_quote_when_cache_is_missing():
    market_data_service = AsyncMock()
    market_data_service.get_market_data.return_value = None

    quote_timestamp = datetime.now(timezone.utc).isoformat()
    kite_service = AsyncMock()
    kite_service.get_quotes.return_value = {
        "INFY": SimpleNamespace(
            last_price=1524.6,
            volume=2750000,
            timestamp=quote_timestamp,
            ohlc={"open": 1510.0, "high": 1530.0, "low": 1504.0, "close": 1501.2},
        )
    }
    kite_service.get_historical_data.return_value = [
        {"date": "2026-03-24T00:00:00+00:00", "close": 1501.2, "volume": 1200000}
    ]

    service = AgentArtifactService(
        _Container(
            {
                "market_data_service": market_data_service,
                "kite_connect_service": kite_service,
            }
        )
    )

    market_context = await service._load_market_context("INFY")

    assert market_context["market_data"]["ltp"] == 1524.6
    assert market_context["market_data"]["provider"] == "zerodha_kite"
    assert market_context["market_data_freshness"]["status"] == "fresh"
    assert market_context["market_data_freshness"]["has_intraday_quote"] is True
    market_data_service.subscribe_market_data.assert_awaited_once_with("INFY")
    kite_service.get_quotes.assert_awaited_once_with(["INFY"])


@pytest.mark.asyncio
async def test_load_market_context_uses_quote_prefight_subscription_before_broker_fallback():
    stale_market_data = SimpleNamespace(
        ltp=428.75,
        open_price=430.0,
        high_price=432.0,
        low_price=425.0,
        close_price=429.5,
        volume=100000,
        timestamp="2026-03-27T09:15:00+05:30",
        provider="zerodha_kite",
    )
    fresh_market_data = SimpleNamespace(
        ltp=431.2,
        open_price=430.0,
        high_price=433.5,
        low_price=429.0,
        close_price=429.5,
        volume=165000,
        timestamp=datetime.now(timezone.utc).isoformat(),
        provider="zerodha_kite",
    )

    market_data_service = AsyncMock()
    market_data_service.get_market_data = AsyncMock(side_effect=[stale_market_data, fresh_market_data])
    market_data_service.subscribe_market_data = AsyncMock(return_value=True)

    kite_service = AsyncMock()
    kite_service.get_quotes.return_value = {}
    kite_service.get_historical_data.return_value = [
        {"date": "2026-03-28T00:00:00+00:00", "close": 429.5, "volume": 120000}
    ]

    service = AgentArtifactService(
        _Container(
            {
                "market_data_service": market_data_service,
                "kite_connect_service": kite_service,
            }
        )
    )
    service.RESEARCH_QUOTE_PREFLIGHT_WAIT_SECONDS = 0.01
    service.RESEARCH_QUOTE_PREFLIGHT_POLL_SECONDS = 0.0

    market_context = await service._load_market_context("DELHIVERY")

    assert market_context["market_data"]["ltp"] == 431.2
    assert market_context["market_data_freshness"]["status"] == "fresh"
    market_data_service.subscribe_market_data.assert_awaited_once_with("DELHIVERY")
    kite_service.get_quotes.assert_not_awaited()


def test_finalize_research_packet_ignores_account_level_market_data_blocker_when_symbol_quote_is_fresh():
    service = AgentArtifactService(_Container({}))
    candidate = SimpleNamespace(
        candidate_id="cand-1",
        symbol="DELHIVERY",
        confidence=0.78,
        rationale="Fresh logistics candidate.",
    )
    research = ResearchPacket(
        research_id="research-1",
        candidate_id="cand-1",
        account_id="paper_main",
        symbol="DELHIVERY",
        thesis="Fresh quote exists, but external evidence is still missing.",
        evidence=["Quote is fresh."],
        risks=[],
        invalidation="Break support.",
        confidence=0.6,
        thesis_confidence=0.6,
        actionability="watch_only",
    )
    research_inputs = {
        "source_summary": [
            {
                "source_type": "discovery_watchlist",
                "label": "Discovery watchlist entry",
                "timestamp": "2026-03-29T06:00:00+00:00",
                "freshness": "fresh",
                "detail": "WATCH",
            },
            {
                "source_type": "market_quote",
                "label": "Current market quote",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "freshness": "fresh",
                "detail": "Intraday quote is current enough for operator review.",
            },
            {
                "source_type": "technical_context",
                "label": "OHLCV technical state",
                "timestamp": "2026-03-29T06:00:00+00:00",
                "freshness": "fresh",
                "detail": "Mixed trend.",
            },
        ],
        "evidence_citations": [],
        "market_data_freshness": {
            "status": "fresh",
            "summary": "Intraday quote is current enough for operator review.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "zerodha_kite",
            "has_intraday_quote": True,
            "has_historical_data": True,
        },
        "fresh_external_research": {
            "errors": ["Codex runtime timed out after 30.0s."],
        },
        "screening_snapshot": {
            "watchlist": {"id": "cand-1"},
        },
    }

    finalized = service._finalize_research_packet(
        research,
        candidate=candidate,
        account_id="paper_main",
        research_inputs=research_inputs,
        capability_summary={
            "blockers": ["Market data cache is stale for active paper-trading symbols."],
        },
    )

    normalized_risks = [risk.lower() for risk in finalized.risks]
    assert "market data cache is stale for active paper-trading symbols." not in normalized_risks
    assert finalized.market_data_freshness.status == "fresh"


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
                key="ai_runtime",
                label="AI Runtime",
                status=CapabilityStatus.READY,
                summary="AI runtime is ready.",
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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )

    envelope = await service.get_review_view("paper_main")

    assert envelope.status == "empty"
    assert envelope.review is None


@pytest.mark.asyncio
async def test_review_view_uses_only_benchmarked_strategy_proposals(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(
        account_id="paper_main",
        current_balance=100000.0,
        buying_power=90000.0,
        monthly_pnl=500.0,
    )
    account_manager.get_open_positions.return_value = [
        SimpleNamespace(
            symbol="INFY",
            quantity=10,
            entry_price=100.0,
            current_price=108.0,
            unrealized_pnl=80.0,
            unrealized_pnl_pct=8.0,
            days_held=3,
            stop_loss=95.0,
            target_price=115.0,
            market_price_status="live",
        )
    ]
    account_manager.get_closed_trades.return_value = []
    account_manager.get_performance_metrics.return_value = {"win_rate": 50.0, "profit_factor": 1.5}

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="ai_runtime",
                label="AI Runtime",
                status=CapabilityStatus.READY,
                summary="AI runtime is ready.",
            )
        ],
        account_id="paper_main",
    )

    improvement_service = AsyncMock()
    improvement_service.get_improvement_report.return_value = SimpleNamespace(
        model_dump=lambda mode="json": {
            "promotable_proposals": [
                {
                    "proposal_id": "improvement_min_confidence_0_50",
                    "title": "Raise Minimum Research Confidence",
                    "summary": "Promote after removing two losses without sacrificing wins.",
                    "rationale": "Low-confidence losses dominate the sample.",
                    "guardrail": "Only trade when research confidence is at least 0.50.",
                }
            ]
        }
    )

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "trading_capability_service": capability_service,
                "paper_trading_improvement_service": improvement_service,
            }
        )
    )

    async def _valid_status():
        return SimpleNamespace(is_valid=True)

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        service,
        "_run_structured_role",
        AsyncMock(
            return_value=(
                ReviewReport(
                    review_id="review-1",
                    summary="Bounded review.",
                    strengths=["Risk was contained."],
                    weaknesses=["Sample remains small."],
                    risk_flags=[],
                    top_lessons=["Wait for stronger setups."],
                    strategy_proposals=[
                        StrategyProposal(
                            proposal_id="freeform",
                            title="Unverified idea",
                            recommendation="Invented by Claude",
                            rationale="Should be overwritten.",
                            guardrail="None",
                        )
                    ],
                ),
                {"provider": "codex", "model": "gpt-5.4", "reasoning": "medium"},
            )
        ),
    )

    envelope = await service.get_review_view("paper_main", refresh=True)

    assert envelope.status == "ready"
    assert len(envelope.review.strategy_proposals) == 1
    assert envelope.review.strategy_proposals[0].proposal_id == "improvement_min_confidence_0_50"
    assert envelope.review.strategy_proposals[0].title == "Raise Minimum Research Confidence"


@pytest.mark.asyncio
async def test_review_view_marks_thin_samples_as_low_confidence(monkeypatch):
    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(
        account_id="paper_main",
        current_balance=100000.0,
        buying_power=98000.0,
        monthly_pnl=0.0,
    )
    account_manager.get_open_positions.return_value = [
        SimpleNamespace(
            symbol="INFY",
            quantity=10,
            entry_price=100.0,
            current_price=101.0,
            unrealized_pnl=10.0,
            unrealized_pnl_pct=1.0,
            days_held=1,
            stop_loss=95.0,
            target_price=110.0,
            market_price_status="live",
        )
    ]
    account_manager.get_closed_trades.return_value = []
    account_manager.get_performance_metrics.return_value = {"win_rate": 0.0, "profit_factor": 0.0}

    capability_service = AsyncMock()
    capability_service.get_snapshot.return_value = TradingCapabilitySnapshot.build(
        mode="paper_only",
        checks=[
            CapabilityCheck(
                key="ai_runtime",
                label="AI Runtime",
                status=CapabilityStatus.READY,
                summary="AI runtime is ready.",
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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
        _valid_status,
    )
    monkeypatch.setattr(
        service,
        "_run_structured_role",
        AsyncMock(
            return_value=(
                ReviewReport(
                    review_id="review-2",
                    summary="Too little realized data to draw strong conclusions.",
                    strengths=["Risk stayed bounded."],
                    weaknesses=["No realized trades yet."],
                    risk_flags=[],
                    top_lessons=[],
                    strategy_proposals=[],
                ),
                {"provider": "codex", "model": "gpt-5.4", "reasoning": "medium"},
            )
        ),
    )

    envelope = await service.get_review_view("paper_main", refresh=True)

    assert envelope.status == "ready"
    assert envelope.review.confidence < service.REVIEW_READY_CONFIDENCE
    assert envelope.blockers
    assert "observational" in envelope.blockers[0].lower()


@pytest.mark.asyncio
async def test_run_structured_role_recreates_and_cleans_up_client(monkeypatch):
    runtime_client = AsyncMock()
    runtime_client.run_focused_research.return_value = {
        "research": {
            "research_id": "r-1",
            "candidate_id": "cand-1",
            "account_id": "paper_main",
            "symbol": "TCS",
            "thesis": "test",
            "evidence": [],
            "risks": [],
            "invalidation": "x",
            "confidence": 0.5,
            "next_step": "y",
        },
        "provider_metadata": {"provider": "codex", "model": "gpt-5.4", "reasoning": "medium"},
    }
    service = AgentArtifactService(
        _Container(
            {
                "codex_runtime_client": runtime_client,
            }
        )
    )
    service.container.config = SimpleNamespace(
        ai_runtime=SimpleNamespace(
            codex_model="gpt-5.4",
            codex_reasoning_light="low",
            codex_reasoning_deep="medium",
        ),
        project_dir="/tmp",
    )

    result, provider_metadata = await service._run_structured_role(
        client_type="agent_research_paper_main",
        role_name="research",
        system_prompt="system",
        prompt="prompt",
        output_model=ResearchPacket,
        allowed_tools=[],
        session_id="research:paper_main",
    )

    assert result.symbol == "TCS"
    assert provider_metadata["provider"] == "codex"
    runtime_client.run_focused_research.assert_awaited_once()
    payload = runtime_client.run_focused_research.await_args.args[0]
    assert payload["reasoning"] == "low"
    assert "The JSON must validate against this schema" not in payload["prompt"]
    assert payload["output_schema"]["additionalProperties"] is False
    assert "required" in payload["output_schema"]
    assert payload["output_schema"]["properties"]["provider_metadata"]["additionalProperties"] is False


@pytest.mark.asyncio
async def test_run_structured_role_parses_fenced_json_when_sdk_appends_rate_limit_event(monkeypatch):
    runtime_client = AsyncMock()
    runtime_client.run_focused_research.return_value = {
        "research": {
            "research_id": "r-1",
            "candidate_id": "cand-1",
            "account_id": "paper_main",
            "symbol": "INFY",
            "thesis": "test",
            "evidence": [],
            "risks": [],
            "invalidation": "x",
            "confidence": 0.5,
            "next_step": "y",
        },
        "provider_metadata": {"provider": "codex", "model": "gpt-5.4", "reasoning": "medium"},
    }
    service = AgentArtifactService(_Container({"codex_runtime_client": runtime_client}))
    service.container.config = SimpleNamespace(
        ai_runtime=SimpleNamespace(
            codex_model="gpt-5.4",
            codex_reasoning_light="low",
            codex_reasoning_deep="medium",
        ),
        project_dir="/tmp",
    )

    result, provider_metadata = await service._run_structured_role(
        client_type="agent_research_paper_main",
        role_name="research",
        system_prompt="system",
        prompt="prompt",
        output_model=ResearchPacket,
        allowed_tools=[],
        session_id="research:paper_main",
    )

    assert result.symbol == "INFY"
    assert provider_metadata["provider"] == "codex"


@pytest.mark.asyncio
async def test_run_structured_role_cleans_up_client_after_sdk_error(monkeypatch):
    runtime_client = AsyncMock()
    runtime_client.run_focused_research.side_effect = CodexRuntimeError("runtime exploded")
    service = AgentArtifactService(_Container({"codex_runtime_client": runtime_client}))
    service.container.config = SimpleNamespace(
        ai_runtime=SimpleNamespace(
            codex_model="gpt-5.4",
            codex_reasoning_light="low",
            codex_reasoning_deep="medium",
        ),
        project_dir="/tmp",
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


def test_finalize_research_packet_marks_partial_external_evidence_and_caps_confidence():
    service = AgentArtifactService(_Container({}))
    candidate = Candidate(
        candidate_id="cand-1",
        symbol="INFY",
        source="stateful_watchlist",
        priority="high",
        confidence=0.82,
        rationale="Fresh setup",
        next_step="Research it",
    )
    research = ResearchPacket(
        research_id="research-1",
        candidate_id="cand-1",
        account_id="paper_main",
        symbol="INFY",
        thesis="Fresh thesis",
        evidence=["Press coverage exists."],
        risks=[],
        invalidation="Break support",
        confidence=0.9,
        thesis_confidence=0.9,
    )

    finalized = service._finalize_research_packet(
        research,
        candidate=candidate,
        account_id="paper_main",
        research_inputs={
            "source_summary": [
                {
                    "source_type": "reputable_financial_news",
                    "label": "Financial daily",
                    "timestamp": "2026-03-25T15:00:00+00:00",
                    "freshness": "fresh",
                    "detail": "Coverage",
                }
            ],
            "evidence_citations": [
                {
                    "source_type": "reputable_financial_news",
                    "label": "Financial daily",
                    "reference": "https://example.com/news",
                    "freshness": "fresh",
                    "timestamp": "2026-03-25T15:00:00+00:00",
                }
            ],
            "market_data_freshness": {
                "status": "stale",
                "summary": "Live quote is stale.",
                "timestamp": "2026-03-25T09:00:00+00:00",
                "provider": "zerodha_kite",
                "has_intraday_quote": True,
                "has_historical_data": True,
            },
            "fresh_external_research": {"errors": ["optional_enrichment: timeout"]},
            "screening_snapshot": {"watchlist": {"id": "cand-1"}},
        },
        capability_summary={"blockers": []},
    )

    assert finalized.external_evidence_status == "partial"
    assert finalized.source_summary[0].tier == "secondary"
    assert finalized.evidence_citations[0].tier == "secondary"
    assert finalized.confidence <= 0.49
