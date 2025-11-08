"""Task state domain model.

Represents individual task state with rich behavior.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from ...models.scheduler import TaskStatus, TaskType, QueueName


@dataclass
class TaskState:
    """Immutable snapshot of task state.

    Represents a single task with all its attributes and computed properties.

    Attributes:
        task_id: Unique task identifier
        queue_name: Queue this task belongs to
        task_type: Type of task
        status: Current task status
        priority: Task priority (1-10, higher = more urgent)
        payload: Task payload data
        retry_count: Number of times task has been retried
        max_retries: Maximum retry attempts
        scheduled_at: When task was created
        started_at: When task execution started
        completed_at: When task completed
        error_message: Error message if failed
    """

    task_id: str
    queue_name: str
    task_type: str
    status: str
    priority: int
    payload: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'TaskState':
        """Create TaskState from database row.

        Args:
            row: Database row as dictionary

        Returns:
            TaskState instance
        """
        import json

        # Parse JSON payload if it's a string
        payload = row.get('payload', {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}

        return cls(
            task_id=row['task_id'],
            queue_name=row['queue_name'],
            task_type=row['task_type'],
            status=row['status'],
            priority=row.get('priority', 5),
            payload=payload,
            retry_count=row.get('retry_count', 0),
            max_retries=row.get('max_retries', 3),
            scheduled_at=row.get('scheduled_at'),
            started_at=row.get('started_at'),
            completed_at=row.get('completed_at'),
            error_message=row.get('error_message')
        )

    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate task duration in milliseconds.

        Returns:
            Duration in milliseconds, or None if not completed
        """
        if not self.started_at or not self.completed_at:
            return None

        try:
            start = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.completed_at.replace('Z', '+00:00'))
            duration = (end - start).total_seconds() * 1000
            return int(duration)
        except (ValueError, AttributeError):
            return None

    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.status == TaskStatus.RUNNING.value

    @property
    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status == TaskStatus.PENDING.value

    @property
    def is_completed(self) -> bool:
        """Check if task completed successfully."""
        return self.status == TaskStatus.COMPLETED.value

    @property
    def is_failed(self) -> bool:
        """Check if task failed."""
        return self.status == TaskStatus.FAILED.value

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.is_failed and self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses.

        Returns:
            Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "queue_name": self.queue_name,
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "payload": self.payload,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "scheduled_at": self.scheduled_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "is_running": self.is_running,
            "is_pending": self.is_pending,
            "is_completed": self.is_completed,
            "is_failed": self.is_failed,
            "can_retry": self.can_retry
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"TaskState(id={self.task_id}, queue={self.queue_name}, "
            f"type={self.task_type}, status={self.status})"
        )
