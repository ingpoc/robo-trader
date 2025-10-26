"""
Claude Agent SDK Authentication and Validation

Ensures the system has valid Claude Agent SDK access and displays status.
SDK uses Claude Code CLI for authentication, no direct API keys needed.
"""

import os
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from loguru import logger


class ClaudeAuthStatus:
    """Claude API authentication status."""
    
    def __init__(
        self,
        is_valid: bool,
        api_key_present: bool,
        error: Optional[str] = None,
        account_info: Optional[Dict[str, Any]] = None,
        checked_at: Optional[str] = None,
        rate_limit_info: Optional[Dict[str, Any]] = None
    ):
        self.is_valid = is_valid
        self.api_key_present = api_key_present
        self.error = error
        self.account_info = account_info or {}
        self.checked_at = checked_at or datetime.now(timezone.utc).isoformat()
        self.rate_limit_info = rate_limit_info or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "api_key_present": self.api_key_present,
            "error": self.error,
            "account_info": self.account_info,
            "checked_at": self.checked_at,
            "status": "connected" if self.is_valid else "disconnected",
            "rate_limit_info": self.rate_limit_info
        }


async def validate_claude_sdk_auth() -> ClaudeAuthStatus:
    """
    Validate Claude Agent SDK authentication.

    The Claude Agent SDK uses Claude Code CLI for authentication, NOT direct API calls.
    The SDK communicates with the 'claude' CLI command, which handles auth internally.

    Authentication method:
    - Claude Code CLI authentication (uses Claude subscription or OAuth)

    Returns:
        ClaudeAuthStatus with validation results
    """
    cli_status = await check_claude_code_cli_auth()
    if cli_status["authenticated"]:
        auth_method = cli_status.get("auth_method", "subscription")
        logger.info(f"✓ Claude Agent SDK authenticated via Claude Code CLI ({auth_method})")
        rate_limit_info = cli_status.get("rate_limit_info", {})

        return ClaudeAuthStatus(
            is_valid=True,
            api_key_present=False,
            account_info={
                "auth_method": f"claude_code_cli_{auth_method}",
                "subscription": "active" if auth_method == "subscription" else "oauth",
                "note": "SDK uses CLI authentication only",
                **cli_status
            },
            rate_limit_info=rate_limit_info
        )

    logger.error("Claude Agent SDK not authenticated - Claude Code CLI not available")
    return ClaudeAuthStatus(
        is_valid=False,
        api_key_present=False,
        error=(
            "Claude Agent SDK not authenticated. To enable AI features:\n"
            "1. Install Claude Code: https://docs.anthropic.com/claude/docs/desktop-setup\n"
            "2. Run: claude auth login\n"
            "3. Follow browser authentication flow\n"
            "4. Restart the application"
        )
    )


