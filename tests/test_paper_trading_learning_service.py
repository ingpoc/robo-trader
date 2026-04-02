import aiosqlite
import pytest

from src.models.agent_artifacts import DecisionPacket, ResearchPacket, ReviewReport
from src.models.paper_trading import AccountType, RiskLevel, TradeType
from src.services.paper_trading_learning_service import PaperTradingLearningService
from src.stores.paper_trading_learning_store import PaperTradingLearningStore
from src.stores.paper_trading_store import PaperTradingStore


@pytest.mark.asyncio
async def test_learning_service_records_research_and_evaluates_closed_trade():
    conn = await aiosqlite.connect(":memory:")
    paper_store = PaperTradingStore(conn)
    learning_store = PaperTradingLearningStore(conn)
    await paper_store.initialize()
    await learning_store.initialize()

    await paper_store.create_account(
        account_name="Paper Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        account_id="paper_main",
    )

    service = PaperTradingLearningService(learning_store, paper_store)
    await service.record_research_packet(
        "paper_main",
        "cand-1",
        ResearchPacket(
            research_id="research-1",
            candidate_id="cand-1",
            account_id="paper_main",
            symbol="INFY",
            thesis="Momentum remains constructive.",
            evidence=["Relative strength improved."],
            risks=["Needs fresh market data."],
            invalidation="Break below support.",
            confidence=0.42,
            screening_confidence=0.55,
            thesis_confidence=0.42,
            analysis_mode="stale_evidence",
            actionability="watch_only",
            why_now="The stock is still near the top of the watchlist.",
            source_summary=[
                {
                    "source_type": "research_ledger",
                    "label": "Structured screening ledger",
                    "timestamp": "2026-03-20T09:00:00+00:00",
                    "freshness": "fresh",
                    "detail": "Action BUY at score 0.66",
                }
            ],
            evidence_citations=[
                {
                    "source_type": "research_ledger",
                    "label": "Structured screening ledger",
                    "reference": "ledger:research-1",
                    "freshness": "fresh",
                    "timestamp": "2026-03-20T09:00:00+00:00",
                }
            ],
            market_data_freshness={
                "status": "stale",
                "summary": "Only historical context is available.",
                "timestamp": "2026-03-20T09:00:00+00:00",
                "provider": "zerodha_kite",
                "has_intraday_quote": False,
                "has_historical_data": True,
            },
            next_step="Wait for confirmation.",
            generated_at="2026-03-20T09:00:00+00:00",
        ),
        sector="Technology",
    )

    trade = await paper_store.create_trade(
        account_id="paper_main",
        symbol="INFY",
        trade_type=TradeType.BUY,
        quantity=10,
        entry_price=100.0,
        strategy_rationale="Test strategy",
        claude_session_id="session-1",
    )
    await paper_store.close_trade(trade.trade_id, exit_price=106.0, realized_pnl=60.0)

    created = await service.evaluate_closed_trades("paper_main")
    summary = await service.get_learning_summary("paper_main", refresh=False)
    symbol_context = await service.get_symbol_learning_context("paper_main", "INFY")
    discovery_memory = await service.get_discovery_memory("paper_main")

    assert len(created) == 1
    assert created[0].outcome == "win"
    assert created[0].research_id == "research-1"
    assert summary.total_evaluations == 1
    assert summary.wins == 1
    assert "INFY" in summary.top_lessons[0]
    assert symbol_context["recent_outcomes"] == ["win"]
    assert symbol_context["latest_research"]["sector"] == "Technology"
    assert symbol_context["latest_research"]["analysis_mode"] == "stale_evidence"
    assert symbol_context["latest_research"]["source_summary"][0]["source_type"] == "research_ledger"
    assert discovery_memory["recent_research"][0]["sector"] == "Technology"

    await conn.close()


@pytest.mark.asyncio
async def test_learning_service_uses_loss_feedback_to_raise_improvement_bar():
    conn = await aiosqlite.connect(":memory:")
    paper_store = PaperTradingStore(conn)
    learning_store = PaperTradingLearningStore(conn)
    await paper_store.initialize()
    await learning_store.initialize()

    await paper_store.create_account(
        account_name="Paper Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        account_id="paper_main",
    )

    service = PaperTradingLearningService(learning_store, paper_store)
    await service.record_research_packet(
        "paper_main",
        "cand-2",
        ResearchPacket(
            research_id="research-2",
            candidate_id="cand-2",
            account_id="paper_main",
            symbol="TCS",
            thesis="Low-conviction setup.",
            evidence=["Weak momentum."],
            risks=["Stale market data blocked validation."],
            invalidation="Breakdown continues.",
            confidence=0.25,
            next_step="Avoid entry without fresh data.",
            generated_at="2026-03-20T09:00:00+00:00",
        ),
    )

    trade = await paper_store.create_trade(
        account_id="paper_main",
        symbol="TCS",
        trade_type=TradeType.BUY,
        quantity=10,
        entry_price=100.0,
        strategy_rationale="Test strategy",
        claude_session_id="session-2",
    )
    await paper_store.close_trade(trade.trade_id, exit_price=96.0, realized_pnl=-40.0)

    await service.evaluate_closed_trades("paper_main")
    summary = await service.get_learning_summary("paper_main", refresh=False)

    assert summary.losses == 1
    assert any("minimum 0.5 confidence" in item for item in summary.improvement_focus)

    await conn.close()


