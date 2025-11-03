# Web Utils Directory Guidelines

> **Scope**: Applies to `src/web/utils/` directory. Read `src/web/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `web/utils/` directory contains utility functions and helpers for the web layer. These utilities provide common functionality for HTTP handling, WebSocket management, and response formatting.

## Architecture Pattern

### Utility Functions

Utilities in this directory provide:
- **HTTP Helpers** - Request/response utilities
- **WebSocket Helpers** - WebSocket connection utilities
- **Response Formatting** - Standardized response formatting
- **Validation Helpers** - Request validation utilities

## Rules

### ✅ DO

- ✅ Keep utilities focused (one responsibility per utility)
- ✅ Use async operations when appropriate
- ✅ Provide clear function documentation
- ✅ Handle errors gracefully
- ✅ Max 350 lines per utility file
- ✅ Export utilities through `__init__.py`

### ❌ DON'T

- ❌ Mix multiple responsibilities in one utility
- ❌ Skip error handling
- ❌ Block on I/O operations
- ❌ Exceed file size limits
- ❌ Include business logic in utilities

## Utility Pattern

Each utility should follow this pattern:

```python
from typing import Dict, Any
from fastapi import Request

async def format_response(
    data: Any,
    success: bool = True,
    message: str = None
) -> Dict[str, Any]:
    """
    Format API response.
    
    Args:
        data: Response data
        success: Whether operation succeeded
        message: Optional message
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "success": success,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if message:
        response["message"] = message
    
    return response

async def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    return request.client.host if request.client else "unknown"
```

## Best Practices

1. **Single Responsibility**: Each utility function has one clear purpose
2. **Async When Needed**: Use async for I/O operations
3. **Documentation**: Document function purpose and parameters
4. **Error Handling**: Handle errors gracefully
5. **Type Hints**: Provide type hints for all functions
6. **Reusability**: Design utilities for reuse across routes
7. **Testing**: Utilities should be easily testable

## Dependencies

Utilities typically depend on:
- `fastapi` - For request/response handling
- `datetime` - For timestamp generation
- `typing` - For type hints

