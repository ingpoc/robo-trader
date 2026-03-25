"""Stateful learning models for paper-trading improvement loops."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


OutcomeLabel = Literal["win", "loss", "flat"]
ImprovementDecision = Literal["promote", "watch", "reject", "insufficient_evidence"]


class ResearchMemoryEntry(BaseModel):
    """Persisted research packet used as a future learning anchor."""

    research_id: str
    account_id: str
    candidate_id: str = ""
    symbol: str
    thesis: str
    evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    invalidation: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    screening_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    thesis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis_mode: str = "insufficient_evidence"
    actionability: str = "watch_only"
    why_now: str = ""
    source_summary: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    market_data_freshness: Dict[str, Any] = Field(default_factory=dict)
    next_step: str = ""
    generated_at: str = Field(default_factory=_utc_now)
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class TradeOutcomeEvaluation(BaseModel):
    """Post-trade evaluation tied back to prior research memory."""

    evaluation_id: str
    account_id: str
    trade_id: str
    research_id: Optional[str] = None
    symbol: str
    outcome: OutcomeLabel
    realized_pnl: float = 0.0
    pnl_percentage: float = 0.0
    holding_days: int = 0
    lesson: str
    improvement: str
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class LearningSummary(BaseModel):
    """Aggregate stateful learning summary for future research and review."""

    account_id: str
    generated_at: str = Field(default_factory=_utc_now)
    total_evaluations: int = 0
    wins: int = 0
    losses: int = 0
    flats: int = 0
    average_pnl_percentage: float = 0.0
    top_lessons: List[str] = Field(default_factory=list)
    improvement_focus: List[str] = Field(default_factory=list)
    recent_evaluations: List[TradeOutcomeEvaluation] = Field(default_factory=list)


class ImprovementBenchmark(BaseModel):
    """Deterministic benchmark result for a candidate strategy improvement."""

    proposal_id: str
    proposal_key: str
    title: str
    rationale: str
    guardrail: str
    hypothesis: str
    decision: ImprovementDecision
    impacted_trades: int = 0
    kept_trades: int = 0
    skipped_wins: int = 0
    skipped_losses: int = 0
    skipped_flats: int = 0
    baseline_win_rate: float = 0.0
    candidate_win_rate: float = 0.0
    baseline_average_pnl_percentage: float = 0.0
    candidate_average_pnl_percentage: float = 0.0
    baseline_total_realized_pnl: float = 0.0
    candidate_total_realized_pnl: float = 0.0
    avoided_loss_amount: float = 0.0
    missed_profit_amount: float = 0.0
    net_benefit_amount: float = 0.0
    summary: str


class ImprovementReport(BaseModel):
    """Account-level improvement report backed by deterministic benchmarks."""

    account_id: str
    generated_at: str = Field(default_factory=_utc_now)
    baseline_trade_count: int = 0
    evaluated_trade_count: int = 0
    benchmarked_proposals: List[ImprovementBenchmark] = Field(default_factory=list)
    promotable_proposals: List[ImprovementBenchmark] = Field(default_factory=list)
    watch_proposals: List[ImprovementBenchmark] = Field(default_factory=list)
