"""Deterministic benchmarking for paper-trading strategy improvements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.models.paper_trading_learning import ImprovementBenchmark, ImprovementReport


@dataclass
class _EvaluatedTrade:
    trade_id: str
    symbol: str
    realized_pnl: float
    pnl_percentage: float
    outcome: str
    confidence: float
    thesis_confidence: float
    stale_data_risk: bool
    analysis_mode: str
    source_count: int
    fresh_source_count: int
    research_id: Optional[str]


class PaperTradingImprovementService:
    """Benchmark rule changes against persisted paper-trade outcomes."""

    def __init__(self, learning_service, learning_store, paper_trading_store):
        self.learning_service = learning_service
        self.learning_store = learning_store
        self.paper_trading_store = paper_trading_store

    async def get_improvement_report(
        self,
        account_id: str,
        *,
        refresh: bool = True,
        limit: int = 100,
    ) -> ImprovementReport:
        if refresh:
            await self.learning_service.evaluate_closed_trades(account_id, limit=limit)

        evaluated_trades = await self._load_evaluated_trades(account_id, limit=limit)
        if not evaluated_trades:
            return ImprovementReport(
                account_id=account_id,
                baseline_trade_count=0,
                evaluated_trade_count=0,
                benchmarked_proposals=[],
                promotable_proposals=[],
                watch_proposals=[],
            )

        proposals = self._build_candidate_proposals(evaluated_trades)
        benchmarks = [self._benchmark_proposal(proposal, evaluated_trades) for proposal in proposals]

        promotable = [item for item in benchmarks if item.decision == "promote"]
        watchlist = [item for item in benchmarks if item.decision == "watch"]

        return ImprovementReport(
            account_id=account_id,
            baseline_trade_count=len(evaluated_trades),
            evaluated_trade_count=len(evaluated_trades),
            benchmarked_proposals=benchmarks,
            promotable_proposals=promotable,
            watch_proposals=watchlist,
        )

    async def _load_evaluated_trades(self, account_id: str, *, limit: int) -> List[_EvaluatedTrade]:
        closed_trades = await self.paper_trading_store.get_closed_trades(account_id, limit=limit)
        rows: List[_EvaluatedTrade] = []

        for trade in closed_trades:
            research = await self.learning_store.get_latest_research_memory(
                account_id,
                trade.symbol,
                before_timestamp=trade.entry_timestamp,
            )
            if not research:
                continue

            pnl_percentage = self._trade_pnl_percentage(trade)
            rows.append(
                _EvaluatedTrade(
                    trade_id=trade.trade_id,
                    symbol=trade.symbol,
                    realized_pnl=float(trade.realized_pnl or 0.0),
                    pnl_percentage=pnl_percentage,
                    outcome=self._categorize_outcome(pnl_percentage),
                    confidence=float(research.get("confidence") or 0.0),
                    thesis_confidence=float(
                        research.get("thesis_confidence")
                        or research.get("confidence")
                        or 0.0
                    ),
                    stale_data_risk=self._has_stale_data_risk(research),
                    analysis_mode=str(research.get("analysis_mode") or "insufficient_evidence"),
                    source_count=len(research.get("source_summary") or []),
                    fresh_source_count=self._count_fresh_sources(research),
                    research_id=research.get("research_id"),
                )
            )

        return rows

    @staticmethod
    def _build_candidate_proposals(trades: List[_EvaluatedTrade]) -> List[Dict[str, str]]:
        proposals: List[Dict[str, str]] = []

        low_conf_losses = sum(1 for trade in trades if trade.outcome == "loss" and trade.confidence < 0.5)
        low_conf_wins = sum(1 for trade in trades if trade.outcome == "win" and trade.confidence < 0.5)
        low_thesis_losses = sum(1 for trade in trades if trade.outcome == "loss" and trade.thesis_confidence < 0.55)
        low_thesis_wins = sum(1 for trade in trades if trade.outcome == "win" and trade.thesis_confidence < 0.55)
        stale_losses = sum(1 for trade in trades if trade.outcome == "loss" and trade.stale_data_risk)
        stale_wins = sum(1 for trade in trades if trade.outcome == "win" and trade.stale_data_risk)
        thin_evidence_losses = sum(
            1
            for trade in trades
            if trade.outcome == "loss"
            and (trade.fresh_source_count < 2 or trade.analysis_mode != "fresh_evidence")
        )
        thin_evidence_wins = sum(
            1
            for trade in trades
            if trade.outcome == "win"
            and (trade.fresh_source_count < 2 or trade.analysis_mode != "fresh_evidence")
        )

        if low_conf_losses or low_conf_wins:
            proposals.append(
                {
                    "proposal_key": "min_confidence_0_50",
                    "title": "Raise Minimum Research Confidence",
                    "rationale": (
                        f"Low-confidence trades produced {low_conf_losses} losses and {low_conf_wins} wins. "
                        "Benchmark whether a 0.50 confidence floor improves trade quality."
                    ),
                    "guardrail": "Only promote a research packet into a trade if confidence is at least 0.50.",
                    "hypothesis": "Filtering out weak-conviction setups should improve realized trade quality.",
                }
            )

        if stale_losses or stale_wins:
            proposals.append(
                {
                    "proposal_key": "require_fresh_data",
                    "title": "Require Fresh Market Data Before Entry",
                    "rationale": (
                        f"Trades with stale-data warnings produced {stale_losses} losses and {stale_wins} wins. "
                        "Benchmark whether fresh-data gating removes avoidable losses."
                    ),
                    "guardrail": "Do not promote a trade when the research packet still flags stale market data.",
                    "hypothesis": "Fresh-data gating should avoid preventable losses caused by invalid marks.",
                }
            )

        if (low_conf_losses or low_conf_wins) and (stale_losses or stale_wins):
            proposals.append(
                {
                    "proposal_key": "confidence_and_fresh_data",
                    "title": "Require Confidence And Fresh Data",
                    "rationale": (
                        "Losses were clustered in trades that were both low-conviction and data-compromised. "
                        "Benchmark a compound gate before promoting automation."
                    ),
                    "guardrail": (
                        "Promote a research packet into a trade only when confidence is at least 0.50 "
                        "and stale market data is not present."
                    ),
                    "hypothesis": "The compound gate should remove weak, low-quality trades without discarding the best setups.",
                }
            )

        if low_thesis_losses or low_thesis_wins:
            proposals.append(
                {
                    "proposal_key": "min_thesis_confidence_0_55",
                    "title": "Raise Minimum Thesis Confidence",
                    "rationale": (
                        f"Low-thesis-confidence trades produced {low_thesis_losses} losses and {low_thesis_wins} wins. "
                        "Benchmark whether thesis formation needs a stricter bar than initial screening."
                    ),
                    "guardrail": "Only promote research into a trade when thesis confidence is at least 0.55.",
                    "hypothesis": "A thesis-confidence gate should filter weak narratives better than screening confidence alone.",
                }
            )

        if thin_evidence_losses or thin_evidence_wins:
            proposals.append(
                {
                    "proposal_key": "require_two_fresh_sources",
                    "title": "Require Two Fresh Evidence Categories",
                    "rationale": (
                        f"Thin-evidence trades produced {thin_evidence_losses} losses and {thin_evidence_wins} wins. "
                        "Benchmark whether at least two fresh evidence categories improve trade quality."
                    ),
                    "guardrail": (
                        "Only promote a research packet when it is in fresh_evidence mode and includes at least two fresh sources."
                    ),
                    "hypothesis": "Fresh multi-source evidence should outperform packets built on stale or thin inputs.",
                }
            )

        if not proposals:
            proposals.append(
                {
                    "proposal_key": "preserve_current_rules",
                    "title": "Preserve Current Research Promotion Rules",
                    "rationale": "The current evaluated sample does not show a repeatable failure pattern worth promoting.",
                    "guardrail": "Keep the current rules and continue collecting closed paper trades.",
                    "hypothesis": "No tested rule change currently has enough evidence to outperform the baseline.",
                }
            )

        return proposals

    def _benchmark_proposal(
        self,
        proposal: Dict[str, str],
        trades: List[_EvaluatedTrade],
    ) -> ImprovementBenchmark:
        kept = [trade for trade in trades if not self._trade_blocked_by_proposal(trade, proposal["proposal_key"])]
        skipped = [trade for trade in trades if self._trade_blocked_by_proposal(trade, proposal["proposal_key"])]

        baseline = self._compute_metrics(trades)
        candidate = self._compute_metrics(kept)

        skipped_wins = sum(1 for trade in skipped if trade.outcome == "win")
        skipped_losses = sum(1 for trade in skipped if trade.outcome == "loss")
        skipped_flats = sum(1 for trade in skipped if trade.outcome == "flat")
        avoided_loss_amount = round(sum(abs(trade.realized_pnl) for trade in skipped if trade.realized_pnl < 0), 2)
        missed_profit_amount = round(sum(trade.realized_pnl for trade in skipped if trade.realized_pnl > 0), 2)
        net_benefit_amount = round(avoided_loss_amount - missed_profit_amount, 2)
        decision = self._decide_promotion(
            proposal_key=proposal["proposal_key"],
            impacted_trades=len(skipped),
            kept_trades=len(kept),
            baseline=baseline,
            candidate=candidate,
            skipped_wins=skipped_wins,
            skipped_losses=skipped_losses,
            net_benefit_amount=net_benefit_amount,
        )

        summary = self._build_summary(
            decision=decision,
            impacted_trades=len(skipped),
            skipped_wins=skipped_wins,
            skipped_losses=skipped_losses,
            net_benefit_amount=net_benefit_amount,
            baseline=baseline,
            candidate=candidate,
        )

        return ImprovementBenchmark(
            proposal_id=f"improvement_{proposal['proposal_key']}",
            proposal_key=proposal["proposal_key"],
            title=proposal["title"],
            rationale=proposal["rationale"],
            guardrail=proposal["guardrail"],
            hypothesis=proposal["hypothesis"],
            decision=decision,
            impacted_trades=len(skipped),
            kept_trades=len(kept),
            skipped_wins=skipped_wins,
            skipped_losses=skipped_losses,
            skipped_flats=skipped_flats,
            baseline_win_rate=baseline["win_rate"],
            candidate_win_rate=candidate["win_rate"],
            baseline_average_pnl_percentage=baseline["average_pnl_percentage"],
            candidate_average_pnl_percentage=candidate["average_pnl_percentage"],
            baseline_total_realized_pnl=baseline["total_realized_pnl"],
            candidate_total_realized_pnl=candidate["total_realized_pnl"],
            avoided_loss_amount=avoided_loss_amount,
            missed_profit_amount=missed_profit_amount,
            net_benefit_amount=net_benefit_amount,
            summary=summary,
        )

    @staticmethod
    def _trade_blocked_by_proposal(trade: _EvaluatedTrade, proposal_key: str) -> bool:
        if proposal_key == "min_confidence_0_50":
            return trade.confidence < 0.5
        if proposal_key == "min_thesis_confidence_0_55":
            return trade.thesis_confidence < 0.55
        if proposal_key == "require_fresh_data":
            return trade.stale_data_risk
        if proposal_key == "confidence_and_fresh_data":
            return trade.confidence < 0.5 or trade.stale_data_risk
        if proposal_key == "require_two_fresh_sources":
            return trade.analysis_mode != "fresh_evidence" or trade.fresh_source_count < 2
        return False

    @staticmethod
    def _compute_metrics(trades: List[_EvaluatedTrade]) -> Dict[str, float]:
        if not trades:
            return {
                "trade_count": 0,
                "win_rate": 0.0,
                "average_pnl_percentage": 0.0,
                "total_realized_pnl": 0.0,
            }

        trade_count = len(trades)
        wins = sum(1 for trade in trades if trade.outcome == "win")
        average_pnl_percentage = sum(trade.pnl_percentage for trade in trades) / trade_count
        total_realized_pnl = sum(trade.realized_pnl for trade in trades)

        return {
            "trade_count": trade_count,
            "win_rate": round((wins / trade_count) * 100, 2),
            "average_pnl_percentage": round(average_pnl_percentage, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
        }

    @staticmethod
    def _decide_promotion(
        *,
        proposal_key: str,
        impacted_trades: int,
        kept_trades: int,
        baseline: Dict[str, float],
        candidate: Dict[str, float],
        skipped_wins: int,
        skipped_losses: int,
        net_benefit_amount: float,
    ) -> str:
        if proposal_key == "preserve_current_rules":
            return "watch"
        if impacted_trades == 0:
            return "insufficient_evidence"
        if kept_trades == 0:
            return "reject"
        if impacted_trades < 2:
            return "insufficient_evidence"

        win_rate_improved = candidate["win_rate"] >= baseline["win_rate"]
        pnl_improved = candidate["average_pnl_percentage"] >= baseline["average_pnl_percentage"]
        avoided_more_losses_than_wins = skipped_losses > skipped_wins

        if net_benefit_amount > 0 and win_rate_improved and pnl_improved and avoided_more_losses_than_wins:
            return "promote"
        if net_benefit_amount >= 0 and avoided_more_losses_than_wins:
            return "watch"
        return "reject"

    @staticmethod
    def _build_summary(
        *,
        decision: str,
        impacted_trades: int,
        skipped_wins: int,
        skipped_losses: int,
        net_benefit_amount: float,
        baseline: Dict[str, float],
        candidate: Dict[str, float],
    ) -> str:
        if decision == "promote":
            return (
                f"Promote: filtered {impacted_trades} trades, removed {skipped_losses} losses versus {skipped_wins} wins, "
                f"and improved average PnL from {baseline['average_pnl_percentage']:.2f}% to "
                f"{candidate['average_pnl_percentage']:.2f}%."
            )
        if decision == "watch":
            return (
                f"Watch: filtered {impacted_trades} trades with net benefit {net_benefit_amount:.2f}, "
                f"but the sample is not strong enough to auto-promote."
            )
        if decision == "insufficient_evidence":
            return f"Insufficient evidence: only {impacted_trades} historical trade(s) were affected."
        return (
            f"Reject: the proposal would filter {impacted_trades} trades without improving the baseline "
            f"({baseline['average_pnl_percentage']:.2f}% avg PnL)."
        )

    @staticmethod
    def _trade_pnl_percentage(trade: Any) -> float:
        if trade.realized_pnl is not None and trade.entry_price > 0 and trade.quantity > 0:
            capital = trade.entry_price * trade.quantity
            if capital > 0:
                return round((trade.realized_pnl / capital) * 100, 2)
        if trade.exit_price is not None and trade.entry_price > 0:
            return round(((trade.exit_price - trade.entry_price) / trade.entry_price) * 100, 2)
        return 0.0

    @staticmethod
    def _categorize_outcome(pnl_percentage: float) -> str:
        if pnl_percentage >= 1.0:
            return "win"
        if pnl_percentage <= -1.0:
            return "loss"
        return "flat"

    @staticmethod
    def _has_stale_data_risk(research: Dict[str, Any]) -> bool:
        return any("stale" in str(risk).lower() for risk in research.get("risks", []))

    @staticmethod
    def _count_fresh_sources(research: Dict[str, Any]) -> int:
        source_summary = research.get("source_summary") or []
        return sum(1 for source in source_summary if str(source.get("freshness") or "").lower() == "fresh")
