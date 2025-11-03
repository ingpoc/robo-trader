# Queue Management Config Directory Guidelines

> **Scope**: Applies to `src/services/queue_management/config/` directory. Read `src/services/queue_management/CLAUDE.md` for context.

## Purpose

The `config/` directory contains configuration classes for the Queue Management Service. It defines service settings, orchestration parameters, scheduling configurations, and monitoring thresholds.

## Architecture Pattern

### Configuration Dataclass Pattern

The configuration uses Python dataclasses to define service settings. Configurations are immutable and type-safe.

### Directory Structure

```
config/
└── service_config.py    # Service configuration class
```

## Rules

### ✅ DO

- ✅ Use dataclasses for configuration
- ✅ Provide default values
- ✅ Document configuration options
- ✅ Use type hints
- ✅ Validate configuration values
- ✅ Support environment variable overrides

### ❌ DON'T

- ❌ Hardcode configuration values
- ❌ Skip default values
- ❌ Use mutable default values
- ❌ Skip validation
- ❌ Mix configuration with business logic

## Configuration Pattern

```python
from dataclasses import dataclass
from src.services.queue_management.config.service_config import QueueManagementConfig

# Initialize configuration
config = QueueManagementConfig(
    max_concurrent_executions=10,
    default_execution_timeout=300
)

# Access configuration
max_concurrent = config.max_concurrent_executions
timeout = config.default_execution_timeout
```

## Configuration Structure

```python
@dataclass
class QueueManagementConfig:
    """Configuration for Queue Management Service."""
    
    # Service settings
    service_name: str = "queue_management"
    service_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Orchestration settings
    max_concurrent_executions: int = 5
    default_execution_timeout: int = 300
    
    # Scheduling settings
    max_concurrent_tasks: int = 10
    task_priority_levels: int = 10
    
    # Queue settings
    queue_concurrency_limits: Dict[str, int] = field(default_factory=lambda: {
        "portfolio_sync": 1,
        "data_fetcher": 3,
        "ai_analysis": 2
    })
    
    # Monitoring settings
    monitoring_enabled: bool = True
    health_check_interval: int = 30
    
    # Alert thresholds
    alert_thresholds: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "queue_backlog": {"warning": 50, "critical": 100},
        "task_failure_rate": {"warning": 0.1, "critical": 0.25}
    })
```

## Environment Variable Overrides

```python
import os
from dataclasses import dataclass

@dataclass
class QueueManagementConfig:
    max_concurrent_executions: int = 5
    
    @classmethod
    def from_env(cls):
        """Create config from environment variables."""
        return cls(
            max_concurrent_executions=int(
                os.getenv("QUEUE_MAX_CONCURRENT", "5")
            )
        )
```

## Configuration Validation

```python
@dataclass
class QueueManagementConfig:
    max_concurrent_executions: int = 5
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.max_concurrent_executions < 1:
            raise ValueError("max_concurrent_executions must be >= 1")
        if self.max_concurrent_executions > 100:
            raise ValueError("max_concurrent_executions must be <= 100")
```

## Dependencies

Config components depend on:
- `dataclasses` - For configuration classes
- `typing` - For type hints
- `os` - For environment variable access (optional)

## Testing

Test configuration:

```python
import pytest
from src.services.queue_management.config.service_config import QueueManagementConfig

def test_config_defaults():
    """Test configuration default values."""
    config = QueueManagementConfig()
    assert config.max_concurrent_executions == 5
    assert config.default_execution_timeout == 300

def test_config_validation():
    """Test configuration validation."""
    with pytest.raises(ValueError):
        QueueManagementConfig(max_concurrent_executions=0)
```

## Maintenance

When adding new configuration options:

1. Add field to configuration class
2. Provide default value
3. Add validation if needed
4. Document configuration option
5. Update this CLAUDE.md file

