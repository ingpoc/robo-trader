"""Data models for queue management operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class ExecutionStatus(str, Enum):
    """Status of task/queue execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AlertSeverity(str, Enum):
    """Severity levels for monitoring alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ServiceComponent(str, Enum):
    """Service components for health monitoring."""
    ORCHESTRATION_LAYER = "orchestration_layer"
    SCHEDULING_ENGINE = "scheduling_engine"
    MONITORING = "monitoring"
    EVENT_BUS = "event_bus"
    DATABASE = "database"


@dataclass
class QueueStatus:
    """Status information for a queue."""
    queue_name: str
    is_running: bool
    current_task_id: Optional[str]
    pending_tasks_count: int
    completed_tasks_count: int
    failed_tasks_count: int
    average_execution_time: float
    last_execution_time: Optional[datetime]
    registered_handlers: List[str]
    queue_specific_status: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecutionResult:
    """Result of a task execution."""
    task_id: str
    queue_name: str
    task_type: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime]
    execution_time: Optional[float]
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class OrchestrationResult:
    """Result of an orchestration operation."""
    execution_id: str
    mode: str  # "sequential", "parallel", "event_driven"
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_duration: Optional[float]
    queues_executed: List[str]
    tasks_completed: int
    tasks_failed: int
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringAlert:
    """Monitoring alert information."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    source: str
    component: Optional[ServiceComponent]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)


@dataclass
class ServiceHealth:
    """Health status for a service component."""
    component: ServiceComponent
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: datetime
    response_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    component: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float] = field(default_factory=dict)
    active_connections: int = 0
    queue_depth: int = 0
    throughput: float = 0.0  # tasks per second
    latency: float = 0.0  # average response time
    error_rate: float = 0.0


@dataclass
class SystemResources:
    """System resource usage information."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    active_processes: int = 0


@dataclass
class QueueMetrics:
    """Metrics specific to queue operations."""
    queue_name: str
    timestamp: datetime
    tasks_queued: int
    tasks_processing: int
    tasks_completed: int
    tasks_failed: int
    average_wait_time: float
    average_processing_time: float
    throughput_per_minute: float
    error_rate: float
    backlog_size: int
    concurrency_utilization: float


@dataclass
class OrchestrationMetrics:
    """Metrics for orchestration operations."""
    timestamp: datetime
    active_executions: int
    completed_executions: int
    failed_executions: int
    average_execution_time: float
    rules_triggered: int
    events_processed: int
    cross_queue_triggers: int


@dataclass
class AIMetrics:
    """Metrics for AI operations."""
    timestamp: datetime
    requests_sent: int
    requests_completed: int
    requests_failed: int
    average_response_time: float
    token_usage: int = 0
    cost_accumulated: float = 0.0
    confidence_average: float = 0.0
    recommendations_generated: int = 0


@dataclass
class DataFetcherMetrics:
    """Metrics for data fetching operations."""
    timestamp: datetime
    api_calls_made: int
    api_calls_failed: int
    data_points_fetched: int
    cache_hits: int
    cache_misses: int
    average_response_time: float
    rate_limits_hit: int = 0


@dataclass
class PortfolioMetrics:
    """Metrics for portfolio operations."""
    timestamp: datetime
    accounts_synced: int
    positions_updated: int
    pnl_calculated: int
    risk_checks_performed: int
    sync_errors: int = 0
    average_sync_time: float = 0.0


# Utility functions for model conversion

def queue_status_to_dict(status: QueueStatus) -> Dict[str, Any]:
    """Convert QueueStatus to dictionary."""
    return {
        "queue_name": status.queue_name,
        "is_running": status.is_running,
        "current_task_id": status.current_task_id,
        "pending_tasks_count": status.pending_tasks_count,
        "completed_tasks_count": status.completed_tasks_count,
        "failed_tasks_count": status.failed_tasks_count,
        "average_execution_time": status.average_execution_time,
        "last_execution_time": status.last_execution_time.isoformat() if status.last_execution_time else None,
        "registered_handlers": status.registered_handlers,
        "queue_specific_status": status.queue_specific_status
    }


def task_execution_result_to_dict(result: TaskExecutionResult) -> Dict[str, Any]:
    """Convert TaskExecutionResult to dictionary."""
    return {
        "task_id": result.task_id,
        "queue_name": result.queue_name,
        "task_type": result.task_type,
        "status": result.status.value,
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "execution_time": result.execution_time,
        "result_data": result.result_data,
        "error_message": result.error_message,
        "retry_count": result.retry_count,
        "max_retries": result.max_retries
    }


def orchestration_result_to_dict(result: OrchestrationResult) -> Dict[str, Any]:
    """Convert OrchestrationResult to dictionary."""
    return {
        "execution_id": result.execution_id,
        "mode": result.mode,
        "status": result.status.value,
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "total_duration": result.total_duration,
        "queues_executed": result.queues_executed,
        "tasks_completed": result.tasks_completed,
        "tasks_failed": result.tasks_failed,
        "results": result.results,
        "metadata": result.metadata
    }


def monitoring_alert_to_dict(alert: MonitoringAlert) -> Dict[str, Any]:
    """Convert MonitoringAlert to dictionary."""
    return {
        "alert_id": alert.alert_id,
        "severity": alert.severity.value,
        "title": alert.title,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat(),
        "source": alert.source,
        "component": alert.component.value if alert.component else None,
        "resolved": alert.resolved,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "metadata": alert.metadata,
        "recommended_actions": alert.recommended_actions
    }


def service_health_to_dict(health: ServiceHealth) -> Dict[str, Any]:
    """Convert ServiceHealth to dictionary."""
    return {
        "component": health.component.value,
        "status": health.status,
        "last_check": health.last_check.isoformat(),
        "response_time": health.response_time,
        "error_message": health.error_message,
        "metrics": health.metrics,
        "dependencies": health.dependencies
    }