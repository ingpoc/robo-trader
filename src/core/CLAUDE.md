# Core Infrastructure - src/core/

## Components
| Component | Purpose | Max |
|-----------|---------|-----|
| orchestrator.py | Facade | 300 |
| coordinators/*.py | Orchestrators | 150 |
| di.py | DI container | 500 |
| event_bus.py | Events | 350 |
| database_state/ | Async state + locking | 350 |

## Database Locking (CRITICAL)
```python
class MyState:
    def __init__(self):
        self._lock = asyncio.Lock()
    async def op(self):
        async with self._lock:
            cursor = await self.db.execute(...)
```
Prevents "database is locked" on concurrent async access

## Coordinator Pattern
```python
class MyCoordinator(BaseCoordinator):
    async def initialize(self):
        self.event_bus.subscribe(EventType.EVENT, self)
    async def handle_event(self, event):
        await self._handle_event(event)
```
Max 150 lines, single responsibility, no business logic

## Events
`Event(type=EventType.X, source="Y", data={})` → `await event_bus.publish(event)`

## DI
`register_singleton/factory` → `await container.get("key")`

## Common Issues
| Problem | Fix |
|---------|-----|
| database is locked | Add asyncio.Lock() |
| Init failures | Track _initialization_complete |
| Memory leaks | Call unsubscribe() in cleanup() |

## SDK (MANDATORY)
✅ `ClaudeSDKClientManager.get_instance()` + `query_with_timeout()`
❌ Never import anthropic directly

