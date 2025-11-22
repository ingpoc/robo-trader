# Core Infrastructure - src/core/

**Last Updated**: 2025-11-22

## Component Overview

| Component | Purpose | Max Lines |
|-----------|---------|-----------|
| `orchestrator.py` | Thin facade, delegates to coordinators | 300 |
| `coordinators/base_coordinator.py` | Base for all coordinators | N/A |
| `coordinators/*.py` | Service orchestrators | 150 each |
| `di.py` | Dependency injection container | 500 |
| `event_bus.py` | Event-driven communication | 350 |
| `errors.py` | Error hierarchy with context | 220 |
| `database_state/` | Async state with locking | 350 per file |
| `background_scheduler/` | Task processing | 350 per file |

## Database Locking (CRITICAL)

**Every database state class MUST use `asyncio.Lock()`**:
```python
class MyState:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def my_operation(self):
        async with self._lock:  # CRITICAL: All DB ops need lock
            cursor = await self.db.connection.execute(...)
```

Why: SQLite "database is locked" errors happen when multiple async operations access DB concurrently.

## Coordinator Pattern

```python
class MyCoordinator(BaseCoordinator):
    async def initialize(self):
        self.service = await self.container.get("service_name")
        self.event_bus.subscribe(EventType.EVENT, self)

    async def handle_event(self, event: Event):
        await self._handle_event(event)

    async def cleanup(self):
        self.event_bus.unsubscribe(EventType.EVENT, self)
```

Rules:
- ✅ Inherit from BaseCoordinator
- ✅ Implement initialize() + cleanup()
- ✅ Max 150 lines
- ✅ Single responsibility
- ❌ No business logic
- ❌ No direct service calls

## Event-Driven Communication

```python
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.PORTFOLIO_CHANGE,
    source="MyCoordinator",
    timestamp=datetime.utcnow(),
    data={"key": "value"}
)
await self.event_bus.publish(event)
```

## Dependency Injection Pattern

```python
# Register in DI container
container.register_singleton(MyService, "my_service")
container.register_factory(MyClass, lambda c: MyClass())

# Get from container
service = await container.get("my_service")
```

## Error Hierarchy

```python
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

class CustomError(TradingError):
    def __init__(self, msg, **kwargs):
        super().__init__(msg, category=ErrorCategory.SYSTEM, **kwargs)
```

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "database is locked" | No asyncio.Lock() in state class | Add `async with self._lock:` wrapper |
| Silent initialization failures | Fire-and-forget create_task() | Implement `_initialization_complete` flag |
| Memory leaks | Services don't unsubscribe from events | Call `unsubscribe()` in `cleanup()` |
| Circular dependencies | DI container ordering issue | Check initialization order in `di.py` |

## Initialization Status Tracking

Background components must track initialization:
```python
class Component:
    def __init__(self):
        self._initialized = False
        self._initialization_complete = False
        self._initialization_error = None

    async def start(self):
        try:
            self._initialized = True
            # ... initialization ...
            self._initialization_complete = True
        except Exception as e:
            self._initialized = False
            self._initialization_error = e
            raise RuntimeError(f"Init failed: {e}") from e

    def is_ready(self):
        return self._initialization_complete and not self._initialization_error
```

## SDK Integration (MANDATORY)

✅ **DO**:
```python
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)
await query_with_timeout(client, prompt, timeout=60.0)
```

❌ **DON'T**:
```python
from anthropic import AsyncAnthropic  # FORBIDDEN
client = AsyncAnthropic(api_key="...")  # FORBIDDEN
```
