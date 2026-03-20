# Core Infrastructure - src/core/

**Context**: Agent SDK bot core infrastructure. Claude Code debugs coordinators/DI/events.

## Components

| Component | Purpose | Max Lines |
|-----------|---------|-----------|
| orchestrator.py | Facade pattern | 300 |
| coordinators/*.py | Event orchestrators | 150 |
| di.py | DI container | 500 |
| event_bus.py | Event system | 350 |
| database_state/ | Async state + locking | 350 |

## Critical Patterns

| Pattern | Implementation | Why |
|---------|----------------|-----|
| Database locking | `async with self._lock: await db.execute()` | Prevents "database is locked" |
| Coordinators | Extend `BaseCoordinator`, max 150 lines | Single responsibility, event-driven |
| Events | `Event(type=EventType.X, data={})` + `event_bus.publish()` | Loose coupling |
| DI resolution | `await container.get("state_manager")` | Exact name from di_registry_*.py |
| Event loop | `asyncio.get_running_loop()` | Never `get_event_loop()` → crashes |

## DI Service Names

✅ **CORRECT**: `await container.get("state_manager")`
❌ **WRONG**: `await container.get("database_state_manager")`

Common: `state_manager`, `event_bus`, `config`, `resource_manager`
(Check di_registry_*.py for exact names)

## Common Issues

| Problem | Fix |
|---------|-----|
| database is locked | Use `asyncio.Lock()` in state classes |
| Event loop closed | Use `asyncio.get_running_loop()` not `get_event_loop()` |
| Service not found | Check exact name in di_registry_*.py files |
| Init failures | Track `_initialization_complete` flag |
| Memory leaks | Call `unsubscribe()` in cleanup methods |
| SDK errors | See src/CLAUDE.md - SDK-only rule |

## Read Before Changing

- `src/CLAUDE.md` - Backend-wide patterns (SDK, event loop, DI)
- `src/core/coordinators/CLAUDE.md` - Coordinator-specific patterns


