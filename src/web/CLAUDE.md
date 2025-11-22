# Web Layer - src/web/

**Last Updated**: 2025-11-22

## Endpoint Pattern (Max 300 lines per file)

```python
@router.get("/api/endpoint")
async def get_endpoint(request: Request, container: DependencyContainer = Depends(get_container)):
    try:
        service = await container.get("service_name")
        result = await service.operation()
        return {"success": True, "data": result}
    except TradingError as e:
        logger.error(f"Error: {e.context.code}")
        return JSONResponse(
            status_code=500 if e.context.severity.value == "critical" else 400,
            content=e.to_dict()
        )
```

## Middleware Error Handling

```python
@app.middleware("http")
async def error_middleware(request: Request, call_next):
    request.state.correlation_id = str(uuid.uuid4())
    try:
        return await call_next(request)
    except TradingError as e:
        return JSONResponse(status_code=400, content=e.to_dict())
    except Exception as e:
        logger.exception(f"Unhandled: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal error"})
```

## Rate Limiting (Environment-Configurable)

```python
DASHBOARD_LIMIT = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")
TRADE_LIMIT = os.getenv("RATE_LIMIT_TRADES", "10/minute")

@limiter.limit(DASHBOARD_LIMIT)
async def dashboard_endpoint(request: Request):
    return await get_dashboard()
```

## Input Validation (Pydantic v2)

✅ **DO** - Use `pattern=` not `regex=` (Pydantic v2):
```python
class TradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int = Field(..., gt=0, le=10000)
```

❌ **DON'T** - Use deprecated `regex=`:
```python
side: str = Field(..., regex="^(BUY|SELL)$")  # BREAKS in Pydantic v2
```

## WebSocket Connection Management

```python
class ConnectionManager:
    def __init__(self):
        self.connections = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: dict):
        disconnected = []
        for conn in self.connections:
            try:
                await conn.send_json(message)
            except:
                disconnected.append(conn)
        for conn in disconnected:
            await self.disconnect(conn)
```

## Database Access in Endpoints (CRITICAL)

✅ **CORRECT** - Use locked state methods:
```python
@router.get("/api/analysis")
async def get_analysis(request: Request, container: DependencyContainer = Depends()):
    config_state = await container.get("configuration_state")
    data = await config_state.get_analysis_history()
    return {"analysis": data}
```

❌ **WRONG** - Direct database access:
```python
database = await container.get("database")
conn = database.connection
cursor = await conn.execute(...)  # NO LOCK!
```

## Critical Rules

| Rule | Reason |
|------|--------|
| Use ConfigurationState locked methods | Prevents "database is locked" |
| Always use error middleware | Safe error handling + client safety |
| Validate input with Pydantic | Automatic 422 response on error |
| Use environment variables for rates | Runtime configuration |
| Never expose stack traces | Security + clean error messages |
| Handle WebSocket cleanup | Prevent memory leaks |

## Common Issues

| Issue | Fix |
|-------|-----|
| "Pydantic validation failed" | Check field constraints (pattern, gt, le, etc.) |
| "regex parameter error" | Use `pattern=` not `regex=` (Pydantic v2) |
| Pages freeze during analysis | Use locked methods in endpoints |
| WebSocket disconnects | Implement ConnectionManager.disconnect() |
| Rate limit not working | Check environment variables with defaults |
| Stack traces in response | Remove from error handling, only log server-side |

## SDK-Only AI Endpoints

✅ **CORRECT** - Use SDK services from container:
```python
@router.get("/api/claude/analysis")
async def get_analysis(request: Request, container = Depends()):
    analysis_logger = await container.get("analysis_logger")
    return await analysis_logger.get_analysis_history()
```

❌ **FORBIDDEN** - Direct SDK calls:
```python
from anthropic import AsyncAnthropic  # NOT ALLOWED
client = AsyncAnthropic(api_key="...")
```
