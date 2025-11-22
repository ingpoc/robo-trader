# Core Infrastructure Guidelines

> **Scope**: Applies to `src/core/` directory. Read after `src/CLAUDE.md` for context.
>
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference + How-To + Explanation
>
> **Read in this order**:
> 1. `src/CLAUDE.md` - Backend architecture overview (read first)
> 2. This file - Core patterns: orchestrator, coordinator, DI, events, errors
> 3. `src/services/CLAUDE.md` - How services use core infrastructure
> 4. Layer-specific guides (scheduler, background_scheduler, etc.)

## Quick Reference - SDK Usage

- **Client Manager**: Always use `ClaudeSDKClientManager.get_instance()` - saves ~70s startup time
- **Timeout Helpers**: Always use `query_with_timeout()` and `receive_response_with_timeout()` - never call directly
- **Prompt Validation**: Validate system prompts with `validate_system_prompt_size()` - keep under 8000 tokens
- **Error Handling**: SDK helpers handle all error types automatically

**Files**:
- `claude_sdk_client_manager.py` - Singleton client manager
- `sdk_helpers.py` - Timeout and error handling helpers

Core layer provides infrastructure, cross-cutting concerns, and foundational patterns for the entire application. This layer must remain framework-agnostic and highly reusable.

## Claude Agent SDK Integration (CRITICAL)

### SDK-Only Core Infrastructure (MANDATORY)

All AI-related core infrastructure must use **ONLY** Claude Agent SDK. No direct Anthropic API calls are permitted.

**Core AI Infrastructure** (SDK-Only):
- `ai_planner.py` - AI planning and decision making
- `learning_engine.py` - Learning and improvement engine
- `conversation_manager.py` - Claude conversation management
- `coordinators/claude_agent_coordinator.py` - AI agent lifecycle management

**SDK Core Integration Pattern**:
```python
from claude_agent_sdk import ClaudeAgentOptions, tool
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout, validate_system_prompt_size

class AICoordinator(BaseCoordinator):
    async def initialize(self) -> None:
        """Initialize AI coordinator with SDK client manager."""
        await super().initialize()
        
        # Validate system prompt size
        system_prompt = self._build_system_prompt()
        is_valid, token_count = validate_system_prompt_size(system_prompt)
        
        # Use client manager (CRITICAL for performance)
        client_manager = await self.container.get("claude_sdk_client_manager")
        options = ClaudeAgentOptions(...)
        self.client = await client_manager.get_client("trading", options)
        
        # Use timeout helpers (MANDATORY)
        await query_with_timeout(self.client, prompt, timeout=90.0)
```

## Initialization Error Handling Pattern (CRITICAL)

### Problem: Silent Initialization Failures

Background components (schedulers, managers) often use fire-and-forget `asyncio.create_task()` to start background loops. If initialization fails, exceptions are silently suppressed and there's no mechanism for the orchestrator to detect the failure.

**Symptoms**:
- Background component tasks created but loop never executes
- Exception occurs during initialization but no error is logged
- Orchestrator doesn't know initialization failed
- System appears to start successfully but key components are offline

### Solution: Initialization Status Tracking

Every component that starts background tasks must implement initialization status tracking:

**Pattern**:
```python
class MyComponent:
    def __init__(self):
        # Status tracking flags
        self._initialized = False
        self._initialization_complete = False
        self._initialization_error: Optional[Exception] = None
        self._initialization_error_traceback: Optional[str] = None

    async def start(self) -> None:
        """Start component with proper error handling."""
        # Already running check
        if self._initialized:
            return

        self._initialized = True

        try:
            # Initialize all dependencies first
            self._log_init_step("Initializing dependency 1")
            await self.dep1.initialize()
            self._log_init_step("Dependency 1 initialized")

            self._log_init_step("Initializing dependency 2")
            await self.dep2.initialize()
            self._log_init_step("Dependency 2 initialized")

            # Create background task
            self._log_init_step("Creating background task")
            self._task = asyncio.create_task(self._run_background_loop())
            self._log_init_step("Background task created")

            # Mark as complete ONLY if all steps succeed
            self._initialization_complete = True
            logger.info("Component started successfully")

        except Exception as e:
            # Capture error details
            self._initialized = False
            self._initialization_error = e
            self._initialization_error_traceback = traceback.format_exc()
            self._log_init_step("Component initialization", success=False, error=e)

            # Re-raise so orchestrator can detect failure
            raise RuntimeError(f"Component initialization failed: {e}") from e

    def _log_init_step(self, step: str, success: bool = True, error: Optional[Exception] = None) -> None:
        """Log initialization step with structured format."""
        if success:
            msg = f"[INIT] {step}"
            print(f"*** {msg} - OK ***")  # Print to stdout
            logger.info(msg)  # Log to logger
        else:
            msg = f"[INIT FAILED] {step}"
            print(f"*** {msg}: {error} ***")
            logger.error(f"{msg}: {error}")
            if error:
                tb = traceback.format_exc()
                print(f"*** TRACEBACK: {tb} ***")
                logger.error(f"Traceback: {tb}")

    def is_ready(self) -> bool:
        """Check if component is ready to process."""
        return self._initialization_complete and self._initialization_error is None

    def get_initialization_status(self) -> Tuple[bool, Optional[str]]:
        """Get initialization status."""
        if self._initialization_error:
            return False, f"{self._initialization_error.__class__.__name__}: {str(self._initialization_error)}"
        return self._initialization_complete, None
```

