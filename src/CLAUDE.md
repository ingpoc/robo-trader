# Backend Layer - src/

**Context**: Agent SDK bot code. Claude Code debugs this, doesn't implement trading logic.

## Architecture Layers

| Layer | Max Size | Pattern |
|-------|----------|---------|
| core/ | 350 lines | DI, events, state |
| services/ | 400 lines | EventHandler + DI |
| web/ | 300 lines | FastAPI routes |
| models/ | 200 lines | Pydantic models |

## Critical Rules

| Rule | Pattern | Why |
|------|---------|-----|
| SDK-only | `ClaudeSDKClientManager.get_instance()` | Never import `anthropic` directly |
| Locked state | `config_state.store_*()` | Never direct DB connection → locks |
| Event loop | `asyncio.get_running_loop()` | Never `get_event_loop()` → crashes |
| Service names | `"state_manager"` not `"database_state_manager"` | Check di_registry_*.py |
| Async I/O | `async with aiofiles.open()` | Non-blocking file operations |
| Services | Extend `EventHandler` class | Event-driven via EventBus |
| Errors | `TradingError(category=ErrorCategory.*)` | Structured error handling |

## DI Container Service Names

✅ **CORRECT**: `await container.get("state_manager")`
❌ **WRONG**: `await container.get("database_state_manager")`

Common names: `state_manager`, `event_bus`, `config`, `resource_manager`, `background_scheduler`
(Check `di_registry_*.py` for exact names)

## Common Issues

| Issue | Fix |
|-------|-----|
| database is locked | Use locked state methods: `config_state.store_*()`|
| Event loop is closed | Use `asyncio.get_running_loop()` not `get_event_loop()` |
| Service not registered | Check exact service name in di_registry_*.py |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |
| SDK timeout | Increase timeout in sdk_helpers.py |
| Import errors | Clear __pycache__: `find . -name "*.pyc" -delete` |

## Read Before Changing

- `src/core/CLAUDE.md` - Core infrastructure patterns
- `src/services/CLAUDE.md` - Service implementation patterns
- `src/web/CLAUDE.md` - API/web patterns

