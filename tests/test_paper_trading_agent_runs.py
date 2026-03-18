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
