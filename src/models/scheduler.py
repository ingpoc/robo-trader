"""Data models for scheduler tasks and queues."""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


class QueueName(str, Enum):
    """Sequential queue names."""
    PORTFOLIO_SYNC = "portfolio_sync"
    DATA_FETCHER = "data_fetcher"
    AI_ANALYSIS = "ai_analysis"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskType(str, Enum):
    """Task type identifiers."""
    # Portfolio sync queue
    SYNC_ACCOUNT_BALANCES = "sync_account_balances"
    UPDATE_POSITIONS = "update_positions"
    CALCULATE_OVERNIGHT_PNL = "calculate_overnight_pnl"

    # Data fetcher queue
    NEWS_MONITORING = "news_monitoring"
    EARNINGS_CHECK = "earnings_check"
    EARNINGS_SCHEDULER = "earnings_scheduler"
    FUNDAMENTALS_UPDATE = "fundamentals_update"

    # AI analysis queue
    CLAUDE_MORNING_PREP = "claude_morning_prep"
    CLAUDE_EVENING_REVIEW = "claude_evening_review"
    RECOMMENDATION_GENERATION = "recommendation_generation"


@dataclass
class SchedulerTask:
    """Individual scheduler task."""
    task_id: str
    queue_name: QueueName
    task_type: TaskType
    priority: int  # 1-10, where 10 is highest priority
    payload: Dict[str, Any]  # Task-specific data
    dependencies: List[str] = field(default_factory=list)  # task_ids that must complete first
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    scheduled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['queue_name'] = self.queue_name.value
        d['task_type'] = self.task_type.value
        d['status'] = self.status.value
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SchedulerTask':
        """Create from dictionary."""
        import ast
        data = data.copy()
        data['queue_name'] = QueueName(data['queue_name'])
        data['task_type'] = TaskType(data['task_type'])
        data['status'] = TaskStatus(data['status'])
        # Parse dependencies from JSON string to list
        if isinstance(data.get('dependencies'), str):
            data['dependencies'] = json.loads(data['dependencies']) if data['dependencies'] else []
        # Parse payload from JSON string to dict (CRITICAL: was causing 'str' has no attribute 'keys' error)
        # Handle both JSON format and legacy Python dict string format
        if isinstance(data.get('payload'), str):
            payload_str = data['payload']
            if payload_str:
                try:
                    # Try JSON first (preferred format)
                    data['payload'] = json.loads(payload_str)
                except (json.JSONDecodeError, ValueError):
                    # Fall back to Python literal eval for legacy format (Python dict with single quotes)
                    try:
                        data['payload'] = ast.literal_eval(payload_str)
                    except (ValueError, SyntaxError):
                        # If both fail, use empty dict
                        data['payload'] = {}
            else:
                data['payload'] = {}
        return SchedulerTask(**data)

    def is_ready_to_run(self, completed_tasks: List[str]) -> bool:
        """Check if all dependencies are satisfied."""
        print(f"*** is_ready_to_run() for {self.task_id}: dependencies={self.dependencies} (type={type(self.dependencies)}), completed_tasks={completed_tasks[:5] if completed_tasks else []} ***")
        dep_checks = [(dep_id, dep_id in completed_tasks) for dep_id in self.dependencies]
        print(f"*** dependency checks: {dep_checks} ***")
        result = all(dep_id in completed_tasks for dep_id in self.dependencies)
        print(f"*** is_ready_to_run() result: {result} ***")
        return result

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow().isoformat()

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.error_message = error
        if self.retry_count < self.max_retries:
            self.status = TaskStatus.RETRYING
        else:
            self.status = TaskStatus.FAILED

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.error_message = None


@dataclass
class QueueStatistics:
    """Statistics for a queue."""
    queue_name: QueueName
    pending_count: int
    running_count: int
    completed_today: int
    failed_count: int
    average_duration_ms: float
    last_completed_task_id: Optional[str] = None
    last_completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['queue_name'] = self.queue_name.value
        return d
