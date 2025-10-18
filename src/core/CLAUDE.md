# Core Infrastructure Guidelines

> **Scope**: Applies to `src/core/` and coordination between major systems. Read after `src/CLAUDE.md`.

## Core Responsibilities

### 1. Orchestrator (`orchestrator.py`)

**Responsibility**: Thin facade coordinating coordinators. NOT business logic.

**Rules**:
- ✅ Create and initialize coordinators
- ✅ Delegate all operations to coordinators
- ✅ Maintain authentication state
- ✅ Keep under 300 lines
- ❌ NO business logic
- ❌ NO direct service calls
- ❌ NO data transformations

**Pattern**:
```python
class RoboTraderOrchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.coordinators = {}  # Lazy initialize

    async def initialize(self):
        # Initialize coordinators
        await self.session_coordinator.initialize()
        await self.query_coordinator.initialize()
        # ... etc
```

### 2. Coordinators (`coordinators/`)

**Responsibility**: Each coordinator manages one major responsibility.

**Current Coordinators**:
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - Status aggregation
- `LifecycleCoordinator` - Emergency operations
- `BroadcastCoordinator` - UI state broadcasting

**Implementation Rule**:
```python
from .base_coordinator import BaseCoordinator

class MyCoordinator(BaseCoordinator):
    async def initialize(self) -> None:
        """Setup resources."""
        self._log_info("Starting initialization")
        # Setup here
        self._initialized = True

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if not self._initialized:
            return
        self._log_info("Cleaning up")
        # Cleanup here
```

**Limits**:
- ✅ Max 150 lines per coordinator
- ✅ Max 10 methods
- ✅ Single responsibility
- ❌ NO business logic (delegate to services)
- ❌ NO direct database access

### 3. Dependency Injection Container (`di.py`)

**Responsibility**: Centralized dependency management.

**Key Pattern**:
```python
class DependencyContainer:
    async def get(self, service_class):
        """Get or create service instance."""
        # Return singleton if exists
        # Otherwise create and register
        pass
```

**Rules**:
- ✅ Register all services at startup
- ✅ Singletons for expensive resources (DB, APIs, EventBus)
- ✅ Factories for stateful instances
- ✅ Thread-safe with asyncio.Lock
- ❌ Don't create services outside container
- ❌ Don't modify container after initialization

### 4. Event Bus (`event_bus.py`)

**Responsibility**: Cross-service communication via events.

**Event Structure**:
```python
@dataclass
class Event:
    id: str                           # Unique event ID
    type: EventType                   # From EventType enum
    timestamp: str                    # ISO format
    source: str                       # Service name
    data: Dict[str, Any]              # Event payload
    correlation_id: Optional[str]     # For tracing
    version: str = "1.0"              # Schema version
```

**Usage Pattern**:
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

**Rules**:
- ✅ All events have EventType from enum
- ✅ All events have source and timestamp
- ✅ All events have correlation_id for tracing
- ✅ Handlers are async
- ✅ Proper cleanup in unsubscribe
- ❌ Don't create custom event types
- ❌ Don't emit personal data in events

### 5. Error Hierarchy (`errors.py`)

**Responsibility**: Structured error context for debugging.

**Error Categories**: TRADING, MARKET_DATA, API, VALIDATION, RESOURCE, CONFIGURATION, SYSTEM

**Error Severities**: CRITICAL, HIGH, MEDIUM, LOW

**Usage Pattern**:
```python
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

raise MarketDataError(
    "Failed to fetch symbol data",
    symbol="SBIN",
    severity=ErrorSeverity.HIGH,
    recoverable=True,
    retry_after_seconds=5,
    metadata={"exchange": "NSE"}
)
```

**Error Properties**:
- `category` - Error domain
- `severity` - Impact level
- `code` - Unique error code
- `message` - User-facing message
- `details` - Technical details
- `metadata` - Additional context
- `recoverable` - Can retry?
- `retry_after_seconds` - How long to wait

**Rules**:
- ✅ Always use specific error type
- ✅ Set appropriate severity
- ✅ Include recoverable flag
- ✅ Add metadata for debugging
- ✅ Log with context
- ❌ Never use generic Exception
- ❌ Never expose stack traces to UI

### 6. Background Scheduler (`background_scheduler/`)

**Responsibility**: Periodic task processing.

**Modular Structure**:
- `models.py` (77 lines) - Task definitions
- `stores/task_store.py` (130 lines) - Async persistence
- `clients/` - Unified API clients
- `processors/` - Domain logic
- `monitors/` - Health/risk/market monitoring
- `config/` - Configuration management
- `events/` - Event routing
- `core/task_scheduler.py` - Task lifecycle
- `background_scheduler.py` (357 lines) - Facade

**Rules**:
- ✅ Max 350 lines per file
- ✅ Max 10 methods per class
- ✅ One domain per module
- ✅ Consolidate duplicate API calls
- ✅ aiofiles for all I/O
- ✅ Error handling mandatory
- ✅ Emit domain events
- ❌ No monolithic files
- ❌ No direct HTTP requests

**Task Types**:
- EARNINGS_ANALYSIS
- NEWS_PROCESSING
- FUNDAMENTAL_ANALYSIS
- MARKET_MONITORING
- RISK_MONITORING
- HEALTH_CHECK

### 7. State Management (`database_state.py`)

**Responsibility**: Persistent application state.

