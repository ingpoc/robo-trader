# Web Routes Directory Guidelines

> **Scope**: Applies to `src/web/routes/` directory. Read `src/web/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `web/routes/` directory contains FastAPI route definitions for HTTP endpoints. Routes handle request validation, delegate to coordinators/services, and return structured responses.

## Architecture Pattern

### Route Handlers

Routes in this directory:
- **Validate Requests** - Input validation before processing
- **Delegate to Coordinators** - Routes delegate to coordinators, not services directly
- **Return Structured Responses** - Consistent response format
- **Handle Errors** - Use error middleware for consistent error handling
- **Apply Rate Limiting** - All endpoints have rate limiting

### Route Pattern

Each route file should follow this pattern:

```python
from fastapi import APIRouter, Depends, Request
from src.core.di import DependencyContainer
from src.web.dependencies import get_container
from src.core.errors import TradingError

router = APIRouter(prefix="/api/domain", tags=["domain"])

@router.get("/endpoint")
async def get_endpoint(
    request: Request,
    container: DependencyContainer = Depends(get_container)
):
    """
    Endpoint description.
    
    Returns structured response.
    """
    try:
        # Get coordinator from container
        coordinator = await container.get("domain_coordinator")
        
        # Delegate to coordinator
        result = await coordinator.get_data()
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except TradingError as e:
        # TradingError is handled by middleware
        raise
    
    except Exception as e:
        # Wrap unexpected errors
        raise TradingError(
            f"Failed to get data: {str(e)}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM
        )
```

## Rules

### ✅ DO

- ✅ Use FastAPI routers with proper prefixes
- ✅ Validate request input with Pydantic models
- ✅ Delegate to coordinators (not services directly)
- ✅ Use dependency injection for container access
- ✅ Return structured responses
- ✅ Apply tags for API documentation
- ✅ Max 350 lines per route file

### ❌ DON'T

- ❌ Access services directly (use coordinators)
- ❌ Skip input validation
- ❌ Return unstructured responses
- ❌ Handle errors directly (use middleware)
- ❌ Skip rate limiting
- ❌ Exceed file size limits

## Request Validation Pattern

Use Pydantic models for validation:

```python
from pydantic import BaseModel, Field

class OrderRequest(BaseModel):
    """Order request model."""
    symbol: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    order_type: str = Field(..., regex="^(buy|sell)$")

@router.post("/orders")
async def create_order(
    request: OrderRequest,
    container: DependencyContainer = Depends(get_container)
):
    """Create trading order."""
    # Request is automatically validated by FastAPI
    coordinator = await container.get("portfolio_coordinator")
    result = await coordinator.create_order(
        symbol=request.symbol,
        quantity=request.quantity,
        order_type=request.order_type
    )
    return {"success": True, "data": result}
```

## Error Handling Pattern

Let middleware handle errors:

```python
@router.get("/data")
async def get_data(container: DependencyContainer = Depends(get_container)):
    """Get data."""
    coordinator = await container.get("data_coordinator")
    
    # TradingError is automatically handled by middleware
    result = await coordinator.get_data()
    
    return {"success": True, "data": result}
```

## Rate Limiting Pattern

Rate limiting is applied at router level:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/endpoint")
@limiter.limit("10/minute")  # Rate limit applied
async def get_endpoint(request: Request, ...):
    """Rate-limited endpoint."""
    pass
```

## Best Practices

1. **Validation**: Always validate input with Pydantic models
2. **Delegation**: Delegate to coordinators, not services
3. **Error Handling**: Let middleware handle errors
4. **Response Structure**: Return consistent response format
5. **Documentation**: Provide clear endpoint descriptions
6. **Rate Limiting**: Apply appropriate rate limits
7. **Tags**: Use tags for API documentation organization

## Dependencies

Routes depend on:
- `fastapi` - For route definitions
- `src/web/dependencies` - For container access
- `src/core/coordinators` - For business logic delegation
- `src/core/errors` - For error handling

