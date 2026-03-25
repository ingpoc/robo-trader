"""Closed-loop paper-trading learning service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.agent_artifacts import ResearchPacket
from src.models.paper_trading_learning import (
    LearningSummary,
    ResearchMemoryEntry,
    TradeOutcomeEvaluation,
)
from src.services.paper_trading.performance_calculator import PerformanceCalculator


class PaperTradingLearningService:
    """Persist research, evaluate outcomes, and expose lessons for future research."""

    def __init__(self, learning_store, paper_trading_store):
        self.learning_store = learning_store
        self.paper_trading_store = paper_trading_store

    async def record_research_packet(
        self,
        account_id: str,
        candidate_id: Optional[str],
        research: ResearchPacket,
    ) -> None:
        entry = ResearchMemoryEntry(
            research_id=research.research_id,
            account_id=account_id,
            candidate_id=candidate_id or research.candidate_id,
            symbol=research.symbol,
            thesis=research.thesis,
            evidence=research.evidence,
            risks=research.risks,
            invalidation=research.invalidation,
            confidence=research.confidence,
            screening_confidence=research.screening_confidence,
            thesis_confidence=research.thesis_confidence,
            analysis_mode=research.analysis_mode,
            actionability=research.actionability,
            why_now=research.why_now,
            source_summary=[item.model_dump(mode="json") for item in research.source_summary],
            evidence_citations=[item.model_dump(mode="json") for item in research.evidence_citations],
            market_data_freshness=research.market_data_freshness.model_dump(mode="json"),
            next_step=research.next_step,
            generated_at=research.generated_at,
        )
        await self.learning_store.store_research_memory(entry.to_store_dict())

    async def evaluate_closed_trades(
        self,
        account_id: str,
        *,
        limit: int = 50,
    ) -> List[TradeOutcomeEvaluation]:
        closed_trades = await self.paper_trading_store.get_closed_trades(account_id, limit=limit)
        created: List[TradeOutcomeEvaluation] = []

        for trade in closed_trades:
            if await self.learning_store.has_trade_evaluation(trade.trade_id):
                continue

            pnl_percentage = self._trade_pnl_percentage(trade)
            outcome = self._categorize_outcome(pnl_percentage)
            holding_days = PerformanceCalculator.calculate_days_held(
                trade.entry_timestamp,
                trade.exit_timestamp,
            )
            research = await self.learning_store.get_latest_research_memory(
                account_id,
                trade.symbol,
                before_timestamp=trade.entry_timestamp,
            )

            lesson = self._build_lesson(trade.symbol, outcome, pnl_percentage, research)
            improvement = self._build_improvement(trade.symbol, outcome, pnl_percentage, research)

            evaluation = TradeOutcomeEvaluation(
                evaluation_id=f"eval_{uuid.uuid4().hex[:16]}",
                account_id=account_id,
                trade_id=trade.trade_id,
                research_id=research.get("research_id") if research else None,
                symbol=trade.symbol,
                outcome=outcome,
                realized_pnl=trade.realized_pnl or 0.0,
                pnl_percentage=round(pnl_percentage, 2),
                holding_days=holding_days,
                lesson=lesson,
                improvement=improvement,
                created_at=trade.exit_timestamp or datetime.utcnow().isoformat(),
            )
            await self.learning_store.store_trade_evaluation(evaluation.to_store_dict())
            created.append(evaluation)

        return created

    async def get_learning_summary(self, account_id: str, *, refresh: bool = True) -> LearningSummary:
        if refresh:
            await self.evaluate_closed_trades(account_id)
        return await self.learning_store.get_learning_summary(account_id)

    async def get_symbol_learning_context(
        self,
        account_id: str,
        symbol: str,
        *,
        limit: int = 3,
    ) -> Dict[str, Any]:
        await self.evaluate_closed_trades(account_id)
        evaluations = await self.learning_store.list_trade_evaluations(account_id, symbol=symbol, limit=limit)
        return {
            "symbol": symbol,
            "recent_lessons": [evaluation.lesson for evaluation in evaluations],
            "recent_improvements": [evaluation.improvement for evaluation in evaluations],
            "recent_outcomes": [evaluation.outcome for evaluation in evaluations],
            "latest_research": await self.learning_store.get_latest_research_memory(account_id, symbol),
        }

    @staticmethod
    def _trade_pnl_percentage(trade: Any) -> float:
        if trade.realized_pnl is not None and trade.entry_price > 0 and trade.quantity > 0:
            capital = trade.entry_price * trade.quantity
            if capital > 0:
                return (trade.realized_pnl / capital) * 100

        if trade.exit_price is not None:
            return PerformanceCalculator.calculate_pnl_percentage(trade.entry_price, trade.exit_price)

        return 0.0

    @staticmethod
    def _categorize_outcome(pnl_percentage: float) -> str:
        if pnl_percentage >= 1.0:
            return "win"
        if pnl_percentage <= -1.0:
            return "loss"
        return "flat"

    @staticmethod
    def _build_lesson(
        symbol: str,
        outcome: str,
        pnl_percentage: float,
        research: Optional[Dict[str, Any]],
    ) -> str:
        confidence = float(research.get("confidence", 0.0)) if research else 0.0
        if outcome == "win":
            if confidence < 0.5:
                return f"{symbol}: profitable despite low prior confidence; screening may be underweighting this setup."
            return f"{symbol}: profitable trade validated the prior research thesis with {pnl_percentage:.2f}% return."
        if outcome == "loss":
            if confidence < 0.5:
                return f"{symbol}: low-confidence trade lost {abs(pnl_percentage):.2f}%; weak-conviction setups should stay filtered."
            return f"{symbol}: trade lost {abs(pnl_percentage):.2f}%; invalidation and entry quality need tightening."
        return f"{symbol}: outcome stayed flat; thesis lacked enough edge to justify capital deployment."

    @staticmethod
    def _build_improvement(
        symbol: str,
        outcome: str,
        pnl_percentage: float,
        research: Optional[Dict[str, Any]],
    ) -> str:
        confidence = float(research.get("confidence", 0.0)) if research else 0.0
        stale_data_risk = any("stale" in risk.lower() for risk in (research or {}).get("risks", []))

        if outcome == "loss" and (confidence < 0.5 or stale_data_risk):
            return f"{symbol}: require fresh market data and minimum 0.5 confidence before promoting research into a trade."
        if outcome == "loss":
            return f"{symbol}: tighten invalidation thresholds and improve entry timing before reusing this thesis pattern."
        if outcome == "win" and confidence < 0.5:
            return f"{symbol}: investigate why the setup worked despite low confidence before adjusting screening weights."
        if outcome == "win":
            return f"{symbol}: preserve the thesis template but keep validating it in paper mode before increasing automation."
        return f"{symbol}: avoid neutral setups unless a clearer catalyst or stronger risk-reward profile appears."
