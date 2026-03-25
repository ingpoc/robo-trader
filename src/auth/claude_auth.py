"""
Claude Agent SDK Authentication and Validation

Ensures the system has valid Claude Agent SDK access and displays status.
SDK uses Claude Code CLI for authentication, no direct API keys needed.
"""

import asyncio
import json
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


def _extract_usage_limited_info(
    raw_text: Optional[str],
    *,
    error_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize temporary Claude quota failures into one structure."""
    message = (raw_text or "").strip()
    lowered = message.lower()
    if not (
        error_code == "rate_limit"
        or "out of extra usage" in lowered
        or "rate limit" in lowered
        or "spending cap reached" in lowered
        or "spending cap" in lowered
    ):
        return {}

    return {
        "status": "exhausted",
        "code": error_code or ("spending_cap" if "spending cap" in lowered else "rate_limit"),
        "message": message or "Claude usage is temporarily exhausted.",
    }


async def _probe_claude_sdk_runtime() -> Dict[str, Any]:
    """Probe the Claude SDK with a minimal request to detect usage exhaustion."""
    from claude_agent_sdk import ClaudeAgentOptions
    from src.core.claude_sdk_client_manager import ClaudeSDKClientManager

    manager = await ClaudeSDKClientManager.get_instance()
    options = ClaudeAgentOptions(
        allowed_tools=[],
        max_turns=1,
        system_prompt="Reply with OK.",
    )
    client_type = "auth_probe"
    client = None
    assistant_error_message = None

    try:
        client = await manager.get_client(client_type, options, force_recreate=True)
        await asyncio.wait_for(client.query("Reply with OK."), timeout=15.0)

        async for message in client.receive_response():
            if hasattr(message, "subtype") and message.subtype == "init":
                continue

            error_code = getattr(message, "error", None)
            text_fragments = []

            if hasattr(message, "content"):
                for content_block in message.content:
                    block_text = getattr(content_block, "text", None)
                    if block_text:
                        text_fragments.append(block_text)
            elif getattr(message, "result", None):
                text_fragments.append(str(message.result))
            elif hasattr(message, "text") and getattr(message, "text", None):
                text_fragments.append(message.text)

            error_text = "\n".join(fragment.strip() for fragment in text_fragments if fragment).strip()
            usage_limited_info = _extract_usage_limited_info(error_text, error_code=error_code)
            if usage_limited_info:
                return {
                    "sdk_authenticated": True,
                    "rate_limit_info": usage_limited_info,
                }

            if hasattr(message, "subtype") and message.subtype == "success" and getattr(message, "is_error", False):
                assistant_error_message = assistant_error_message or error_text or "Claude SDK session ended with error"
                usage_limited_info = _extract_usage_limited_info(assistant_error_message, error_code=error_code)
                if usage_limited_info:
                    return {
                        "sdk_authenticated": True,
                        "rate_limit_info": usage_limited_info,
                    }
                raise RuntimeError(assistant_error_message)

        return {
            "sdk_authenticated": True,
            "rate_limit_info": {},
        }
    finally:
        if client is not None:
            try:
                await manager.cleanup_client(client_type)
            except Exception as exc:
                logger.debug(f"Claude SDK auth probe cleanup failed: {exc}")


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

    The Claude Agent SDK runs through Claude Code CLI, which should be
    authenticated via `claude auth login` for subscription-based usage.

    Returns:
        {
            "authenticated": bool,
            "cli_installed": bool,
            "version": str | None,
            "user": str | None,
            "auth_method": str | None
        }
    """
    version = None
    auth_status = {}

    try:
        version_process = await asyncio.create_subprocess_exec(
            "claude", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(version_process.communicate(), timeout=2.0)
        if version_process.returncode != 0:
            return {
                "authenticated": False,
                "cli_installed": False,
                "version": None,
                "user": None,
                "auth_method": None,
                "rate_limit_info": {},
            }
        version = stdout.decode().strip()
    except FileNotFoundError:
        logger.debug("Claude CLI not found in PATH")
        return {
            "authenticated": False,
            "cli_installed": False,
            "version": None,
            "user": None,
            "auth_method": None,
            "rate_limit_info": {},
        }
    except Exception as exc:
        logger.debug(f"Claude CLI version check failed: {exc}")
        return {
            "authenticated": False,
            "cli_installed": False,
            "version": None,
            "user": None,
            "auth_method": None,
            "rate_limit_info": {},
        }

    try:
        status_process = await asyncio.create_subprocess_exec(
            "claude", "auth", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        status_stdout, _ = await asyncio.wait_for(status_process.communicate(), timeout=2.0)
        if status_stdout:
            auth_status = json.loads(status_stdout.decode())
    except Exception as exc:
        logger.debug(f"Claude auth status probe failed: {exc}")

    logged_in = bool(auth_status.get("loggedIn"))

    # Primary signal: can the real SDK client path execute a minimal request?
    try:
        sdk_probe = await _probe_claude_sdk_runtime()
        sdk_authenticated = bool(sdk_probe.get("sdk_authenticated"))
        rate_limit_info = sdk_probe.get("rate_limit_info", {}) or {}
    except Exception as exc:
        logger.debug(f"Claude SDK auth probe failed: {exc}")
        sdk_authenticated = False
        rate_limit_info = {}

    if sdk_authenticated or (logged_in and rate_limit_info.get("status") == "exhausted"):
        return {
            "authenticated": True,
            "cli_installed": True,
            "version": version,
            "user": auth_status.get("user"),
            "auth_method": auth_status.get("authMethod") or "sdk_available",
            "rate_limit_info": rate_limit_info or auth_status.get("rate_limit_info", {}),
        }

    return {
        "authenticated": logged_in,
        "cli_installed": True,
        "version": version,
        "user": auth_status.get("user"),
        "auth_method": auth_status.get("authMethod"),
        "rate_limit_info": rate_limit_info or auth_status.get("rate_limit_info", {}),
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
        status = await validate_claude_sdk_auth()
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


async def get_claude_status() -> ClaudeAuthStatus:
    """Backward-compatible alias for SDK status lookup."""
    return await get_claude_sdk_status()


async def get_claude_status_cached() -> ClaudeAuthStatus:
    """Backward-compatible alias for cached SDK status lookup."""
    return await get_claude_sdk_status_cached()


def invalidate_status_cache():
    """Invalidate the status cache to force refresh."""
    global _cached_status
    _cached_status = None
    logger.debug("Claude status cache invalidated")


def record_claude_runtime_limit(message: str, *, code: Optional[str] = None) -> None:
    """Update cached Claude status immediately when a live request hits a usage cap."""
    global _cached_status

    usage_limited_info = _extract_usage_limited_info(message, error_code=code)
    if not usage_limited_info:
        return

    account_info = _cached_status.account_info.copy() if _cached_status is not None else {}
    if "auth_method" not in account_info:
        account_info["auth_method"] = "claude_code_cli_sdk_available"

    _cached_status = ClaudeAuthStatus(
        is_valid=True,
        api_key_present=False,
        account_info=account_info,
        checked_at=datetime.now(timezone.utc).isoformat(),
        rate_limit_info=usage_limited_info,
    )
