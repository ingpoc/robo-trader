# Backend Architecture Guidelines

> **Scope**: Applies to all files under `src/` directory. Read after root CLAUDE.md.

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

### 3. Background Scheduler (`src/core/background_scheduler/`)

**Responsibility**: Periodic task processing (earnings, news, monitoring).

**Structure** (modularized):
- `models.py` - Task definitions
- `stores/` - Async file persistence
- `clients/` - Unified API clients
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
- ✅ Handle rate limits
- ✅ Error handling with retry logic
- ✅ Use aiofiles for file operations

### 5. Auth & Security (`src/auth/`)

**Responsibility**: Authentication and security checks.

**Rules**:
- ✅ Follow `.kilocode/rules/security.md`
- ✅ No hardcoded API keys (use environment variables)
- ✅ Never commit credentials
- ✅ Use secure token storage

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
await self.event_bus.emit(event)
```

### ❌ DON'T

```python
# WRONG - No event emission
order = await place_order(...)

# WRONG - Custom event types
await event_bus.emit({"type": "order_placed", "data": {...}})
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

## Pre-Commit Checklist - Backend

- [ ] All file I/O uses `aiofiles` in async context
- [ ] No blocking I/O in `__init__()` methods
- [ ] All errors inherit from `TradingError`
- [ ] Significant operations emit events
- [ ] Services receive dependencies via DI
- [ ] Max 350 lines per file
- [ ] Async/await used throughout
- [ ] External API calls have retry logic
- [ ] No hardcoded credentials

---

## Quick File Reference

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

1. **New Service**
   - Create in `services/` directory
   - Inherit domain from single responsibility
   - Register in DI container
   - Emit domain events

2. **New Background Task**
   - Add to `core/background_scheduler/{domain}/`
   - Max 350 lines
   - Use aiofiles for I/O
   - Handle errors with retry logic

3. **New Coordinator**
   - Inherit from `BaseCoordinator`
   - Implement `initialize()` and `cleanup()`
   - Delegate to services
   - Emit lifecycle events

4. **Refactoring**
   - Keep imports working (wrapper pattern)
   - Maintain backward compatibility
   - Update only single file/module at a time
   - Verify tests pass

