# Background Scheduler Stores Guidelines

> **Scope**: Applies to `src/core/background_scheduler/stores/` directory. Read `src/core/background_scheduler/CLAUDE.md` for parent context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Purpose

The `stores/` directory contains **async file persistence stores** that handle data persistence for tasks, stock state, and strategy logs.

## Architecture Pattern

### Async File Persistence Pattern

The stores use an **async file persistence architecture** with focused stores:

- **Core Stores**:
  - `task_store.py` - Task persistence
  - `stock_state_store.py` - Stock state persistence
  - `strategy_log_store.py` - Strategy log persistence
  - `fundamental_store.py` - Fundamental data persistence

## File Structure

```
stores/
├── __init__.py
├── task_store.py           # Task persistence (max 350 lines)
├── stock_state_store.py    # Stock state (max 350 lines)
├── strategy_log_store.py   # Strategy logs (max 350 lines)
└── fundamental_store.py    # Fundamental data (max 350 lines)
```

## Rules

### ✅ DO

- ✅ **Keep stores < 350 lines** - Refactor if exceeds limit
- ✅ **Use `aiofiles`** - Use async file operations
- ✅ **Atomic writes** - Use temp file → `os.replace()` pattern
- ✅ **Handle errors gracefully** - Wrap in `TradingError`
- ✅ **Cache in memory** - Cache frequently accessed data
- ✅ **Lock operations** - Use locks for concurrent access

### ❌ DON'T

- ❌ **Exceed line limits** - Refactor if store exceeds 350 lines
- ❌ **Use blocking I/O** - Always use async operations
- ❌ **Skip atomic writes** - Always use atomic write pattern
- ❌ **Access files directly** - Use locked methods

## Dependencies

- `aiofiles` - For async file operations
- `asyncio.Lock` - For locking
- Domain-specific models - For data models

## Testing

- Test file persistence works correctly
- Test atomic writes work
- Test locking prevents race conditions
- Test error handling and recovery

## Maintenance

- **When store grows**: Split into focused stores or extract supporting modules
- **When patterns change**: Update this CLAUDE.md and parent `src/core/background_scheduler/CLAUDE.md`
- **When new data types needed**: Create new focused store

