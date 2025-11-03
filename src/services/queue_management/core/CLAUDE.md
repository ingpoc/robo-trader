# Queue Management Core Directory Guidelines

> **Scope**: Applies to `src/services/queue_management/core/` directory. Read `src/services/queue_management/CLAUDE.md` for context.

## Purpose

The `core/` directory contains core orchestration and scheduling components for the Queue Management Service. It includes the orchestration layer, scheduling engine, monitoring, and base queue class.

## Architecture Pattern

### Orchestration Layer Pattern

The core components implement advanced orchestration and scheduling patterns:
- **Queue Orchestration Layer** - Manages workflow orchestration and event-driven triggers
- **Task Scheduling Engine** - Advanced scheduling with priority and dependency management
- **Queue Monitoring** - Health monitoring and performance metrics
- **Base Queue** - Base class for queue implementations

### Directory Structure

```
core/
├── queue_orchestration_layer.py    # Workflow orchestration
├── task_scheduling_engine.py        # Task scheduling engine
├── queue_monitoring.py              # Health monitoring
└── base_queue.py                    # Base queue class
```

## Rules

### ✅ DO

- ✅ Use orchestration layer for workflow management
- ✅ Implement dependency resolution for tasks
- ✅ Emit events for orchestration lifecycle
- ✅ Monitor queue health and performance
- ✅ Use async operations throughout
- ✅ Implement retry logic with exponential backoff
- ✅ Support multiple orchestration modes

### ❌ DON'T

- ❌ Execute queues directly without orchestration
- ❌ Skip dependency resolution
- ❌ Mix orchestration logic with queue implementations
- ❌ Use blocking operations
- ❌ Skip monitoring
- ❌ Hardcode orchestration rules

## Orchestration Layer Pattern

```python
from src.services.queue_management.core.queue_orchestration_layer import QueueOrchestrationLayer

# Initialize orchestration layer
orchestration = QueueOrchestrationLayer(
    task_service=task_service,
    event_bus=event_bus,
    config=config
)

# Execute sequential workflow
result = await orchestration.execute_sequential_workflow([
    QueueName.PORTFOLIO_SYNC,
    QueueName.DATA_FETCHER,
    QueueName.AI_ANALYSIS
])
```

## Scheduling Engine Pattern

```python
from src.services.queue_management.core.task_scheduling_engine import TaskSchedulingEngine

# Initialize scheduling engine
scheduler = TaskSchedulingEngine(
    task_service=task_service,
    event_bus=event_bus,
    config=config
)

# Schedule task with dependencies
task = await scheduler.schedule_task_with_dependencies(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"symbols": ["AAPL"]},
    dependencies=[previous_task_id],
    priority=7
)
```

## Monitoring Pattern

```python
from src.services.queue_management.core.queue_monitoring import QueueMonitoring

# Initialize monitoring
monitoring = QueueMonitoring(
    orchestration_layer=orchestration,
    scheduling_engine=scheduler,
    config=config
)

# Get monitoring status
status = monitoring.get_monitoring_status()

# Check for alerts
alerts = monitoring.get_alerts(severity="CRITICAL")
```

## Base Queue Pattern

```python
from src.services.queue_management.core.base_queue import BaseQueue

class CustomQueue(BaseQueue):
    """Custom queue implementation."""
    
    def __init__(self, task_service, event_bus):
        super().__init__(
            queue_name=QueueName.CUSTOM,
            task_service=task_service,
            event_bus=event_bus
        )
    
    async def process_task(self, task):
        """Process task."""
        # Implementation
        pass
```

## Dependencies

Core components depend on:
- `SchedulerTaskService` - For task management
- `EventBus` - For event-driven workflows
- `QueueManagementConfig` - For configuration
- Database - For task persistence

## Testing

Test orchestration workflows:

```python
import pytest
from src.services.queue_management.core.queue_orchestration_layer import QueueOrchestrationLayer

async def test_sequential_workflow():
    """Test sequential workflow execution."""
    orchestration = QueueOrchestrationLayer(...)
    
    result = await orchestration.execute_sequential_workflow([
        QueueName.PORTFOLIO_SYNC
    ])
    
    assert result['status'] == 'completed'
```

## Maintenance

When modifying core components:

1. Update orchestration rules in `queue_orchestration_layer.py`
2. Update scheduling logic in `task_scheduling_engine.py`
3. Update monitoring thresholds in `queue_monitoring.py`
4. Update base queue in `base_queue.py`
5. Update this CLAUDE.md file

