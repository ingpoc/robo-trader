"""
Authentication module for Robo Trader.

Handles:
- Claude API authentication
- Web UI authentication (future)
- Zerodha OAuth (future)
"""

from .claude_auth import (ClaudeAuthStatus, get_claude_sdk_status,
                          get_claude_sdk_status_cached,
                          invalidate_status_cache, require_claude_api,
                          validate_claude_sdk_auth)

__all__ = [
    "validate_claude_sdk_auth",
    "get_claude_sdk_status",
    "get_claude_sdk_status_cached",
    "ClaudeAuthStatus",
    "require_claude_api",
    "invalidate_status_cache",
]
