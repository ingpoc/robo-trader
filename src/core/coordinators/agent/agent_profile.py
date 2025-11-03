"""
Agent Profile and Role Definitions for Multi-Agent Framework

Defines agent profiles, roles, and capabilities for agent registration.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum


class AgentRole(Enum):
    """Roles that agents can have in the trading system."""

    TECHNICAL_ANALYST = "technical_analyst"
    FUNDAMENTAL_SCREENER = "fundamental_screener"
    RISK_MANAGER = "risk_manager"
    PORTFOLIO_ANALYST = "portfolio_analyst"
    MARKET_MONITOR = "market_monitor"
    STRATEGY_AGENT = "strategy_agent"
    EXECUTION_AGENT = "execution_agent"
    RECOMMENDATION_AGENT = "recommendation_agent"
    ALERT_AGENT = "alert_agent"
    EDUCATIONAL_AGENT = "educational_agent"
    COLLABORATION_COORDINATOR = "collaboration_coordinator"


@dataclass
class AgentProfile:
    """Profile information for a registered agent."""

    agent_id: str
    role: AgentRole
    capabilities: List[str]
    status: str = "active"
    last_heartbeat: Optional[datetime] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now(timezone.utc)
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.config is None:
            self.config = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "performance_metrics": self.performance_metrics,
            "config": self.config
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentProfile":
        """Create profile from dictionary."""
        profile = cls(
            agent_id=data["agent_id"],
            role=AgentRole(data["role"]),
            capabilities=data["capabilities"],
            status=data.get("status", "active"),
            performance_metrics=data.get("performance_metrics"),
            config=data.get("config")
        )

        if data.get("last_heartbeat"):
            profile.last_heartbeat = datetime.fromisoformat(data["last_heartbeat"])

        return profile

    def update_heartbeat(self) -> None:
        """Update the last heartbeat time."""
        self.last_heartbeat = datetime.now(timezone.utc)

    def is_alive(self, timeout_seconds: int = 60) -> bool:
        """Check if agent is considered alive based on heartbeat."""
        if not self.last_heartbeat:
            return False

        now = datetime.now(timezone.utc)
        diff = (now - self.last_heartbeat).total_seconds()
        return diff <= timeout_seconds

    def add_capability(self, capability: str) -> None:
        """Add a capability to the agent profile."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def remove_capability(self, capability: str) -> None:
        """Remove a capability from the agent profile."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities