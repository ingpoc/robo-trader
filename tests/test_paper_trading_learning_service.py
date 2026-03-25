import aiosqlite
import pytest

from src.models.agent_artifacts import ResearchPacket
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

    assert len(created) == 1
    assert created[0].outcome == "win"
    assert created[0].research_id == "research-1"
    assert summary.total_evaluations == 1
    assert summary.wins == 1
    assert "INFY" in summary.top_lessons[0]
    assert symbol_context["recent_outcomes"] == ["win"]
    assert symbol_context["latest_research"]["analysis_mode"] == "stale_evidence"
    assert symbol_context["latest_research"]["source_summary"][0]["source_type"] == "research_ledger"

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