**Key Points**:
1. ✅ Use outer try/except wrapping entire initialization sequence
2. ✅ Log each step to both stdout AND logger (print + logging module)
3. ✅ Set `_initialization_complete=True` ONLY on full success
4. ✅ Capture exception details (_initialization_error, _initialization_error_traceback)
5. ✅ Re-raise as RuntimeError so orchestrator detects failures
6. ✅ Provide `is_ready()` and `get_initialization_status()` for external queries

### Benefits
- ✅ Orchestrator can detect initialization failures
- ✅ Structured logging makes debugging easier
- ✅ Clear failure vs success states
- ✅ Prevents silent failures from fire-and-forget patterns
- ✅ External code can query readiness before proceeding

---

## Core Architecture Patterns

### 1. Orchestrator Pattern (Responsibility: Application Facade)

**Implementation**: `orchestrator.py` - Thin facade that delegates to coordinators only.

**Rules**:
- ✅ Maximum 300 lines (thin facade)
- ✅ No business logic in orchestrator
- ✅ Only coordinates coordinator lifecycle
- ✅ All delegation through coordinator interfaces
- ❌ No direct service calls
- ❌ No business logic implementation

```python
class RoboTraderOrchestrator:
    """Thin facade - delegates to coordinators only."""

    def __init__(self, container: DependencyContainer):
        self.container = container
        self.session_coordinator = container.get(SessionCoordinator)
        self.query_coordinator = container.get(QueryCoordinator)
        # ... other coordinators

    async def initialize(self) -> None:
        """Initialize all coordinators."""
        await asyncio.gather(*[
            coord.initialize() for coord in self.coordinators
        ])

    async def process_query(self, query: str) -> str:
        """Delegate to query coordinator."""
        return await self.query_coordinator.process_query(query)
```

### 2. Coordinator Pattern (Responsibility: Service Orchestration)

**Base Implementation**: `coordinators/base_coordinator.py`

**Current Coordinators**:
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `LifecycleCoordinator` - Emergency operations
- `BroadcastCoordinator` - UI state broadcasting
- `ClaudeAgentCoordinator` - AI agent session management
- `AgentCoordinator` - Multi-agent coordination
- `MessageCoordinator` - Inter-agent communication
- `QueueCoordinator` - Queue management
- `PortfolioCoordinator` - Portfolio operations
- `FeatureManagementCoordinator` - Feature flag management

**Rules**:
- ✅ Inherit from `BaseCoordinator`
- ✅ Single responsibility per coordinator
- ✅ Async `initialize()` and `cleanup()` methods
- ✅ Delegate to services, don't implement business logic
- ✅ Emit lifecycle events
- ✅ Proper error handling and logging
- ❌ No more than 150 lines per coordinator
- ❌ No direct service-to-service calls

**Verification (2025-11-22)**: 41 coordinators found in codebase. Verify all follow:
- ✅ Max 150 line rule
- ✅ Inherit from BaseCoordinator
- ✅ Single responsibility principle
- ✅ Proper initialize() and cleanup() methods

### 3. Dependency Injection Pattern (Responsibility: Service Lifecycle)

**Implementation**: `di.py` - Centralized dependency container.

