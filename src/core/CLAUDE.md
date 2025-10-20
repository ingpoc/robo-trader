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

#### 6.1 API Client Consolidation Pattern

**Responsibility**: Unified external API interactions with resilience.

**Pattern**: One client class per external API with centralized:
- API key rotation for rate limit management
- Exponential backoff retry logic
- Structured response parsing
- Timeout handling and error recovery

**Implementation**:
```python
class UnifiedAPIClient:
    def __init__(self, api_key_rotator: APIKeyRotator, model: str = "sonar-pro", timeout_seconds: int = 45):
        self.key_rotator = api_key_rotator
        self.model = model
        self.timeout = timeout_seconds

    async def fetch_data(self, query: str, max_retries: int = 3) -> Dict[str, Any]:
        """Fetch with automatic retry and key rotation."""
        for attempt in range(max_retries):
            try:
                api_key = self.key_rotator.get_next_key()
                response = await self._call_api(query, api_key)
                return response
            except RateLimitError as e:
                self.key_rotator.rotate_on_error()
                backoff_delay = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(backoff_delay)
            except APIError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
```

**Rules**:
- ✅ One client class per external service (PerplexityClient, KiteClient, etc.)
- ✅ Consolidate all duplicate API calls into unified methods
- ✅ Use API key rotation to avoid rate limits
- ✅ Implement exponential backoff for retries
- ✅ Handle authentication errors with key rotation
- ✅ Set appropriate timeouts for all requests
- ✅ Return structured, parsed data (not raw responses)
- ❌ Don't create separate functions for similar API calls
- ❌ Don't make HTTP requests without retry logic
- ❌ Don't hard-code API keys (use DI container)
- ❌ Don't ignore rate limit errors

#### 6.2 Fallback Parsing Strategy Pattern

**Responsibility**: Resilient data extraction from external APIs.

**Pattern**: Multi-layer parsing with progressive fallback:
1. **Primary**: Comprehensive structured parsing with detailed patterns
2. **Secondary**: Simplified regex-based extraction
3. **Tertiary**: Basic field extraction with minimal processing

**Implementation**:
```python
class DataParser:
    @staticmethod
    def parse_data(raw_text: str) -> Dict[str, Any]:
        """Parse with automatic fallback on failure."""
        try:
            return DataParser._parse_structured(raw_text)
        except Exception as e:
            logger.debug(f"Structured parsing failed: {e}")
            try:
                return DataParser._parse_regex(raw_text)
            except Exception as e:
                logger.debug(f"Regex parsing failed: {e}")
                return DataParser._basic_extraction(raw_text)

    @staticmethod
    def _parse_structured(text: str) -> Dict[str, Any]:
        """Comprehensive parsing with full data extraction."""
        # Complex regex patterns, validation, etc.
        pass

    @staticmethod
    def _parse_regex(text: str) -> Dict[str, Any]:
        """Simplified regex patterns for fallback."""
        # Basic patterns, less validation
        pass

    @staticmethod
    def _basic_extraction(text: str) -> Dict[str, Any]:
        """Minimal extraction, better than nothing."""
        # Extract only critical fields
        pass
```

**Rules**:
- ✅ Always implement at least 2 fallback levels
- ✅ Log which parsing strategy succeeded (for monitoring)
- ✅ Return partial data rather than complete failure
- ✅ Test each parsing strategy independently
- ✅ Each strategy more lenient than previous
- ✅ Emit event with parsing success/fallback used
- ❌ Don't raise exceptions on parsing failure
- ❌ Don't return empty dict on first parsing failure
- ❌ Don't skip fallback strategies silently
- ❌ Don't lose data in fallback (return what you got)

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

## Anti-Patterns - What NOT to Do

### Background Scheduler Anti-Patterns

**❌ Anti-Pattern 1: Multiple API Clients for Same Service**
```python
# WRONG - Creates multiple clients, inconsistent error handling
async def fetch_earnings():
    response = await httpx.AsyncClient().get("https://api.example.com/earnings")

async def fetch_fundamentals():
    response = await httpx.AsyncClient().get("https://api.example.com/fundamentals")
```
**Why Bad**: Duplicate retry logic, key rotation, error handling across files
**Fix**: Use consolidated `UnifiedAPIClient` with single initialization

---

### API Client Anti-Patterns

**❌ Anti-Pattern 2: Direct HTTP Requests Without Retry**
```python
# WRONG - No retry on failure, no rate limit handling
async def get_data(query: str):
    response = await httpx.get(f"https://api.example.com/query?q={query}")
    return response.json()
```
**Why Bad**: Transient failures cause immediate failure, no resilience
**Fix**: Use API client with exponential backoff and max_retries

---

### Parsing Anti-Patterns

**❌ Anti-Pattern 3: Single-Level Parsing Without Fallback**
```python
# WRONG - Parsing failure = no data extracted
def parse_earnings(text: str) -> Dict:
    # Complex regex
    return structured_data  # Raises if pattern doesn't match
```
**Why Bad**: Any format variation causes complete failure
**Fix**: Implement 3-level fallback parsing strategy

---

### Event Handler Anti-Patterns

**❌ Anti-Pattern 4: No Event Handler Cleanup**
```python
# WRONG - Memory leak, event subscriptions never removed
class MyService:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        event_bus.subscribe(EventType.ORDER_FILLED, self._handle)

    # No cleanup() method!
```
**Why Bad**: Event handlers accumulate, memory grows unbounded
**Fix**: Always unsubscribe in `cleanup()` method

---

### Task Anti-Patterns

**❌ Anti-Pattern 5: Direct HTTP Requests in Background Tasks**
```python
# WRONG - No timeout, no retry, blocking operations
async def process_earnings():
    for symbol in symbols:
        response = await httpx.get(f"https://api.example.com/earnings/{symbol}")
```
**Why Bad**: Long-running tasks can hang indefinitely, no resilience
**Fix**: Use API client with timeouts and retry logic

---

### File I/O Anti-Patterns

**❌ Anti-Pattern 6: Blocking File I/O in Async Functions**
```python
# WRONG - Blocks event loop
async def load_tasks():
    with open("tasks.json") as f:  # BLOCKS!
        return json.load(f)
```
**Why Bad**: Blocks entire async event loop
**Fix**: Use `aiofiles` with `async with`

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