**Features**:
- Async SQLite storage
- Type-safe queries
- Event-driven updates
- Migrations support

**Rules**:
- ✅ All state operations async
- ✅ Use aiofiles for persistence
- ✅ Emit events on state changes
- ✅ Type-safe access methods
- ❌ No synchronous I/O
- ❌ No direct SQL in services

---

## Async/Timeout Pattern - Core Specific

### ✅ DO: Timeout with Cancellation Protection

```python
async def run_with_timeout(self, task_coro, timeout_seconds: int):
    """Run task with timeout and proper cancellation."""
    execution_task = None
    try:
        execution_task = asyncio.create_task(task_coro)
        result = await asyncio.wait_for(execution_task, timeout=timeout_seconds)
        return result

    except asyncio.TimeoutError:
        logger.error(f"Task timed out after {timeout_seconds}s")
        if execution_task and not execution_task.done():
            execution_task.cancel()
            try:
                # CRITICAL: Timeout must wrap the cancellation await
                await asyncio.wait_for(execution_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        raise

    except asyncio.CancelledError:
        logger.warning("Task was cancelled")
        raise
```

### ❌ DON'T

```python
# WRONG - No timeout when awaiting cancelled task
async def run_with_timeout(self, task_coro, timeout_seconds: int):
    execution_task = asyncio.create_task(task_coro)
    try:
        await asyncio.wait_for(execution_task, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        execution_task.cancel()
        await execution_task  # CAN HANG INDEFINITELY!

# WRONG - No cancellation
async def run_with_timeout(self, task_coro, timeout_seconds: int):
    await asyncio.wait_for(task_coro, timeout=timeout_seconds)
```

---

## Coordinator Initialization Pattern

### ✅ DO

```python
class MyCoordinator(BaseCoordinator):
    def __init__(self, config: Config, event_bus: EventBus):
        super().__init__(config, event_bus)
        self._service = None  # Lazy init

    async def initialize(self) -> None:
        """Initialize coordinator and dependencies."""
        self._log_info("Initializing coordinator")

        # Initialize service with DI
        self._service = await self._get_service()

        # Subscribe to events
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self._handle_price)

        self._initialized = True

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if not self._initialized:
            return

        self._log_info("Cleaning up")

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.MARKET_PRICE_UPDATE)

        # Cleanup service
        if self._service:
            await self._service.cleanup()

    async def _handle_price(self, event: Event):
        """Handle market price updates."""
        try:
            await self._service.process_price(event.data)
        except TradingError as e:
            self._log_error(f"Error processing price: {e.context.code}")
```

### ❌ DON'T

```python
# WRONG - Not inheriting from BaseCoordinator
class MyCoordinator:
    async def initialize(self):
        pass

# WRONG - No cleanup
class MyCoordinator(BaseCoordinator):
    async def initialize(self):
        pass

    async def cleanup(self):
        pass  # No actual cleanup

# WRONG - Direct service instantiation
class MyCoordinator(BaseCoordinator):
    async def initialize(self):
        self._service = MyService()  # Should use DI
```

---

## Event Subscription Pattern

### ✅ DO

```python
class MyCoordinator(BaseCoordinator):
    async def initialize(self) -> None:
        # Subscribe
        self.event_bus.subscribe(EventType.RISK_BREACH, self._handle_risk)

    async def cleanup(self) -> None:
        # Unsubscribe
        self.event_bus.unsubscribe(EventType.RISK_BREACH)

    async def _handle_risk(self, event: Event):
        """Handle risk breach events."""
        try:
            await self._process_risk(event.data)
            # Emit follow-up event
            await self.event_bus.emit(Event(
                id=str(uuid.uuid4()),
                type=EventType.SYSTEM_ALERT,
                source="MyCoordinator",
                data={"alert": "Risk threshold exceeded"}
            ))
        except TradingError as e:
            self._log_error(f"Risk handling failed: {e.context.code}")
```

### ❌ DON'T

```python
# WRONG - No unsubscribe (memory leak)
async def cleanup(self):
    pass  # Should unsubscribe

# WRONG - No error handling in handler
async def _handle_risk(self, event: Event):
    await self._process_risk(event.data)  # Can throw

# WRONG - Blocking operation in async handler
async def _handle_risk(self, event: Event):
    data = json.load(open('data.json'))  # BLOCKS!
```

---

## Pre-Commit Checklist - Core

- [ ] Orchestrator under 300 lines (thin facade)
- [ ] Coordinators inherit from BaseCoordinator
- [ ] All services registered in DI container
- [ ] Timeout operations use asyncio.wait_for() for cancellation
- [ ] Event handlers have error handling
- [ ] Event subscriptions cleaned up in coordinator.cleanup()
- [ ] Errors inherit from TradingError
- [ ] Significant operations emit events
- [ ] No synchronous file I/O (use aiofiles)
- [ ] Max 350 lines per background scheduler file

---

## Quick Reference - Core Patterns

| Component | Purpose | Max Size | Pattern |
|-----------|---------|----------|---------|
| Orchestrator | Facade | 300 lines | Thin, delegates only |
| Coordinator | Service coordination | 150 lines | Inherits BaseCoordinator |
| DI Container | Dependency resolution | 500 lines | Singleton registry |
| EventBus | Event infrastructure | 350 lines | Pub/sub with type safety |
| Error | Error context | 220 lines | Hierarchy with metadata |
| BackgroundScheduler | Task processing | 8 files, 350 each | Modularized facade |

