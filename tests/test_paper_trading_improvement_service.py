import aiosqlite
import pytest

from src.models.agent_artifacts import ResearchPacket
from src.models.paper_trading import AccountType, RiskLevel, TradeType
from src.services.paper_trading_improvement_service import PaperTradingImprovementService
from src.services.paper_trading_learning_service import PaperTradingLearningService
from src.stores.paper_trading_learning_store import PaperTradingLearningStore
from src.stores.paper_trading_store import PaperTradingStore


@pytest.mark.asyncio
async def test_improvement_report_promotes_confidence_guardrail_when_it_removes_losses():
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

    learning_service = PaperTradingLearningService(learning_store, paper_store)
    improvement_service = PaperTradingImprovementService(learning_service, learning_store, paper_store)

    for idx, symbol, confidence, exit_price, realized_pnl in [
        (1, "INFY", 0.30, 95.0, -50.0),
        (2, "TCS", 0.35, 96.0, -40.0),
        (3, "RELIANCE", 0.80, 110.0, 100.0),
        (4, "HDFCBANK", 0.75, 108.0, 80.0),
    ]:
        generated_at = f"2026-03-1{idx}T09:00:00+00:00"
        await learning_service.record_research_packet(
            "paper_main",
            f"cand-{idx}",
            ResearchPacket(
                research_id=f"research-{idx}",
                candidate_id=f"cand-{idx}",
                account_id="paper_main",
                symbol=symbol,
                thesis="Test thesis",
                evidence=["Screening signal."],
                risks=[],
                invalidation="Break support",
                confidence=confidence,
                screening_confidence=confidence,
                thesis_confidence=confidence,
                analysis_mode="fresh_evidence",
                actionability="actionable",
                source_summary=[
                    {
                        "source_type": "research_ledger",
                        "label": "Structured screening ledger",
                        "timestamp": generated_at,
                        "freshness": "fresh",
                        "detail": "Action BUY",
                    },
                    {
                        "source_type": "claude_web_news",
                        "label": "Fresh external news",
                        "timestamp": generated_at,
                        "freshness": "fresh",
                        "detail": "News context",
                    },
                ],
                next_step="Test",
                generated_at=generated_at,
            ),
        )
        trade = await paper_store.create_trade(
            account_id="paper_main",
            symbol=symbol,
            trade_type=TradeType.BUY,
            quantity=10,
            entry_price=100.0,
            strategy_rationale="Test strategy",
            claude_session_id=f"session-{idx}",
        )
        await paper_store.close_trade(trade.trade_id, exit_price=exit_price, realized_pnl=realized_pnl)

    report = await improvement_service.get_improvement_report("paper_main", refresh=True)

    confidence_rule = next(
        item for item in report.benchmarked_proposals if item.proposal_key == "min_confidence_0_50"
    )

    assert report.baseline_trade_count == 4
    assert confidence_rule.decision == "promote"
    assert confidence_rule.skipped_losses == 2
    assert confidence_rule.skipped_wins == 0
    assert confidence_rule.candidate_average_pnl_percentage > confidence_rule.baseline_average_pnl_percentage

    await conn.close()


@pytest.mark.asyncio
async def test_improvement_report_benchmarks_fresh_evidence_guardrail():
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

    learning_service = PaperTradingLearningService(learning_store, paper_store)
    improvement_service = PaperTradingImprovementService(learning_service, learning_store, paper_store)

    cases = [
        ("INFY", "stale_evidence", [{"source_type": "stored_external_research", "label": "Stored", "timestamp": "2026-03-10T09:00:00+00:00", "freshness": "stale", "detail": ""}], 94.0, -60.0),
        ("TCS", "stale_evidence", [{"source_type": "stored_external_research", "label": "Stored", "timestamp": "2026-03-11T09:00:00+00:00", "freshness": "stale", "detail": ""}], 95.0, -50.0),
        ("RELIANCE", "fresh_evidence", [
            {"source_type": "research_ledger", "label": "Ledger", "timestamp": "2026-03-12T09:00:00+00:00", "freshness": "fresh", "detail": ""},
            {"source_type": "claude_web_news", "label": "News", "timestamp": "2026-03-12T09:00:00+00:00", "freshness": "fresh", "detail": ""},
        ], 110.0, 100.0),
        ("HDFCBANK", "fresh_evidence", [
            {"source_type": "research_ledger", "label": "Ledger", "timestamp": "2026-03-13T09:00:00+00:00", "freshness": "fresh", "detail": ""},
            {"source_type": "claude_web_news", "label": "News", "timestamp": "2026-03-13T09:00:00+00:00", "freshness": "fresh", "detail": ""},
        ], 108.0, 80.0),
    ]

    for idx, (symbol, analysis_mode, source_summary, exit_price, realized_pnl) in enumerate(cases, start=1):
        generated_at = f"2026-03-1{idx}T09:00:00+00:00"
        await learning_service.record_research_packet(
            "paper_main",
            f"cand-{idx}",
            ResearchPacket(
                research_id=f"evidence-{idx}",
                candidate_id=f"cand-{idx}",
                account_id="paper_main",
                symbol=symbol,
                thesis="Test thesis",
                evidence=["Evidence mix."],
                risks=[],
                invalidation="Break support",
                confidence=0.65,
                screening_confidence=0.65,
                thesis_confidence=0.65,
                analysis_mode=analysis_mode,
                actionability="watch_only" if analysis_mode != "fresh_evidence" else "actionable",
                source_summary=source_summary,
                next_step="Test",
                generated_at=generated_at,
            ),
        )
        trade = await paper_store.create_trade(
            account_id="paper_main",
            symbol=symbol,
            trade_type=TradeType.BUY,
            quantity=10,
            entry_price=100.0,
            strategy_rationale="Test strategy",
            claude_session_id=f"evidence-session-{idx}",
        )
        await paper_store.close_trade(trade.trade_id, exit_price=exit_price, realized_pnl=realized_pnl)

    report = await improvement_service.get_improvement_report("paper_main", refresh=True)

    evidence_rule = next(
        item for item in report.benchmarked_proposals if item.proposal_key == "require_two_fresh_sources"
    )

    assert evidence_rule.decision == "promote"
    assert evidence_rule.skipped_losses == 2
    assert evidence_rule.skipped_wins == 0

    await conn.close()


@pytest.mark.asyncio
async def test_improvement_report_returns_empty_without_evaluated_trades():
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

    learning_service = PaperTradingLearningService(learning_store, paper_store)
    improvement_service = PaperTradingImprovementService(learning_service, learning_store, paper_store)

    report = await improvement_service.get_improvement_report("paper_main", refresh=True)

    assert report.baseline_trade_count == 0
    assert report.benchmarked_proposals == []
    assert report.promotable_proposals == []

    await conn.close()
