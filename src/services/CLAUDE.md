# Services Layer - src/services/

**Context**: Agent SDK bot services. Claude Code debugs service implementations.

Max 400 lines per service. Extend `EventHandler`, use event-driven communication.

## Service Pattern

Extend `EventHandler` → subscribe to events → handle in `handle_event()` → cleanup via `cleanup()`

## Critical Rules

| Rule | Implementation | Why |
|------|----------------|-----|
| Locked state | `config_state.store_*()` methods | Prevents "database is locked" |
| Event-driven | Emit events, never call services directly | Loose coupling |
| Cleanup | `unsubscribe()` in `cleanup()` method | Prevents memory leaks |
| Async I/O | `async with aiofiles.open()` | Non-blocking file operations |
| Queue AI tasks | `QueueName.AI_ANALYSIS` with max 3 symbols | Prevents turn limit exhaustion |
| Event loop | `asyncio.get_running_loop()` | Never `get_event_loop()` → crashes |
| Errors | `TradingError(category=ErrorCategory.*)` | Structured error context |

## Database Access

✅ **CORRECT**: `await config_state.store_analysis_history(symbol, ts, data)`
❌ **NEVER**: `db.connection.execute()` (no lock → database locked error)

## Queue AI Analysis (MANDATORY)

✅ **CORRECT**: `await task_service.create_task(queue_name=QueueName.AI_ANALYSIS, task_type=TaskType.STOCK_ANALYSIS, payload={"agent_name": "scan", "symbols": ["AAPL", "GOOGL", "MSFT"]})`
❌ **NEVER**: Direct analyzer calls (exhausts turn limits on large portfolios)

Max 3 stocks per task to prevent timeouts.

## File I/O

Use `aiofiles` for async: `async with aiofiles.open(path) as f: data = await f.read()`
Atomic writes: write to temp → `os.replace(temp, final)`

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Direct service calls | Emit events via EventBus |
| No cleanup() | Unsubscribe in cleanup() method |
| Sync I/O (open/read/write) | Use aiofiles for async operations |
| No error handling | Use TradingError with error category |
| Hardcoded config | Load from DI container: `await container.get("config")` |
| Event loop closure | Use `asyncio.get_running_loop()` not `get_event_loop()` |

## Implementation Status

Track mock vs real implementations to prevent silent failures:

| Service | Method | Status | Missing |
|---------|--------|--------|---------|
| `paper_trading_execution_service` | `execute_buy_trade` | ✅ REAL | - |
| `paper_trading_execution_service` | `execute_sell_trade` | ✅ REAL | - |
| `kite_connect_service` | `get_ltp` | ✅ REAL | - |

**Fixed 2025-12-26**: BUG-002 resolved - execution service now writes to `paper_trades` table via `paper_trading_state.create_trade()`.

## Read Before Changing

- `src/CLAUDE.md` - Backend patterns (SDK, event loop, DI, locked state)
- `src/core/CLAUDE.md` - Core infrastructure (events, coordinators)

