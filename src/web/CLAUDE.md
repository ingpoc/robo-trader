# Web Layer - src/web/

Max 300 lines per route file. Use FastAPI + DependencyContainer pattern.

## Endpoint Pattern

```python
@router.get("/api/endpoint")
async def get_endpoint(request: Request, container = Depends(get_container)):
    try:
        service = await container.get("service_name")
        return {"success": True, "data": await service.operation()}
    except TradingError as e:
        return JSONResponse(status_code=400, content=e.to_dict())
```

## Critical Rules

| Rule | Why |
|------|-----|
| Use ConfigurationState locked methods | Prevents "database is locked" |
| Always use error middleware | Safe error handling |
| Validate with Pydantic v2 `pattern=` | Never use `regex=` (deprecated) |
| Environment vars for rate limits | Runtime configuration |
| Never expose stack traces | Security |
| SDK via container only | Never import anthropic directly |

## Patterns

| Task | Pattern |
|------|---------|
| Database access | `config_state.get_analysis_history()` |
| WebSocket cleanup | `ConnectionManager.disconnect()` on error |
| Input validation | `Field(..., pattern="^(BUY\|SELL)$")` Pydantic v2 |
| Rate limiting | `@limiter.limit(os.getenv("RATE_LIMIT_X", "30/minute"))` |
| AI analysis | Via `analysis_logger` from container, never direct SDK |

## Event Loop Safety (CRITICAL)
| Rule | Fix |
|------|-----|
| **Event loop closure errors** | **Use `asyncio.get_running_loop()` not `get_event_loop()`** |
| **System stability** | **Never call `asyncio.get_event_loop()` in routes** |

## Database Locking in Routes
```python
# ✅ CORRECT: Use locked state methods
state_manager = await container.get("state_manager")  # NOT database_state_manager
await state_manager.paper_trading.get_automation_config()

# ❌ NEVER: Direct database access
cursor = await db.execute(...)  # Causes "database is locked"
```

## Task Payload Requirements
AI_ANALYSIS tasks MUST include symbols:
```python
payload={"agent_name": "scan", "symbols": ["AAPL"]}  # Required
payload={"agent_name": "scan"}  # WRONG - causes token exhaustion
```

## Common Issues

| Issue | Fix |
|-------|-----|
| "database is locked" | Use locked state methods |
| **Event loop is closed** | **Use `asyncio.get_running_loop()`** |
| **Service not registered** | **Use exact service names like "state_manager"** |
| Pydantic validation fails | Check `pattern=`, `gt=`, `le=` constraints |
| Pages freeze | Use locked methods in endpoints |
| WebSocket leaks | Implement proper disconnect cleanup |
| Stack traces leak | Log server-side, return safe error messages |
