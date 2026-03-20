"""Structured capability models for mission-critical trading readiness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CapabilityStatus(str, Enum):
    """Capability readiness states."""

    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass
class CapabilityCheck:
    """Single subsystem capability check."""

    key: str
    label: str
    status: CapabilityStatus
    summary: str
    blocking: bool = True
    detail: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the capability check."""
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass
class TradingCapabilitySnapshot:
    """Top-level readiness snapshot for paper-trading automation."""

    mode: str
    overall_status: CapabilityStatus
    automation_allowed: bool
    generated_at: str
    checks: List[CapabilityCheck]
    blockers: List[str] = field(default_factory=list)
    account_id: Optional[str] = None

    @classmethod
    def build(
        cls,
        *,
        mode: str,
        checks: List[CapabilityCheck],
        account_id: Optional[str] = None,
    ) -> "TradingCapabilitySnapshot":
        """Create a snapshot and derive the aggregate readiness."""
        blocking_checks = [check for check in checks if check.blocking]

        if any(check.status == CapabilityStatus.BLOCKED for check in blocking_checks):
            overall = CapabilityStatus.BLOCKED
        elif any(check.status == CapabilityStatus.DEGRADED for check in blocking_checks):
            overall = CapabilityStatus.DEGRADED
        elif any(check.status == CapabilityStatus.DEGRADED for check in checks):
            overall = CapabilityStatus.DEGRADED
        else:
            overall = CapabilityStatus.READY

        blockers = [check.summary for check in blocking_checks if check.status == CapabilityStatus.BLOCKED]

        return cls(
            mode=mode,
            overall_status=overall,
            automation_allowed=all(check.status == CapabilityStatus.READY for check in blocking_checks),
            generated_at=datetime.now(timezone.utc).isoformat(),
            checks=checks,
            blockers=blockers,
            account_id=account_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the readiness snapshot."""
        return {
            "mode": self.mode,
            "overall_status": self.overall_status.value,
            "automation_allowed": self.automation_allowed,
            "generated_at": self.generated_at,
            "account_id": self.account_id,
            "blockers": self.blockers,
            "checks": [check.to_dict() for check in self.checks],
        }
