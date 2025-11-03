# Scheduler Service Directory Guidelines

> **Scope**: Applies to `src/services/scheduler/` directory. Read `src/services/CLAUDE.md` for context.

## Purpose

The `scheduler/` directory contains the core scheduler service with queue management. It provides `SequentialQueueManager` for parallel queue execution (queues run in parallel, tasks within queues run sequentially) and `SchedulerTaskService` for task management.

## Architecture Pattern

### Parallel Queue, Sequential Task Pattern

The scheduler implements a three-queue architecture:
- **3 queues execute in PARALLEL**: PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS
- **Tasks WITHIN each queue execute SEQUENTIALLY**: One-at-a-time per queue

This prevents turn limit exhaustion for AI analysis while allowing parallel processing across different queue types.

### Directory Structure

```
scheduler/
├── queue_manager.py    # Sequential queue manager
└── task_service.py     # Scheduler task service
```

## Rules

### ✅ DO

- ✅ Execute 3 queues in parallel using `asyncio.gather()`
- ✅ Execute tasks within each queue sequentially (one-at-a-time)
- ✅ Use `SchedulerTaskService` for task management
- ✅ Register task handlers for each task type
- ✅ Emit events for task lifecycle
- ✅ Track completed tasks to prevent duplicates
- ✅ Use async operations throughout

### ❌ DON'T

- ❌ Execute queues sequentially (WRONG)
- ❌ Execute tasks in parallel within queues (WRONG - causes turn limit exhaustion)
- ❌ Skip task handler registration
- ❌ Skip event emission
- ❌ Use blocking operations
- ❌ Skip error handling

## Queue Manager Pattern

```python
from src.services.scheduler.queue_manager import SequentialQueueManager

# Initialize queue manager
queue_manager = SequentialQueueManager(task_service)

# Execute all queues in parallel
await queue_manager.execute_queues()

# Architecture:
# - PORTFOLIO_SYNC queue processes tasks sequentially
# - DATA_FETCHER queue processes tasks sequentially  
# - AI_ANALYSIS queue processes tasks sequentially
# - All three queues run in PARALLEL
```

## Task Service Pattern

```python
from src.services.scheduler.task_service import SchedulerTaskService

# Initialize task service
task_service = SchedulerTaskService(store, execution_tracker)

# Register task handler
task_service.register_handler(
    TaskType.RECOMMENDATION_GENERATION,
    handle_recommendation_generation
)

# Create task
task = await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"symbols": ["AAPL"]},
    priority=7
)

# Execute task
result = await task_service.execute_task(task)
```

## Parallel Queue Execution

```python
async def execute_queues(self) -> None:
    """Execute all queues in parallel."""
    # Execute each queue concurrently
    await asyncio.gather(
        self._execute_queue(QueueName.PORTFOLIO_SYNC),
        self._execute_queue(QueueName.DATA_FETCHER),
        self._execute_queue(QueueName.AI_ANALYSIS),
        return_exceptions=True
    )
```

## Sequential Task Execution

```python
async def _execute_queue(self, queue_name: QueueName) -> None:
    """Execute all tasks in a queue sequentially."""
    while True:
        # Get next task
        task = await self.task_service.get_next_task(queue_name)
        if not task:
            break

        # Execute task (one-at-a-time)
        await self.task_service.execute_task(task)

        # Wait before next task (if needed)
        await asyncio.sleep(0.1)
```

## Task Execution Timeout (CRITICAL)

### Problem: Aggressive Timeouts Causing Premature Failures

**Symptoms**:
- AI analysis tasks fail with "Task execution timeout" error after 5 minutes
- Task status changes to FAILED instead of COMPLETED
- Error message: "Task execution timeout (>300s)"

**Root Cause**:
- Claude AI analysis on portfolios with 2+ stocks takes 5-10+ minutes
- Analysis includes: reasoning, SDK turns, data fetching, Claude interactions
- 300-second (5-minute) timeout was too aggressive

**Solution**:
```python
# In queue_manager.py _execute_single_task()
result = await asyncio.wait_for(
    self.task_service.execute_task(task),
    timeout=900.0  # 15 minutes for AI analysis
)
```

**Why 15 minutes?**
- AI_ANALYSIS queue tasks (recommendation_generation) need 5-10+ min
- Claude Agent SDK analysis with portfolio data is naturally slow
- Better to have generous timeout than lose legitimate analysis results
- Task-specific: PORTFOLIO_SYNC and DATA_FETCHER can still use shorter timeouts if needed

**Lessons Learned**:
1. ✅ AI analysis timeouts must account for Claude SDK reasoning time
2. ✅ Test with actual portfolio data to understand execution time
3. ✅ Document timeout rationale in code comments
4. ✅ Monitor logs to detect if timeout is still too aggressive
5. ✅ Consider making timeout configurable per task type if needed

### When to Adjust Timeout

- **Still timing out?** Increase to 1200s (20 min) if analyzing large portfolios
- **Timeout never hit?** Can reduce if consistently completing in <3 min (unlikely for AI)
- **Different queue?** PORTFOLIO_SYNC can use 60-300s, DATA_FETCHER 120-600s

## Dependencies

Scheduler components depend on:
- `SchedulerTaskStore` - For task persistence
- `ExecutionTracker` - For execution logging
- `EventBus` - For event emission
- Task handlers - For task execution logic

## Testing

Test queue execution:

```python
import pytest
from src.services.scheduler.queue_manager import SequentialQueueManager

async def test_parallel_queue_execution():
    """Test queues execute in parallel."""
    queue_manager = SequentialQueueManager(task_service)
    
    # Execute queues
    await queue_manager.execute_queues()
    
    # Verify all queues executed
    assert queue_manager._running is False
```

## Maintenance

When modifying scheduler:

1. Keep parallel queue execution (CRITICAL)
2. Keep sequential task execution within queues (CRITICAL)
3. Register task handlers for new task types
4. Update this CLAUDE.md file

