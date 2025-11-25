# Web Models - src/web/models/

## Pattern
```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class BuyTradeRequest(BaseModel):
    """Validated buy trade request."""
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: int = Field(..., gt=0, le=10000)
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")
    price: Optional[float] = Field(None, gt=0)

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalpha():
            raise ValueError('Symbol must be alphabetic')
        return v.upper()

    class Config:
        example = {
            "symbol": "AAPL",
            "quantity": 10,
            "order_type": "MARKET"
        }
```

## Rules
| Rule | Requirement |
|------|-------------|
| Base class | Pydantic BaseModel ONLY |
| Validation | Field(...) with constraints |
| Type hints | Required on all fields |
| Examples | Config.example with sample data |
| Patterns | Use pattern= for regex (Pydantic v2) |
| Logic | NO business logic, models only |
| Defaults | Provide sensible defaults |

## Field Constraints
- `Field(..., min_length=X, max_length=Y)` - String length
- `Field(..., gt=0, le=10000)` - Numeric range (gt, ge, lt, le)
- `Field(..., pattern="^regex$")` - Regex matching (v2)
- `Field(default=X)` - Default value
- `Optional[T]` - Nullable field

