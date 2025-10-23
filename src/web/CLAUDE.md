# Web Layer Guidelines

> **Scope**: Applies to `src/web/` directory (FastAPI, WebSockets, HTTP endpoints). Read after `src/CLAUDE.md` and `src/core/CLAUDE.md`.

The web layer handles HTTP endpoints, WebSocket connections, and client communication. It must enforce error handling, rate limiting, and input validation for all requests.

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

## Input Validation Pattern

All endpoints must validate request data:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class TradeRequest(BaseModel):
    """Validated trade request."""

    portfolio_id: str = Field(..., min_length=1)
    symbol: str = Field(..., regex="^[A-Z0-9]{1,10}$")
    quantity: int = Field(..., gt=0, le=10000)
    order_type: str = Field(..., regex="^(BUY|SELL)$")
    limit_price: Optional[float] = Field(None, gt=0)

    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v.isupper():
            raise ValueError('Symbol must be uppercase')
        return v

@app.post("/api/trades")
@limiter.limit(TRADE_LIMIT)
async def place_trade(request: Request, trade: TradeRequest):
    """Place trade with validated input."""
    try:
        # Input already validated by Pydantic
        result = await trade_coordinator.place_trade(
            portfolio_id=trade.portfolio_id,
            symbol=trade.symbol,
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

### Rules for Validation

- ✅ Use Pydantic models for all requests
- ✅ Define field constraints (min, max, regex, etc.)
- ✅ Include validators for complex logic
- ✅ Return validation errors clearly
- ❌ NEVER skip validation
- ❌ NEVER trust client input
- ❌ NEVER expose validation details

---

## Pre-Commit Checklist - Web Layer

- [ ] Error middleware catches all exceptions
- [ ] Rate limiting applied to all endpoints
- [ ] Input validation using Pydantic models
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
**Fix**: Use Pydantic models with validators

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