@pytest.mark.asyncio
async def test_learning_service_persists_decision_review_and_retrospective():
    conn = await aiosqlite.connect(":memory:")
    paper_store = PaperTradingStore(conn)
    learning_store = PaperTradingLearningStore(conn)
    await paper_store.initialize()
    await learning_store.initialize()

    await paper_store.create_account(
        account_name="Paper Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        account_id="paper_main",
    )

    service = PaperTradingLearningService(learning_store, paper_store)
    await service.record_decision_packet(
        "paper_main",
        DecisionPacket(
            decision_id="decision-1",
            symbol="INFY",
            action="review_exit",
            confidence=0.74,
            thesis="Drawdown broke the expected tolerance.",
            invalidation="Recover above trend support.",
            next_step="Review an exit before the next session.",
            risk_note="Fresh loss control required.",
        ),
        provider_metadata={"provider": "codex", "model": "gpt-5.4"},
    )
    await service.record_review_report(
        "paper_main",
        ReviewReport(
            review_id="review-1",
            summary="Recent outcomes remain mixed.",
            confidence=0.61,
            strengths=["The operator stayed within manual-only mode."],
            weaknesses=["Research evidence degraded on slow external fetches."],
            risk_flags=["Confidence remains observational."],
            top_lessons=["Protect capital when evidence is thin."],
        ),
        provider_metadata={"provider": "codex", "model": "gpt-5.4"},
    )
    retrospective = await service.create_session_retrospective(
        "paper_main",
        session_id="session-1",
        keep=[{"title": "Manual-only runtime"}],
        remove=[],
        fix=[{"title": "External evidence latency"}],
        improve=[{"title": "Two-stage external research"}],
        evidence=[{"kind": "run_history", "detail": "research stayed within deadline"}],
        owner="paper_trading_operator",
        promotion_state="queued",
    )

    latest_decision = await service.get_latest_decision_packet("paper_main", "INFY")
    latest_review = await service.get_latest_review_report("paper_main")
    latest_retrospective = await service.get_latest_session_retrospective("paper_main")
    queued_improvement = await service.enqueue_promotable_improvement(
        "paper_main",
        title="Promote quote freshness gate",
        summary="Keep stale quote blocks mandatory before trade execution.",
        owner="paper_trading_operator",
        promotion_state="ready_now",
        outcome_evidence=[{"kind": "preflight", "detail": "stale quote was blocked"}],
        benchmark_evidence=[{"kind": "replay", "detail": "historical stale-quote actions were denied"}],
        guardrail="Do not bypass quote freshness checks.",
    )
    outcomes = await service.list_trade_outcomes("paper_main", limit=5)
    improvements = await service.list_promotable_improvements("paper_main", limit=5)
    readiness = await service.get_learning_readiness("paper_main")
    decided = await service.decide_promotable_improvement(
        "paper_main",
        improvement_id=queued_improvement.improvement_id,
        decision="promote",
        owner="paper_trading_operator",
        reason="This is a direct reliability fix.",
        benchmark_evidence=[],
        guardrail="Keep deterministic quote gates intact.",
    )

    assert latest_decision is not None
    assert latest_decision.decision_id == "decision-1"
    assert latest_review is not None
    assert latest_review.review_id == "review-1"
    assert latest_retrospective is not None
    assert latest_retrospective.retrospective_id == retrospective.retrospective_id
    assert outcomes == []
    assert len(improvements) == 1
    assert improvements[0].improvement_id == queued_improvement.improvement_id
    assert readiness.queued_promotable_count == 1
    assert readiness.decision_pending_improvement_count == 1
    assert decided is not None
    assert decided.promotion_state == "ready_now"
    assert decided.decision == "promote"
    assert decided.guardrail == "Keep deterministic quote gates intact."

    await conn.close()


@pytest.mark.asyncio
async def test_learning_service_downgrades_research_policy_promotion_without_benchmark_evidence():
    conn = await aiosqlite.connect(":memory:")
    paper_store = PaperTradingStore(conn)
    learning_store = PaperTradingLearningStore(conn)
    await paper_store.initialize()
    await learning_store.initialize()

    await paper_store.create_account(
        account_name="Paper Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        account_id="paper_main",
    )

    service = PaperTradingLearningService(learning_store, paper_store)
    improvement = await service.enqueue_promotable_improvement(
        "paper_main",
        title="Research threshold tuning",
        summary="Adjust the research confidence threshold before promotion.",
        owner="paper_trading_operator",
        promotion_state="queued",
        category="research_policy",
        outcome_evidence=[{"kind": "outcome", "detail": "low-confidence trades underperformed"}],
        benchmark_evidence=[],
    )

    decided = await service.decide_promotable_improvement(
        "paper_main",
        improvement_id=improvement.improvement_id,
        decision="promote",
        owner="paper_trading_operator",
        reason="Attempting to promote policy change without benchmark evidence.",
        benchmark_evidence=[],
    )

    assert decided is not None
    assert decided.promotion_state == "watch"
    assert decided.decision == "watch"
    assert "benchmark evidence" in decided.decision_reason.lower()

    await conn.close()
