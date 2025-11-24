# Backend Layer - src/

## Architecture Layers
| Layer | Max Size | Pattern |
|-------|----------|---------|
| core/ | 350 lines | DI, events, state |
| services/ | 400 lines | EventHandler + DI |
| web/ | 300 lines | FastAPI routes |
| models/ | 200 lines | Pydantic models |

## SDK-Only Rule (MANDATORY)
✅ Use `ClaudeSDKClientManager.get_instance()` + `query_with_timeout()`
❌ NEVER import `anthropic` directly

## Database Access (CRITICAL)
✅ Use locked state: `config_state.store_analysis_history(symbol, ts, data)`
❌ Never: `db.connection.execute()` → locks database!

## Service Pattern
```python
class MyService(EventHandler):
    async def handle_event(self, event: Event):
        if event.type == EventType.EVENT_NAME:
            await self._handle_event(event)
```

## Error Handling
```python
raise TradingError("msg", category=ErrorCategory.API, recoverable=True)
```

## File I/O
Use `aiofiles` for async: `async with aiofiles.open(path) as f: data = await f.read()`

## Event Loop Safety (CRITICAL)
| Rule | Why |
|------|-----|
| Use `asyncio.get_running_loop()` | Prevents "event loop is closed" system failures |
| Never use `asyncio.get_event_loop()` | Can return closed loops causing complete system crash |

## DI Container Service Names (CRITICAL)
✅ **CORRECT**: `await container.get("state_manager")`
❌ **WRONG**: `await container.get("database_state_manager")`

**Common Service Names**:
- `"state_manager"` (not "database_state_manager")
- `"event_bus"`
- `"config"`
- `"resource_manager"`
- `"background_scheduler"`

Check `di_registry_*.py` files for exact service names.

## Common Issues
| Issue | Fix |
|-------|-----|
| database is locked | Use locked state methods |
| **Event loop is closed** | **Use `asyncio.get_running_loop()` not `get_event_loop()`** |
| **Service not registered** | **Check exact service name in di_registry_*.py files** |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |
| SDK timeout | Increase timeout in sdk_helpers.py |
| Import errors | Clear __pycache__ directories |

## Read Before Changing
- src/core/CLAUDE.md - Core infrastructure
- src/services/CLAUDE.md - Service patterns
- src/web/CLAUDE.md - Web patterns
