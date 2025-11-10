"""Queue state domain model.

Represents the complete state of a queue at a point in time.
This is a rich domain object that encapsulates queue status logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class QueueStatus(str, Enum):
    """Queue status enumeration."""

    RUNNING = "running"  # Has tasks currently executing
    ACTIVE = "active"    # Has pending tasks but none running
    IDLE = "idle"        # No pending or running tasks
    ERROR = "error"      # Has failed tasks
    STOPPED = "stopped"  # Queue is not operational


@dataclass
class QueueState:
    """Immutable snapshot of queue state.

    This is the single source of truth for queue status.
    All queue status queries should return this object.

    Attributes:
        name: Queue name (e.g., "ai_analysis")
        status: Computed queue status
        pending_tasks: Count of pending tasks
        running_tasks: Count of running tasks
        completed_tasks: Count of completed tasks (today)
        failed_tasks: Count of failed tasks
        avg_duration_ms: Average task duration in milliseconds
        last_activity_ts: Timestamp of last completed task
        current_task_id: ID of currently running task (if any)
        current_task_type: Type of currently running task
        current_task_started_at: When current task started
        snapshot_ts: When this snapshot was taken
    """

    name: str
    status: QueueStatus
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_duration_ms: float = 0.0
    last_activity_ts: Optional[str] = None
    current_task_id: Optional[str] = None
    current_task_type: Optional[str] = None
    current_task_started_at: Optional[str] = None
    snapshot_ts: Optional[str] = None

    @classmethod
    def from_aggregation(
        cls,
        queue_name: str,
        pending: int,
        running: int,
        completed: int,
        failed: int,
        avg_duration: Optional[float],
        last_activity: Optional[str],
        current_task: Optional[Dict[str, Any]] = None,
        snapshot_ts: Optional[str] = None
    ) -> 'QueueState':
        """Create QueueState from database aggregation results.

        Args:
            queue_name: Name of the queue
            pending: Count of pending tasks
            running: Count of running tasks
            completed: Count of completed tasks (today)
            failed: Count of failed tasks
            avg_duration: Average duration in milliseconds
            last_activity: Timestamp of last activity
            current_task: Current task details (if any)
            snapshot_ts: Snapshot timestamp

        Returns:
            QueueState instance with computed status
        """
        # Compute status based on counts
        status = cls._compute_status(running, pending, failed)

        # Extract current task details
        current_task_id = None
        current_task_type = None
        current_task_started_at = None

        if current_task:
            current_task_id = current_task.get('task_id')
            current_task_type = current_task.get('task_type')
            current_task_started_at = current_task.get('started_at')

        return cls(
            name=queue_name,
            status=status,
            pending_tasks=pending,
            running_tasks=running,
            completed_tasks=completed,
            failed_tasks=failed,
            avg_duration_ms=avg_duration or 0.0,
            last_activity_ts=last_activity,
            current_task_id=current_task_id,
            current_task_type=current_task_type,
            current_task_started_at=current_task_started_at,
            snapshot_ts=snapshot_ts or datetime.utcnow().isoformat()
        )

    @staticmethod
    def _compute_status(running: int, pending: int, failed: int) -> QueueStatus:
        """Compute queue status from task counts.

        Priority:
        1. RUNNING - if any tasks are currently executing
        2. ACTIVE - if tasks are pending
        3. ERROR - if any tasks have failed (only if no running/pending)
        4. IDLE - otherwise

        Args:
            running: Count of running tasks
            pending: Count of pending tasks
            failed: Count of failed tasks

        Returns:
            Computed QueueStatus
        """
        if running > 0:
            return QueueStatus.RUNNING
        elif pending > 0:
            return QueueStatus.ACTIVE
        elif failed > 0:
            return QueueStatus.ERROR
        else:
            return QueueStatus.IDLE

    @property
    def total_tasks(self) -> int:
        """Total number of tasks (all states)."""
        return (
            self.pending_tasks +
            self.running_tasks +
            self.completed_tasks +
            self.failed_tasks
        )

    @property
    def is_healthy(self) -> bool:
        """Check if queue is healthy (no errors, not stopped)."""
        return self.status not in (QueueStatus.ERROR, QueueStatus.STOPPED)

    @property
    def is_active(self) -> bool:
        """Check if queue has active work (running or pending)."""
        return self.running_tasks > 0 or self.pending_tasks > 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (completed / (completed + failed)).

        Returns:
            Success rate as percentage (0.0 to 100.0)
        """
        total_finished = self.completed_tasks + self.failed_tasks
        if total_finished == 0:
            return 100.0

        return (self.completed_tasks / total_finished) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "queue_name": self.name,
            "status": self.status.value,
            "pending_count": self.pending_tasks,
            "running_count": self.running_tasks,
            "completed_today": self.completed_tasks,
            "failed_count": self.failed_tasks,
            "average_duration_ms": self.avg_duration_ms,
            "last_activity": self.last_activity_ts,
            "current_task": {
                "task_id": self.current_task_id,
                "task_type": self.current_task_type,
                "queue_name": self.name,
                "started_at": self.current_task_started_at
            } if self.current_task_id else None,
            "total_tasks": self.total_tasks,
            "is_healthy": self.is_healthy,
            "is_active": self.is_active,
            "success_rate": self.success_rate,
            "snapshot_ts": self.snapshot_ts
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"QueueState(name={self.name}, status={self.status.value}, "
            f"pending={self.pending_tasks}, running={self.running_tasks}, "
            f"completed={self.completed_tasks}, failed={self.failed_tasks})"
        )
