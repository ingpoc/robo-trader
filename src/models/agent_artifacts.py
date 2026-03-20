"""Typed Claude agent artifacts for paper-trading workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ArtifactStatus = Literal["ready", "blocked", "empty"]
CandidatePriority = Literal["high", "medium", "low"]
DecisionAction = Literal["hold", "review_exit", "tighten_stop", "take_profit"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactEnvelope(BaseModel):
    """Shared envelope for progressive-disclosure artifact APIs."""

    status: ArtifactStatus
    generated_at: str = Field(default_factory=_utc_now)
    blockers: List[str] = Field(default_factory=list)
    context_mode: str
    artifact_count: int = 0


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
    next_step: str = ""
    generated_at: str = Field(default_factory=_utc_now)


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
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    top_lessons: List[str] = Field(default_factory=list)
    strategy_proposals: List[StrategyProposal] = Field(default_factory=list)
    generated_at: str = Field(default_factory=_utc_now)


class DiscoveryEnvelope(ArtifactEnvelope):
    candidates: List[Candidate] = Field(default_factory=list)


class DecisionEnvelope(ArtifactEnvelope):
    decisions: List[DecisionPacket] = Field(default_factory=list)


class ResearchEnvelope(ArtifactEnvelope):
    research: Optional[ResearchPacket] = None


class ReviewEnvelope(ArtifactEnvelope):
    review: Optional[ReviewReport] = None


class AgentPromptContext(BaseModel):
    """Compact prompt context used by the role-specific agent runner."""

    account_id: str
    account_summary: Dict[str, Any]
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    recent_trades: List[Dict[str, Any]] = Field(default_factory=list)
    capability_summary: Dict[str, Any] = Field(default_factory=dict)
