"""Configuration for the Queue Management Service."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class QueueManagementConfig:
    """Configuration for the Queue Management Service."""

    # Service settings
    service_name: str = "queue_management"
    service_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8001

    # Orchestration settings
    max_concurrent_executions: int = 5
    default_execution_timeout: int = 300  # seconds
    orchestration_rules_enabled: bool = True

    # Scheduling settings
    max_concurrent_tasks: int = 10
    task_priority_levels: int = 10
    default_task_timeout: int = 300  # seconds
    scheduling_strategy: str = "priority_queue"

    # Queue settings
    queue_concurrency_limits: Dict[str, int] = field(default_factory=lambda: {
        "portfolio_sync": 1,      # Sequential for data consistency
        "data_fetcher": 3,        # Parallel data fetching
        "ai_analysis": 2          # Limited AI resource usage
    })

    # Monitoring settings
    monitoring_enabled: bool = True
    health_check_interval: int = 30  # seconds
    metrics_collection_interval: int = 10  # seconds
    alert_check_interval: int = 15  # seconds
    performance_monitoring_interval: int = 60  # seconds

    # Alert thresholds
    alert_thresholds: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "queue_backlog": {"warning": 50, "critical": 100},
        "task_failure_rate": {"warning": 0.1, "critical": 0.25},
        "task_execution_time": {"warning": 300, "critical": 600},
        "system_memory": {"warning": 0.8, "critical": 0.9},
        "system_cpu": {"warning": 0.8, "critical": 0.9}
    })

    # AI settings
    ai_enabled: bool = True
    claude_integration_enabled: bool = True
    max_ai_concurrent_requests: int = 2
    ai_request_timeout: int = 120  # seconds

    # Data settings
    data_fetching_enabled: bool = True
    max_concurrent_data_requests: int = 5
    data_cache_enabled: bool = True
    data_cache_ttl: int = 300  # seconds

    # Portfolio settings
    portfolio_sync_enabled: bool = True
    portfolio_update_interval: int = 300  # seconds
    risk_checks_enabled: bool = True

    # Event routing settings
    event_routing_enabled: bool = True
    event_batch_size: int = 10
    event_processing_timeout: int = 30  # seconds

    # Logging settings
    log_level: str = "INFO"
    log_to_file: bool = True
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    # Security settings
    api_auth_enabled: bool = False  # Enable when authentication is implemented
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 60

    # Database settings (inherited from main config)
    database_connection_pool_size: int = 10
    database_connection_timeout: int = 30

    # External service integrations
    external_services: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "claude_agent": {
            "enabled": False,  # Set to True when Claude service is available
            "endpoint": "http://localhost:8002",
            "timeout": 120
        },
        "market_data": {
            "enabled": False,  # Set to True when market data service is available
            "endpoint": "http://localhost:8003",
            "timeout": 30
        },
        "portfolio": {
            "enabled": False,  # Set to True when portfolio service is available
            "endpoint": "http://localhost:8004",
            "timeout": 30
        },
        "fundamental": {
            "enabled": False,  # Set to True when fundamental service is available
            "endpoint": "http://localhost:8005",
            "timeout": 60
        }
    })

    def get_external_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for an external service."""
        return self.external_services.get(service_name)

    def is_external_service_enabled(self, service_name: str) -> bool:
        """Check if an external service is enabled."""
        service_config = self.get_external_service_config(service_name)
        return service_config.get("enabled", False) if service_config else False

    def get_queue_concurrency_limit(self, queue_name: str) -> int:
        """Get concurrency limit for a specific queue."""
        return self.queue_concurrency_limits.get(queue_name, 1)

    def get_alert_threshold(self, metric_name: str, level: str) -> Optional[float]:
        """Get alert threshold for a metric and level."""
        metric_thresholds = self.alert_thresholds.get(metric_name)
        return metric_thresholds.get(level) if metric_thresholds else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "host": self.host,
            "port": self.port,
            "max_concurrent_executions": self.max_concurrent_executions,
            "default_execution_timeout": self.default_execution_timeout,
            "orchestration_rules_enabled": self.orchestration_rules_enabled,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_priority_levels": self.task_priority_levels,
            "default_task_timeout": self.default_task_timeout,
            "scheduling_strategy": self.scheduling_strategy,
            "queue_concurrency_limits": self.queue_concurrency_limits,
            "monitoring_enabled": self.monitoring_enabled,
            "health_check_interval": self.health_check_interval,
            "metrics_collection_interval": self.metrics_collection_interval,
            "alert_check_interval": self.alert_check_interval,
            "performance_monitoring_interval": self.performance_monitoring_interval,
            "alert_thresholds": self.alert_thresholds,
            "ai_enabled": self.ai_enabled,
            "claude_integration_enabled": self.claude_integration_enabled,
            "max_ai_concurrent_requests": self.max_ai_concurrent_requests,
            "ai_request_timeout": self.ai_request_timeout,
            "data_fetching_enabled": self.data_fetching_enabled,
            "max_concurrent_data_requests": self.max_concurrent_data_requests,
            "data_cache_enabled": self.data_cache_enabled,
            "data_cache_ttl": self.data_cache_ttl,
            "portfolio_sync_enabled": self.portfolio_sync_enabled,
            "portfolio_update_interval": self.portfolio_update_interval,
            "risk_checks_enabled": self.risk_checks_enabled,
            "event_routing_enabled": self.event_routing_enabled,
            "event_batch_size": self.event_batch_size,
            "event_processing_timeout": self.event_processing_timeout,
            "log_level": self.log_level,
            "log_to_file": self.log_to_file,
            "log_max_size": self.log_max_size,
            "log_backup_count": self.log_backup_count,
            "api_auth_enabled": self.api_auth_enabled,
            "rate_limiting_enabled": self.rate_limiting_enabled,
            "max_requests_per_minute": self.max_requests_per_minute,
            "database_connection_pool_size": self.database_connection_pool_size,
            "database_connection_timeout": self.database_connection_timeout,
            "external_services": self.external_services
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "QueueManagementConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)