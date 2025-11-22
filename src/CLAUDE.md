# Backend Layer - src/

**Last Updated**: 2025-11-22

## Architecture Layers

| Layer | Responsibility | Max Size | Pattern |
|-------|---|---|---|
| `core/` | Infrastructure (DI, events, state) | Per-file: 350 lines | Coordinator base + services |
| `services/` | Business logic | 400 lines/file | EventHandler + DI injection |
| `web/` | FastAPI endpoints | 300 lines/file | Dependency injection via route |
| `models/` | Data structures | 200 lines/file | Pydantic models + enums |

## SDK-Only Rule (MANDATORY)

- ✅ Use `ClaudeSDKClientManager.get_instance()` for all AI
- ✅ Use `query_with_timeout()` + `receive_response_with_timeout()`
- ❌ NEVER import `anthropic` directly

## Database Access Pattern (CRITICAL)

✅ **DO**: Use locked state methods
```python
config_state = await container.get("configuration_state")
await config_state.store_analysis_history(symbol, timestamp, data)
```

❌ **DON'T**: Direct connection access
```python
db.connection.execute(...)  # LOCKS DATABASE!
```

## Service Event Handler Pattern

```python
class MyService(EventHandler):
    def __init__(self, event_bus):
        event_bus.subscribe(EventType.EVENT_NAME, self)

    async def handle_event(self, event: Event):
        try:
            if event.type == EventType.EVENT_NAME:
                await self._handle_event(event)
        except TradingError as e:
            logger.error(f"Error: {e.context.code}")

    async def cleanup(self):
        event_bus.unsubscribe(EventType.EVENT_NAME, self)
```

## Error Handling Pattern

```python
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

raise TradingError(
    "Message",
    category=ErrorCategory.API,
    severity=ErrorSeverity.HIGH,
    recoverable=True
)
```

## File I/O Pattern

✅ Use `aiofiles` for async operations
```python
async with aiofiles.open(path, 'r') as f:
    data = await f.read()
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "database is locked" | Direct connection access | Use locked state methods |
| "Port 8000 in use" | Orphaned process | `lsof -ti:8000 \| xargs kill -9` |
| SDK timeout | Prompt too large | Increase timeout in `sdk_helpers.py` |
| Import errors | Stale bytecode | `find . -type d -name __pycache__ -exec rm -rf {} +` |
| Hanging tasks | No timeout wrapper | Use `asyncio.wait_for(task, timeout=X)` |

## Read Layer Guides Before Changing

- `src/core/CLAUDE.md` - Core infrastructure patterns
- `src/services/CLAUDE.md` - Service patterns
- `src/web/CLAUDE.md` - Web endpoint patterns
