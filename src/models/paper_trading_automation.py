"""Models for local Codex-backed paper-trading automation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


AutomationJobType = Literal[
    "research_cycle",
    "decision_review_cycle",
    "exit_check_cycle",
    "daily_review_cycle",
    "improvement_eval_cycle",
]
AutomationRunStatus = Literal["queued", "in_progress", "ready", "blocked", "empty", "error", "cancelled"]
AutomationRunTerminalStatus = Literal["ready", "blocked", "empty", "error", "cancelled"]


class CodexRuntimeReadiness(BaseModel):
    status: Literal["ready", "degraded", "blocked"]
    provider: str = "codex"
    authenticated: bool = False
    model: str = ""
    checked_at: str = Field(default_factory=_utc_now)
    error: Optional[str] = None
    last_successful_validation_at: Optional[str] = None
    usage_limited: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutomationRunRequest(BaseModel):
    account_id: str
    job_type: AutomationJobType
    limit: Optional[int] = Field(default=None, ge=1, le=50)
    candidate_id: Optional[str] = None
    symbol: Optional[str] = None
    dry_run: bool = True
    schedule_source: Literal["manual", "scheduled"] = "manual"
    trigger_reason: str = ""


class AutomationBlockReason(BaseModel):
    code: str
    message: str
    classification: Literal["dependency_failure", "policy_gate", "operator_pause", "duplicate_run"]


class AutomationArtifactEnvelope(BaseModel):
    run_id: str
    account_id: str
    job_type: AutomationJobType
    status: AutomationRunStatus
    block_reason: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    artifact_path: Optional[str] = None
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)


class AutomationRunRecord(BaseModel):
    run_id: str
    account_id: str
    job_type: AutomationJobType
    provider: str = "codex_subscription_local"
    runtime_session_id: Optional[str] = None
    status: AutomationRunStatus
    status_reason: str = ""
    block_reason: str = ""
    schedule_source: str = "manual"
    trigger_reason: str = ""
    input_digest: str = ""
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_trace: List[Dict[str, Any]] = Field(default_factory=list)
    artifact_path: Optional[str] = None
    started_at: str = Field(default_factory=_utc_now)
    completed_at: Optional[str] = None
    timeout_at: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)

    def to_store_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class AutomationJobControl(BaseModel):
    job_type: AutomationJobType
    enabled: bool = True
    schedule_minutes: int = 60
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    paused_at: Optional[str] = None
    pause_reason: str = ""

    def advance_next_run(self, *, from_timestamp: Optional[str] = None) -> None:
        base = datetime.now(timezone.utc)
        if from_timestamp:
            try:
                observed = datetime.fromisoformat(from_timestamp.replace("Z", "+00:00"))
                base = observed if observed.tzinfo else observed.replace(tzinfo=timezone.utc)
            except ValueError:
                base = datetime.now(timezone.utc)
        self.next_run_at = (base.astimezone(timezone.utc) + timedelta(minutes=self.schedule_minutes)).isoformat()

    def to_store_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class AutomationControlState(BaseModel):
    global_pause: bool = False
    paused_job_types: List[AutomationJobType] = Field(default_factory=list)
    updated_at: str = Field(default_factory=_utc_now)
    controls: List[AutomationJobControl] = Field(default_factory=list)

