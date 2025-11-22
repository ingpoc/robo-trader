# Queue Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/queue/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Overview

Queue coordinators manage task queue execution and event routing. The architecture follows an orchestrator pattern where `QueueCoordinator` delegates to focused queue coordinators.

## Architecture Pattern

### Orchestrator + Focused Coordinators

- **`QueueCoordinator`**: Main orchestrator (max 200 lines)
  - Delegates to focused queue coordinators
  - Provides unified queue management API
  - Manages queue lifecycle

- **Focused Coordinators** (max 150 lines each):
  - `QueueLifecycleCoordinator` - Start/stop queues
  - `QueueExecutionCoordinator` - Queue execution (sequential/concurrent)
  - `QueueMonitoringCoordinator` - Queue status and health checks
  - `QueueEventCoordinator` - Event routing and handlers

## Queue Architecture (CRITICAL)

### Parallel Queue Execution

**3 queues execute in PARALLEL**:
- `PORTFOLIO_SYNC` - Portfolio operations and trading
- `DATA_FETCHER` - Market data fetching and analysis
- `AI_ANALYSIS` - Claude-powered analysis (MUST use for all Claude requests)

**Tasks WITHIN each queue execute SEQUENTIALLY** (one-at-a-time per queue).

### Why This Matters

- Prevents turn limit exhaustion (AI_ANALYSIS tasks run sequentially)
- Prevents database contention (PORTFOLIO_SYNC tasks run sequentially)
- Allows parallel processing across different queue types
- Better resource utilization

## Rules

### ✅ DO

- ✅ Inherit from `BaseCoordinator`
- ✅ Delegate execution to `SequentialQueueManager`
- ✅ Use `QueueName` enum for queue identification
- ✅ Implement health checks
- ✅ Emit queue lifecycle events
- ✅ Handle queue failures gracefully
- ✅ Keep orchestrators under 200 lines
- ✅ Keep focused coordinators under 150 lines

### ❌ DON'T

- ❌ Execute queues sequentially (use parallel execution)
- ❌ Implement queue logic directly (delegate to `SequentialQueueManager`)
- ❌ Block on queue operations
- ❌ Exceed line limits

## Implementation Pattern

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.coordinators.queue.queue_lifecycle_coordinator import QueueLifecycleCoordinator
from src.core.coordinators.queue.queue_execution_coordinator import QueueExecutionCoordinator
from src.models.scheduler import QueueName

class QueueCoordinator(BaseCoordinator):
    """Orchestrates queue operations."""
    
    def __init__(self, config: Config, container: DependencyContainer):
        super().__init__(config)
        self.lifecycle_coordinator = QueueLifecycleCoordinator(config)
        self.execution_coordinator = QueueExecutionCoordinator(config)
        # ... other focused coordinators
    
    async def start_queues(self) -> None:
        """Start all queues."""
        await self.lifecycle_coordinator.start_queues()
    
    async def execute_queues_sequential(self) -> Dict[str, Any]:
        """Execute all queues in sequence."""
        return await self.execution_coordinator.execute_queues_sequential()
```

## Queue Execution Patterns

### Sequential Execution

Use for testing or when strict ordering is required:

```python
result = await queue_coordinator.execute_queues_sequential()
```

### Concurrent Execution

Use for production (default):

```python
# Delegates to SequentialQueueManager which executes in parallel
result = await queue_coordinator.execute_queues_concurrent(max_concurrent=2)
```

## Event Routing

- Use `QueueEventCoordinator` for event handling
- Route market events to appropriate handlers
- Trigger event routing for high-impact events (impact_score > 0.7)
- Handle event routing failures gracefully

## Dependencies

Queue coordinators typically depend on:
- `SequentialQueueManager` - For queue execution and task management
- `EventBus` - For event-driven communication
- `BroadcastCoordinator` - For UI updates

