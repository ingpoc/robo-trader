# Web Models Directory Guidelines

> **Scope**: Applies to `src/web/models/` directory. Read `src/web/CLAUDE.md` for context.

## Purpose

The `models/` directory contains Pydantic models for web API request/response validation. Models define data structures for HTTP requests and responses in the web layer.

## Architecture Pattern

### Pydantic Model Pattern

Models use Pydantic `BaseModel` for request/response validation. Models provide automatic validation, serialization, and documentation.

### Directory Structure

```
models/
└── trade_request.py    # Trade request/response models
```

## Rules

### ✅ DO

- ✅ Use Pydantic `BaseModel` for models
- ✅ Use `Field` for field validation
- ✅ Provide default values where appropriate
- ✅ Document model fields
- ✅ Use type hints
- ✅ Implement example values

### ❌ DON'T

- ❌ Skip field validation
- ❌ Use mutable default values
- ❌ Mix business logic with models
- ❌ Skip type hints
- ❌ Omit example values

## Model Pattern

```python
from pydantic import BaseModel, Field
from typing import Optional

class BuyTradeRequest(BaseModel):
    """Validated buy trade request."""
    
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    quantity: int = Field(..., gt=0, le=10000, description="Number of shares")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    
    class Config:
        example = {
            "symbol": "AAPL",
            "quantity": 10,
            "order_type": "MARKET",
            "price": None
        }
```

## Request Model Pattern

```python
from pydantic import BaseModel, Field

class BuyTradeRequest(BaseModel):
    """Buy trade request model."""
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., gt=0, description="Share quantity")
```

## Response Model Pattern

```python
from pydantic import BaseModel

class TradeResponse(BaseModel):
    """Trade response model."""
    trade_id: str
    status: str
    symbol: str
    quantity: int
    price: float
    timestamp: str
```

## Field Validation

```python
from pydantic import BaseModel, Field, validator

class BuyTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: int = Field(..., gt=0, le=10000)
    price: Optional[float] = Field(None, gt=0)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate stock symbol."""
        if not v.isalpha():
            raise ValueError('Symbol must be alphabetic')
        return v.upper()
```

## Example Values

```python
class BuyTradeRequest(BaseModel):
    symbol: str
    quantity: int
    
    class Config:
        example = {
            "symbol": "AAPL",
            "quantity": 10
        }
```

## Dependencies

Model components depend on:
- `Pydantic` - For model validation
- `typing` - For type hints
- `FastAPI` - For integration with FastAPI routes

## Testing

Test models:

```python
import pytest
from src.web.models.trade_request import BuyTradeRequest

def test_buy_trade_request():
    """Test buy trade request model."""
    request = BuyTradeRequest(
        symbol="AAPL",
        quantity=10,
        order_type="MARKET"
    )
    
    assert request.symbol == "AAPL"
    assert request.quantity == 10
    assert request.order_type == "MARKET"

def test_buy_trade_request_validation():
    """Test buy trade request validation."""
    with pytest.raises(ValueError):
        BuyTradeRequest(symbol="AAPL", quantity=-1)
```

## Maintenance

When adding new models:

1. Create Pydantic `BaseModel`
2. Add field validation
3. Provide example values
4. Document model fields
5. Update this CLAUDE.md file

