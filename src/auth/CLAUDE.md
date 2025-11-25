# Authentication - src/auth/

## Purpose
Claude Code CLI authentication for SDK integration (NO API keys).

## Files
| File | Purpose |
|------|---------|
| claude_auth.py | Auth validation & status tracking |

## Pattern
```python
from src.auth.claude_auth import validate_claude_sdk_auth

# Validate (non-blocking, graceful)
status = await validate_claude_sdk_auth()

if status.is_valid:
    # Use AI features
    pass
else:
    # Degraded mode (no AI)
    pass
```

## Status Structure
```python
@dataclass
class ClaudeAuthStatus:
    is_valid: bool
    api_key_present: bool
    account_info: Dict[str, Any]
    checked_at: datetime
    rate_limit_info: Optional[Dict] = None
```

## Rules
| Rule | Requirement |
|------|-------------|
| Errors | Handle gracefully, DON'T raise |
| Startup | Never block startup for auth |
| Degradation | Continue without AI if unavailable |
| Caching | No indefinite caching |
| Security | Never expose sensitive details |

