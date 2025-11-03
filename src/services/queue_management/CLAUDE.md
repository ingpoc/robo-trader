# Queue Management Service Directory Guidelines

> **Scope**: Applies to `src/services/queue_management/` directory. Read `src/services/CLAUDE.md` for context.

## Purpose

The `queue_management/` directory contains an advanced task scheduling and orchestration service. It manages execution flow of trading operations across specialized queues with dependency management, monitoring, and event-driven triggers.

## Architecture Pattern

### Queue Orchestration Pattern

The service uses a queue orchestration layer that manages complex workflows:
- **Queue Orchestration Layer** - Manages workflow orchestration and event-driven triggers
- **Task Scheduling Engine** - Advanced scheduling with priority and dependency management
- **Queue Monitoring** - Health monitoring and performance metrics
- **Queue Implementations** - Specialized queues (Portfolio, Data Fetcher, AI Analysis)

### Directory Structure

```
queue_management/
├── main.py                  # Service entry point
├── core/                     # Core orchestration components
│   ├── queue_orchestration_layer.py
│   ├── task_scheduling_engine.py
│   ├── queue_monitoring.py
│   └── base_queue.py
├── queues/                   # Queue implementations
│   ├── portfolio_queue.py
│   ├── data_fetcher_queue.py
│   └── ai_analysis_queue.py
├── api/                      # API routes
│   └── routes.py
├── config/                    # Configuration
│   └── service_config.py
└── models/                   # Data models
    └── queue_models.py
```

## Rules

### ✅ DO

- ✅ Use orchestration layer for workflow management
- ✅ Implement dependency resolution for tasks
- ✅ Emit events for task lifecycle
- ✅ Monitor queue health and performance
- ✅ Use async operations throughout
- ✅ Implement retry logic with exponential backoff
- ✅ Support multiple orchestration modes (sequential, parallel, conditional, event-driven)

### ❌ DON'T

- ❌ Execute queues directly without orchestration layer
- ❌ Skip dependency resolution
- ❌ Mix queue implementations
- ❌ Use blocking operations
- ❌ Skip monitoring
- ❌ Hardcode orchestration rules

## Queue Orchestration Pattern

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

# Execute parallel workflow
result = await orchestration.execute_parallel_workflow([
    QueueName.PORTFOLIO_SYNC,
    QueueName.DATA_FETCHER
])
```

## Task Scheduling Pattern

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

## Queue Monitoring Pattern

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

## Orchestration Modes

### Sequential Mode
```python
# Execute queues in strict order
result = await orchestration.execute_sequential_workflow([
    QueueName.PORTFOLIO_SYNC,
    QueueName.DATA_FETCHER,
    QueueName.AI_ANALYSIS
])
```

### Parallel Mode
```python
# Execute queues concurrently
result = await orchestration.execute_parallel_workflow([
    QueueName.PORTFOLIO_SYNC,
    QueueName.DATA_FETCHER
])
```

### Conditional Mode
```python
# Execute based on conditions
result = await orchestration.execute_conditional_workflow(
    queues=[QueueName.AI_ANALYSIS],
    conditions={"portfolio_synced": True}
)
```

### Event-Driven Mode
```python
# Execute on event trigger
result = await orchestration.execute_event_driven_workflow(
    queues=[QueueName.AI_ANALYSIS],
    trigger_events=[EventType.PORTFOLIO_UPDATED]
)
```

## Queue Implementations

### Portfolio Queue
```python
from src.services.queue_management.queues.portfolio_queue import PortfolioQueue

portfolio_queue = PortfolioQueue(base_queue, task_service)
await portfolio_queue.process_task(task)
```

### Data Fetcher Queue
```python
from src.services.queue_management.queues.data_fetcher_queue import DataFetcherQueue

data_fetcher_queue = DataFetcherQueue(base_queue, task_service)
await data_fetcher_queue.process_task(task)
```

### AI Analysis Queue
```python
from src.services.queue_management.queues.ai_analysis_queue import AIAnalysisQueue

ai_queue = AIAnalysisQueue(base_queue, task_service)
await ai_queue.process_task(task)
```

## Dependencies

Queue management components depend on:
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

When modifying queue management:

1. Update orchestration rules in `queue_orchestration_layer.py`
2. Update scheduling logic in `task_scheduling_engine.py`
3. Update monitoring thresholds in `queue_monitoring.py`
4. Update this CLAUDE.md file

