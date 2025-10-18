# Robo Trader - Architectural Patterns & Rules

## Core Architecture Overview

The Robo Trader uses a **layered, event-driven, coordinator-based architecture** with clear separation of concerns:

```
UI Layer (React + WebSocket)
    ↓
API Layer (FastAPI endpoints)
    ↓
Orchestration Layer (RoboTraderOrchestrator + Coordinators)
    ↓
Domain Layer (Services + Processors)
    ↓
Infrastructure Layer (DI, Event Bus, Database, External APIs)
```

---

## 1. Coordinator Pattern (Core Architecture)

### ✅ DO: Use Coordinators for Service Orchestration

**Pattern**: Each major responsibility gets its own focused coordinator inheriting from `BaseCoordinator`.

**Coordinators in Use**:
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `LifecycleCoordinator` - Emergency stop/resume operations
- `BroadcastCoordinator` - UI state broadcasting

**Why**: Replaces god object pattern with focused, testable components. Each has single responsibility.

**Implementation Rule**:
```python
class NewCoordinator(BaseCoordinator):
    async def initialize(self) -> None:
        """Setup resources."""
        pass

    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
```

### ❌ DON'T:
- Add business logic directly to RoboTraderOrchestrator (it's a thin facade)
- Create coordinators without inheriting from BaseCoordinator
- Mix initialization and business logic

---

## 2. Dependency Injection Container (DI Pattern)

### ✅ DO: Use DependencyContainer for All Dependencies

**Pattern**: Centralized DI manages singleton instances, factories, and service lifecycle.

**Key Principles**:
- All services resolved through container
- Singletons for expensive resources (database, API clients, event bus)
- Factories for stateful instances
- Async-safe initialization via `asyncio.Lock`

**Usage**:
```python
# In initialization
container = DependencyContainer()
await container.initialize(config)
orchestrator = await container.get(RoboTraderOrchestrator)

# In services
def __init__(self, container: DependencyContainer):
    self.scheduler = container.get(BackgroundScheduler)
```

### ❌ DON'T:
- Create service instances directly (use container)
- Use global variables for shared state
- Tightly couple services without DI

---

## 3. Event-Driven Communication

### ✅ DO: Use EventBus for Inter-Service Communication

**Pattern**: Services emit events, handlers subscribe and react. No direct coupling.

**Event Types** (in `EventType` enum):
- Market events (price updates, volume spikes, news)
- Portfolio events (position changes, PnL updates)
- Risk events (breach, stop-loss, exposure changes)
- Execution events (order lifecycle)
- AI events (recommendations, analysis, learning)
- System events (health checks, errors, maintenance)

**Usage**:
```python
# Emit event
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.RISK_STOP_LOSS_TRIGGER,
    source="RiskMonitor",
    data={"symbol": "SBIN", "price": 450.5}
)
await event_bus.emit(event)

# Subscribe to events
async def handle_stop_loss(event: Event):
    await self.execute_stop_loss(event.data)

event_bus.subscribe(EventType.RISK_STOP_LOSS_TRIGGER, handle_stop_loss)
```

### ❌ DON'T:
- Direct service-to-service calls for cross-cutting concerns
- Emit events without proper EventType enum
- Subscribe to events without proper cleanup

---

## 4. Error Handling Strategy

### ✅ DO: Use Custom Exception Hierarchy with Context

**Pattern**: All errors inherit from `TradingError` with rich context (category, severity, code, metadata).

**Error Categories**: TRADING, MARKET_DATA, API, VALIDATION, RESOURCE, CONFIGURATION, SYSTEM

**Error Severities**: CRITICAL, HIGH, MEDIUM, LOW

**Usage**:
```python
raise MarketDataError(
    "Failed to fetch symbol data",
    symbol="SBIN",
    severity=ErrorSeverity.HIGH,
    recoverable=True,
    retry_after_seconds=5
)
```

**Handling**:
```python
try:
    await market_service.get_data(symbol)
except TradingError as e:
    logger.error(f"Trading error: {e.context.code} - {e.context.message}")
    if e.context.recoverable:
        await retry_with_backoff()
    else:
        await broadcast_error(e.to_dict())
```

### ❌ DON'T:
- Use bare `except Exception:`
- Raise generic `Exception` or `RuntimeError`
- Expose internal stack traces to UI
- Suppress errors silently

---

## 5. Modularized Background Scheduler

### ✅ DO: Organize Scheduler Components by Domain

**Structure** (`src/core/background_scheduler/`):
- `models.py` - Task definitions (TaskType, TaskPriority, BackgroundTask)
- `stores/task_store.py` - Async file persistence
- `clients/` - Unified API clients (Perplexity, API key rotation)
- `processors/` - Domain logic (earnings, news, fundamentals analysis)
- `monitors/` - Monitoring services (market, risk, health)
- `config/task_config_manager.py` - Configuration management
- `events/event_handler.py` - Event routing
- `core/task_scheduler.py` - Task lifecycle management
- `background_scheduler.py` - Facade coordinating all

**File Size Limits**: Max 300-350 lines per file

**Max Methods/Class**: 10 methods per class (tight cohesion)

### ❌ DON'T:
- Create monolithic scheduler files
- Mix domain logic in core scheduler
- Duplicate API clients (consolidate into one)

---

## 6. Backward Compatibility Pattern

### ✅ DO: Use Wrapper Layer for Major Refactors

When refactoring, maintain old import paths:

```python
# Original: src/core/background_scheduler.py
# After refactor - now a backward compatibility wrapper:

from src.core.background_scheduler.background_scheduler import BackgroundScheduler
from src.core.background_scheduler.models import TaskType, TaskPriority

__all__ = ["BackgroundScheduler", "TaskType", "TaskPriority"]
```

**Benefit**: Existing code breaks, refactored code works, zero migration overhead.

### ❌ DON'T:
- Break existing import paths
- Move files without updating references
- Force immediate code migration

---

## 7. Frontend Component Architecture

### ✅ DO: Organize React Components by Feature

**Structure**:
- `pages/` - Page-level components (Dashboard, Trading, Config, etc.)
- `features/` - Feature-specific components (news-earnings, notifications)
- `components/` - Shared UI components (dashboard cards, forms, alerts)
- `components/ui/` - Reusable primitives (Button, Input, Card, Dialog)
- `hooks/` - Custom React hooks (useWebSocket, useMarketData)
- `utils/` - Utility functions (formatting, validation)

**Component Rules**:
- One component per file
- Props interface defined at top
- Use TypeScript (no any types)
- Memoize expensive components

### ❌ DON'T:
- Mix multiple components in one file
- Use CSS in component files (use Tailwind or external CSS)
- Create deeply nested component hierarchies

---

## 8. WebSocket Real-Time Updates

### ✅ DO: Use Differential Updates Pattern

**Pattern**: Send only changed data, client applies diffs, reduces bandwidth.

**Usage**:
```python
# Backend sends only changes
changes = {
    "holdings": [{"symbol": "SBIN", "quantity": 100, "ltp": 450.5}],
    "pnl": {"total": 2500, "percentage": 1.2}
}
await websocket.send_json({"type": "dashboard_update", "data": changes})

# Frontend applies diffs
setDashboard(prev => ({ ...prev, ...data }))
```

**Benefits**: Lower latency, reduced server load, better UX

### ❌ DON'T:
- Send full state on every update
- Use polling for real-time data
- Block WebSocket with long-running operations

---

## 9. State Management

### ✅ DO: Use StateCoordinator for Distributed State

**Pattern**: Focused state stores per domain, centralized through coordinator.

**Key Features**:
- Async-first design
- Event-driven updates
- Persistent storage when needed
- Clear subscription/unsubscription

### ❌ DON'T:
- Use legacy StateManager (deprecated)
- Store state in global variables
- Update state synchronously

---

## 10. Configuration Management

### ✅ DO: Centralize Configuration in Config Class

**Pattern**: Single `Config` class loads from environment and config files.

**Lifecycle**:
- Initialize once at startup
- Pass to all services via DI
- Never modify after initialization

**Usage**:
```python
config = Config.from_file("config/config.json")
container = DependencyContainer()
await container.initialize(config)
```

### ❌ DON'T:
- Hardcode configuration values
- Load config multiple times
- Use different config sources in different modules

---

## Summary: Architecture Principles

| Principle | Implementation | Benefit |
|-----------|----------------|---------|
| **Single Responsibility** | One coordinator per domain | Easy to test, maintain, extend |
| **Dependency Injection** | DependencyContainer | Loose coupling, testability |
| **Event-Driven** | EventBus pub/sub | Decoupled communication |
| **Rich Error Context** | TradingError hierarchy | Better debugging, UI feedback |
| **Async-First** | aiofiles, async/await | Non-blocking, scalable |
| **Backward Compatible** | Wrapper layers | Zero migration overhead |
| **Feature-Organized** | Feature folders | Scalable, intuitive structure |
| **Modularized** | Small focused files | Low cognitive load |

---

## When Adding New Features

1. **Identify responsibility** - Which coordinator owns this?
2. **Check DI** - What dependencies are needed?
3. **Choose events** - What events should this emit?
4. **Define errors** - What can fail? Create custom exceptions
5. **Organize code** - Create feature folder, not monolithic file
6. **No duplication** - Consolidate repeated patterns
7. **Follow limits** - Max 300 lines/file, 10 methods/class
8. **Test coverage** - Mock externals, test business logic

