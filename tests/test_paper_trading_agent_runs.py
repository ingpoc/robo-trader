import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.web.routes import paper_trading
from src.models.agent_artifacts import (
    Candidate,
    DecisionEnvelope,
    DecisionPacket,
    DiscoveryEnvelope,
    ResearchEnvelope,
    ResearchPacket,
    ReviewEnvelope,
    ReviewReport,
)


def _assert_manual_run_metadata(response: dict, expected_reason: str) -> None:
    assert response["run_id"].startswith("run_")
    assert response["started_at"]
    assert response["completed_at"]
    assert isinstance(response["duration_ms"], int)
    assert response["duration_ms"] >= 0
    assert response["status_reason"] == expected_reason


def test_paper_trading_router_uses_agent_run_routes_not_legacy_scheduler_triggers():
    paths = {route.path for route in paper_trading.router.routes}

    assert "/api/paper-trading/accounts/{account_id}/research" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning-summary" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning/readiness" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning/evaluate-closed-trades" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning/outcomes" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning/promotable-improvements" in paths
    assert "/api/paper-trading/accounts/{account_id}/learning/promotable-improvements/{improvement_id}/decision" in paths
    assert "/api/paper-trading/accounts/{account_id}/improvement-report" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/discovery" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/research" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/decision-review" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/daily-review" in paths
    assert "/api/paper-trading/accounts/{account_id}/runs/exit-check" in paths
    assert "/api/paper-trading/accounts/{account_id}/positions/health" in paths
    assert "/api/paper-trading/accounts/{account_id}/operator/refresh-readiness" in paths
    assert "/api/paper-trading/accounts/{account_id}/execution/proposal" in paths
    assert "/api/paper-trading/accounts/{account_id}/execution/preflight" in paths
    assert "/api/paper-trading/accounts/{account_id}/retrospectives" in paths
    assert "/api/paper-trading/accounts/{account_id}/retrospectives/latest" in paths
    assert "/api/paper-trading/accounts/{account_id}/operator-snapshot" in paths
    assert "/api/paper-trading/accounts/{account_id}/operator-incidents" in paths
    assert "/api/paper-trading/runtime/validate-ai" in paths
    assert "/api/paper-trading/accounts/{account_id}/runtime/refresh-market-data" in paths

    assert "/api/paper-trading/discovery/trigger-daily" not in paths
    assert "/api/paper-trading/discovery/trigger-sector" not in paths
    assert "/api/paper-trading/discovery/status" not in paths