**Rules**:
- ✅ All services registered in container
- ✅ Singleton for expensive resources (database, APIs)
- ✅ Factory for stateful instances
- ✅ Proper initialization ordering
- ✅ Circular dependency prevention
- ❌ No global state or direct instantiation
- ❌ No service locator pattern in business logic

```python
class DependencyContainer:
    """Centralized dependency injection."""

    def __init__(self):
        self._services = {}
        self._singletons = {}
        self._initialized = False

    async def initialize(self, config: Config) -> None:
        """Initialize all dependencies."""
        self.config = config

        # Register singletons first
        await self._register_singletons()

        # Register services
        await self._register_services()

        # Register coordinators
        await self._register_coordinators()

        self._initialized = True

    def get(self, service_type: Type[T]) -> T:
        """Get service instance."""
        if service_type in self._singletons:
            return self._singletons[service_type]

        if service_type in self._services:
            return self._services[service_type](self)

        raise ValueError(f"Service {service_type} not registered")
```

### 4. Event-Driven Communication Pattern (Responsibility: Decoupled Communication)

**Implementation**: `event_bus.py` - Type-safe event system.

**Rules**:
- ✅ Use `EventType` enum for all events
- ✅ Events carry source, timestamp, correlation ID
- ✅ Services subscribe via `EventHandler` base class
- ✅ Proper cleanup in `close()` methods
- ✅ Event filtering and routing
- ❌ No direct service-to-service calls
- ❌ No event mutations after publishing

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict
import uuid
from datetime import datetime, timezone

class EventType(Enum):
    """Type-safe event types."""
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    PORTFOLIO_UPDATED = "portfolio_updated"
    TRADE_EXECUTED = "trade_executed"
    ANALYSIS_COMPLETED = "analysis_completed"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class Event:
    """Typed event with metadata."""
    id: str
    type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: str | None = None

class EventBus:
    """Type-safe event bus."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: 'EventHandler') -> None:
        """Subscribe to event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        """Publish event to subscribers."""
        if event.type in self._subscribers:
            await asyncio.gather(*[
                handler.handle_event(event)
                for handler in self._subscribers[event.type]
            ])
```

### 5. Error Handling Pattern (Responsibility: Structured Error Context)

**Implementation**: `errors.py` - Rich error hierarchy with context.

**Error Categories**:
- `TRADING` - Trading operations and market data
- `API` - External API calls and integrations
- `VALIDATION` - Input validation and data errors
- `RESOURCE` - Resource allocation and system limits
- `CONFIGURATION` - Configuration and setup issues
- `SYSTEM` - System-level errors and infrastructure

**Error Severities**:
- `CRITICAL` - System failure, immediate attention required
- `HIGH` - Major functionality impacted
- `MEDIUM` - Partial functionality affected
- `LOW` - Minor issues, informational

**Rules**:
- ✅ All errors inherit from `TradingError`
- ✅ Include category, severity, code, and metadata
- ✅ Provide recoverable flag and retry guidance
- ✅ Never expose internal stack traces to clients
- ✅ Log with full context for debugging

```python
class TradingError(Exception):
    """Base error with rich context."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
        retry_after_seconds: int | None = None,
        details: Dict[str, Any] | None = None,
        code: str | None = None
    ):
        super().__init__(message)
        self.context = ErrorContext(
            category=category,
            severity=severity,
            recoverable=recoverable,
            retry_after_seconds=retry_after_seconds,
            details=details or {},
            code=code or self.__class__.__name__
        )

class APIError(TradingError):
    """External API errors with retry logic."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: int | None = None,
        **kwargs
    ):
        super().__init__(message, category=ErrorCategory.API, **kwargs)
        self.api_name = api_name
        self.status_code = status_code

class ValidationError(TradingError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        field: str,
        value: Any,
        **kwargs
    ):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)
        self.field = field
        self.value = value
