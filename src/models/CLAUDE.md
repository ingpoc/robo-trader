# Models Directory Guidelines

> **Scope**: Applies to `src/models/` directory. Read `src/CLAUDE.md` for context.
>
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference + Explanation
>
> **Read in this order**:
> 1. `src/CLAUDE.md` - Backend architecture overview
> 2. This file - Model patterns and best practices
> 3. `src/services/CLAUDE.md` - How models are used in services

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

## Data Serialization Pattern (CRITICAL)

### Problem: String vs Dict Serialization Mismatch

**Symptoms**:
- Error: `'str' object has no attribute 'keys'` when accessing task payload
- Task created but processing fails when accessing nested data in payload
- Legacy database entries incompatible with new code

**Root Cause**:
Two-part issue:
1. **Storage Issue**: `str(dict)` creates Python dict string representation instead of JSON
2. **Deserialization Issue**: Deserialization code doesn't parse string back to dict

**Solution**:
```python
# Storage: Always use json.dumps() for proper JSON
payload_json = json.dumps(payload or {})  # ✅ Correct
# NOT: str(payload_json)  # ❌ Wrong - creates Python repr

# Deserialization: Implement fallback parsing with two levels
@staticmethod
def from_dict(data: Dict[str, Any]) -> 'SchedulerTask':
    """Create from dictionary with payload parsing."""
    if isinstance(data.get('payload'), str):
        payload_str = data['payload']
        if payload_str:
            try:
                # Level 1: Try JSON first (preferred format)
                data['payload'] = json.loads(payload_str)
            except (json.JSONDecodeError, ValueError):
                # Level 2: Fall back to Python literal eval for legacy format
                try:
                    data['payload'] = ast.literal_eval(payload_str)
                except (ValueError, SyntaxError):
                    # Level 3: Use empty dict if both fail
                    data['payload'] = {}
        else:
            data['payload'] = {}
    return SchedulerTask(**data)
```

**Key Points**:
1. ✅ Always use `json.dumps()` for JSON serialization
2. ✅ Implement 2-level fallback for backward compatibility
3. ✅ Level 1: `json.loads()` for new proper JSON format
4. ✅ Level 2: `ast.literal_eval()` for legacy Python dict strings
5. ✅ Level 3: Empty dict `{}` if both fail
6. ✅ Prevents "AttributeError: 'str' object has no attribute" errors

**Lessons Learned**:
- Storage must use `json.dumps()`, not `str()`
- Deserialization must handle both JSON and legacy formats
- This enables seamless migration of existing database entries
- Always test with real database data, not mocked dictionaries

## Best Practices

1. **Type Safety**: Always provide type hints
2. **Validation**: Include validation logic when needed
3. **Immutability**: Use frozen dataclasses when appropriate
4. **Serialization**: Always use `json.dumps()` for JSON, never `str(dict)` - see Data Serialization Pattern above
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

## Quick Fix Guide - Common Model Errors

**Error: `'str' object has no attribute 'keys'`**
- **Cause**: Payload stored as string, not parsed back to dict (see Data Serialization Pattern)
- **Fix**: Check `from_dict()` method implements 3-level fallback parsing (json.loads → ast.literal_eval → {})
- **Prevention**: Always use `json.dumps()` for storage, never `str(dict)`

**Error: `TypeError: missing required field 'X'`**
- **Cause**: Missing field in model instantiation
- **Fix**: Check all non-Optional fields have values, use Field(...) for Pydantic
- **Prevention**: Provide type hints, use dataclass defaults properly

**Error: `ValueError: field must be positive`**
- **Cause**: Validation logic rejected value (Field(gt=0) in Pydantic)
- **Fix**: Check input values meet constraints before creating model
- **Prevention**: Document constraints in field docstrings

## Maintenance Instructions

**For Contributors**: This CLAUDE.md is a living document. When you:
- ✅ Add a new model type → Document pattern section
- ✅ Fix a model error → Add to Quick Fix Guide
- ✅ Change serialization logic → Update Data Serialization Pattern
- ✅ Change best practices → Update Best Practices section
- ⚠️ Update this file → Run your changes through prompt optimizer tool
- ⚠️ Share improvements → Commit alongside code changes so team benefits

**Last Review**: 2025-11-22