@pytest.mark.asyncio
async def test_run_paper_trading_discovery_returns_fresh_envelope():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    discovery_service = SimpleNamespace(run_discovery_session=AsyncMock(return_value={"status": "completed"}))
    artifact_service = SimpleNamespace(
        get_discovery_view=AsyncMock(
            return_value=DiscoveryEnvelope(
                status="ready",
                context_mode="stateful_watchlist",
                artifact_count=1,
                blockers=[],
                candidates=[
                    Candidate(
                        candidate_id="cand-1",
                        symbol="INFY",
                        source="stateful_opportunity_funnel",
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
            "stock_discovery_service": discovery_service,
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
    _assert_manual_run_metadata(response, "Manual run completed successfully.")
    discovery_service.run_discovery_session.assert_awaited_once_with(
        session_type="manual_operator_refresh",
        account_id="paper_main",
    )
    artifact_service.get_discovery_view.assert_awaited_once_with("paper_main", limit=5)


@pytest.mark.asyncio
async def test_run_paper_trading_discovery_returns_blocked_envelope_when_runtime_is_limited():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    discovery_service = SimpleNamespace(
        run_discovery_session=AsyncMock(
            return_value={
                "status": "blocked",
                "blockers": ["AI runtime is usage-limited for discovery generation. Try again later."],
            }
        )
    )
    artifact_service = SimpleNamespace(
        get_discovery_view=AsyncMock(
            return_value=DiscoveryEnvelope(
                status="ready",
                context_mode="stateful_watchlist",
                artifact_count=1,
                blockers=[],
                candidates=[
                    Candidate(
                        candidate_id="cand-1",
                        symbol="INFY",
                        source="stateful_opportunity_funnel",
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
            "stock_discovery_service": discovery_service,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    response = await paper_trading.run_paper_trading_discovery.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=5,
        container=container,
    )

    assert response["status"] == "blocked"
    assert response["artifact_count"] == 0
    assert response["candidates"] == []
    assert response["blockers"] == ["AI runtime is usage-limited for discovery generation. Try again later."]
    _assert_manual_run_metadata(
        response,
        "AI runtime is usage-limited for discovery generation. Try again later.",
    )
    artifact_service.get_discovery_view.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_paper_trading_discovery_returns_timeout_blocker_without_hanging(monkeypatch):
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    discovery_service = SimpleNamespace(run_discovery_session=AsyncMock(return_value={"status": "completed"}))
    artifact_service = SimpleNamespace(
        get_discovery_view=AsyncMock(
            return_value=DiscoveryEnvelope(
                status="ready",
                context_mode="stateful_watchlist",
                artifact_count=1,
                blockers=[],
                candidates=[],
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "stock_discovery_service": discovery_service,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    async def _raise_timeout(awaitable, *args, **kwargs):
        awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr("src.web.routes.paper_trading.asyncio.wait_for", _raise_timeout)

    response = await paper_trading.run_paper_trading_discovery.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=5,
        container=container,
    )

    assert response["status"] == "blocked"
    assert response["artifact_count"] == 0
    assert response["candidates"] == []
    assert response["blockers"] == [
        "Manual run exceeded the 60s deadline and was cancelled before completion."
    ]
    _assert_manual_run_metadata(
        response,
        "Manual run exceeded the 60s deadline and was cancelled before completion.",
    )
    discovery_service.run_discovery_session.assert_not_awaited()
    artifact_service.get_discovery_view.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_paper_trading_discovery_is_read_only_and_does_not_trigger_new_run():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    artifact_service = SimpleNamespace(
        get_discovery_view=AsyncMock(
            return_value=DiscoveryEnvelope(
                status="ready",
                context_mode="stateful_watchlist",
                artifact_count=1,
                blockers=[],
                candidates=[
                    Candidate(
                        candidate_id="cand-1",
                        symbol="INFY",
                        source="stateful_opportunity_funnel",
                        priority="high",
                        confidence=0.82,
                        rationale="Relative strength remains strong.",
                        next_step="Build a research packet before any trade decision.",
                    )
                ],
            )
        )
    )
    discovery_service = SimpleNamespace(run_discovery_session=AsyncMock())
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "stock_discovery_service": discovery_service,
            "agent_artifact_service": artifact_service,
        }[name])
    )

    response = await paper_trading.get_paper_trading_discovery.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=5,
        container=container,
    )

    assert response["status"] == "ready"
    assert response["artifact_count"] == 1
    assert response["candidates"][0]["symbol"] == "INFY"
    discovery_service.run_discovery_session.assert_not_awaited()
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
    _assert_manual_run_metadata(response, "Manual run completed successfully.")
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
                    "AI runtime is usage-limited for research generation. You're out of extra usage · resets 5:30pm (Asia/Calcutta)"
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
    _assert_manual_run_metadata(
        response,
        "AI runtime is usage-limited for research generation. You're out of extra usage · resets 5:30pm (Asia/Calcutta)",
    )
    artifact_service.get_research_view.assert_awaited_once_with(
        "paper_main",
        candidate_id="cand-1",
        symbol=None,
        refresh=True,
    )


@pytest.mark.asyncio
async def test_run_paper_trading_decision_review_returns_envelope():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    artifact_service = SimpleNamespace(
        get_decision_view=AsyncMock(
            return_value=DecisionEnvelope(
                status="ready",
                context_mode="delta_position_review",
                artifact_count=1,
                blockers=[],
                decisions=[
                    DecisionPacket(
                        decision_id="decision-1",
                        symbol="INFY",
                        action="hold",
                        confidence=0.74,
                        thesis="Trend is still intact.",
                        invalidation="Close below prior swing low.",
                        next_step="Hold and re-evaluate tomorrow.",
                        risk_note="Fresh market data is available.",
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

    response = await paper_trading.run_paper_trading_decision_review.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=3,
        container=container,
    )

    assert response["status"] == "ready"
    assert response["decisions"][0]["decision_id"] == "decision-1"
    _assert_manual_run_metadata(response, "Manual run completed successfully.")
    artifact_service.get_decision_view.assert_awaited_once_with("paper_main", limit=3, refresh=True)


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
    _assert_manual_run_metadata(response, "Manual run completed successfully.")
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
async def test_get_paper_trading_run_history_returns_recent_manual_runs():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    store = SimpleNamespace(
        get_manual_run_audit_entries=AsyncMock(
            return_value=[
                {
                    "run_id": "run_b",
                    "route_name": "paper_trading.review",
                    "status": "blocked",
                    "status_reason": "runtime unavailable",
                },
                {
                    "run_id": "run_a",
                    "route_name": "paper_trading.discovery",
                    "status": "ready",
                    "status_reason": "ok",
                },
            ]
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "paper_trading_store": store,
        }[name])
    )

    response = await paper_trading.get_paper_trading_run_history.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=10,
        container=container,
    )

    assert response["account_id"] == "paper_main"
    assert response["count"] == 2
    assert response["runs"][0]["run_id"] == "run_b"
    store.get_manual_run_audit_entries.assert_awaited_once_with("paper_main", limit=10)


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


@pytest.mark.asyncio
async def test_get_paper_trading_operator_snapshot_returns_incidents(monkeypatch):
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    expected_snapshot = {
        "generated_at": "2026-03-28T00:00:00+00:00",
        "selected_account_id": "paper_main",
        "health": {"status": "healthy"},
        "configuration_status": {"status": "manual_only"},
        "queue_status": {"status": "healthy"},
        "capability_snapshot": {"overall_status": "blocked"},
        "overview": {"accountId": "paper_main"},
        "positions": [],
        "trades": [],
        "performance": {"period": "month"},
        "discovery": {"status": "empty"},
        "decisions": {"status": "blocked"},
        "review": {"status": "empty"},
        "learning_summary": {"account_id": "paper_main"},
        "improvement_report": {"account_id": "paper_main"},
        "run_history": {"account_id": "paper_main", "count": 0, "runs": []},
        "incidents": [
            {
                "incident_id": "capability:ai_runtime",
                "type": "capability",
                "summary": "AI runtime is not ready.",
            }
        ],
    }
    build_snapshot = AsyncMock(return_value=expected_snapshot)
    monkeypatch.setattr(paper_trading, "_build_operator_snapshot_payload", build_snapshot)
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
        }[name])
    )

    response = await paper_trading.get_paper_trading_operator_snapshot.__wrapped__(
        request=request,
        account_id="paper_main",
        container=container,
    )

    assert response["selected_account_id"] == "paper_main"
    assert response["incidents"][0]["incident_id"] == "capability:ai_runtime"
    build_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_paper_trading_ai_runtime_returns_live_status(monkeypatch):
    request = SimpleNamespace()
    runtime_status = SimpleNamespace(
        to_dict=lambda: {
            "status": "connected",
            "provider": "codex",
            "is_valid": True,
        }
    )
    get_ai_runtime_status = AsyncMock(return_value=runtime_status)
    monkeypatch.setattr(paper_trading, "get_ai_runtime_status", get_ai_runtime_status)
    capability_service = SimpleNamespace(
        get_snapshot=AsyncMock(
            return_value=SimpleNamespace(
                to_dict=lambda: {"overall_status": "ready", "checks": []},
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "trading_capability_service": capability_service,
        }[name])
    )

    response = await paper_trading.validate_paper_trading_ai_runtime.__wrapped__(
        request=request,
        account_id=None,
        container=container,
    )

    assert response["ai_runtime"]["provider"] == "codex"
    assert response["capability_snapshot"]["overall_status"] == "ready"
    get_ai_runtime_status.assert_awaited_once_with(force_refresh=True)
    capability_service.get_snapshot.assert_awaited_once_with(account_id=None)


@pytest.mark.asyncio
async def test_refresh_paper_trading_market_data_runtime_resubscribes_open_symbols():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    store = SimpleNamespace(
        get_open_trades=AsyncMock(
            return_value=[
                SimpleNamespace(symbol="INFY"),
                SimpleNamespace(symbol="TCS"),
                SimpleNamespace(symbol="INFY"),
            ]
        )
    )
    market_data_service = SimpleNamespace(
        subscribe_market_data=AsyncMock(return_value=True),
        refresh_active_subscriptions=AsyncMock(return_value=["INFY", "TCS"]),
        get_quote_stream_status=AsyncMock(
            return_value=SimpleNamespace(
                to_metadata=lambda: {"status": "connected", "active_symbols": 2},
            )
        ),
    )
    capability_service = SimpleNamespace(
        get_snapshot=AsyncMock(
            return_value=SimpleNamespace(
                to_dict=lambda: {"overall_status": "ready", "checks": []},
            )
        )
    )
    container = SimpleNamespace(
        get=AsyncMock(side_effect=lambda name: {
            "paper_trading_account_manager": account_manager,
            "paper_trading_store": store,
            "market_data_service": market_data_service,
            "trading_capability_service": capability_service,
        }[name])
    )

    response = await paper_trading.refresh_paper_trading_market_data_runtime.__wrapped__(
        request=request,
        account_id="paper_main",
        container=container,
    )

    assert response["status"] == "ready"
    assert response["symbols_requested"] == ["INFY", "TCS"]
    assert response["symbols_subscribed"] == ["INFY", "TCS"]
    assert response["quote_stream_status"]["active_symbols"] == 2
    market_data_service.subscribe_market_data.assert_any_await("INFY")
    market_data_service.subscribe_market_data.assert_any_await("TCS")


@pytest.mark.asyncio
async def test_execution_preflight_denies_stale_quote_and_weak_research():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(
        get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")),
        get_open_positions=AsyncMock(return_value=[]),
    )
    market_data_service = SimpleNamespace(
        get_market_data=AsyncMock(
            return_value=SimpleNamespace(
                timestamp="2026-03-20T09:00:00+00:00",
                ltp=123.4,
                provider="zerodha_kite",
            )
        ),
        subscribe_market_data=AsyncMock(return_value=True),
    )
    learning_service = SimpleNamespace(
        learning_store=SimpleNamespace(
            get_latest_research_memory=AsyncMock(
                return_value={
                    "research_id": "research-1",
                    "confidence": 0.41,
                    "actionability": "watch_only",
                    "external_evidence_status": "partial",
                }
            )
        ),
        get_latest_decision_packet=AsyncMock(return_value=None),
        get_latest_review_report=AsyncMock(return_value=None),
    )
    container = SimpleNamespace(
        get=AsyncMock(
            side_effect=lambda name: {
                "paper_trading_account_manager": account_manager,
                "paper_trading_store": SimpleNamespace(get_trade=AsyncMock(return_value=None)),
                "paper_trading_learning_service": learning_service,
                "market_data_service": market_data_service,
                "queue_state_repository": None,
            }[name]
        )
    )

    response = await paper_trading.validate_paper_trading_execution_preflight.__wrapped__(
        request=request,
        account_id="paper_main",
        body=paper_trading.ExecutionPreflightRequest(
            action="buy",
            symbol="INFY",
            quantity=5,
            dry_run=True,
        ),
        container=container,
    )

    assert response["allowed"] is False
    assert response["freshness"]["status"] == "stale"
    assert response["research_gate"]["passed"] is False
    assert any("fresh live quote" in reason.lower() or "stale" in reason.lower() for reason in response["reasons"])
    assert any("research packet" in reason.lower() for reason in response["reasons"])


@pytest.mark.asyncio
async def test_create_retrospective_persists_and_queues_improvements():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    retrospective = SimpleNamespace(
        retrospective_id="retro-1",
        model_dump=lambda mode="json": {"retrospective_id": "retro-1"},
    )
    queued = SimpleNamespace(model_dump=lambda mode="json": {"improvement_id": "impr-1", "promotion_state": "ready_now"})
    learning_service = SimpleNamespace(
        create_session_retrospective=AsyncMock(return_value=retrospective),
        enqueue_promotable_improvement=AsyncMock(return_value=queued),
    )
    container = SimpleNamespace(
        get=AsyncMock(
            side_effect=lambda name: {
                "paper_trading_account_manager": account_manager,
                "paper_trading_learning_service": learning_service,
            }[name]
        )
    )

    response = await paper_trading.create_paper_trading_retrospective.__wrapped__(
        request=request,
        account_id="paper_main",
        body=paper_trading.SessionRetrospectiveRequest(
            improve=[
                {
                    "title": "Repair quote freshness gate",
                    "summary": "Promote the quote preflight fix.",
                    "category": "truthfulness",
                }
            ],
            evidence=[{"kind": "api", "detail": "execution preflight denied stale marks"}],
        ),
        container=container,
    )

    assert response["retrospective"]["retrospective_id"] == "retro-1"
    assert response["queued_improvements"][0]["promotion_state"] == "ready_now"
    learning_service.enqueue_promotable_improvement.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_learning_outcomes_returns_lineage_payload():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    evaluation = SimpleNamespace(
        model_dump=lambda mode="json": {
            "evaluation_id": "eval-1",
            "trade_id": "trade-1",
            "symbol": "INFY",
            "artifact_lineage": {"research_id": "research-1", "decision_id": "decision-1"},
        }
    )
    learning_service = SimpleNamespace(
        list_trade_outcomes=AsyncMock(return_value=[evaluation]),
    )
    container = SimpleNamespace(
        get=AsyncMock(
            side_effect=lambda name: {
                "paper_trading_account_manager": account_manager,
                "paper_trading_learning_service": learning_service,
            }[name]
        )
    )

    response = await paper_trading.get_paper_trading_learning_outcomes.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=5,
        symbol="INFY",
        container=container,
    )

    assert response["account_id"] == "paper_main"
    assert response["count"] == 1
    assert response["evaluations"][0]["artifact_lineage"]["decision_id"] == "decision-1"
    learning_service.list_trade_outcomes.assert_awaited_once_with("paper_main", symbol="INFY", limit=5)


@pytest.mark.asyncio
async def test_get_promotable_improvements_returns_queue_payload():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    improvement = SimpleNamespace(
        model_dump=lambda mode="json": {
            "improvement_id": "impr-1",
            "title": "Keep quote freshness gate",
            "promotion_state": "ready_now",
        }
    )
    learning_service = SimpleNamespace(
        list_promotable_improvements=AsyncMock(return_value=[improvement]),
    )
    container = SimpleNamespace(
        get=AsyncMock(
            side_effect=lambda name: {
                "paper_trading_account_manager": account_manager,
                "paper_trading_learning_service": learning_service,
            }[name]
        )
    )

    response = await paper_trading.get_paper_trading_promotable_improvements.__wrapped__(
        request=request,
        account_id="paper_main",
        limit=5,
        container=container,
    )

    assert response["account_id"] == "paper_main"
    assert response["count"] == 1
    assert response["improvements"][0]["promotion_state"] == "ready_now"
    learning_service.list_promotable_improvements.assert_awaited_once_with("paper_main", limit=5)


@pytest.mark.asyncio
async def test_evaluate_closed_trades_returns_created_evaluations_and_readiness():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    evaluation = SimpleNamespace(model_dump=lambda mode="json": {"evaluation_id": "eval-1", "trade_id": "trade-1"})
    readiness = SimpleNamespace(model_dump=lambda mode="json": {"unevaluated_closed_trade_count": 0})
    summary = SimpleNamespace(model_dump=lambda mode="json": {"total_evaluations": 1})
    learning_service = SimpleNamespace(
        evaluate_closed_trades=AsyncMock(return_value=[evaluation]),
        get_learning_readiness=AsyncMock(return_value=readiness),
        get_learning_summary=AsyncMock(return_value=summary),
    )
    container = SimpleNamespace(
        get=AsyncMock(
            side_effect=lambda name: {
                "paper_trading_account_manager": account_manager,
                "paper_trading_learning_service": learning_service,
            }[name]
        )
    )

    response = await paper_trading.evaluate_paper_trading_closed_trades.__wrapped__(
        request=request,
        account_id="paper_main",
        body=paper_trading.EvaluateClosedTradesRequest(limit=10, symbol="INFY"),
        container=container,
    )

    assert response["created_count"] == 1
    assert response["evaluations"][0]["evaluation_id"] == "eval-1"
    assert response["learning_readiness"]["unevaluated_closed_trade_count"] == 0
    learning_service.evaluate_closed_trades.assert_awaited_once_with("paper_main", limit=10, symbol="INFY")


@pytest.mark.asyncio
async def test_decide_promotable_improvement_returns_updated_decision():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    updated = SimpleNamespace(
        decision="watch",
        model_dump=lambda mode="json": {"improvement_id": "impr-1", "promotion_state": "watch", "decision": "watch"},
    )
    recent = SimpleNamespace(decision="watch", model_dump=lambda mode="json": {"improvement_id": "impr-1", "decision": "watch"})
    learning_service = SimpleNamespace(
        decide_promotable_improvement=AsyncMock(return_value=updated),
        list_promotable_improvements=AsyncMock(return_value=[recent]),
    )
    container = SimpleNamespace(
        get=AsyncMock(
            side_effect=lambda name: {
                "paper_trading_account_manager": account_manager,
                "paper_trading_learning_service": learning_service,
            }[name]
        )
    )

    response = await paper_trading.decide_paper_trading_promotable_improvement.__wrapped__(
        request=request,
        account_id="paper_main",
        improvement_id="impr-1",
        body=paper_trading.PromotableImprovementDecisionRequest(decision="watch", reason="Need replay evidence."),
        container=container,
    )

    assert response["improvement"]["promotion_state"] == "watch"
    assert response["latest_improvement_decisions"][0]["decision"] == "watch"
    learning_service.decide_promotable_improvement.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_execution_proposal_includes_exact_payload_and_proposal_id():
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    container = SimpleNamespace(get=AsyncMock(return_value=account_manager))

    original = paper_trading._build_execution_preflight_payload
    paper_trading._build_execution_preflight_payload = AsyncMock(
        return_value={
            "allowed": True,
            "account_id": "paper_main",
            "action": "buy",
            "symbol": "INFY",
            "trade_id": None,
            "freshness": {"status": "fresh"},
            "risk_checks": {"queue_clean": True},
            "research_gate": {"passed": True},
            "decision_gate": {"passed": True},
            "reasons": [],
            "idempotency_key": "ptx_123",
            "state_signature": "pts_123",
        }
    )
    try:
        response = await paper_trading.build_paper_trading_execution_proposal.__wrapped__(
            request=request,
            account_id="paper_main",
            body=paper_trading.ExecutionPreflightRequest(action="buy", symbol="INFY", quantity=5, dry_run=False),
            container=container,
        )
    finally:
        paper_trading._build_execution_preflight_payload = original

    assert response["proposal_id"].startswith("proposal_")
    assert response["exact_action_payload"]["symbol"] == "INFY"
    assert response["exact_action_payload"]["quantity"] == 5
    assert response["http_method"] == "POST"


@pytest.mark.asyncio
async def test_refresh_operator_readiness_returns_snapshot(monkeypatch):
    request = SimpleNamespace()
    account_manager = SimpleNamespace(get_account=AsyncMock(return_value=SimpleNamespace(account_id="paper_main")))
    container = SimpleNamespace(get=AsyncMock(return_value=account_manager))
    snapshot = {"selected_account_id": "paper_main", "health": {"status": "healthy"}}

    async def fake_build_operator_snapshot_payload(**kwargs):
        return snapshot

    monkeypatch.setattr(paper_trading, "_build_operator_snapshot_payload", fake_build_operator_snapshot_payload)

    response = await paper_trading.refresh_paper_trading_operator_readiness.__wrapped__(
        request=request,
        account_id="paper_main",
        container=container,
    )

    assert response["snapshot"]["selected_account_id"] == "paper_main"
