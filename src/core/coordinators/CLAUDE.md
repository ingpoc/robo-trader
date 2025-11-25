# Coordinators - src/core/coordinators/

Coordinator-based monolithic (better perf than microservices). Orchestrator + focused subcoordinators.

## Directory Structure

```
coordinators/
├── core/        # Core system (session, query, lifecycle)
├── status/      # Status aggregation
├── queue/       # Queue management
├── task/        # Task lifecycle
├── message/     # Message routing
├── broadcast/   # UI broadcasting
└── agent/       # Agent coordination
```

## Pattern

Inherit `BaseCoordinator`, max 150 lines each. Organize by domain.

```python
class MyCoordinator(BaseCoordinator, EventHandler):
    async def initialize(self):
        self.service = await self.container.get("my_service")
        self.event_bus.subscribe(EventType.MY_EVENT, self)

    async def cleanup(self):
        self.event_bus.unsubscribe(EventType.MY_EVENT, self)

    async def handle_event(self, event: Event):
        if event.type == EventType.MY_EVENT:
            await self._handle(event)
```

## Refactoring (>150 lines)

1. Identify responsibilities
2. Create focused subfolder
3. Extract to focused coordinators
4. Orchestrator delegates
5. Update CLAUDE.md

## Rules

| DO | DON'T |
|----|-------|
| Inherit BaseCoordinator | Direct service calls |
| Domain subdirectories | God coordinators |
| Emit events | Block on I/O |
| Use DI | Exceed 150 lines |
| Async throughout | Access directly |
| Unsubscribe in cleanup | Skip logging |

## Dependencies

BaseCoordinator, EventBus, Config, injected services

