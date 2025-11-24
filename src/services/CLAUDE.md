# Services Layer - src/services/

Max 400 lines per file. Inherit from EventHandler, event-driven comms via EventBus.

## Service Pattern

```python
class MyService(EventHandler):
    def __init__(self, dep1, event_bus):
        self.dep1 = dep1
        self.event_bus = event_bus
        event_bus.subscribe(EventType.RELEVANT_EVENT, self)

    async def handle_event(self, event: Event):
        if event.type == EventType.RELEVANT_EVENT:
            await self._handle(event)

    async def cleanup(self):
        self.event_bus.unsubscribe(EventType.RELEVANT_EVENT, self)
```

## Critical Rules

| Rule | Why |
|------|-----|
| Use locked state methods | Prevents "database is locked" |
| Never call services directly | Emit events instead |
| Implement cleanup() | Prevents memory leaks |
| Async/await throughout | Non-blocking I/O |
| Queue AI analysis tasks | Prevents turn limit exhaustion |
| Use error hierarchy | Structured error context |

## Database Access

✅ `await config_state.store_analysis_history(symbol, ts, data)` (locked)
❌ Never: `db.connection.execute()` (no lock!)

## File I/O

```python
async with aiofiles.open(path, 'r') as f:
    content = await f.read()
# Atomic writes
async with aiofiles.open(temp, 'w') as f:
    await f.write(data)
os.replace(temp, final)
```

## Queue AI Analysis (MANDATORY)

```python
await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"agent_name": "scan", "symbols": ["AAPL"]}
)
```

❌ Never direct analyzer calls—turn limits exhaust on large portfolios.

## Common Mistakes
| Mistake | Fix |
|---------|-----|
| Direct service calls | Emit events |
| No cleanup() | Unsubscribe in cleanup |
| Sync I/O | Use `aiofiles` |
| No error handling | TradingError with context |
| Hardcoded config | Load from DI container |
| **Event loop closure** | **ALWAYS use `asyncio.get_running_loop()` not `get_event_loop()`** |

## Event Loop Safety (CRITICAL)
```python
# ✅ SAFE: Get current running loop
self._loop = asyncio.get_running_loop()
if not self._loop.is_running():
    raise RuntimeError("Event loop is not running")

# ❌ DANGEROUS: Can return closed loops
self._loop = asyncio.get_event_loop()  # CAUSES SYSTEM FAILURE
```