```

### 6. Background Scheduler Pattern (Responsibility: Modular Task Processing)

**Implementation**: `background_scheduler/` - Domain-separated task processing.

**Structure**:
- `background_scheduler.py` - Facade
- `models.py` - Task definitions
- `stores/` - Async file persistence
- `clients/` - Unified API clients
- `processors/` - Domain logic
- `monitors/` - Monitoring and health checks
- `config/` - Configuration management
- `events/` - Event routing

**Rules**:
- ✅ Max 350 lines per module
- ✅ One domain per module
- ✅ Consolidate duplicate API calls
- ✅ Use `aiofiles` for all file I/O
- ✅ Implement exponential backoff retry
- ✅ Check stock state before API calls
- ❌ No monolithic files
- ❌ No blocking I/O operations

### 7. State Management Pattern (Responsibility: Consistent Data Access)

**Implementation**: `database_state/` - Async state management with SQLite.

**Components**:
- `base.py` - Base state manager with connection handling
- `portfolio_state.py` - Portfolio data management
- `intent_state.py` - Trading intent tracking
- `approval_state.py` - Approval queue management
- `database_state.py` - Unified state manager

**Rules**:
- ✅ All database operations async
- ✅ Use `aiofiles` for file I/O
- ✅ Atomic writes with temp files
- ✅ Connection pooling and management
- ✅ Automatic table creation and migrations
- ✅ **CRITICAL**: All database state classes must use `asyncio.Lock()` for concurrent operations
- ❌ No synchronous database operations
- ❌ No direct SQL in business logic

#### Database Locking Pattern (CRITICAL - Prevents "database is locked" errors)

**Problem**: SQLite "database is locked" errors occur when multiple async operations access the database concurrently without proper synchronization.

**Solution**: Every database state class must implement its own `asyncio.Lock()` and use `async with self._lock:` for ALL database operations.

**Implementation Pattern**:
```python
class MyDatabaseState:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self._lock = asyncio.Lock()  # CRITICAL: Each state class needs its own lock

    async def my_database_operation(self, param: str) -> Dict[str, Any]:
        async with self._lock:  # CRITICAL: Always acquire lock for database operations
            try:
                cursor = await self.db.connection.execute("SELECT * FROM my_table WHERE param = ?", (param,))
                rows = await cursor.fetchall()
                return self._process_rows(rows)
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                return {}

    async def initialize(self) -> None:  # CRITICAL: Even initialization needs locking
        async with self._lock:
            # Create tables, initialize data, etc.
            pass
```

**Why This Matters**:
- SQLite allows only one writer at a time
- Multiple concurrent async operations can cause "database is locked"
- Each state class needs its own lock (don't share locks between classes)
- Initialization operations must also be locked
- **Lesson Learned**: ConfigurationState class initially lacked proper locking, causing database lock errors during concurrent API calls

## Async/File Operations - Core Layer (MANDATORY)

### ✅ DO

```python
# Atomic file writes
async def save_config(self, data: Dict[str, Any]) -> None:
    """Save configuration atomically."""
    import tempfile
    import os

    temp_file = f"{self.config_file}.tmp"
    async with aiofiles.open(temp_file, 'w') as f:
        await f.write(json.dumps(data, indent=2))

    # Atomic replace
    os.replace(temp_file, self.config_file)

# Lazy loading
class Config:
    def __init__(self):
        self._data: Dict[str, Any] | None = None

    @property
    def data(self) -> Dict[str, Any]:
        if self._data is None:
            self._data = asyncio.create_task(self._load_config())
        return self._data
```

### ❌ DON'T

```python
# WRONG - Blocking I/O
async def load_config(self):
    with open(self.config_file, 'r') as f:  # BLOCKS!
        return json.load(f)

# WRONG - Direct write without atomicity
async def save_config(self, data):
    async with aiofiles.open(self.config_file, 'w') as f:
        await f.write(json.dumps(data))  # Not atomic!
