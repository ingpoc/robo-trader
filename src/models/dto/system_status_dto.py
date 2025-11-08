"""System Status DTO - Unified schema for system-wide status.

Provides consistent schema for system health across all API endpoints.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ComponentStatusDTO:
    """Status of a system component.

    Attributes:
        name: Component name (e.g., "database", "websocket", "claude_agent")
        status: Status string ("healthy", "degraded", "error", "inactive")
        last_check: When status was last checked
        details: Additional component-specific details
    """

    name: str
    status: str
    last_check: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SystemStatusDTO:
    """Unified system status schema.

    Attributes:
        status: Overall system status ("healthy", "degraded", "error")
        timestamp: When this status was generated
        components: Status of individual components
        queues: Queue statuses (list of QueueStatusDTO)
        summary: High-level statistics
    """

    status: str
    timestamp: str
    components: List[ComponentStatusDTO]
    queues: List[Dict[str, Any]]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "components": [c.to_dict() for c in self.components],
            "queues": self.queues,
            "summary": self.summary
        }
