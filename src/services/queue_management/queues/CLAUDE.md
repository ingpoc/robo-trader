# Queue Management Queues Directory Guidelines

> **Scope**: Applies to `src/services/queue_management/queues/` directory. Read `src/services/queue_management/CLAUDE.md` for context.

## Purpose

The `queues/` directory contains specialized queue implementations for the Queue Management Service. Each queue handles specific task types for its domain (Portfolio, Data Fetcher, AI Analysis).

## Architecture Pattern

### Specialized Queue Pattern

Each queue extends `BaseQueue` and implements domain-specific task processing logic. Queues handle task execution, error management, and event emission.

### Directory Structure

```
queues/
├── portfolio_queue.py        # Portfolio synchronization queue
├── data_fetcher_queue.py     # Data fetching queue
└── ai_analysis_queue.py      # AI analysis queue
```

## Rules

### ✅ DO

- ✅ Extend `BaseQueue` for queue implementations
- ✅ Implement domain-specific task processing
- ✅ Register task handlers for each task type
- ✅ Emit events for task lifecycle
- ✅ Handle errors gracefully
- ✅ Use async operations throughout
- ✅ Track queue-specific metrics

### ❌ DON'T

- ❌ Mix multiple queue responsibilities
- ❌ Skip task handler registration
- ❌ Use blocking operations
- ❌ Skip error handling
- ❌ Omit event emission
- ❌ Create queue dependencies

## Queue Pattern

```python
from src.services.queue_management.queues.portfolio_queue import PortfolioQueue
from src.services.queue_management.core.base_queue import BaseQueue

class PortfolioQueue(BaseQueue):
    """Portfolio synchronization queue."""
    
    def __init__(self, task_service, event_bus):
        super().__init__(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_service=task_service,
            event_bus=event_bus
        )
        
        # Register task handlers
        self.register_task_handler(
            TaskType.SYNC_ACCOUNT_BALANCES,
            self._handle_sync_balances
        )
    
    async def _handle_sync_balances(self, task):
        """Handle balance synchronization."""
        # Implementation
        pass
```

## Portfolio Queue Pattern

```python
from src.services.queue_management.queues.portfolio_queue import PortfolioQueue

portfolio_queue = PortfolioQueue(task_service, event_bus)

# Process portfolio task
result = await portfolio_queue.process_task(task)

# Portfolio queue handles:
# - Account balance synchronization
# - Position updates
# - P&L calculations
# - Risk validation
```

## Data Fetcher Queue Pattern

```python
from src.services.queue_management.queues.data_fetcher_queue import DataFetcherQueue

data_fetcher_queue = DataFetcherQueue(task_service, event_bus)

# Process data fetching task
result = await data_fetcher_queue.process_task(task)

# Data fetcher queue handles:
# - News monitoring
# - Earnings data collection
# - Fundamental data updates
# - Options data fetching
```

## AI Analysis Queue Pattern

```python
from src.services.queue_management.queues.ai_analysis_queue import AIAnalysisQueue

ai_queue = AIAnalysisQueue(task_service, event_bus)

# Process AI analysis task
result = await ai_queue.process_task(task)

# AI analysis queue handles:
# - Morning preparation analysis
# - Evening performance reviews
# - Trading recommendations
# - Strategy analysis
```

## Task Handler Registration

```python
class PortfolioQueue(BaseQueue):
    def __init__(self, task_service, event_bus):
        super().__init__(...)
        
        # Register task handlers
        self.register_task_handler(
            TaskType.SYNC_ACCOUNT_BALANCES,
            self._handle_sync_balances
        )
        self.register_task_handler(
            TaskType.UPDATE_POSITIONS,
            self._handle_update_positions
        )
```

## Event Emission

Queues emit events for task lifecycle:

```python
from src.core.event_bus import Event, EventType

# Emit task started event
await self.event_bus.publish(Event(
    type=EventType.TASK_STARTED,
    source="portfolio_queue",
    data={"task_id": task.task_id}
))

# Emit task completed event
await self.event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    source="portfolio_queue",
    data={"task_id": task.task_id, "result": result}
))
```

## Dependencies

Queue components depend on:
- `BaseQueue` - Base queue class
- `SchedulerTaskService` - For task management
- `EventBus` - For event emission
- Domain services - For business logic (PortfolioService, etc.)

## Testing

Test queue implementations:

```python
import pytest
from src.services.queue_management.queues.portfolio_queue import PortfolioQueue

async def test_portfolio_queue():
    """Test portfolio queue."""
    queue = PortfolioQueue(task_service, event_bus)
    
    task = create_test_task(TaskType.SYNC_ACCOUNT_BALANCES)
    result = await queue.process_task(task)
    
    assert result['status'] == 'completed'
```

## Maintenance

When adding new queues:

1. Extend `BaseQueue`
2. Register task handlers
3. Implement task processing logic
4. Emit lifecycle events
5. Update this CLAUDE.md file

