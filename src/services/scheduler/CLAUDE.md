# Scheduler Service - src/services/scheduler/

## Architecture
| Component | Pattern | Rule |
|-----------|---------|------|
| Queues | 3 PARALLEL (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS) | asyncio.gather() |
| Tasks | SEQUENTIAL within each queue | while loop, one-at-a-time |
| Timeout | 900s (15min) for AI_ANALYSIS | Increase if analyzing 2+ stocks |

## Patterns

```python
# Queue manager initialization
queue_manager = SequentialQueueManager(task_service)
await queue_manager.execute_queues()

# Task creation (MUST include symbols for AI_ANALYSIS)
await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"symbols": ["AAPL"]}
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

## Common Issues
| Error | Fix |
|-------|-----|
| Task timeout >900s | Increase timeout in queue_manager.py line 132 |
| Queue stuck | Check handler is not blocking, wrap with asyncio.wait_for() |
| Tasks out of order | Verify _execute_queue() uses while loop, not asyncio.gather() |
| Task never starts | Check background scheduler init complete flag |

