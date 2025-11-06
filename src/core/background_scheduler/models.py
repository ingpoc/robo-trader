"""
Task models for Background Scheduler.

Defines core data structures for task management.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TaskType(Enum):
    """Types of background tasks."""

    MARKET_MONITORING = "market_monitoring"
    EARNINGS_CHECK = "earnings_check"
    EARNINGS_SCHEDULER = "earnings_scheduler"
    STOP_LOSS_MONITOR = "stop_loss_monitor"
    NEWS_MONITORING = "news_monitoring"
    NEWS_DAILY = "news_daily"
    FUNDAMENTAL_MONITORING = "fundamental_monitoring"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    HEALTH_CHECK = "health_check"
    PORTFOLIO_SCAN = "portfolio_scan"
    MARKET_SCREENING = "market_screening"
    AI_PLANNING = "ai_planning"
    EARNINGS_FUNDAMENTALS = "earnings_fundamentals"
    MARKET_NEWS_ANALYSIS = "market_news_analysis"
    DEEP_FUNDAMENTAL_ANALYSIS = "deep_fundamental_analysis"


class TaskPriority(Enum):
    """Task priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BackgroundTask:
    """Represents a scheduled background task."""

    task_id: str
    task_type: TaskType
    priority: TaskPriority
    execute_at: datetime
    interval_seconds: Optional[int] = None
    max_retries: int = 3
    retry_count: int = 0
    last_executed: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["task_type"] = self.task_type.value
        data["priority"] = self.priority.value
        data["execute_at"] = self.execute_at.isoformat()
        if self.last_executed:
            data["last_executed"] = self.last_executed.isoformat()
        if self.next_execution:
            data["next_execution"] = self.next_execution.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackgroundTask":
        data_copy = data.copy()
        data_copy["task_type"] = TaskType(data["task_type"])
        data_copy["priority"] = TaskPriority(data["priority"])
        data_copy["execute_at"] = datetime.fromisoformat(data["execute_at"])
        if "last_executed" in data and data["last_executed"]:
            data_copy["last_executed"] = datetime.fromisoformat(data["last_executed"])
        if "next_execution" in data and data["next_execution"]:
            data_copy["next_execution"] = datetime.fromisoformat(data["next_execution"])
        return cls(**data_copy)
