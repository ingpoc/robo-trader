"""Queue Monitoring - Comprehensive monitoring and metrics collection."""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from ....models.scheduler import QueueName, TaskStatus
from ....services.scheduler.task_service import SchedulerTaskService
from ....core.event_bus import EventBus, Event, EventType
from ..config.service_config import QueueManagementConfig
from .queue_orchestration_layer import QueueOrchestrationLayer
from .task_scheduling_engine import TaskSchedulingEngine

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point."""
    name: str
    value: Any
    type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class Alert:
    """Monitoring alert."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    source: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Health status for a component."""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: datetime
    response_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class QueueMonitoring:
    """Comprehensive monitoring system for queue management."""

    def __init__(
        self,
        orchestration_layer: QueueOrchestrationLayer,
        scheduling_engine: TaskSchedulingEngine,
        config: QueueManagementConfig
    ):
        """Initialize monitoring system."""
        self.orchestration_layer = orchestration_layer
        self.scheduling_engine = scheduling_engine
        self.config = config

        # Monitoring state
        self._running = False
        self._metrics: List[Metric] = []
        self._alerts: List[Alert] = []
        self._health_status: Dict[str, HealthStatus] = {}

        # Alert thresholds
        self._alert_thresholds = self._setup_alert_thresholds()

        # Performance tracking
        self._performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self._system_metrics_history: List[Dict[str, Any]] = []

        # Monitoring intervals
        self._health_check_interval = 30  # seconds
        self._metrics_collection_interval = 10  # seconds
        self._alert_check_interval = 15  # seconds

        # Control
        self._shutdown_event = asyncio.Event()
        self._monitoring_tasks: List[asyncio.Task] = []

    def _setup_alert_thresholds(self) -> Dict[str, Any]:
        """Setup alert thresholds for monitoring."""
        return {
            "queue_backlog_threshold": {
                "warning": 50,
                "critical": 100
            },
            "task_failure_rate_threshold": {
                "warning": 0.1,  # 10%
                "critical": 0.25  # 25%
            },
            "task_execution_time_threshold": {
                "warning": 300,  # 5 minutes
                "critical": 600  # 10 minutes
            },
            "system_memory_threshold": {
                "warning": 0.8,  # 80%
                "critical": 0.9  # 90%
            },
            "system_cpu_threshold": {
                "warning": 0.8,  # 80%
                "critical": 0.9  # 90%
            }
        }

    async def initialize(self) -> None:
        """Initialize monitoring system."""
        logger.info("Initializing Queue Monitoring...")

        # Initialize health status for all components
        components = ["orchestration_layer", "scheduling_engine", "task_service"]
        for component in components:
            self._health_status[component] = HealthStatus(
                component=component,
                status="initializing",
                last_check=datetime.utcnow(),
                response_time=0.0
            )

        logger.info("Queue Monitoring initialized")

    async def start(self) -> None:
        """Start monitoring system."""
        if self._running:
            return

        self._running = True
        logger.info("Queue Monitoring started")

        # Start monitoring tasks
        self._monitoring_tasks = [
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._metrics_collection_loop()),
            asyncio.create_task(self._alert_check_loop()),
            asyncio.create_task(self._performance_monitoring_loop())
        ]

    async def stop(self) -> None:
        """Stop monitoring system."""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)

        logger.info("Queue Monitoring stopped")

    async def _health_check_loop(self) -> None:
        """Continuous health checking loop."""
        logger.info("Starting health check loop")

        while not self._shutdown_event.is_set():
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)

        logger.info("Health check loop stopped")

    async def _metrics_collection_loop(self) -> None:
        """Continuous metrics collection loop."""
        logger.info("Starting metrics collection loop")

        while not self._shutdown_event.is_set():
            try:
                await self._collect_metrics()
                await asyncio.sleep(self._metrics_collection_interval)
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(5)

        logger.info("Metrics collection loop stopped")

    async def _alert_check_loop(self) -> None:
        """Continuous alert checking loop."""
        logger.info("Starting alert check loop")

        while not self._shutdown_event.is_set():
            try:
                await self._check_alerts()
                await asyncio.sleep(self._alert_check_interval)
            except Exception as e:
                logger.error(f"Alert check loop error: {e}")
                await asyncio.sleep(5)

        logger.info("Alert check loop stopped")

    async def _performance_monitoring_loop(self) -> None:
        """Continuous performance monitoring loop."""
        logger.info("Starting performance monitoring loop")

        while not self._shutdown_event.is_set():
            try:
                await self._collect_performance_metrics()
                await asyncio.sleep(60)  # Every minute
            except Exception as e:
                logger.error(f"Performance monitoring loop error: {e}")
                await asyncio.sleep(30)

        logger.info("Performance monitoring loop stopped")

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all components."""
        components_to_check = {
            "orchestration_layer": self.orchestration_layer.health_check,
            "scheduling_engine": self.scheduling_engine.health_check,
            # Add more components as needed
        }

        for component_name, health_check_func in components_to_check.items():
            start_time = time.time()
            try:
                health_result = await health_check_func()
                response_time = time.time() - start_time

                # Update health status
                status = "healthy" if health_result.get("status") == "healthy" else "unhealthy"
                self._health_status[component_name] = HealthStatus(
                    component=component_name,
                    status=status,
                    last_check=datetime.utcnow(),
                    response_time=response_time,
                    metrics=health_result
                )

                # Record metric
                self._record_metric(Metric(
                    name=f"health_check_{component_name}",
                    value=1 if status == "healthy" else 0,
                    type=MetricType.GAUGE,
                    timestamp=datetime.utcnow(),
                    tags={"component": component_name}
                ))

            except Exception as e:
                response_time = time.time() - start_time
                logger.error(f"Health check failed for {component_name}: {e}")

                self._health_status[component_name] = HealthStatus(
                    component=component_name,
                    status="unhealthy",
                    last_check=datetime.utcnow(),
                    response_time=response_time,
                    error_message=str(e)
                )

                # Record failure metric
                self._record_metric(Metric(
                    name=f"health_check_{component_name}",
                    value=0,
                    type=MetricType.GAUGE,
                    timestamp=datetime.utcnow(),
                    tags={"component": component_name, "error": "true"}
                ))

    async def _collect_metrics(self) -> None:
        """Collect operational metrics."""
        timestamp = datetime.utcnow()

        # Queue metrics
        orchestration_status = self.orchestration_layer.get_orchestration_status()
        scheduling_status = self.scheduling_engine.get_scheduling_status()

        # Record queue backlog metrics
        for queue_name, stats in orchestration_status.get("pending_tasks_by_queue", {}).items():
            if isinstance(stats, int):
                self._record_metric(Metric(
                    name="queue_backlog",
                    value=stats,
                    type=MetricType.GAUGE,
                    timestamp=timestamp,
                    tags={"queue": queue_name}
                ))

        # Record active executions
        self._record_metric(Metric(
            name="active_executions",
            value=orchestration_status.get("active_executions", 0),
            type=MetricType.GAUGE,
            timestamp=timestamp
        ))

        # Record scheduling metrics
        self._record_metric(Metric(
            name="priority_queue_size",
            value=scheduling_status.get("priority_queue_size", 0),
            type=MetricType.GAUGE,
            timestamp=timestamp
        ))

        self._record_metric(Metric(
            name="running_tasks",
            value=scheduling_status.get("running_tasks", 0),
            type=MetricType.GAUGE,
            timestamp=timestamp
        ))

        # System metrics
        system_metrics = self._collect_system_metrics()
        for metric_name, value in system_metrics.items():
            self._record_metric(Metric(
                name=f"system_{metric_name}",
                value=value,
                type=MetricType.GAUGE,
                timestamp=timestamp
            ))

    def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system-level metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3)
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}

    async def _check_alerts(self) -> None:
        """Check for alert conditions and generate alerts."""
        # Check queue backlog alerts
        await self._check_queue_backlog_alerts()

        # Check task failure rate alerts
        await self._check_task_failure_alerts()

        # Check system resource alerts
        await self._check_system_resource_alerts()

        # Check component health alerts
        await self._check_component_health_alerts()

    async def _check_queue_backlog_alerts(self) -> None:
        """Check for queue backlog alerts."""
        orchestration_status = self.orchestration_layer.get_orchestration_status()
        pending_tasks = orchestration_status.get("pending_tasks_by_queue", {})

        for queue_name, count in pending_tasks.items():
            if isinstance(count, int):
                thresholds = self._alert_thresholds["queue_backlog_threshold"]

                if count >= thresholds["critical"]:
                    await self._generate_alert(
                        severity=AlertSeverity.CRITICAL,
                        title=f"Critical Queue Backlog: {queue_name}",
                        message=f"Queue {queue_name} has {count} pending tasks (threshold: {thresholds['critical']})",
                        source="queue_monitoring",
                        metadata={"queue": queue_name, "pending_count": count}
                    )
                elif count >= thresholds["warning"]:
                    await self._generate_alert(
                        severity=AlertSeverity.WARNING,
                        title=f"High Queue Backlog: {queue_name}",
                        message=f"Queue {queue_name} has {count} pending tasks (threshold: {thresholds['warning']})",
                        source="queue_monitoring",
                        metadata={"queue": queue_name, "pending_count": count}
                    )

    async def _check_task_failure_alerts(self) -> None:
        """Check for task failure rate alerts."""
        scheduling_metrics = self.scheduling_engine.get_scheduling_status().get("metrics", {})
        total_tasks = scheduling_metrics.get("tasks_completed", 0) + scheduling_metrics.get("tasks_failed", 0)

        if total_tasks > 0:
            failure_rate = scheduling_metrics.get("tasks_failed", 0) / total_tasks
            thresholds = self._alert_thresholds["task_failure_rate_threshold"]

            if failure_rate >= thresholds["critical"]:
                await self._generate_alert(
                    severity=AlertSeverity.CRITICAL,
                    title="Critical Task Failure Rate",
                    message=f"Task failure rate is {failure_rate:.2%} (threshold: {thresholds['critical']:.2%})",
                    source="queue_monitoring",
                    metadata={"failure_rate": failure_rate, "total_tasks": total_tasks}
                )
            elif failure_rate >= thresholds["warning"]:
                await self._generate_alert(
                    severity=AlertSeverity.WARNING,
                    title="High Task Failure Rate",
                    message=f"Task failure rate is {failure_rate:.2%} (threshold: {thresholds['warning']:.2%})",
                    source="queue_monitoring",
                    metadata={"failure_rate": failure_rate, "total_tasks": total_tasks}
                )

    async def _check_system_resource_alerts(self) -> None:
        """Check for system resource alerts."""
        system_metrics = self._collect_system_metrics()

        # Memory alerts
        memory_percent = system_metrics.get("memory_percent", 0)
        memory_thresholds = self._alert_thresholds["system_memory_threshold"]

        if memory_percent >= memory_thresholds["critical"] * 100:
            await self._generate_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Memory Usage",
                message=f"System memory usage is {memory_percent:.1f}% (threshold: {memory_thresholds['critical']*100:.1f}%)",
                source="system_monitoring",
                metadata={"memory_percent": memory_percent}
            )
        elif memory_percent >= memory_thresholds["warning"] * 100:
            await self._generate_alert(
                severity=AlertSeverity.WARNING,
                title="High Memory Usage",
                message=f"System memory usage is {memory_percent:.1f}% (threshold: {memory_thresholds['warning']*100:.1f}%)",
                source="system_monitoring",
                metadata={"memory_percent": memory_percent}
            )

        # CPU alerts
        cpu_percent = system_metrics.get("cpu_percent", 0)
        cpu_thresholds = self._alert_thresholds["system_cpu_threshold"]

        if cpu_percent >= cpu_thresholds["critical"] * 100:
            await self._generate_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical CPU Usage",
                message=f"System CPU usage is {cpu_percent:.1f}% (threshold: {cpu_thresholds['critical']*100:.1f}%)",
                source="system_monitoring",
                metadata={"cpu_percent": cpu_percent}
            )
        elif cpu_percent >= cpu_thresholds["warning"] * 100:
            await self._generate_alert(
                severity=AlertSeverity.WARNING,
                title="High CPU Usage",
                message=f"System CPU usage is {cpu_percent:.1f}% (threshold: {cpu_thresholds['warning']*100:.1f}%)",
                source="system_monitoring",
                metadata={"cpu_percent": cpu_percent}
            )

    async def _check_component_health_alerts(self) -> None:
        """Check for component health alerts."""
        for component_name, health_status in self._health_status.items():
            if health_status.status == "unhealthy":
                await self._generate_alert(
                    severity=AlertSeverity.ERROR,
                    title=f"Component Unhealthy: {component_name}",
                    message=f"Component {component_name} is unhealthy: {health_status.error_message}",
                    source="health_monitoring",
                    metadata={
                        "component": component_name,
                        "response_time": health_status.response_time,
                        "error": health_status.error_message
                    }
                )

    async def _generate_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Generate a new alert."""
        alert = Alert(
            alert_id=f"alert_{int(time.time())}_{len(self._alerts)}",
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            source=source,
            metadata=metadata or {}
        )

        self._alerts.append(alert)

        # Keep only recent alerts (last 1000)
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]

        logger.warning(f"Alert generated: {title} ({severity.value})")

        # Record alert metric
        self._record_metric(Metric(
            name="alerts_generated",
            value=1,
            type=MetricType.COUNTER,
            timestamp=datetime.utcnow(),
            tags={"severity": severity.value, "source": source}
        ))

    async def _collect_performance_metrics(self) -> None:
        """Collect detailed performance metrics."""
        timestamp = datetime.utcnow()

        # Get current performance data
        orchestration_status = self.orchestration_layer.get_orchestration_status()
        scheduling_status = self.scheduling_engine.get_scheduling_status()

        performance_data = {
            "timestamp": timestamp.isoformat(),
            "orchestration": orchestration_status,
            "scheduling": scheduling_status,
            "system": self._collect_system_metrics(),
            "health": {name: status.status for name, status in self._health_status.items()}
        }

        # Store in history (keep last 100 entries)
        self._system_metrics_history.append(performance_data)
        if len(self._system_metrics_history) > 100:
            self._system_metrics_history = self._system_metrics_history[-100:]

    def _record_metric(self, metric: Metric) -> None:
        """Record a metric."""
        self._metrics.append(metric)

        # Keep only recent metrics (last 10000)
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-10000:]

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        return {
            "running": self._running,
            "health_status": {
                name: {
                    "status": status.status,
                    "last_check": status.last_check.isoformat(),
                    "response_time": status.response_time,
                    "error_message": status.error_message
                }
                for name, status in self._health_status.items()
            },
            "active_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved
                }
                for alert in self._alerts[-50:]  # Last 50 alerts
            ],
            "recent_metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "type": metric.type.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "tags": metric.tags
                }
                for metric in self._metrics[-100:]  # Last 100 metrics
            ],
            "performance_history_size": len(self._system_metrics_history),
            "total_alerts": len(self._alerts),
            "total_metrics": len(self._metrics)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform monitoring system health check."""
        try:
            # Check if all monitoring tasks are running
            running_tasks = sum(1 for task in self._monitoring_tasks if not task.done())

            return {
                "status": "healthy" if self._running and running_tasks == len(self._monitoring_tasks) else "degraded",
                "monitoring_tasks_running": running_tasks,
                "total_monitoring_tasks": len(self._monitoring_tasks),
                "health_checks_performed": len(self._health_status),
                "active_alerts": len([a for a in self._alerts if not a.resolved]),
                "metrics_collected": len(self._metrics)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering."""
        alerts = self._alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]

        # Return most recent first
        alerts = sorted(alerts, key=lambda x: x.timestamp, reverse=True)

        return [
            {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "source": alert.source,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "metadata": alert.metadata
            }
            for alert in alerts[:limit]
        ]

    def get_metrics(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get metrics with optional filtering."""
        metrics = self._metrics

        if name:
            metrics = [m for m in metrics if m.name == name]

        if tags:
            metrics = [
                m for m in metrics
                if all(m.tags.get(k) == v for k, v in tags.items())
            ]

        # Return most recent first
        metrics = sorted(metrics, key=lambda x: x.timestamp, reverse=True)

        return [
            {
                "name": metric.name,
                "value": metric.value,
                "type": metric.type.value,
                "timestamp": metric.timestamp.isoformat(),
                "tags": metric.tags,
                "description": metric.description
            }
            for metric in metrics[:limit]
        ]