"""
Claude API Authentication and Validation

Ensures the system has valid Claude API access and displays status.
"""

import os
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from anthropic import Anthropic, APIError, AuthenticationError
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


async def validate_claude_api(api_key: Optional[str] = None) -> ClaudeAuthStatus:
    """
    Validate Claude API access via API key OR Claude Pro subscription.
    
    The Claude Agent SDK uses Claude Code CLI which supports two auth methods:
    1. API key (ANTHROPIC_API_KEY environment variable)
    2. Claude Pro/Team subscription (browser session auth via Claude Code CLI)
    
    Args:
        api_key: Optional API key. If not provided, reads from environment.
    
    Returns:
        ClaudeAuthStatus with validation results
    """
    # Get API key from parameter or environment
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    
    # If no API key, check if Claude Code CLI is authenticated via subscription
    if not api_key:
        logger.debug("No ANTHROPIC_API_KEY found, checking Claude Code CLI subscription auth...")

        # Check if Claude Code CLI is installed and authenticated
        cli_status = await check_claude_code_cli_auth()
        if cli_status["authenticated"]:
            logger.info("✓ Claude Code CLI authenticated via subscription")
            rate_limit_info = cli_status.get("rate_limit_info", {})
            return ClaudeAuthStatus(
                is_valid=True,
                api_key_present=False,
                account_info={
                    "auth_method": "claude_code_cli",
                    "subscription": "active",
                    **cli_status
                },
                rate_limit_info=rate_limit_info
            )
        else:
            logger.debug("Neither API key nor Claude Code CLI subscription found")
            return ClaudeAuthStatus(
                is_valid=False,
                api_key_present=False,
                error="No Claude authentication found. Either set ANTHROPIC_API_KEY or ensure Claude Code CLI is authenticated with your Pro subscription."
            )
    
    # Validate API key
    logger.info("Validating Claude API key...")
    
    # Check if key format is valid (basic check)
    if not api_key.startswith("sk-ant-"):
        logger.error("Invalid Claude API key format")
        return ClaudeAuthStatus(
            is_valid=False,
            api_key_present=True,
            error="Invalid API key format. Must start with 'sk-ant-'"
        )
    
    # Validate by making a minimal API call
    try:
        client = Anthropic(api_key=api_key)
        
        # Test with a minimal request
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        
        logger.info("✓ Claude API key validated successfully")
        
        # Extract account info from response metadata if available
        account_info = {
            "auth_method": "api_key",
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }
        
        return ClaudeAuthStatus(
            is_valid=True,
            api_key_present=True,
            account_info=account_info
        )
        
    except AuthenticationError as e:
        logger.error(f"Claude API authentication failed: {e}")
        return ClaudeAuthStatus(
            is_valid=False,
            api_key_present=True,
            error=f"Authentication failed: {str(e)}. Check your API key."
        )
    
    except APIError as e:
        logger.error(f"Claude API error: {e}")
        return ClaudeAuthStatus(
            is_valid=False,
            api_key_present=True,
            error=f"API error: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error validating Claude API: {e}")
        return ClaudeAuthStatus(
            is_valid=False,
            api_key_present=True,
            error=f"Unexpected error: {str(e)}"
        )


async def check_claude_code_cli_auth() -> Dict[str, Any]:
    """
    Check if Claude Code CLI is installed and authenticated.
    
    The Claude Agent SDK runs through Claude Code CLI, which can be
    authenticated via Claude Pro subscription.
    
    Returns:
        {
            "authenticated": bool,
            "cli_installed": bool,
            "version": str | None,
            "user": str | None
        }
    """
    import subprocess
    
    try:
        # Check if claude CLI is installed and authenticated
        # The correct command is 'claude', not 'claude-code'
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.debug(f"Claude CLI version: {version}")
            
            # Test if authentication is working by attempting a minimal query
            test_result = subprocess.run(
                ["claude", "--print", "test"],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            # Parse the output for rate limit information
            output = test_result.stdout + test_result.stderr
            rate_limit_info = {}
            
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
            
            # Check if we got a response (even if it's a rate limit error)
            # Rate limit errors mean authentication is working
            if test_result.returncode == 0 or "limit" in output.lower():
                logger.debug("Claude CLI authenticated successfully")
                return {
                    "authenticated": True,
                    "cli_installed": True,
                    "version": version,
                    "user": "claude_subscriber",
                    "rate_limit_info": rate_limit_info
                }
            else:
                logger.debug(f"Claude CLI not authenticated: {test_result.stderr}")
                return {
                    "authenticated": False,
                    "cli_installed": True,
                    "version": version,
                    "user": None,
                    "rate_limit_info": {}
                }
            
    except FileNotFoundError:
        # claude CLI not found in PATH
        logger.debug("Claude CLI not found in PATH")
        return {
            "authenticated": False,
            "cli_installed": False,
            "version": None,
            "user": None
        }
    except subprocess.TimeoutExpired:
        logger.debug("Claude Code CLI check timed out")
        return {
            "authenticated": False,
            "cli_installed": True,
            "version": None,
            "user": None
        }
    except Exception as e:
        logger.debug(f"Claude Code CLI check failed: {e}")
        return {
            "authenticated": False,
            "cli_installed": False,
            "version": None,
            "user": None
        }


async def get_claude_status() -> ClaudeAuthStatus:
    """
    Get current Claude API status.
    
    Returns:
        ClaudeAuthStatus with current connection state
    """
    return await validate_claude_api()


def require_claude_api(func):
    """
    Decorator to require valid Claude API before function execution.
    
    Usage:
        @require_claude_api
        async def my_function():
            # Will only execute if Claude API is valid
            pass
    """
    async def wrapper(*args, **kwargs):
        status = await get_claude_status()
        if not status.is_valid:
            raise RuntimeError(
                f"Claude API not available: {status.error}. "
                "Set ANTHROPIC_API_KEY environment variable."
            )
        return await func(*args, **kwargs)
    
    return wrapper


# Cache status to avoid repeated API calls
_cached_status: Optional[ClaudeAuthStatus] = None
_cache_duration_seconds = 300  # 5 minutes


async def get_claude_status_cached() -> ClaudeAuthStatus:
    """Get Claude status with caching to reduce API calls."""
    global _cached_status
    
    if _cached_status is None:
        _cached_status = await validate_claude_api()
        return _cached_status
    
    # Check cache age
    from datetime import datetime
    cache_time = datetime.fromisoformat(_cached_status.checked_at)
    age_seconds = (datetime.now(timezone.utc) - cache_time).total_seconds()
    
    if age_seconds > _cache_duration_seconds:
        logger.debug("Claude status cache expired, refreshing")
        _cached_status = await validate_claude_api()
    
    return _cached_status


def invalidate_status_cache():
    """Invalidate the status cache to force refresh."""
    global _cached_status
    _cached_status = None
    logger.debug("Claude status cache invalidated")