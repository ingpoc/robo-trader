from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.web.routes import paper_trading
from src.models.agent_artifacts import (
    Candidate,
    DiscoveryEnvelope,
    ResearchEnvelope,
    ResearchPacket,
    ReviewEnvelope,
    ReviewReport,
)


def test_paper_trading_router_uses_agent_run_routes_not_legacy_scheduler_triggers():
    paths = {route.path for route in paper_trading.router.routes}

    assert "/api/paper-trading/accounts/{account_id}/research" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning-summary" in paths
    assert "/api/paper-trading/accounts/{account_id}/improvement-report" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/discovery" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/research" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/decision-review" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/daily-review" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/exit-check" in paths

    assert "/api/paper-trading/discovery/trigger-daily" not in paths
    assert "/api/paper-trading/discovery/trigger-sector" not in paths
    assert "/api/paper-trading/discovery/status" not in paths


@pytest.mark.asyncio
async def test_run_paper_trading_discovery_returns_fresh_envelope():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    artifact_service = SimpleNamespace(
        get_discovery_view=AsyncMock(
            return_value=DiscoveryEnvelope(
                status="ready",
                context_mode="watchlist_only",
                artifact_count=1,
                blockers=[],
                candidates=[
                    Candidate(
                        candidate_id="cand-1",
                        symbol="INFY",
                        source="watchlist",
                        priority="high",
                        confidence=0.82,
                        rationale="Relative strength remains strong.",
                        next_step="Build a research packet before any trade decision.",
                    )
                ],
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    response = await paper_trading.run_paper_trading_discovery.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=5,
        container=container,
    )

    assert response["status"] == "ready"
    assert response["artifact_count"] == 1
    assert response["candidates"][0]["symbol"] == "INFY"
    artifact_service.get_discovery_view.assert_awaited_once_with("paper_main", limit=5)


@pytest.mark.asyncio
async def test_run_paper_trading_research_returns_research_envelope():
    request = SimpleNamespace()
    research_request = paper_trading.ResearchRunRequest(candidate_id="cand-1", symbol=None)
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    artifact_service = SimpleNamespace(
        get_research_view=AsyncMock(
            return_value=ResearchEnvelope(
                status="ready",
                context_mode="single_candidate_research",
                artifact_count=1,
                blockers=[],
                research=ResearchPacket(
                    research_id="research-1",
                    candidate_id="cand-1",
                    account_id="paper_main",
                    symbol="INFY",
                    thesis="Momentum remains constructive after earnings.",
                    evidence=["Relative strength remains above peers."],
                    risks=["Breakout may fail if volume fades."],
                    invalidation="Close below breakout pivot.",
                    confidence=0.76,
                    screening_confidence=0.81,
                    thesis_confidence=0.76,
                    analysis_mode="fresh_evidence",
                    actionability="actionable",
                    why_now="Fresh evidence still supports the setup.",
                    source_summary=[
                        {
                            "source_type": "research_ledger",
                            "label": "Structured screening ledger",
                            "timestamp": "2026-03-23T09:00:00+00:00",
                            "freshness": "fresh",
                            "detail": "Action BUY",
                        }
                    ],
                    evidence_citations=[
                        {
                            "source_type": "research_ledger",
                            "label": "Structured screening ledger",
                            "reference": "ledger:entry-1",
                            "freshness": "fresh",
                            "timestamp": "2026-03-23T09:00:00+00:00",
                        }
                    ],
                    market_data_freshness={
                        "status": "fresh",
                        "summary": "Intraday quote is current enough for operator review.",
                        "timestamp": "2026-03-23T09:10:00+00:00",
                        "provider": "zerodha_kite",
                        "has_intraday_quote": True,
                        "has_historical_data": True,
                    },
                    next_step="Only promote if price holds the breakout.",
                ),
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    response = await paper_trading.run_paper_trading_research.__wrapped__(
        request=request,
        account_id="paper_main",
        research_request=research_request,
        container=container,
    )

    assert response["status"] == "ready"
    assert response["research"]["research_id"] == "research-1"
    assert response["research"]["analysis_mode"] == "fresh_evidence"
    assert response["research"]["source_summary"][0]["source_type"] == "research_ledger"
    artifact_service.get_research_view.assert_awaited_once_with(
        "paper_main",
        candidate_id="cand-1",
        symbol=None,
        refresh=True,
    )


@pytest.mark.asyncio
async def test_run_paper_trading_research_returns_blocked_envelope_when_runtime_is_limited():
    request = SimpleNamespace()
    research_request = paper_trading.ResearchRunRequest(candidate_id="cand-1", symbol=None)
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    artifact_service = SimpleNamespace(
        get_research_view=AsyncMock(
            return_value=ResearchEnvelope(
                status="blocked",
                context_mode="single_candidate_research",
                artifact_count=0,
                blockers=[
                    "Claude runtime is usage-limited for research generation. You're out of extra usage · resets 5:30pm (Asia/Calcutta)"
                ],
                research=None,
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    response = await paper_trading.run_paper_trading_research.__wrapped__(
        request=request,
        account_id="paper_main",
        research_request=research_request,
        container=container,
    )

    assert response["status"] == "blocked"
    assert response["research"] is None
    assert "usage-limited" in response["blockers"][0]
    artifact_service.get_research_view.assert_awaited_once_with(
        "paper_main",
        candidate_id="cand-1",
        symbol=None,
        refresh=True,
    )


@pytest.mark.asyncio
async def test_run_paper_trading_daily_review_returns_envelope():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    artifact_service = SimpleNamespace(
        get_review_view=AsyncMock(
            return_value=ReviewEnvelope(
                status="ready",
                context_mode="delta_daily_review",
                artifact_count=1,
                blockers=[],
                review=ReviewReport(
                    review_id="review-1",
                    summary="Risk stayed bounded and no invalidation signals were ignored.",
                    strengths=["Stops were respected."],
                    weaknesses=["No fresh entries met the bar."],
                    risk_flags=[],
                    top_lessons=["Stay patient when the watchlist is thin."],
                    strategy_proposals=[],
                ),
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    response = await paper_trading.run_paper_trading_daily_review.__wrapped__(
        request=request,
        account_id="paper_main",
        container=container,
    )

    assert response["status"] == "ready"
    assert response["review"]["review_id"] == "review-1"
    artifact_service.get_review_view.assert_awaited_once_with("paper_main", refresh=True)


@pytest.mark.asyncio
async def test_get_paper_trading_learning_summary_returns_stateful_feedback():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    learning_service = SimpleNamespace(
        get_learning_summary=AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda mode="json": {
                    "account_id": "paper_main",
                    "total_evaluations": 2,
                    "wins": 1,
                    "losses": 1,
                    "flats": 0,
                    "average_pnl_percentage": 1.2,
                    "top_lessons": ["INFY: profitable trade validated the prior research thesis."],
                    "improvement_focus": ["TCS: require fresh market data before promoting low-confidence setups."],
                    "recent_evaluations": [],
                    "generated_at": "2026-03-23T00:00:00+00:00",
                }
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "paper_trading_learning_service": learning_service,
        }[name])
    )

    response = await paper_trading.get_paper_trading_learning_summary.__wrapped__(
        request=request,
        account_id="paper_main",
        container=container,
    )

    assert response["account_id"] == "paper_main"
    assert response["wins"] == 1
    assert "fresh market data" in response["improvement_focus"][0]
    learning_service.get_learning_summary.assert_awaited_once_with("paper_main", refresh=True)


@pytest.mark.asyncio
async def test_get_paper_trading_improvement_report_returns_benchmarked_proposals():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    improvement_service = SimpleNamespace(
        get_improvement_report=AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda mode="json": {
                    "account_id": "paper_main",
                    "baseline_trade_count": 4,
                    "evaluated_trade_count": 4,
                    "benchmarked_proposals": [
                        {
                            "proposal_id": "improvement_min_confidence_0_50",
                            "proposal_key": "min_confidence_0_50",
                            "decision": "promote",
                            "summary": "Promote after removing two losses without sacrificing wins.",
                        }
                    ],
                    "promotable_proposals": [
                        {
                            "proposal_id": "improvement_min_confidence_0_50",
                            "proposal_key": "min_confidence_0_50",
                            "decision": "promote",
                            "summary": "Promote after removing two losses without sacrificing wins.",
                        }
                    ],
                    "watch_proposals": [],
                    "generated_at": "2026-03-23T00:00:00+00:00",
                }
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "paper_trading_improvement_service": improvement_service,
        }[name])
    )

    response = await paper_trading.get_paper_trading_improvement_report.__wrapped__(
        request=request,
        account_id="paper_main",
        container=container,
    )

    assert response["account_id"] == "paper_main"
    assert response["promotable_proposals"][0]["proposal_key"] == "min_confidence_0_50"
    improvement_service.get_improvement_report.assert_awaited_once_with("paper_main", refresh=True)
