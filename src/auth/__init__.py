"""
Authentication module for Robo Trader.

Handles:
- Claude API authentication
- Web UI authentication (future)
- Zerodha OAuth (future)
"""

from .claude_auth import validate_claude_api, get_claude_status

__all__ = ["validate_claude_api", "get_claude_status"]