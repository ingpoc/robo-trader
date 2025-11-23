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

## Common Issues

| Issue | Fix |
|-------|-----|
| "database is locked" | Use locked state methods |
| Pydantic validation fails | Check `pattern=`, `gt=`, `le=` constraints |
| Pages freeze | Use locked methods in endpoints |
| WebSocket leaks | Implement proper disconnect cleanup |
| Stack traces leak | Log server-side, return safe error messages |
