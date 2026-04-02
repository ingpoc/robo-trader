"""Closed-loop paper-trading learning service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.models.agent_artifacts import DecisionPacket, ResearchPacket, ReviewReport
from src.models.paper_trading_learning import (
    DecisionMemoryEntry,
    LearningReadinessSummary,
    LearningSummary,
    PromotableImprovement,
    ResearchMemoryEntry,
    ReviewMemoryEntry,
    SessionRetrospective,
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
        *,
        sector: Optional[str] = None,
    ) -> None:
        entry = ResearchMemoryEntry(
            research_id=research.research_id,
            account_id=account_id,
            candidate_id=candidate_id or research.candidate_id,
            symbol=research.symbol,
            sector=sector or "",
            thesis=research.thesis,
            evidence=research.evidence,
            risks=research.risks,
            invalidation=research.invalidation,
            confidence=research.confidence,
            screening_confidence=research.screening_confidence,
            thesis_confidence=research.thesis_confidence,
            analysis_mode=research.analysis_mode,
            actionability=research.actionability,
            external_evidence_status=research.external_evidence_status,
            why_now=research.why_now,
            source_summary=[item.model_dump(mode="json") for item in research.source_summary],
            evidence_citations=[item.model_dump(mode="json") for item in research.evidence_citations],
            market_data_freshness=research.market_data_freshness.model_dump(mode="json"),
            next_step=research.next_step,
            provider_metadata=research.provider_metadata,
            generated_at=research.generated_at,
        )
        await self.learning_store.store_research_memory(entry.to_store_dict())

    async def evaluate_closed_trades(
        self,
        account_id: str,
        *,
        limit: int = 50,
        symbol: Optional[str] = None,
    ) -> List[TradeOutcomeEvaluation]:
        closed_trades = await self.paper_trading_store.get_closed_trades(account_id, symbol=symbol, limit=limit)
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
            decision = await self.learning_store.get_latest_decision_memory(account_id, trade.symbol)
            review = await self.learning_store.get_latest_review_memory(account_id)

            lesson = self._build_lesson(trade.symbol, outcome, pnl_percentage, research)
            improvement = self._build_improvement(trade.symbol, outcome, pnl_percentage, research)
            artifact_lineage = {
                "candidate_id": research.get("candidate_id") if research else None,
                "research_id": research.get("research_id") if research else None,
                "decision_id": getattr(decision, "decision_id", None),
                "review_id": getattr(review, "review_id", None),
                "research_generated_at": research.get("generated_at") if research else None,
                "decision_generated_at": getattr(decision, "generated_at", None),
                "review_generated_at": getattr(review, "generated_at", None),
            }
            prompt_model_metadata = {
                "research": (research or {}).get("provider_metadata", {}),
                "decision": getattr(decision, "provider_metadata", {}),
                "review": getattr(review, "provider_metadata", {}),
            }

            evaluation = TradeOutcomeEvaluation(
                evaluation_id=f"eval_{uuid.uuid4().hex[:16]}",
                account_id=account_id,
                trade_id=trade.trade_id,
                candidate_id=research.get("candidate_id") if research else None,
                research_id=research.get("research_id") if research else None,
                decision_id=getattr(decision, "decision_id", None),
                review_id=getattr(review, "review_id", None),
                symbol=trade.symbol,
                outcome=outcome,
                realized_pnl=trade.realized_pnl or 0.0,
                pnl_percentage=round(pnl_percentage, 2),
                holding_days=holding_days,
                lesson=lesson,
                improvement=improvement,
                artifact_lineage=artifact_lineage,
                prompt_model_metadata=prompt_model_metadata,
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

    async def get_discovery_memory(
        self,
        account_id: str,
        *,
        limit: int = 20,
    ) -> Dict[str, Any]:
        await self.evaluate_closed_trades(account_id)
        recent_research = await self.learning_store.list_recent_research_memory(account_id, limit=limit)
        evaluations = await self.learning_store.list_trade_evaluations(account_id, limit=limit)
        return {
            "account_id": account_id,
            "recent_research": recent_research,
            "recent_evaluations": [evaluation.model_dump(mode="json") for evaluation in evaluations],
            "recent_symbols": [entry.get("symbol") for entry in recent_research if entry.get("symbol")],
            "recently_blocked_symbols": [
                entry.get("symbol")
                for entry in recent_research
                if entry.get("symbol") and entry.get("actionability") == "blocked"
            ],
        }

    async def record_decision_packet(
        self,
        account_id: str,
        decision: DecisionPacket,
        *,
        provider_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = DecisionMemoryEntry(
            decision_id=decision.decision_id,
            account_id=account_id,
            symbol=decision.symbol,
            action=decision.action,
            confidence=decision.confidence,
            thesis=decision.thesis,
            invalidation=decision.invalidation,
            next_step=decision.next_step,
            risk_note=decision.risk_note,
            provider_metadata=provider_metadata or {},
            generated_at=decision.generated_at,
        )
        await self.learning_store.store_decision_memory(entry.to_store_dict())

    async def get_latest_decision_packet(
        self,
        account_id: str,
        symbol: str,
    ) -> Optional[DecisionMemoryEntry]:
        return await self.learning_store.get_latest_decision_memory(account_id, symbol)

    async def record_review_report(
        self,
        account_id: str,
        review: ReviewReport,
        *,
        provider_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = ReviewMemoryEntry(
            review_id=review.review_id,
            account_id=account_id,
            summary=review.summary,
            confidence=review.confidence,
            strengths=review.strengths,
            weaknesses=review.weaknesses,
            risk_flags=review.risk_flags,
            top_lessons=review.top_lessons,
            strategy_proposals=[proposal.model_dump(mode="json") for proposal in review.strategy_proposals],
            provider_metadata=provider_metadata or {},
            generated_at=review.generated_at,
        )
        await self.learning_store.store_review_memory(entry.to_store_dict())

    async def get_latest_review_report(self, account_id: str) -> Optional[ReviewMemoryEntry]:
        return await self.learning_store.get_latest_review_memory(account_id)

    async def create_session_retrospective(
        self,
        account_id: str,
        *,
        session_id: Optional[str],
        keep: List[Dict[str, Any]],
        remove: List[Dict[str, Any]],
        fix: List[Dict[str, Any]],
        improve: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        owner: str = "paper_trading_operator",
        promotion_state: str = "queued",
    ) -> SessionRetrospective:
        retrospective = SessionRetrospective(
            retrospective_id=f"retro_{uuid.uuid4().hex[:16]}",
            session_id=session_id or f"session_{uuid.uuid4().hex[:12]}",
            account_id=account_id,
            keep=keep,
            remove=remove,
            fix=fix,
            improve=improve,
            evidence=evidence,
            owner=owner,
            promotion_state=promotion_state,
        )
        await self.learning_store.store_session_retrospective(retrospective.to_store_dict())
        return retrospective

    async def get_latest_session_retrospective(self, account_id: str) -> Optional[SessionRetrospective]:
        return await self.learning_store.get_latest_session_retrospective(account_id)

    async def get_learning_readiness(
        self,
        account_id: str,
        *,
        limit: int = 500,
    ) -> LearningReadinessSummary:
        closed_trades = await self.paper_trading_store.get_closed_trades(account_id, limit=limit)
        evaluations = await self.learning_store.list_trade_evaluations(account_id, limit=limit)
        improvements = await self.learning_store.list_promotable_improvements(account_id, limit=limit)
        retrospective = await self.learning_store.get_latest_session_retrospective(account_id)

        evaluated_trade_ids = {evaluation.trade_id for evaluation in evaluations}
        decision_pending_count = sum(1 for improvement in improvements if not improvement.decision)
        queued_count = sum(
            1
            for improvement in improvements
            if str(improvement.promotion_state) in {"queued", "ready_now", "watch"}
        )

        return LearningReadinessSummary(
            account_id=account_id,
            closed_trade_count=len(closed_trades),
            evaluated_trade_count=len(evaluations),
            unevaluated_closed_trade_count=max(0, len([trade for trade in closed_trades if trade.trade_id not in evaluated_trade_ids])),
            queued_promotable_count=queued_count,
            decision_pending_improvement_count=decision_pending_count,
            latest_retrospective_at=getattr(retrospective, "generated_at", None),
        )

    async def list_trade_outcomes(
        self,
        account_id: str,
        *,
        symbol: Optional[str] = None,
        limit: int = 20,
    ) -> List[TradeOutcomeEvaluation]:
        return await self.learning_store.list_trade_evaluations(
            account_id,
            symbol=symbol,
            limit=limit,
        )

    async def list_promotable_improvements(
        self,
        account_id: str,
        *,
        limit: int = 20,
    ) -> List[PromotableImprovement]:
        return await self.learning_store.list_promotable_improvements(account_id, limit=limit)

    async def enqueue_promotable_improvement(
        self,
        account_id: str,
        *,
        title: str,
        summary: str,
        owner: str,
        promotion_state: str,
        category: str = "",
        retrospective_id: Optional[str] = None,
        outcome_evidence: List[Dict[str, Any]],
        benchmark_evidence: List[Dict[str, Any]],
        guardrail: str = "",
    ) -> PromotableImprovement:
        improvement = PromotableImprovement(
            improvement_id=f"impr_{uuid.uuid4().hex[:16]}",
            account_id=account_id,
            title=title,
            summary=summary,
            owner=owner,
            promotion_state=promotion_state,
            category=category,
            retrospective_id=retrospective_id,
            outcome_evidence=outcome_evidence,
            benchmark_evidence=benchmark_evidence,
            guardrail=guardrail,
        )
        await self.learning_store.store_promotable_improvement(improvement.to_store_dict())
        return improvement

    async def decide_promotable_improvement(
        self,
        account_id: str,
        *,
        improvement_id: str,
        decision: str,
        owner: str,
        reason: str,
        benchmark_evidence: List[Dict[str, Any]],
        guardrail: str = "",
    ) -> Optional[PromotableImprovement]:
        improvement = await self.learning_store.get_promotable_improvement(account_id, improvement_id)
        if improvement is None:
            return None

        category = str(improvement.category or "").strip().lower()
        content = f"{improvement.title} {improvement.summary} {category}".lower()
        benchmark_required = any(term in content for term in ("research", "prompt", "policy", "threshold"))

        normalized_decision = decision.strip().lower()
        normalized_reason = reason.strip()
        if normalized_decision == "promote" and benchmark_required and not benchmark_evidence:
            normalized_decision = "watch"
            governance_note = "Promotion was downgraded to watch because benchmark evidence is required for research or policy changes."
            normalized_reason = f"{normalized_reason} {governance_note}".strip()

        promotion_state = {
            "promote": "ready_now",
            "watch": "watch",
            "reject": "rejected",
        }.get(normalized_decision, improvement.promotion_state)

        updated = improvement.model_copy(
            update={
                "promotion_state": promotion_state,
                "decision": normalized_decision,
                "decision_reason": normalized_reason,
                "decision_owner": owner.strip() or improvement.owner,
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "benchmark_evidence": benchmark_evidence or improvement.benchmark_evidence,
                "guardrail": guardrail or improvement.guardrail,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self.learning_store.store_promotable_improvement(updated.to_store_dict())
        return updated

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
