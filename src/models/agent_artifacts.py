"""Typed Claude agent artifacts for paper-trading workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ArtifactStatus = Literal["ready", "blocked", "empty"]
CandidatePriority = Literal["high", "medium", "low"]
DecisionAction = Literal["hold", "review_exit", "tighten_stop", "take_profit"]
ResearchAnalysisMode = Literal["fresh_evidence", "stale_evidence", "insufficient_evidence"]
ResearchActionability = Literal["actionable", "watch_only", "blocked"]
ResearchEvidenceTier = Literal["primary", "secondary", "derived"]
ExternalEvidenceStatus = Literal["fresh", "partial", "missing"]
ArtifactFreshnessState = Literal["fresh", "stale", "unknown"]
ArtifactEmptyReason = Literal[
    "never_run",
    "stale",
    "blocked_by_runtime",
    "blocked_by_quota",
    "no_candidates",
    "requires_selection",
]
CandidateLifecycleState = Literal["fresh_queue", "actionable", "keep_watch", "rejected"]
ResearchClassification = Literal["actionable_buy_candidate", "keep_watch", "rejected"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactEnvelope(BaseModel):
    """Shared envelope for progressive-disclosure artifact APIs."""

    status: ArtifactStatus
    generated_at: str = Field(default_factory=_utc_now)
    blockers: List[str] = Field(default_factory=list)
    context_mode: str
    artifact_count: int = 0
    criteria: List[str] = Field(default_factory=list)
    considered: List[str] = Field(default_factory=list)
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    status_reason: Optional[str] = None
    last_generated_at: Optional[str] = None
    freshness_state: ArtifactFreshnessState = "unknown"
    empty_reason: Optional[ArtifactEmptyReason] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.last_generated_at:
            self.last_generated_at = self.generated_at


class Candidate(BaseModel):
    candidate_id: str
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    source: str
    priority: CandidatePriority = "medium"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str
    next_step: str
    generated_at: str = Field(default_factory=_utc_now)
    last_researched_at: Optional[str] = None
    last_actionability: Optional[ResearchActionability] = None
    last_thesis_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    last_analysis_mode: Optional[ResearchAnalysisMode] = None
    research_freshness: ArtifactFreshnessState = "unknown"
    fresh_primary_source_count: int = 0
    fresh_external_source_count: int = 0
    market_data_freshness: str = "unknown"
    technical_context_available: bool = False
    evidence_mode: str = ""
    lifecycle_state: CandidateLifecycleState = "fresh_queue"
    reentry_reason: Optional[str] = None
    last_trigger_type: Optional[str] = None
    dark_horse_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ResearchSourceSummary(BaseModel):
    source_type: str
    label: str
    tier: ResearchEvidenceTier = "derived"
    timestamp: str = ""
    freshness: str = "unknown"
    detail: str = ""


class ResearchEvidenceCitation(BaseModel):
    source_type: str
    label: str
    reference: str
    tier: ResearchEvidenceTier = "derived"
    freshness: str = "unknown"
    timestamp: str = ""


class MarketDataFreshness(BaseModel):
    status: str = "unknown"
    summary: str = ""
    timestamp: str = ""
    age_seconds: Optional[float] = None
    provider: str = ""
    has_intraday_quote: bool = False
    has_historical_data: bool = False


class ResearchPacket(BaseModel):
    research_id: str
    candidate_id: str = ""
    account_id: str = ""
    symbol: str
    thesis: str
    evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    invalidation: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    screening_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    thesis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis_mode: ResearchAnalysisMode = "insufficient_evidence"
    actionability: ResearchActionability = "watch_only"
    external_evidence_status: ExternalEvidenceStatus = "missing"
    why_now: str = ""
    source_summary: List[ResearchSourceSummary] = Field(default_factory=list)
    evidence_citations: List[ResearchEvidenceCitation] = Field(default_factory=list)
    market_data_freshness: MarketDataFreshness = Field(default_factory=MarketDataFreshness)
    fresh_primary_source_count: int = 0
    fresh_external_source_count: int = 0
    technical_context_available: bool = False
    evidence_mode: str = ""
    classification: ResearchClassification = "keep_watch"
    what_changed_since_last_research: str = ""
    next_step: str = ""
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=_utc_now)


class SessionLoopSummary(BaseModel):
    target_actionable_count: int = 1
    actionable_found_count: int = 0
    research_attempt_count: int = 0
    attempted_candidates: List[str] = Field(default_factory=list)
    attempted_candidate_ids: List[str] = Field(default_factory=list)
    queue_exhausted: bool = False
    termination_reason: str = "not_started"
    current_candidate_symbol: Optional[str] = None
    current_candidate_id: Optional[str] = None
    latest_transition_reason: Optional[str] = None
    model_usage_by_phase: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    token_usage_by_phase: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    total_candidates_scanned: int = 0
    promoted_actionable_symbols: List[str] = Field(default_factory=list)


class DecisionPacket(BaseModel):
    decision_id: str
    symbol: str
    action: DecisionAction
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    thesis: str
    invalidation: str
    next_step: str
    risk_note: str
    generated_at: str = Field(default_factory=_utc_now)


class StrategyProposal(BaseModel):
    proposal_id: str
    title: str
    recommendation: str
    rationale: str
    guardrail: str


class ReviewReport(BaseModel):
    review_id: str
    summary: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    top_lessons: List[str] = Field(default_factory=list)
    strategy_proposals: List[StrategyProposal] = Field(default_factory=list)
    generated_at: str = Field(default_factory=_utc_now)


class DiscoveryEnvelope(ArtifactEnvelope):
    candidates: List[Candidate] = Field(default_factory=list)
    loop_summary: Optional[SessionLoopSummary] = None


class DecisionEnvelope(ArtifactEnvelope):
    decisions: List[DecisionPacket] = Field(default_factory=list)


class ResearchEnvelope(ArtifactEnvelope):
    research: Optional[ResearchPacket] = None
    loop_summary: Optional[SessionLoopSummary] = None


class ReviewEnvelope(ArtifactEnvelope):
    review: Optional[ReviewReport] = None


class AgentPromptContext(BaseModel):
    """Compact prompt context used by the role-specific agent runner."""

    account_id: str
    account_summary: Dict[str, Any]
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    recent_trades: List[Dict[str, Any]] = Field(default_factory=list)
    capability_summary: Dict[str, Any] = Field(default_factory=dict)
    learning_summary: Dict[str, Any] = Field(default_factory=dict)
    improvement_report: Dict[str, Any] = Field(default_factory=dict)