async def check_claude_code_cli_auth() -> Dict[str, Any]:
    """
    Check if Claude Code CLI is installed and authenticated.

    The Claude Agent SDK runs through Claude Code CLI, which can be
    authenticated via Claude Pro subscription or OAuth token.

    Returns:
        {
            "authenticated": bool,
            "cli_installed": bool,
            "version": str | None,
            "user": str | None,
            "auth_method": str | None
        }
    """
    import asyncio
    import os

    # Check if ANTHROPIC_API_KEY with OAuth token is set
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key.startswith("sk-ant-oat"):
        logger.debug("OAuth token (sk-ant-oat*) found in ANTHROPIC_API_KEY")
        return {
            "authenticated": True,
            "cli_installed": True,
            "version": "oauth_token",
            "user": "oauth_user",
            "auth_method": "oauth_token",
            "rate_limit_info": {"limited": False}
        }

    try:
        # Check if claude CLI is installed and authenticated (non-blocking)
        # The correct command is 'claude', not 'claude-code'
        process = await asyncio.create_subprocess_exec(
            "claude", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=2.0)
            result_code = process.returncode
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.debug("Claude CLI version check timed out")
            return {
                "authenticated": False,
                "cli_installed": True,
                "version": None,
                "user": None,
                "auth_method": None
            }

        if result_code == 0:
            version = stdout.decode().strip()
            logger.debug(f"Claude CLI version: {version}")

            # Test if authentication is working by attempting a simple text input
            # Claude Code 2.0+ responds to any input if authenticated
            # Use echo to pipe input instead of --print which is for file operations
            test_process = await asyncio.create_subprocess_exec(
                "bash", "-c", "echo 'test' | claude",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                test_stdout, test_stderr = await asyncio.wait_for(test_process.communicate(), timeout=10.0)
                test_result_code = test_process.returncode
            except asyncio.TimeoutError:
                test_process.kill()
                await test_process.wait()
                logger.debug("Claude CLI auth test timed out")
                return {
                    "authenticated": False,
                    "cli_installed": True,
                    "version": version,
                    "user": None,
                    "auth_method": None,
                    "rate_limit_info": {}
                }

            # Parse the output for rate limit information
            output = test_stdout.decode() + test_stderr.decode()
            rate_limit_info = {}

            # Check if response contains Claude's output (indicating auth success)
            # Authentication is successful if:
            # 1. Return code is 0 (success), OR
            # 2. Output contains Claude's response (even if it's a rate limit message)
            is_authenticated = False

            # Look for Claude's response patterns
            claude_indicators = [
                "I'm ready to help",
                "I can help",
                "I'm Claude",
                "I'm here to help",
                "limit reached",
                "usage limit",
                "rate limit",
                "weekly limit",
                "daily limit"
            ]

            if any(indicator.lower() in output.lower() for indicator in claude_indicators):
                is_authenticated = True
                logger.debug("Claude CLI authentication confirmed via response")
            elif test_result_code == 0 and output.strip():
                is_authenticated = True
                logger.debug("Claude CLI authentication confirmed via return code")

            if "limit" in output.lower():
                # Extract rate limit details
                if "weekly limit reached" in output.lower():
                    rate_limit_info["limited"] = True
                    rate_limit_info["type"] = "weekly"
                    # Try to extract reset time
                    import re
                    reset_match = re.search(r'resets\s+(\d+:\d+\s*[ap]m)', output, re.IGNORECASE)
                    if reset_match:
                        rate_limit_info["resets_at"] = reset_match.group(1)
                elif "daily limit" in output.lower():
                    rate_limit_info["limited"] = True
                    rate_limit_info["type"] = "daily"
                else:
                    rate_limit_info["limited"] = True
                    rate_limit_info["type"] = "unknown"
            else:
                rate_limit_info["limited"] = False

            if is_authenticated:
                auth_method = "subscription"
                logger.debug(f"Claude CLI authenticated successfully via {auth_method}")
                return {
                    "authenticated": True,
                    "cli_installed": True,
                    "version": version,
                    "user": "claude_user",
                    "auth_method": auth_method,
                    "rate_limit_info": rate_limit_info
                }
            else:
                logger.debug(f"Claude CLI not authenticated: {test_stderr.decode()}")
                return {
                    "authenticated": False,
                    "cli_installed": True,
                    "version": version,
                    "user": None,
                    "auth_method": None,
                    "rate_limit_info": {}
                }

    except FileNotFoundError:
        # claude CLI not found in PATH
        logger.debug("Claude CLI not found in PATH")
        return {
            "authenticated": False,
            "cli_installed": False,
            "version": None,
            "user": None,
            "auth_method": None
        }
    except Exception as e:
        logger.debug(f"Claude Code CLI check failed: {e}")
        return {
            "authenticated": False,
            "cli_installed": False,
            "version": None,
            "user": None,
            "auth_method": None
        }


async def get_claude_sdk_status() -> ClaudeAuthStatus:
    """
    Get current Claude Agent SDK status.

    Returns:
        ClaudeAuthStatus with current SDK connection state
    """
    return await validate_claude_sdk_auth()


def require_claude_api(func):
    """
    Decorator to require valid Claude authentication before function execution.

    Usage:
        @require_claude_api
        async def my_function():
            pass
    """
    async def wrapper(*args, **kwargs):
        status = await get_claude_status()
        if not status.is_valid:
            raise RuntimeError(
                f"Claude authentication failed: {status.error}"
            )
        return await func(*args, **kwargs)

    return wrapper


# Cache status to avoid repeated API calls
_cached_status: Optional[ClaudeAuthStatus] = None
_cache_duration_seconds = 300  # 5 minutes


async def get_claude_sdk_status_cached() -> ClaudeAuthStatus:
    """Get Claude Agent SDK status with caching to reduce CLI calls."""
    global _cached_status

    if _cached_status is None:
        _cached_status = await validate_claude_sdk_auth()
        return _cached_status

    # Check cache age
    from datetime import datetime
    cache_time = datetime.fromisoformat(_cached_status.checked_at)
    age_seconds = (datetime.now(timezone.utc) - cache_time).total_seconds()

    if age_seconds > _cache_duration_seconds:
        logger.debug("Claude SDK status cache expired, refreshing")
        _cached_status = await validate_claude_sdk_auth()

    return _cached_status


def invalidate_status_cache():
    """Invalidate the status cache to force refresh."""
    global _cached_status
    _cached_status = None
    logger.debug("Claude status cache invalidated")