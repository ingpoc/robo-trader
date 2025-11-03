# Models Directory Guidelines

> **Scope**: Applies to `src/models/` directory. Read `src/CLAUDE.md` for context.

## Purpose

The `models/` directory contains data models, schemas, and type definitions used throughout the application. These models provide type safety and data validation.

## Architecture Pattern

### Data Models and Schemas

Models in this directory represent:
- **Domain Models** - Business domain entities (trading, portfolio, market data)
- **API Schemas** - Request/response schemas for API endpoints
- **State Models** - Models for database state management
- **Event Models** - Models for event data

### Directory Structure

```
models/
├── __init__.py                # Model exports
├── paper_trading.py            # Paper trading models
├── market_data.py              # Market data models
├── claude_agent.py             # Claude agent models
└── scheduler.py                # Scheduler task models
```

## Rules

### ✅ DO

- ✅ Use dataclasses or Pydantic models
- ✅ Provide type hints for all fields
- ✅ Include validation logic when needed
- ✅ Use enums for fixed sets of values
- ✅ Keep models focused (one domain per file)
- ✅ Max 350 lines per model file
- ✅ Export models through `__init__.py`

### ❌ DON'T

- ❌ Mix multiple domains in one file
- ❌ Skip type hints
- ❌ Include business logic in models
- ❌ Exceed file size limits
- ❌ Create circular dependencies

## Model Pattern

Models should follow this pattern:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class Order:
    """Trading order model."""
    symbol: str
    quantity: float
    price: float
    order_type: str
    status: OrderStatus
    created_at: datetime
    executed_at: Optional[datetime] = None
    
    def validate(self) -> bool:
        """Validate order data."""
        if self.quantity <= 0:
            return False
        if self.price <= 0:
            return False
        return True
```

## Pydantic Pattern

For validation-heavy models, use Pydantic:

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime

class PortfolioPosition(BaseModel):
    """Portfolio position model with validation."""
    symbol: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    avg_price: float = Field(..., gt=0)
    updated_at: datetime
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v.isupper():
            raise ValueError('Symbol must be uppercase')
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

## Enum Pattern

Use enums for fixed sets of values:

```python
from enum import Enum

class QueueName(Enum):
    """Queue name enumeration."""
    PORTFOLIO_SYNC = "portfolio_sync"
    DATA_FETCHER = "data_fetcher"
    AI_ANALYSIS = "ai_analysis"

class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

## Best Practices

1. **Type Safety**: Always provide type hints
2. **Validation**: Include validation logic when needed
3. **Immutability**: Use frozen dataclasses when appropriate
4. **Serialization**: Implement JSON serialization methods
5. **Documentation**: Document model purpose and fields
6. **Consistency**: Follow consistent naming conventions
7. **Separation**: Keep models separate from business logic

## Model Exports

Export models through `__init__.py`:

```python
# models/__init__.py
from .paper_trading import Order, OrderStatus, Portfolio
from .market_data import MarketData, PriceQuote
from .scheduler import Task, TaskStatus, QueueName

__all__ = [
    'Order', 'OrderStatus', 'Portfolio',
    'MarketData', 'PriceQuote',
    'Task', 'TaskStatus', 'QueueName'
]
```

## Dependencies

Models typically depend on:
- Standard library (`dataclasses`, `enum`, `typing`)
- `pydantic` - For validation (optional)
- `datetime` - For timestamp fields

