# Services Layer - src/services/

**Last Updated**: 2025-11-22

## Service Structure (Max 400 lines per file)

```python
class MyService(EventHandler):
    def __init__(self, dep1, event_bus):
        self.dep1 = dep1
        self.event_bus = event_bus
        event_bus.subscribe(EventType.RELEVANT_EVENT, self)

    async def handle_event(self, event: Event):
        try:
            if event.type == EventType.RELEVANT_EVENT:
                await self._handle(event)
        except TradingError as e:
            logger.error(f"Error: {e.context.code}")

    async def cleanup(self):
        self.event_bus.unsubscribe(EventType.RELEVANT_EVENT, self)
```

## Critical Rules

| Rule | Reason |
|------|--------|
| Use locked state methods | Prevents "database is locked" errors |
| Never call services directly | Must emit events instead |
| Inherit from EventHandler | For event-driven communication |
| Implement cleanup() | Prevents memory leaks |
| Use error hierarchy | Structured error context |
| Async/await throughout | Non-blocking operations |

## Database Access in Services

✅ **CORRECT** - Use ConfigurationState locked methods:
```python
config_state = await container.get("configuration_state")
await config_state.store_analysis_history(symbol, timestamp, analysis)
```

❌ **WRONG** - Direct database access:
```python
database = await container.get("database")
await database.connection.execute(...)  # NO LOCK!
```

## Event Handler Pattern

```python
async def handle_event(self, event: Event):
    try:
        if event.type == EventType.ORDER_FILLED:
            await self._handle_order_filled(event)
        elif event.type == EventType.PORTFOLIO_CHANGE:
            await self._handle_portfolio_change(event)
    except TradingError as e:
        logger.error(f"Error: {e.context.code}")

    # Emit follow-up event
    await self.event_bus.publish(Event(
        id=str(uuid.uuid4()),
        type=EventType.ANALYSIS_COMPLETE,
        source=self.__class__.__name__,
        data={"result": result}
    ))
```

## Current Services

| Service | Purpose |
|---------|---------|
| `portfolio_service.py` | Portfolio operations |
| `risk_service.py` | Risk management |
| `execution_service.py` | Order execution |
| `analytics_service.py` | Data analysis |
| `learning_service.py` | Learning engine |
| `paper_trading/` | Paper trading metrics |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Direct service calls | Emit events instead |
| No cleanup() | Implement unsubscribe in cleanup |
| Synchronous I/O | Use `aiofiles` with `async with` |
| No error handling | Wrap in try/except with TradingError |
| Hardcoded config | Load from DI container |

## File I/O Pattern

```python
async with aiofiles.open(path, 'r') as f:
    content = await f.read()

# Atomic writes
async with aiofiles.open(temp_path, 'w') as f:
    await f.write(data)
os.replace(temp_path, final_path)
```

## Queue-Based Claude Analysis (MANDATORY)

✅ **DO** - Queue analysis tasks:
```python
await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"agent_name": "scan", "symbols": ["AAPL"]},
    priority=7
)
```

❌ **DON'T** - Call analyzer directly:
```python
analyzer = await container.get("portfolio_intelligence_analyzer")
await analyzer.analyze_portfolio_intelligence(...)
```

Why: Direct calls exhaust turn limits on large portfolios. Queue system batches work.
