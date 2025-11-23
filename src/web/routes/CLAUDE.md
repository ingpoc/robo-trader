# Web Routes - src/web/routes/

## Route Pattern
```python
from fastapi import APIRouter, Depends, Request
from src.core.di import DependencyContainer
from src.web.dependencies import get_container

router = APIRouter(prefix="/api/domain", tags=["domain"])

@router.get("/endpoint")
async def get_endpoint(request: Request, container = Depends(get_container)):
    try:
        coordinator = await container.get("domain_coordinator")
        result = await coordinator.get_data()
        return {"success": True, "data": result}
    except TradingError as e:
        raise  # Middleware handles TradingError
    except Exception as e:
        raise TradingError(f"Failed: {e}", category=ErrorCategory.SYSTEM)
```

## Request Validation
```python
class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    order_type: str = Field(..., pattern="^(buy|sell)$")
```

## Rate Limiting
```python
@limiter.limit("10/minute")
async def get_endpoint(request: Request):
    pass
```

## Rules
| Rule | Requirement |
|------|-------------|
| Validation | Use Pydantic models |
| Delegation | Routes → coordinators (NOT services) |
| Errors | Middleware handles, DON'T catch |
| Responses | {"success": true, "data": ...} |
| Max size | 350 lines per route file |
| Rate limiting | Apply @limiter.limit() |

## CRITICAL: Scheduler ID → Task Name Mapping
```python
processor_mapping = {
    "portfolio_sync_scheduler": "portfolio_sync",
    "portfolio_analysis_scheduler": "portfolio_analyzer",  # Map UI ID to DB name
    "ai_analysis_scheduler": "ai_analysis_scheduler"
}
```

