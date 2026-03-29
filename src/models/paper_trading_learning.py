"""Stateful learning models for paper-trading improvement loops."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


OutcomeLabel = Literal["win", "loss", "flat"]
ImprovementDecision = Literal["promote", "watch", "reject", "insufficient_evidence"]
ImprovementPromotionState = Literal["queued", "ready_now", "watch", "rejected"]


class ResearchMemoryEntry(BaseModel):
    """Persisted research packet used as a future learning anchor."""

    research_id: str
    account_id: str
    candidate_id: str = ""
    symbol: str
    sector: str = ""
    thesis: str
    evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    invalidation: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    screening_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    thesis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis_mode: str = "insufficient_evidence"
    actionability: str = "watch_only"
    external_evidence_status: str = "missing"
    why_now: str = ""
    source_summary: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    market_data_freshness: Dict[str, Any] = Field(default_factory=dict)
    next_step: str = ""
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=_utc_now)
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class TradeOutcomeEvaluation(BaseModel):
    """Post-trade evaluation tied back to prior research memory."""

    evaluation_id: str
    account_id: str
    trade_id: str
    candidate_id: Optional[str] = None
    research_id: Optional[str] = None
    decision_id: Optional[str] = None
    review_id: Optional[str] = None
    symbol: str
    outcome: OutcomeLabel
    realized_pnl: float = 0.0
    pnl_percentage: float = 0.0
    holding_days: int = 0
    lesson: str
    improvement: str
    artifact_lineage: Dict[str, Any] = Field(default_factory=dict)
    prompt_model_metadata: Dict[str, Any] = Field(default_factory=dict)
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


class DecisionMemoryEntry(BaseModel):
    decision_id: str
    account_id: str
    symbol: str
    action: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    thesis: str
    invalidation: str
    next_step: str
    risk_note: str
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=_utc_now)
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class ReviewMemoryEntry(BaseModel):
    review_id: str
    account_id: str
    summary: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    top_lessons: List[str] = Field(default_factory=list)
    strategy_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=_utc_now)
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class SessionRetrospective(BaseModel):
    retrospective_id: str
    session_id: str
    account_id: str
    keep: List[Dict[str, Any]] = Field(default_factory=list)
    remove: List[Dict[str, Any]] = Field(default_factory=list)
    fix: List[Dict[str, Any]] = Field(default_factory=list)
    improve: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    owner: str = "paper_trading_operator"
    promotion_state: str = "queued"
    generated_at: str = Field(default_factory=_utc_now)
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class PromotableImprovement(BaseModel):
    improvement_id: str
    account_id: str
    title: str
    summary: str
    owner: str
    promotion_state: ImprovementPromotionState | str
    category: str = ""
    retrospective_id: Optional[str] = None
    outcome_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    benchmark_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    guardrail: str = ""
    decision: Optional[Literal["promote", "watch", "reject"]] = None
    decision_reason: str = ""
    decision_owner: str = ""
    decided_at: Optional[str] = None
    updated_at: str = Field(default_factory=_utc_now)
    created_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")


class LearningReadinessSummary(BaseModel):
    account_id: str
    generated_at: str = Field(default_factory=_utc_now)
    closed_trade_count: int = 0
    evaluated_trade_count: int = 0
    unevaluated_closed_trade_count: int = 0
    queued_promotable_count: int = 0
    decision_pending_improvement_count: int = 0
    latest_retrospective_at: Optional[str] = None

    def to_store_dict(self) -> dict:
        return self.model_dump(mode="json")
