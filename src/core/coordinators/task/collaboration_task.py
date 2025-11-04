"""
Collaboration Task Management for Multi-Agent Framework

Defines task structures and collaboration modes for agent teamwork.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid

from ..agent.agent_profile import AgentRole


class CollaborationMode(Enum):
    """Modes of collaboration between agents."""

    SEQUENTIAL = "sequential"  # Agents work one after another
    PARALLEL = "parallel"     # Agents work simultaneously
    CONSENSUS = "consensus"   # Agents must reach consensus
    COMPETITIVE = "competitive"  # Agents compete, best result chosen
    HIERARCHICAL = "hierarchical"  # Lead agent coordinates others


class TaskStatus(Enum):
    """Status of collaboration tasks."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_AGENTS = "waiting_for_agents"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result from an agent for a task."""

    agent_id: str
    agent_role: AgentRole
    result: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    completion_time: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_role": self.agent_role.value,
            "result": self.result,
            "confidence": self.confidence,
            "completion_time": self.completion_time.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class CollaborationTask:
    """A task that requires collaboration between multiple agents."""

    task_id: str
    description: str
    required_roles: List[AgentRole]
    collaboration_mode: CollaborationMode
    status: TaskStatus
    created_at: datetime
    deadline: Optional[datetime] = None
    assigned_agents: List[str] = None
    results: List[TaskResult] = None
    final_result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        description: str,
        required_roles: List[AgentRole],
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        deadline: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.task_id = str(uuid.uuid4())
        self.description = description
        self.required_roles = required_roles
        self.collaboration_mode = collaboration_mode
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.deadline = deadline
        self.assigned_agents = []
        self.results = []
        self.final_result = None
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_roles": [role.value for role in self.required_roles],
            "collaboration_mode": self.collaboration_mode.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "assigned_agents": self.assigned_agents,
            "results": [result.to_dict() for result in self.results],
            "final_result": self.final_result,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationTask":
        """Create task from dictionary."""
        task = cls(
            description=data["description"],
            required_roles=[AgentRole(role) for role in data["required_roles"]],
            collaboration_mode=CollaborationMode(data["collaboration_mode"]),
            metadata=data.get("metadata")
        )

        task.task_id = data["task_id"]
        task.status = TaskStatus(data["status"])
        task.created_at = datetime.fromisoformat(data["created_at"])
        task.assigned_agents = data.get("assigned_agents", [])
        task.final_result = data.get("final_result")

        if data.get("deadline"):
            task.deadline = datetime.fromisoformat(data["deadline"])

        if data.get("results"):
            for result_data in data["results"]:
                result = TaskResult(
                    agent_id=result_data["agent_id"],
                    agent_role=AgentRole(result_data["agent_role"]),
                    result=result_data["result"],
                    confidence=result_data["confidence"],
                    completion_time=datetime.fromisoformat(result_data["completion_time"]),
                    metadata=result_data.get("metadata")
                )
                task.results.append(result)

        return task

    def assign_agent(self, agent_id: str) -> bool:
        """Assign an agent to this task."""
        if agent_id not in self.assigned_agents:
            self.assigned_agents.append(agent_id)
            return True
        return False

    def add_result(self, result: TaskResult) -> None:
        """Add a result from an agent."""
        self.results.append(result)

    def is_complete(self) -> bool:
        """Check if the task is complete."""
        return self.status == TaskStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the task has failed."""
        return self.status == TaskStatus.FAILED

    def is_overdue(self) -> bool:
        """Check if the task is overdue."""
        if not self.deadline:
            return False
        return datetime.now(timezone.utc) > self.deadline

    def get_progress(self) -> float:
        """Get progress percentage (0.0 to 1.0)."""
        if not self.required_roles:
            return 1.0

        completed_roles = len([r for r in self.results if r.agent_role in self.required_roles])
        return completed_roles / len(self.required_roles)