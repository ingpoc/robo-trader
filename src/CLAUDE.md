# Backend Architecture Guidelines

> **Scope**: Applies to all files under `src/` directory. Read after root CLAUDE.md for context.
> **Last Updated**: 2025-11-04 | **Status**: Production Ready | **Tier**: Reference

This file contains backend-specific patterns, service organization, and layer-specific rules that complement the project-wide patterns in the root CLAUDE.md.

## Contents

- [Layer-Specific Guidelines](#layer-specific-guidelines)
- [Backend Architecture Layers](#backend-architecture-layers)
- [Service Event Handler Pattern](#service-event-handler-pattern)
- [MCP Integration Pattern](#mcp-integration-pattern)
- [Web Layer Patterns](#web-layer-patterns)
- [Async/File Operations](#asyncfile-operations-backend-specific)
- [Error Handling Pattern](#error-handling-pattern-backend)
- [Event Emission Pattern](#event-emission-pattern)
- [DI Usage Pattern](#di-usage-pattern)
- [Anti-Patterns - Backend Failures to Avoid](#anti-patterns---backend-failures-to-avoid)
- [Development Workflow - Backend](#development-workflow---backend)
- [Common Mistakes to Avoid](#common-mistakes-to-avoid)
- [Quick File Reference - Backend](#quick-file-reference---backend)

## Claude Agent SDK Architecture (CRITICAL)

### SDK-Only Architecture (MANDATORY)

**CRITICAL RULE**: This application uses **ONLY** Claude Agent SDK for all AI functionality. No direct Anthropic API calls are permitted.

**Authentication**: Claude Code CLI authentication only (no API keys)
**Implementation**: All AI features use `ClaudeSDKClient` and MCP server pattern
**Tools**: Registered via `@tool` decorators in MCP servers
**Sessions**: Managed through SDK client lifecycle

**✅ CORRECT - SDK Implementation with Client Manager:**
```python
from claude_agent_sdk import ClaudeAgentOptions, tool
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

# Use client manager (CRITICAL for performance)
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)

# Use timeout helpers (MANDATORY)
await query_with_timeout(client, prompt, timeout=60.0)
async for response in receive_response_with_timeout(client, timeout=120.0):
    # Process response
```

**❌ VIOLATION - Direct API Usage:**
```python
# NEVER DO THIS
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key="sk-ant-...")
response = await client.messages.create(...)
```

**Why SDK-Only?**
- Consistent authentication via Claude CLI
- Proper tool execution patterns
- Built-in session management
- MCP server standardization
- No API key management complexity
- Official Claude integration patterns

**Verification**: All AI code must import from `claude_agent_sdk` only. Direct `anthropic` imports are forbidden.

## Backend Architecture Layers

### 1. Core Layer (`src/core/`)

**Responsibility**: Infrastructure and cross-cutting concerns.

**Structure**:
- `orchestrator.py` - Main facade (thin, delegates to coordinators)
- `coordinators/` - Focused service coordinators
- `di.py` - Dependency injection container
- `event_bus.py` - Event infrastructure
- `errors.py` - Error hierarchy
- `background_scheduler/` - Modularized task processing
- Other utilities: state, config, hooks, learning, etc.

**Rules**:
- ✅ Coordinators inherit from `BaseCoordinator`
- ✅ All services registered in DI container
- ✅ Cross-service communication via EventBus
- ✅ Errors inherit from `TradingError`
- ❌ No business logic in orchestrator
- ❌ No direct service-to-service calls

### 2. Services Layer (`src/services/`)

**Responsibility**: Domain-specific business logic.

**Services**:
- `portfolio_service.py` - Portfolio operations
- `risk_service.py` - Risk management
- `execution_service.py` - Order execution
- `analytics_service.py` - Analytics processing
- `learning_service.py` - Learning engine integration

**Rules**:
- ✅ One service = one domain responsibility
- ✅ Services receive dependencies via DI
- ✅ Emit domain events for significant operations
- ✅ Handle all errors with proper context
- ✅ Async-first design (use `async/await`)
- ❌ No synchronous file I/O
- ❌ No direct database access (use state manager)

#### 2.1 Service Event Handler Pattern

**Responsibility**: Services react to cross-cutting events.

**Pattern**: Inherit from `EventHandler` and implement `handle_event()` for event-driven architecture:

**Implementation**:
```python
from src.core.event_bus import EventHandler, Event, EventType

class MyService(EventHandler):
    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._initialized = False

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.PORTFOLIO_CASH_CHANGE, self)

    async def initialize(self) -> None:
        """Initialize service resources."""
        self._initialized = True

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events based on type."""
        try:
            if event.type == EventType.EXECUTION_ORDER_FILLED:
                await self._handle_order_fill(event)
            elif event.type == EventType.PORTFOLIO_CASH_CHANGE:
                await self._handle_cash_change(event)
        except TradingError as e:
            logger.error(f"Failed to handle {event.type.value}: {e.context.code}")

    async def _handle_order_fill(self, event: Event) -> None:
        """Process order fill event."""
        try:
            data = event.data
            order_id = data.get("order_id")
            # Process event
        except Exception as e:
            raise TradingError(f"Order fill processing failed: {e}")

    async def close(self) -> None:
        """Cleanup: unsubscribe from events."""
        if not self._initialized:
            return
        self.event_bus.unsubscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.unsubscribe(EventType.PORTFOLIO_CASH_CHANGE, self)
```

**Rules**:
- ✅ Inherit from `EventHandler` to receive events
- ✅ Subscribe to events in `__init__()`
- ✅ Implement `handle_event()` with type-based routing
- ✅ Unsubscribe in `close()` method
- ✅ Handle errors within event handlers (catch and log)
- ✅ Keep event handlers fast and non-blocking
- ✅ Use correlation_id from event for tracing
- ❌ Don't subscribe without cleanup (memory leak)
- ❌ Don't block in event handlers (keep async)
- ❌ Don't raise unhandled exceptions from event handlers
- ❌ Don't directly call other services (emit events instead)

### 3. Background Scheduler (`src/core/background_scheduler/`)

**Responsibility**: Periodic task processing (earnings, news, monitoring).

**Structure** (modularized):
- `models.py` - Task definitions
- `stores/` - Async file persistence (stock_state_store.py, strategy_log_store.py)
- `clients/` - Unified API clients (perplexity_client.py, retry_handler.py)
- `processors/` - Domain logic (earnings, news, fundamentals)
- `monitors/` - Monitoring (market, risk, health)
- `config/` - Configuration management
- `events/` - Event routing
- `background_scheduler.py` - Facade

**Rules**:
- ✅ Max 350 lines per file
- ✅ Max 10 methods per class
- ✅ One domain per module
- ✅ Consolidate duplicate API calls
- ✅ Error handling mandatory
- ✅ Use aiofiles for all I/O
- ✅ Check stock state before API calls
- ✅ Use retry logic with exponential backoff
- ❌ No monolithic files
- ❌ No direct HTTP requests without retry

### 4. MCP Integration (`src/mcp/`)

**Responsibility**: External MCP server integrations.

**Current Integrations**:
- Kite broker API
- Anthropic Claude API
- Other trading APIs

**Rules**:
- ✅ One client per API
- ✅ Consolidate duplicate logic
- ✅ Handle rate limits with exponential backoff
- ✅ Error handling with retry logic
- ✅ Use aiofiles for file operations
- ✅ Implement key rotation for rate limit management

### 5. Auth & Security (`src/auth/`)

**Responsibility**: Authentication and security checks.

**Rules**:
- ✅ Follow `.kilocode/rules/security.md`
- ✅ No hardcoded API keys (use environment variables)
- ✅ Never commit credentials
- ✅ Use secure token storage

### 6. Web Layer (`src/web/`)

**Responsibility**: FastAPI application, HTTP endpoints, WebSocket connections.

**Structure**:
- `app.py` - Main FastAPI application with middleware
- `chat_api.py` - Chat/AI endpoints
- `connection_manager.py` - WebSocket connection management
- `websocket_differ.py` - Differential update logic

#### 6.1 Middleware Error Handling Pattern

**Responsibility**: Centralized error handling for consistent HTTP responses.

**Pattern**: HTTPMiddleware that catches `TradingError` and generic exceptions separately:

**Implementation**:
```python
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Centralized error handling middleware."""
    try:
        return await call_next(request)
    except TradingError as e:
        # Trading domain errors
        logger.error(f"Trading error: {e.context.code}")
        status_code = 500 if e.context.severity.value in ["critical", "high"] else 400
        return JSONResponse(
            status_code=status_code,
            content=e.to_dict()
        )
    except Exception as e:
        # Generic application errors
        error_context = ErrorHandler.handle_error(e)
        logger.error(f"Unhandled error: {error_context}")
        return JSONResponse(
            status_code=500,
            content=ErrorHandler.format_error_response(e)
        )
```

**Rules**:
- ✅ Catch `TradingError` explicitly for structured responses
- ✅ Use `ErrorHandler.handle_error()` for generic exceptions
- ✅ Return appropriate HTTP status codes based on severity
- ✅ Never expose internal stack traces to clients
- ✅ Log errors with full context for debugging
- ✅ Include correlation_id in error response for tracing
- ❌ Don't let unhandled exceptions propagate to client
- ❌ Don't return generic "Internal Server Error"
- ❌ Don't expose implementation details

#### 6.2 Rate Limiting Pattern

**Responsibility**: Environment-configurable rate limits per endpoint group.

**Pattern**: Use SlowAPI with environment-based configuration:

**Implementation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Environment-configurable limits
dashboard_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")
trade_limit = os.getenv("RATE_LIMIT_TRADES", "10/minute")
agents_limit = os.getenv("RATE_LIMIT_AGENTS", "20/minute")

# Custom key function for load balancer support
def get_rate_limit_key(request: Request):
    """Get client IP, respecting X-Forwarded-For header."""
    return request.headers.get("X-Forwarded-For", get_remote_address(request))

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter

# Apply limits to endpoint groups
@app.get("/api/dashboard")
@limiter.limit(dashboard_limit)
async def api_dashboard(request: Request):
    return await get_dashboard_data()

@app.post("/api/trades/place")
@limiter.limit(trade_limit)
async def place_trade(request: Request, trade: TradeRequest):
    return await execute_trade(trade)
```

**Rules**:
- ✅ Configure limits via environment variables
- ✅ Handle X-Forwarded-For header for load balancers
- ✅ Group endpoints by risk/cost (trades stricter than reads)
- ✅ Use different limits for read vs write operations
- ✅ Return descriptive error message on rate limit
- ✅ Include Retry-After header in response
- ❌ Don't hard-code rate limits
- ❌ Don't apply same limit to all endpoints
- ❌ Don't ignore X-Forwarded-For (breaks behind load balancer)

---

## Async/File Operations - Backend Specific

### ✅ DO

```python
# File I/O in async context
async def load_config(self):
    async with aiofiles.open(self.config_file, 'r') as f:
        content = await f.read()
        return json.loads(content)

# Atomic file writes
async def save_config(self, data):
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        json.dump(data, tmp)
        tmp.flush()
    os.replace(tmp.name, self.config_file)
```

### ❌ DON'T

```python
# WRONG - Blocking I/O
async def load_config(self):
    with open(self.config_file, 'r') as f:  # BLOCKS!
        return json.load(f)

# WRONG - Direct blocking write
async def save_config(self, data):
    with open(self.config_file, 'w') as f:
        json.dump(data, f)  # BLOCKS!
```

---

## Error Handling Pattern - Backend

### ✅ DO

```python
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity, APIError

try:
    data = await kite_api.get_holdings()
except Exception as e:
    raise APIError(
        "Failed to fetch holdings",
        api_name="Kite",
        status_code=500,
        severity=ErrorSeverity.HIGH,
        recoverable=True,
        retry_after_seconds=5
    )
```

### ❌ DON'T

```python
# WRONG - Generic exception
raise Exception("API failed")

# WRONG - Silent suppression
try:
    data = await kite_api.get_holdings()
except:
    pass
```

---

## Event Emission Pattern

### ✅ DO

```python
from src.core.event_bus import Event, EventType
import uuid

# Emit significant business event
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.EXECUTION_ORDER_PLACED,
    source="ExecutionService",
    data={"order_id": order_id, "symbol": symbol, "quantity": qty}
)
await self.event_bus.publish(event)
```

### ❌ DON'T

```python
# WRONG - No event emission
order = await place_order(...)

# WRONG - Custom event types
await event_bus.publish({"type": "order_placed", "data": {...}})
```

---

## DI Usage Pattern

### ✅ DO

```python
from src.core.di import DependencyContainer

# Register in container initialization
container = DependencyContainer()
await container.initialize(config)

# Inject in services
class MyService:
    def __init__(self, container: DependencyContainer):
        self.scheduler = container.get(BackgroundScheduler)
        self.event_bus = container.get(EventBus)
```

### ❌ DON'T

```python
# WRONG - Global imports
from src.core.background_scheduler import BackgroundScheduler
scheduler = BackgroundScheduler()

# WRONG - Direct instantiation
class MyService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()  # Not injected
```

---

## Anti-Patterns - Backend Failures to Avoid

### Service Anti-Patterns

**❌ Anti-Pattern 1: Services Not Inheriting EventHandler**
```python
# WRONG - Service can't receive events
class MyService:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    # Never receives events
```
**Why Bad**: Service can't react to domain events, manual coordination needed
**Fix**: Inherit from `EventHandler`, implement `handle_event()`, subscribe to events

---

**❌ Anti-Pattern 2: Event Subscriptions Without Cleanup**
```python
# WRONG - Memory leak
class MyService(EventHandler):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        event_bus.subscribe(EventType.ORDER_FILLED, self)
        # No cleanup() method
```
**Why Bad**: Services accumulate subscriptions when initialized multiple times
**Fix**: Always unsubscribe in `close()` method

---

### Error Handling Anti-Patterns

**❌ Anti-Pattern 3: Bare Except Clause**
```python
# WRONG - Catches SystemExit, KeyboardInterrupt
try:
    data = await fetch_data()
except:
    pass  # Silent failure!
```
**Why Bad**: Masks all failures, including interrupts
**Fix**: Catch specific exceptions: `except APIError:`, `except TradingError:`

---

**❌ Anti-Pattern 4: Exception Before More Specific One**
```python
# WRONG - Generic before specific
try:
    data = await api.fetch()
except Exception:  # Catches everything first
    pass
except APIError:   # Never reached!
    pass
```
**Why Bad**: Specific handlers never execute
**Fix**: Order from specific to general

---

### Web Layer Anti-Patterns

**❌ Anti-Pattern 5: Exposing Stack Traces to Clients**
```python
# WRONG - Internal details exposed
@app.get("/data")
async def get_data():
    try:
        return await fetch()
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}
```
**Why Bad**: Exposes internal structure, security risk
**Fix**: Return `to_dict()` from `TradingError`, generic message for others

---

**❌ Anti-Pattern 6: Hardcoded Rate Limits**
```python
# WRONG - Can't adjust without redeployment
DASHBOARD_LIMIT = "30/minute"
TRADE_LIMIT = "10/minute"

@app.get("/api/dashboard")
@limiter.limit(DASHBOARD_LIMIT)
async def dashboard():
    pass
```
**Why Bad**: Can't tune for different environments
**Fix**: Load from environment variables with defaults

---

### Async Anti-Patterns

**❌ Anti-Pattern 7: Awaiting Task After Cancel**
```python
# WRONG - Can hang indefinitely
try:
    await asyncio.wait_for(task, timeout=5)
except asyncio.TimeoutError:
    task.cancel()
    await task  # Can hang here!
```
**Why Bad**: Cancelled task doesn't always complete
**Fix**: Wrap in wait_for with timeout: `await asyncio.wait_for(task, timeout=2)`

---

### DI Container Anti-Patterns

**❌ Anti-Pattern 8: Creating Services Outside Container**
```python
# WRONG - Not managed by container
service = MyService()

# WRONG - Global reference
_scheduler = BackgroundScheduler()
def get_scheduler():
    return _scheduler
```
**Why Bad**: Services not in DI, can't mock for testing
**Fix**: Always get from container: `container.get(MyService)`

---

## Anti-Patterns - Backend (What to Avoid)

### Service Coupling Anti-Pattern
- ❌ Direct service-to-service calls (violates DI)
- ✅ Emit events, let handlers react via EventBus

### Missing Cleanup Anti-Pattern
- ❌ Initialize resources without cleanup() method
- ✅ Implement both initialize() and cleanup() with proper unsubscribe

### Async Violations Anti-Pattern
- ❌ Blocking I/O in async methods
- ❌ Synchronous operations in `__init__()`
- ✅ Use `aiofiles`, lazy initialization, async/await throughout

### Error Suppression Anti-Pattern
- ❌ `try/except: pass` (silent failures)
- ❌ Bare `except Exception:` without handling
- ✅ Specific exception types with proper error context

### Rate Limit Ignorance Anti-Pattern
- ❌ Retry without backoff
- ❌ Single API key without rotation
- ✅ Exponential backoff + API key rotation

---

## Pre-Commit Checklist - Backend

- [ ] All file I/O uses `aiofiles` in async context
- [ ] No blocking I/O in `__init__()` methods
- [ ] All errors inherit from `TradingError`
- [ ] Significant operations emit events
- [ ] Services receive dependencies via DI
- [ ] Max 350 lines per file
- [ ] Async/await used throughout (no blocking calls)
- [ ] External API calls have retry logic + exponential backoff
- [ ] Stock state checked before API calls, updated after fetches
- [ ] No hardcoded credentials (use env vars)
- [ ] Event subscriptions cleaned up
- [ ] No direct service-to-service coupling
- [ ] Performance metrics use PerformanceCalculator

---

## Quick File Reference - Backend

| File | Purpose | Max Size |
|------|---------|----------|
| `core/orchestrator.py` | Main facade | 300 lines (thin!) |
| `core/coordinators/*.py` | Service coordination | 150 lines each |
| `core/di.py` | Dependency injection | 500 lines |
| `core/event_bus.py` | Event infrastructure | 350 lines |
| `core/errors.py` | Error hierarchy | 220 lines |
| `services/*.py` | Domain logic | 400 lines each |
| `core/background_scheduler/*` | Task processing | 350 lines each |

---

## Development Workflow - Backend

### 1. New Service

- Create in `services/` directory with single responsibility
- Inherit from `EventHandler` if subscribing to events
- Register in `DependencyContainer`
- Emit domain events for significant operations
- Implement `initialize()` and `cleanup()`
- Max 400 lines per service file

### 2. New Background Task

- Add to `core/background_scheduler/{domain}/`
- Keep under 350 lines (modularize if larger)
- Use `aiofiles` for all file I/O
- Handle errors with `TradingError` and retry logic
- Emit completion/failure events
- Use exponential backoff for retries

### 3. New Coordinator

- Inherit from `BaseCoordinator` (required)
- Implement `initialize()` and `cleanup()`
- Delegate operations to services
- Subscribe to relevant events
- Emit lifecycle events
- Keep under 150 lines

### 4. New API Client

- Create unified client per external API
- Implement key rotation for rate limits
- Add exponential backoff retry logic
- Handle all error cases with `TradingError`
- Return structured, parsed data (not raw responses)
- Set appropriate timeouts

### 5. Refactoring

- Keep imports working (wrapper pattern)
- Maintain backward compatibility
- Update only single file/module at a time
- Verify tests pass before merging
- Document changes in commit message

---

## Common Mistakes to Avoid

### Mistake 1: Duplicate API Calls
**Problem**: Multiple functions calling same API independently
**Solution**: Create single `UnifiedAPIClient` class with key rotation, consolidate all calls

### Mistake 2: No Cleanup on Initialize
**Problem**: Resources leak when services recreated
**Solution**: Always implement `cleanup()` method, unsubscribe from events

### Mistake 3: Awaiting Cancelled Tasks
**Problem**: Can hang indefinitely
**Solution**: Wrap in `asyncio.wait_for()` with timeout when cancelling

### Mistake 4: Silencing Errors
**Problem**: Bugs disappear, debugging impossible
**Solution**: Catch specific exceptions, log with context, never `except: pass`

### Mistake 5: Hardcoded Credentials
**Problem**: Security risk, can't rotate keys
**Solution**: Always use environment variables, implement key rotation

### Mistake 6: Parsing Without Fallback
**Problem**: Any format variation causes complete failure
**Solution**: Implement 3-level fallback parsing (structured → regex → basic)

