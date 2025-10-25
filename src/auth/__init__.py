"""
Authentication module for Robo Trader.

Handles:
- Claude API authentication
- Web UI authentication (future)
- Zerodha OAuth (future)
"""

from .claude_auth import validate_claude_sdk_auth, get_claude_sdk_status, get_claude_sdk_status_cached, ClaudeAuthStatus, require_claude_api, invalidate_status_cache

__all__ = ["validate_claude_sdk_auth", "get_claude_sdk_status", "get_claude_sdk_status_cached", "ClaudeAuthStatus", "require_claude_api", "invalidate_status_cache"]