"""Queue Status DTO - Unified schema for API responses and WebSocket messages.

This DTO ensures identical schema across:
- REST API: GET /api/queues/status
- WebSocket: queue_status_update message
- Frontend: QueueStatusDTO interface

Critical: Any changes here must be reflected in frontend TypeScript types.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class CurrentTaskDTO:
    """Current task information with queue context.

    Attributes:
        task_id: Unique task identifier
        task_type: Type of task (e.g., RECOMMENDATION_GENERATION)
        queue_name: Queue this task belongs to (preserves context)
        started_at: When task execution started
        duration_ms: Current duration (if still running)
    """

    task_id: str
    task_type: str
    queue_name: str
    started_at: str
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class QueueStatusDTO:
    """Unified queue status schema.

    This DTO is used by:
    - REST API responses
    - WebSocket broadcasts
    - Frontend components

    Schema matches exactly what UI expects (from architecture analysis).

    Attributes:
        queue_name: Name of the queue (e.g., "ai_analysis")
        status: Current status ("running", "active", "idle", "error")
        pending_count: Number of pending tasks
        running_count: Number of running tasks
        completed_today: Number of tasks completed today
        failed_count: Number of failed tasks
        average_duration_ms: Average task execution time
        last_activity: Timestamp of last completed task
        current_task: Currently executing task (with queue context)
        total_tasks: Total tasks across all statuses
        is_healthy: Whether queue is in healthy state
        is_active: Whether queue has active work
        success_rate: Percentage of successful completions
        snapshot_ts: When this snapshot was taken
    """

    queue_name: str
    status: str  # "running" | "active" | "idle" | "error"
    pending_count: int
    running_count: int
    completed_today: int
    failed_count: int
    average_duration_ms: float
    last_activity: Optional[str] = None
    current_task: Optional[CurrentTaskDTO] = None
    total_tasks: int = 0
    is_healthy: bool = True
    is_active: bool = False
    success_rate: float = 100.0
    snapshot_ts: Optional[str] = None

    @classmethod
    def from_queue_state(cls, queue_state) -> 'QueueStatusDTO':
        """Create DTO from QueueState domain model.

        Args:
            queue_state: QueueState from repository

        Returns:
            QueueStatusDTO ready for API response
        """
        # Create current task DTO if present
        current_task_dto = None
        if queue_state.current_task_id:
            current_task_dto = CurrentTaskDTO(
                task_id=queue_state.current_task_id,
                task_type=queue_state.current_task_type,
                queue_name=queue_state.name,
                started_at=queue_state.current_task_started_at,
                duration_ms=cls._calculate_duration(queue_state.current_task_started_at)
            )

        return cls(
            queue_name=queue_state.name,
            status=queue_state.status.value,
            pending_count=queue_state.pending_tasks,
            running_count=queue_state.running_tasks,
            completed_today=queue_state.completed_tasks,
            failed_count=queue_state.failed_tasks,
            average_duration_ms=queue_state.avg_duration_ms,
            last_activity=queue_state.last_activity_ts,
            current_task=current_task_dto,
            total_tasks=queue_state.total_tasks,
            is_healthy=queue_state.is_healthy,
            is_active=queue_state.is_active,
            success_rate=queue_state.success_rate,
            snapshot_ts=queue_state.snapshot_ts
        )

    @staticmethod
    def _calculate_duration(started_at: Optional[str]) -> Optional[int]:
        """Calculate current duration in milliseconds.

        Args:
            started_at: ISO timestamp when task started

        Returns:
            Duration in milliseconds or None
        """
        if not started_at:
            return None

        try:
            start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            duration = (now - start).total_seconds() * 1000
            return int(duration)
        except (ValueError, AttributeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary suitable for API response or WebSocket message
        """
        result = {
            "queue_name": self.queue_name,
            "status": self.status,
            "pending_count": self.pending_count,
            "running_count": self.running_count,
            "completed_today": self.completed_today,
            "failed_count": self.failed_count,
            "average_duration_ms": self.average_duration_ms,
            "last_activity": self.last_activity,
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "total_tasks": self.total_tasks,
            "is_healthy": self.is_healthy,
            "is_active": self.is_active,
            "success_rate": self.success_rate,
            "snapshot_ts": self.snapshot_ts
        }
        return result
