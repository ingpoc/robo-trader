from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.models.agent_artifacts import ResearchPacket, ReviewReport, StrategyProposal
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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
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
        "src.services.claude_agent.agent_artifact_service.get_claude_status",
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
        return kwargs["output_model"](
            research_id="research-1",
            symbol="TCS",
            thesis="Trend and post-earnings momentum remain constructive.",
            evidence=["Relative strength is holding above sector peers."],
            risks=["Breakout could fail if volume dries up."],
            invalidation="Daily close below the recent base low.",
            confidence=0.74,
            source_summary=[
                {
                    "source_type": "claude_web_news",
                    "label": "Fresh external news",
                    "timestamp": "2026-03-23T09:05:00+00:00",
                    "freshness": "fresh",
                    "detail": "Claude web research found a fresh catalyst update.",
                }
            ],
            evidence_citations=[
                {
                    "source_type": "claude_web_news",
                    "label": "Fresh external news",
                    "reference": "https://example.com/tcs-news",
                    "freshness": "fresh",
                    "timestamp": "2026-03-23T09:05:00+00:00",
                }
            ],
            next_step="Promote to a decision packet only if the breakout holds.",
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
                ],
                "evidence_citations": [
                    {
                        "source_type": "research_ledger",
                        "label": "Structured screening ledger",
                        "reference": "ledger:entry-1",
                        "freshness": "fresh",
                        "timestamp": "2026-03-23T09:00:00+00:00",
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
    assert envelope.research.actionability == "actionable"
    assert envelope.research.screening_confidence == 0.82
    assert envelope.research.thesis_confidence == 0.74
    assert envelope.research.source_summary[0].source_type == "research_ledger"
    assert any(item.source_type == "claude_web_news" for item in envelope.research.source_summary)
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
async def test_research_view_blocks_when_claude_runtime_is_usage_limited(monkeypatch):
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

    service = AgentArtifactService(
        _Container(
            {
                "paper_trading_account_manager": account_manager,
                "stock_discovery_service": discovery_service,
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
        "Claude runtime is usage-limited for research generation. You're out of extra usage · resets 5:30pm (Asia/Calcutta)"
    ]
    run_structured_role.assert_not_awaited()


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
        "Claude runtime is usage-limited for research generation. You're out of extra usage · resets 6:30pm (Asia/Calcutta)"
    ]


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
        "Claude runtime is usage-limited for research generation. Spending cap reached resets 11:30pm"
    ]


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
        return kwargs["output_model"](
            research_id="research-2",
            symbol="INFY",
            thesis="The setup remains interesting, but current confirmation is weak.",
            evidence=["Stored discovery context remains constructive."],
            risks=[],
            invalidation="Close below support.",
            confidence=0.88,
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
    kite_service.get_quotes.assert_awaited_once_with(["INFY"])


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
                key="claude_runtime",
                label="Claude Runtime",
                status=CapabilityStatus.READY,
                summary="Claude runtime is ready.",
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
            return_value=ReviewReport(
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
            )
        ),
    )

    envelope = await service.get_review_view("paper_main", refresh=True)

    assert envelope.status == "ready"
    assert len(envelope.review.strategy_proposals) == 1
    assert envelope.review.strategy_proposals[0].proposal_id == "improvement_min_confidence_0_50"
    assert envelope.review.strategy_proposals[0].title == "Raise Minimum Research Confidence"


@pytest.mark.asyncio
async def test_run_structured_role_recreates_and_cleans_up_client(monkeypatch):
    service = AgentArtifactService(_Container({}))

    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query_only(client, prompt, timeout):
        return None

    async def _receive(client, timeout):
        yield SimpleNamespace(
            structured_output={
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
            }
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.query_only_with_timeout",
        _query_only,
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.receive_response_with_timeout",
        _receive,
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
async def test_run_structured_role_parses_fenced_json_when_sdk_appends_rate_limit_event(monkeypatch):
    service = AgentArtifactService(_Container({}))

    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query_only(client, prompt, timeout):
        return None

    async def _receive(client, timeout):
        yield SimpleNamespace(
            result=(
                "```json\n"
                "{\n"
                '  "research_id":"r-1",\n'
                '  "candidate_id":"cand-1",\n'
                '  "account_id":"paper_main",\n'
                '  "symbol":"INFY",\n'
                '  "thesis":"test",\n'
                '  "evidence":[],\n'
                '  "risks":[],\n'
                '  "invalidation":"x",\n'
                '  "confidence":0.5,\n'
                '  "next_step":"y"\n'
                "}\n"
                "```\n"
                "RateLimitEvent(rate_limit_info=RateLimitInfo(status='allowed'))"
            )
        )

    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.ClaudeSDKClientManager.get_instance",
        AsyncMock(return_value=manager),
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.query_only_with_timeout",
        _query_only,
    )
    monkeypatch.setattr(
        "src.services.claude_agent.agent_artifact_service.receive_response_with_timeout",
        _receive,
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

    assert result.symbol == "INFY"
    manager.cleanup_client.assert_awaited_once_with("agent_research_paper_main")


@pytest.mark.asyncio
async def test_run_structured_role_cleans_up_client_after_sdk_error(monkeypatch):
    service = AgentArtifactService(_Container({}))

    manager = AsyncMock()
    manager.get_client.return_value = object()
    manager.cleanup_client = AsyncMock()

    async def _query_only(client, prompt, timeout):
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
        "src.services.claude_agent.agent_artifact_service.query_only_with_timeout",
        _query_only,
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
