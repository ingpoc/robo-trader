# Authentication Directory Guidelines

> **Scope**: Applies to `src/auth/` directory. Read `src/CLAUDE.md` and `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `auth/` directory contains Claude Agent SDK authentication logic. This directory manages authentication validation and status tracking for the Claude Code CLI integration.

## Architecture Pattern

### Claude Code CLI Authentication

The authentication system validates Claude Code CLI setup:
- **No API Keys**: Authentication uses Claude Code CLI only (no API keys)
- **Graceful Degradation**: System continues in degraded mode if auth unavailable
- **Status Tracking**: Tracks authentication status and account info

### Authentication Flow

```python
from src.auth.claude_auth import validate_claude_sdk_auth, ClaudeAuthStatus

# Validate authentication (non-blocking, graceful)
status = await validate_claude_sdk_auth()

if status.is_valid:
    # System can use AI features
    pass
else:
    # System continues in paper trading mode without AI
    pass
```

## Files

### `claude_auth.py`

Provides authentication validation:
- `validate_claude_sdk_auth()` - Validates Claude SDK authentication
- `ClaudeAuthStatus` - Status dataclass with validation results

## Rules

### ✅ DO

- ✅ Handle auth failures gracefully (don't raise exceptions)
- ✅ Return structured status objects
- ✅ Log authentication status
- ✅ Allow system to continue in degraded mode
- ✅ Track account information when available
- ✅ Max 350 lines per file

### ❌ DON'T

- ❌ Raise exceptions on auth failure
- ❌ Block system startup if auth unavailable
- ❌ Use API keys (Claude Code CLI only)
- ❌ Cache authentication state indefinitely
- ❌ Expose sensitive authentication details

## Integration Pattern

Authentication is used by `SessionCoordinator`:

```python
from src.auth.claude_auth import validate_claude_sdk_auth

class SessionCoordinator:
    async def validate_authentication(self) -> ClaudeAuthStatus:
        """Validate authentication (non-blocking)."""
        status = await validate_claude_sdk_auth()
        
        if not status.is_valid:
            self._log_warning("Authentication unavailable - degraded mode")
            # DO NOT RAISE - allow system to continue
        
        return status
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

## Best Practices

1. **Graceful Degradation**: System continues without AI if auth fails
2. **Non-Blocking**: Never block system startup for auth
3. **Status Tracking**: Track auth status for UI display
4. **Security**: Never expose sensitive authentication details
5. **Validation**: Regularly validate authentication status

