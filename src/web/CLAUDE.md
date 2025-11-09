# Web Layer Guidelines

> **Scope**: Applies to `src/web/` directory (FastAPI, WebSockets, HTTP endpoints). Read after `src/CLAUDE.md` and `src/core/CLAUDE.md`.
> **Last Updated**: 2025-11-09 | **Status**: Production Ready | **Tier**: Reference

## Quick Reference - SDK Usage

- **Service Access**: Get SDK services from container: `await container.get("research_tracker")`
- **No Direct SDK**: Web layer NEVER uses SDK directly - only through services
- **Services Handle SDK**: Services use client manager internally (transparent to web layer)

The web layer handles HTTP endpoints, WebSocket connections, and client communication. It must enforce error handling, rate limiting, and input validation for all requests.

## Contents

- [Claude Agent SDK Integration](#claude-agent-sdk-integration-critical)
- [Middleware Error Handling Pattern](#middleware-error-handling-pattern)
- [Rate Limiting Pattern](#rate-limiting-pattern)
- [WebSocket Integration](#websocket-integration)
- [API Endpoint Patterns](#api-endpoint-patterns)
- [Development Workflow - Web Layer](#development-workflow---web-layer)
- [Quick Reference - Web Layer](#quick-reference---web-layer)

## Claude Agent SDK Integration (CRITICAL)

### SDK-Only Web Endpoints (MANDATORY)

All AI-related web endpoints must use **ONLY** Claude Agent SDK services. No direct Anthropic API calls are permitted.

**AI Transparency Endpoints** (SDK-Only):
- `/api/claude/transparency/research` - Research activity tracking
- `/api/claude/transparency/analysis` - Analysis logging
- `/api/claude/transparency/execution` - Execution monitoring
- `/api/claude/transparency/daily-evaluation` - Strategy evaluation
- `/api/claude/transparency/daily-summary` - Activity summarization

**SDK Service Integration Pattern**:
```python
# All AI endpoints use SDK-only services from container
# Services use client manager internally (transparent to web layer)

@router.get("/api/claude/research")
async def get_research(request: Request, container: DependencyContainer = Depends(get_container)):
    """Get research activity - SDK-only service."""
    research_tracker = await container.get("research_tracker")
    return await research_tracker.get_research_history(account_type=account_type)
```

**❌ FORBIDDEN - Direct API Usage in Web Layer:**
```python
# NEVER DO THIS in web endpoints
from anthropic import AsyncAnthropic

@app.get("/api/claude/direct")
async def direct_claude_call():
    client = AsyncAnthropic(api_key="sk-ant-...")
    response = await client.messages.create(...)
    return response
```

**Service Registration Requirements**:
All transparency services must be registered in the DI container:
```python
# In src/core/di.py
await container.register_singleton(ResearchTracker, "research_tracker")
await container.register_singleton(AnalysisLogger, "analysis_logger")
await container.register_singleton(ExecutionMonitor, "execution_monitor")
await container.register_singleton(DailyStrategyEvaluator, "daily_strategy_evaluator")
await container.register_singleton(ActivitySummarizer, "activity_summarizer")
```

---

## Web Layer Architecture

### Layer Responsibility

The web layer acts as the bridge between clients and core services:

```
Client (UI/Browser)
    ↓ HTTP/WebSocket
API Endpoints (src/web/app.py)
    ↓
Error Middleware (error handling)
    ↓
Rate Limiting (SlowAPI)
    ↓
Request Handler
    ↓
Coordinators (src/core/coordinators/)
    ↓
Services (src/services/)
```

### Rules for Web Endpoints

- ✅ All endpoints have error middleware protection
- ✅ All endpoints have rate limiting applied
- ✅ Validate request input before processing
- ✅ Return structured error responses from `TradingError`
- ✅ Include correlation_id in all responses for tracing
- ✅ Log all errors with context
- ✅ Use dependency injection for services
- ✅ Implement graceful WebSocket cleanup
- ✅ Use `PerformanceCalculator` for trading metrics endpoints
- ❌ NEVER return stack traces to clients
- ❌ NEVER expose internal error details
- ❌ NEVER skip input validation
- ❌ NEVER hardcode rate limits (use env vars)
- ❌ NEVER leave WebSocket connections open on error

---

## Error Middleware Pattern

All FastAPI applications must have centralized error handling:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.core.errors import TradingError

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Centralized error handling middleware."""
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    try:
        return await call_next(request)

    except TradingError as e:
        # Domain errors - return structured response
        logger.error(f"[{correlation_id}] Trading error: {e.context.code}")
        status_code = 500 if e.context.severity.value == "critical" else 400
        return JSONResponse(
            status_code=status_code,
            content={
                "error": e.context.message,
                "code": e.context.code,
                "category": e.context.category.value,
                "correlation_id": correlation_id,
                "recoverable": e.context.recoverable
            }
        )

    except Exception as e:
        # Generic exceptions - don't expose details
        logger.exception(f"[{correlation_id}] Unhandled error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "correlation_id": correlation_id,
                "recoverable": False
            }
        )
```

### Rules for Error Middleware

- ✅ Catch `TradingError` explicitly for structured responses
- ✅ Return status code based on severity
- ✅ Include correlation_id in every response
- ✅ Log with full context (correlation_id, error code)
- ✅ Never expose implementation details to client
- ✅ Handle generic exceptions separately
- ❌ DON'T return stack traces
- ❌ DON'T expose database/API details
- ❌ DON'T expose file paths

---

## Rate Limiting Pattern

All endpoints must have environment-configurable rate limits:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
import os

# Load limits from environment with defaults
DASHBOARD_LIMIT = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")
TRADE_LIMIT = os.getenv("RATE_LIMIT_TRADES", "10/minute")
AGENT_LIMIT = os.getenv("RATE_LIMIT_AGENTS", "20/minute")

# Custom key function for load balancer support
def get_rate_limit_key(request: Request):
    """Get client IP, respecting X-Forwarded-For header."""
    return request.headers.get("X-Forwarded-For", get_remote_address(request))

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter

# Apply to endpoint groups
@app.get("/api/dashboard")
@limiter.limit(DASHBOARD_LIMIT)
async def get_dashboard(request: Request):
    """Get dashboard data."""
    return await dashboard_coordinator.get_dashboard()

@app.post("/api/trades")
@limiter.limit(TRADE_LIMIT)
async def place_trade(request: Request, trade: TradeRequest):
    """Place trade (strict rate limit)."""
    return await execute_trade(trade)
```

### Rules for Rate Limiting

- ✅ Use environment variables for all limits
- ✅ Group endpoints by risk level (reads vs writes)
- ✅ Stricter limits for trading operations than reads
- ✅ Handle X-Forwarded-For for load balancers
- ✅ Return descriptive error on rate limit (429)
- ✅ Include Retry-After header
- ❌ DON'T hardcode rate limits
- ❌ DON'T apply same limit to all endpoints
- ❌ DON'T ignore X-Forwarded-For

---

## WebSocket Connection Management

WebSocket connections need proper lifecycle management:

```python
from fastapi import WebSocket, WebSocketDisconnect
import logging

class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept connection and track it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected: {client_id}")

    async def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove connection."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {client_id}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up failed connections
        for conn in disconnected:
            await self.disconnect(conn, "unknown")

manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for dashboard updates."""
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)

    try:
        # Send initial data
        initial_data = await dashboard_coordinator.get_initial_data()
        await websocket.send_json(initial_data)

        # Listen for client messages
        while True:
            data = await websocket.receive_json()
            # Process client message

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
        await manager.disconnect(websocket, client_id)

    except Exception as e:
        logger.exception(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(websocket, client_id)
```

### Rules for WebSocket

- ✅ Implement ConnectionManager for cleanup
- ✅ Handle disconnects gracefully
- ✅ Send initial state on connect
- ✅ Implement heartbeat/keepalive for long connections
- ✅ Log all connections and disconnections
- ✅ Clean up resources on error
- ❌ NEVER leave connections open indefinitely
- ❌ NEVER ignore disconnect errors
- ❌ NEVER send large payloads (use differential updates)
- ❌ NEVER block WebSocket handling

---

## API Endpoint Patterns

### Database Access in Endpoints (CRITICAL - Database Locking)

**Rule**: Always use ConfigurationState's locked methods for database access in web endpoints. Never access database connection directly.

**Why**: Direct database access bypasses `asyncio.Lock()` protection, causing "database is locked" errors during concurrent operations.

**✅ CORRECT Pattern**:
```python
@router.get("/api/claude/transparency/analysis")
async def get_analysis_transparency(request: Request, container: DependencyContainer = Depends(get_container)):
    """Get Claude's analysis activities."""
    try:
        configuration_state = await container.get("configuration_state")
        if not configuration_state:
            return {"analysis": {}}

        # Use locked method - prevents "database is locked"
        config_data = await configuration_state.get_analysis_history()
        return {"analysis": config_data}
    except Exception as e:
        logger.warning(f"Could not get analysis: {e}")
        return {"analysis": {}}
```

**❌ WRONG Pattern** (causes database locks):
```python
# NEVER DO THIS:
database = await container.get("database")
conn = database.connection
cursor = await conn.execute(...)  # NO LOCK - CAUSES CONTENTION!
```

**Key Points**:
- Web endpoints must use ConfigurationState's public methods with internal locking
- Methods like `get_analysis_history()`, `store_analysis_history()`, `store_recommendation()` all use `async with self._lock:`
- Direct connection access is only acceptable within database_state classes that manage the lock
- Pages freeze when multiple concurrent requests hit direct database access

**CRITICAL - Current Violations (Fix Immediately)**:
- ⚠️ `src/core/database_state/config_storage/background_tasks_store.py:100` - `await self.db.connection.execute(...)`
- ⚠️ `src/core/database_state/config_storage/background_tasks_store.py:121` - `await self.db.connection.commit()`
- ⚠️ `src/web/claude_agent_api.py:484` - `conn = database.connection`

**Action Required**: Replace direct connection access with ConfigurationState locked methods. This causes database contention and page freezes during 30+ second analysis operations.

---

## Input Validation Pattern

All endpoints must validate request data using Pydantic v2 with proper Field constraints:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class TradeRequest(BaseModel):
    """Validated trade request with comprehensive input validation."""

    # Text fields: min/max length constraints
    symbol: str = Field(..., min_length=1, max_length=20)

    # Pattern validation: Use 'pattern=' in Pydantic v2 (NOT 'regex=')
    side: str = Field(..., pattern="^(BUY|SELL)$")

    # Numeric: greater-than, less-than constraints
    quantity: int = Field(..., gt=0, le=10000)

    # Optional enum-like field with pattern
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")

    # Optional numeric with constraint
    price: Optional[float] = Field(None, gt=0)

    # Custom validation for complex logic
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol is uppercase."""
        if not v.isupper():
            raise ValueError('Symbol must be uppercase')
        return v

@app.post("/api/trades")
@limiter.limit(TRADE_LIMIT)
async def place_trade(request: Request, trade: TradeRequest):
    """Place trade with validated input (422 on validation error)."""
    try:
        # Input already validated by Pydantic
        # Invalid inputs return 422 automatically:
        # - quantity: -10 → 422 (gt=0 violated)
        # - side: "INVALID" → 422 (pattern mismatch)
        # - symbol: "sbin" → 422 (custom validator)

        result = await trade_coordinator.place_trade(
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity
        )
        return {"success": True, "order_id": result}

    except TradingError as e:
        # Error middleware handles this
        raise

    except Exception as e:
        logger.exception(f"Trade placement failed: {e}")
        raise TradingError(f"Trade failed: {e}")
```

### Validation Field Constraints Reference

```python
# Numeric validation
quantity: int = Field(..., gt=0, le=10000)  # > 0, ≤ 10,000
price: float = Field(..., gt=0, lt=1000000)  # > 0, < 1,000,000

# Text validation
symbol: str = Field(..., min_length=1, max_length=20)  # 1-20 chars
name: str = Field(..., min_length=3, max_length=100)  # 3-100 chars

# Pattern matching (Pydantic v2)
side: str = Field(..., pattern="^(BUY|SELL)$")  # Must be BUY or SELL
order_type: str = Field(..., pattern="^(MARKET|LIMIT)$")  # Enum-like

# Optional with constraints
limit_price: Optional[float] = Field(None, gt=0)  # Must be positive if provided

# Custom validators for complex rules
@validator('email')
def validate_email(cls, v):
    if '@' not in v:
        raise ValueError('Invalid email format')
    return v.lower()
```

### Rules for Validation

- ✅ Use Pydantic models for all requests
- ✅ Use Pydantic v2: `pattern=` parameter (NOT deprecated `regex=`)
- ✅ Define field constraints: `gt=`, `lt=`, `min_length=`, `max_length=`
- ✅ Include validators for complex logic (custom validation logic)
- ✅ Return validation errors clearly (422 Unprocessable Entity)
- ✅ Validate at input boundary (before business logic)
- ❌ NEVER skip validation
- ❌ NEVER trust client input
- ❌ NEVER expose validation details
- ❌ NEVER use deprecated `regex=` parameter (use `pattern=` in Pydantic v2)

---

## Pre-Commit Checklist - Web Layer

- [ ] Error middleware catches all exceptions
- [ ] Rate limiting applied to all endpoints (use env vars)
- [ ] Input validation using Pydantic models with Field constraints
- [ ] Validation uses Pydantic v2 syntax (`pattern=`, NOT `regex=`)
- [ ] All numeric fields have constraints (`gt=`, `lt=`, `le=`, `ge=`)
- [ ] All string fields have length constraints (`min_length=`, `max_length=`)
- [ ] Complex validation via `@validator()` decorators
- [ ] Invalid input returns 422 Unprocessable Entity
- [ ] No hardcoded rate limits (use env vars)
- [ ] Correlation ID included in all responses
- [ ] Stack traces never exposed to clients
- [ ] WebSocket connections properly cleaned up
- [ ] Graceful error handling for WebSocket
- [ ] All errors logged with context
- [ ] Status codes appropriate for error severity
- [ ] X-Forwarded-For header respected
- [ ] Trading metrics endpoints use PerformanceCalculator

---

## Common Web Layer Mistakes

### Mistake 1: Missing Error Middleware
```python
# WRONG - No error handling
@app.get("/api/data")
async def get_data():
    data = await fetch_data()  # Can crash!
    return data
```
**Fix**: Add error middleware to app

### Mistake 2: No Input Validation
```python
# WRONG - Trusts client input
@app.post("/api/trade")
async def place_trade(trade_dict: dict):
    return await execute_trade(trade_dict)  # Could have anything!
```
**Fix**: Use Pydantic models with Field constraints

### Mistake 3: Pydantic v1 Syntax in v2 (regex parameter)
```python
# WRONG - 'regex=' deprecated in Pydantic v2
class TradeRequest(BaseModel):
    side: str = Field(..., regex="^(BUY|SELL)$")  # BREAKS!
```
**Error**: `PydanticUserError: 'regex' is removed. use 'pattern' instead`

**Fix**: Use `pattern=` instead of `regex=`
```python
# CORRECT - Pydantic v2 syntax
class TradeRequest(BaseModel):
    side: str = Field(..., pattern="^(BUY|SELL)$")  # ✅
```

### Mistake 4: Negative/Zero Quantity Accepted
```python
# WRONG - No constraint on quantity
class TradeRequest(BaseModel):
    quantity: int  # Accepts -10, 0, anything!
```
**Fix**: Add numeric constraint
```python
# CORRECT - Only positive integers up to 10,000
class TradeRequest(BaseModel):
    quantity: int = Field(..., gt=0, le=10000)
```
**Result**: Invalid input automatically returns 422

### Mistake 3: Exposing Stack Traces
```python
# WRONG - Shows internal details
@app.get("/api/data")
async def get_data():
    try:
        return fetch_data()
    except Exception as e:
        return {"error": traceback.format_exc()}  # EXPOSED!
```
**Fix**: Return generic error message, log full trace server-side

### Mistake 4: No WebSocket Cleanup
```python
# WRONG - Connection never closed
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        # No disconnect handling!
```
**Fix**: Implement ConnectionManager, handle disconnects

### Mistake 5: Hardcoded Rate Limits
```python
# WRONG - Can't adjust per environment
@limiter.limit("30/minute")
```
**Fix**: Load from environment variables with defaults

---

## Quick Reference - Web Layer

| Component | Pattern | Location |
|-----------|---------|----------|
| Error Handling | HTTPMiddleware | app.py |
| Rate Limiting | SlowAPI with env config | app.py |
| Input Validation | Pydantic models | Models in endpoints |
| WebSocket | ConnectionManager | connection_manager.py |
| Correlation ID | Added in middleware | All responses |

---

**Key Principle**: The web layer is the security and interface boundary. All requests must be validated, all errors must be handled, all responses must be safe for clients.