```

## Core Development Workflow

### 1. New Coordinator

1. Inherit from `BaseCoordinator`
2. Implement `initialize()` and `cleanup()`
3. Define single responsibility
4. Add to dependency container
5. Register in orchestrator
6. Keep under 150 lines

### 2. New Event Type

1. Add to `EventType` enum
2. Update event documentation
3. Add subscription pattern where needed
4. Include proper correlation ID handling

### 3. New Error Type

1. Inherit from appropriate base error
2. Include relevant context fields
3. Add to error category documentation
4. Update error handling patterns

## Quick Reference - Core Layer

| Pattern | Implementation | Max Size |
|---------|----------------|----------|
| Orchestrator | `orchestrator.py` (thin facade) | 300 lines |
| Coordinator | `coordinators/*.py` | 150 lines each |
| DI Container | `di.py` | 500 lines |
| Event Bus | `event_bus.py` | 350 lines |
| Error Hierarchy | `errors.py` | 220 lines |
| Background Tasks | `background_scheduler/*.py` | 350 lines each |

## Anti-Patterns - Core Layer (What to Avoid)

### ❌ Service Locator Anti-Pattern
```python
# WRONG - Business code using container directly
class MyService:
    def __init__(self):
        self.other_service = container.get(OtherService)  # Bad!
```
**Fix**: Inject dependencies via constructor

### ❌ God Object Coordinator
```python
# WRONG - Coordinator doing too much
class SuperCoordinator(BaseCoordinator):
    def __init__(self):
        # Handles trading, AI, UI, database, everything...
```
**Fix**: Split into focused coordinators with single responsibilities

### ❌ Direct Event Publishing Without Types
```python
# WRONG - Untyped events
event_bus.publish({"type": "something", "data": {...}})
```
**Fix**: Use `Event` class with proper `EventType` enum

### ❌ Synchronous Operations in Async Context
```python
# WRONG - Blocking operations
async def process_data(self):
    result = some_sync_function()  # Blocks!
    return result
```
**Fix**: Make all operations async or use thread pool

### ❌ Memory Leaks in Event Subscriptions
```python
# WRONG - No cleanup
class MyService(EventHandler):
    def __init__(self, event_bus):
        event_bus.subscribe(EventType.SOMETHING, self)
        # No unsubscribe method!
```
**Fix**: Always implement `close()` with cleanup

## Quick Fix Guide - Common Core Layer Errors

**Error: "Background component task created but never runs"**
- **Cause**: Fire-and-forget `asyncio.create_task()` with no error handling; initialization failed silently
- **Fix**: Implement initialization status tracking with `_initialization_complete` flag and re-raise RuntimeError
- **Prevention**: Document pattern in component initialization, use in BackgroundScheduler and similar components

**Error: "database is locked"**
- **Cause**: Multiple async operations accessing SQLite without proper locking
- **Fix**: Implement `asyncio.Lock()` in each DatabaseState class, wrap all DB operations with `async with self._lock:`
- **Prevention**: Always add lock in state classes handling concurrent access

**Error: "Event subscribers not reacting"**
- **Cause**: Subscriber unsubscribed or event type doesn't match
- **Fix**: Verify EventType enum value matches subscription, check unsubscribe not called prematurely
- **Prevention**: Implement cleanup() methods with explicit unsubscribe, test event flow in isolation

**Error: "SDK client timeout or hangs"**
- **Cause**: Direct `client.query()` without timeout protection
- **Fix**: Use `query_with_timeout(client, prompt, timeout=60.0)` helper
- **Prevention**: Never call SDK client directly, always use timeout helpers

## Maintenance Instructions

**For Contributors**: This CLAUDE.md is a living document. When you:
- ✅ Add new coordinator → Document pattern, add to list, keep under 150 lines
- ✅ Fix core layer bug → Add to Quick Fix Guide with cause/fix/prevention
- ✅ Change DI pattern → Document in DI section with examples
- ✅ Add new event type → Document in event system section
- ⚠️ Update this file → Run changes through prompt optimizer tool
- ⚠️ Share improvements → Commit alongside code changes so team benefits

**CRITICAL Invariants**:
- ✅ Orchestrator remains thin (<300 lines, delegation only)
- ✅ All coordinators stay focused (<150 lines, single responsibility)
- ✅ Events always use EventType enum (never dynamic strings)
- ✅ All AI functionality uses SDK only (never direct API calls)
- ✅ Background components implement initialization tracking

**Last Review**: 2025-11-22

## Pre-Commit Checklist - Core Layer

- [ ] All coordinators inherit from `BaseCoordinator`
- [ ] Max file sizes respected (orchestrator < 300, coordinators < 150)
- [ ] All file I/O uses `aiofiles`
- [ ] All errors inherit from `TradingError`
- [ ] Events use `EventType` enum with proper structure
- [ ] No direct service-to-service calls
- [ ] Event subscriptions have proper cleanup
- [ ] Async operations throughout (no blocking)
- [ ] Dependencies injected via constructor
- [ ] Single responsibility per coordinator/module
- [ ] Proper error context in all exceptions
- [ ] **SDK Client Manager**: Use `ClaudeSDKClientManager` - never create direct `ClaudeSDKClient`
- [ ] **SDK Timeouts**: Use `query_with_timeout()` and `receive_response_with_timeout()` - never call directly
- [ ] **SDK Prompts**: Validate prompt size with `validate_system_prompt_size()` before initialization