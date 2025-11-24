# Scheduler Service - src/services/scheduler/

## Architecture
| Component | Pattern | Rule |
|-----------|---------|------|
| Queues | 3 PARALLEL (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS) | asyncio.gather() |
| Tasks | SEQUENTIAL within each queue | while loop, one-at-a-time |
| Timeout | 180s (3min) for AI_ANALYSIS | Fail-fast for single stocks, batch max 3 |

## Patterns

```python
# Queue manager initialization
queue_manager = SequentialQueueManager(task_service)
await queue_manager.execute_queues()

# Task creation (MUST include symbols for AI_ANALYSIS, max 3 stocks)
await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.STOCK_ANALYSIS,
    payload={"agent_name": "scan", "symbols": ["AAPL", "GOOGL", "MSFT"]}
)

# Parallel queue execution (3 queues at once)
await asyncio.gather(
    self._execute_queue(QueueName.PORTFOLIO_SYNC),
    self._execute_queue(QueueName.DATA_FETCHER),
    self._execute_queue(QueueName.AI_ANALYSIS),
    return_exceptions=True
)

# Sequential task execution (one per queue)
async def _execute_queue(self, queue_name):
    while True:
        task = await self.task_service.get_next_task(queue_name)
        if not task: break
        await self.task_service.execute_task(task)
```

## Critical Rules
✅ DO: 3 queues parallel + sequential tasks | async/await | register handlers | emit events
❌ DON'T: Sequential queues | parallel tasks within queue | blocking ops | skip errors

## Architecture Updates

| Component | Pattern | Rule |
|-----------|---------|------|
| Queues | 3 PARALLEL (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS) | asyncio.gather() |
| Tasks | SEQUENTIAL within each queue | while loop, one-at-a-time |
| Timeout | 180s (3min) for AI_ANALYSIS | Fail-fast for single stocks |
| Capacity | 20 tasks max per queue | Prevents queue overflow |
| Retry | Exponential backoff (1s → 5s → 30s → 300s) | Automatic recovery |

## Common Issues
| Error | Fix |
|-------|-----|
| Task timeout >180s | Reduce batch size or complexity |
| Queue capacity (20) exceeded | Wait for tasks to complete |
| Retry failures | Check exponential backoff logic |
| Queue stuck | Check handler is not blocking, wrap with asyncio.wait_for() |
| Tasks out of order | Verify _execute_queue() uses while loop, not asyncio.gather() |
| Task never starts | Check background scheduler init complete flag |
| **Event loop is closed** | **CRITICAL: Use `asyncio.get_running_loop()` not `asyncio.get_event_loop()`** |

## Service Name Dependencies (CRITICAL)
✅ `await container.get("state_manager")` for task operations
✅ `await container.get("event_bus")` for task events
❌ Never use "database_state_manager" - service name is wrong

```python
# ✅ CORRECT: Use exact service names
state_manager = await container.get("state_manager")  # NOT database_state_manager
task_service = await container.get("task_service")

# ❌ WRONG: Service name doesn't exist
state_manager = await container.get("database_state_manager")  # FAILURE
```

## Event Loop Management (CRITICAL)
```python
# ✅ CORRECT: Always use get_running_loop() to prevent closure errors
self._loop = asyncio.get_running_loop()
if not self._loop.is_running():
    raise RuntimeError("Event loop is not running")

# ❌ NEVER: get_event_loop() can return closed loops
self._loop = asyncio.get_event_loop()  # DANGEROUS - causes system failure
```

