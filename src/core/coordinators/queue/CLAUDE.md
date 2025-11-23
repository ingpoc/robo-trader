# Queue Coordinator - src/core/coordinators/queue/

Manages 3 parallel queues. Tasks within queue execute sequentially.

## Critical: Queue Execution Model
**3 queues in PARALLEL**, tasks within queue SEQUENTIAL:
- PORTFOLIO_SYNC - Portfolio ops, trading
- DATA_FETCHER - Market data, analysis
- AI_ANALYSIS - Claude requests (MANDATORY for all AI)

Why: Prevents turn limit exhaustion, database contention, parallel cross-queue processing.

## Pattern
Orchestrator + focused coordinators. Max 200 lines (orchestrator), max 150 (focused).

```python
await lifecycle_coordinator.start_queues()
await execution_coordinator.execute_parallel()
status = await monitoring_coordinator.get_queue_status()
```

## Coordinators
| Coordinator | Purpose |
|-------------|---------|
| QueueLifecycleCoordinator | Start/stop queues |
| QueueExecutionCoordinator | Sequential execution per queue |
| QueueMonitoringCoordinator | Health checks, status |
| QueueEventCoordinator | Event routing |

## Rules
| DO | DON'T |
|----|-------|
| Delegate to SequentialQueueManager | Execute queues sequentially |
| Use QueueName enum | Implement queue logic directly |
| Emit lifecycle events | Block on I/O |
| Async throughout | Exceed 200/150 lines |
| Health checks | Direct service calls |

## Dependencies
SequentialQueueManager, EventBus, BroadcastCoordinator

