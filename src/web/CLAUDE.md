# Web Layer - src/web/

**Context**: Agent SDK bot API. Claude Code debugs FastAPI routes and validates patterns.

Max 300 lines per route file. Use FastAPI + DependencyContainer pattern.

## Endpoint Pattern

`@router.get()` → `Depends(get_container)` → `await container.get("service")` → `TradingError` → `JSONResponse`

## Critical Rules

| Rule | Implementation | Why |
|------|----------------|-----|
| Locked state | `config_state.get_*()` methods | Prevents "database is locked" |
| Error middleware | Catch `TradingError`, return `JSONResponse` | Safe error handling |
| Pydantic v2 | `Field(pattern="...")` | Never use deprecated `regex=` |
| Rate limiting | `@limiter.limit(os.getenv("RATE_LIMIT"))` | Runtime configuration |
| Security | Never expose stack traces to client | Prevent info leakage |
| SDK access | Via container, never import `anthropic` | Consistent SDK usage |
| Event loop | `asyncio.get_running_loop()` | Never `get_event_loop()` → crashes |

## Common Patterns

| Task | Implementation |
|------|----------------|
| Database | `state_manager = await container.get("state_manager")` then `state_manager.paper_trading.get_*()` |
| WebSocket | `ConnectionManager.disconnect()` on error |
| Validation | `Field(..., pattern="^(BUY\|SELL)$")` Pydantic v2 |
| AI tasks | `payload={"agent_name": "scan", "symbols": ["AAPL"]}` (symbols required) |

## Database Access

✅ **CORRECT**: `state_manager = await container.get("state_manager")` → `state_manager.paper_trading.get_*()`
❌ **NEVER**: `await db.execute()` (no lock → "database is locked" error)

## AI Task Payloads

✅ **CORRECT**: `payload={"agent_name": "scan", "symbols": ["AAPL", "GOOGL", "MSFT"]}` (max 3 stocks)
❌ **NEVER**: `payload={"agent_name": "scan"}` (missing symbols → token exhaustion)

## Common Issues

| Issue | Fix |
|-------|-----|
| "database is locked" | Use locked state methods via `state_manager` |
| Event loop is closed | Use `asyncio.get_running_loop()` not `get_event_loop()` |
| Service not registered | Use exact names: `"state_manager"` not `"database_state_manager"` |
| Pydantic validation | Check `pattern=`, `gt=`, `le=` constraints (Pydantic v2) |
| Pages freeze | Use locked methods in all endpoints |
| WebSocket leaks | Implement `disconnect()` cleanup |
| Stack traces leak | Log server-side, return safe messages only |

## Read Before Changing

- `src/CLAUDE.md` - Backend patterns (SDK, event loop, DI, locked state)
- `src/core/CLAUDE.md` - Core infrastructure (events, coordinators, DI)

