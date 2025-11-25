# Web Utils - src/web/utils/

## Utility Pattern
```python
from typing import Dict, Any
from fastapi import Request
from datetime import datetime

async def format_response(
    data: Any,
    success: bool = True,
    message: str = None
) -> Dict[str, Any]:
    """Format API response."""
    response = {
        "success": success,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    if message:
        response["message"] = message
    return response

async def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    return request.client.host if request.client else "unknown"
```

## Rules
| Rule | Requirement |
|------|-------------|
| Responsibility | Single purpose per utility |
| Async | Use async for I/O operations |
| Documentation | Document purpose & parameters |
| Error handling | Handle gracefully, don't block |
| Type hints | Required on all functions |
| Max size | 350 lines per utility file |
| Testing | Design for testability |

## Exports
```python
# utils/__init__.py
from .response import format_response
from .request import get_client_ip

__all__ = ['format_response', 'get_client_ip']
```

