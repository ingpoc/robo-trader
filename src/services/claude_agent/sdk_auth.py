"""
Claude Agent SDK Authentication Handler

Handles SDK-specific authentication requirements and validation.
Provides proper SDK authentication patterns instead of direct API usage.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

from ...core.di import DependencyContainer
from ...core.errors import ErrorCategory, ErrorSeverity, TradingError

logger = logging.getLogger(__name__)


class ClaudeSDKAuth:
    """
    Claude Agent SDK Authentication Handler

    Manages SDK authentication requirements:
    - Claude Code CLI authentication
    - OAuth token validation
    - SDK session management
    - Authentication state tracking
    """

    def __init__(self, container: DependencyContainer):
        """Initialize SDK authentication handler."""
        self.container = container
        self._auth_status = None
        self._last_check = None
        self._cache_duration = 300  # 5 minutes

    async def initialize(self) -> None:
        """Initialize authentication handler."""
        self._log_info("Initializing ClaudeSDKAuth")
        await self._validate_auth_setup()

    async def validate_auth(self) -> Dict[str, Any]:
        """
        Validate Claude Agent SDK authentication.

        Returns SDK-compliant authentication status.
        """
        # Check cache first
        if self._is_cache_valid():
            return self._auth_status

        try:
            # Check Claude Code CLI authentication
            cli_status = await self._check_claude_cli_auth()

            # Check OAuth token if CLI not available
            oauth_status = (
                await self._check_oauth_token()
                if not cli_status["authenticated"]
                else None
            )

            # Determine overall auth status
            if cli_status["authenticated"]:
                auth_method = "claude_code_cli"
                auth_details = cli_status
            elif oauth_status and oauth_status["valid"]:
                auth_method = "oauth_token"
                auth_details = oauth_status
            else:
                auth_method = None
                auth_details = {
                    "error": "No valid authentication method found",
                    "cli_status": cli_status,
                    "oauth_status": oauth_status,
                }

            # Build SDK auth status
            auth_status = {
                "authenticated": auth_method is not None,
                "auth_method": auth_method,
                "sdk_ready": auth_method is not None,
                "details": auth_details,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "sdk_requirements": {
                    "claude_code_cli": cli_status["installed"],
                    "oauth_token": oauth_status["valid"] if oauth_status else False,
                    "recommended_method": "claude_code_cli",
                },
            }

            # Cache the result
            self._auth_status = auth_status
            self._last_check = datetime.now(timezone.utc)

            self._log_info(f"SDK authentication validated: {auth_method or 'failed'}")
            return auth_status

        except Exception as e:
            self._log_error(f"SDK authentication validation failed: {e}")
            return {
                "authenticated": False,
                "auth_method": None,
                "sdk_ready": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    async def get_sdk_config(self) -> Dict[str, Any]:
        """
        Get SDK configuration for proper initialization.

        Returns configuration needed for SDK usage.
        """
        auth_status = await self.validate_auth()

        if not auth_status["authenticated"]:
            raise TradingError(
                f"SDK authentication failed: {auth_status.get('error', 'Unknown error')}",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False,
            )

        # Build SDK config based on auth method
        config = {
            "auth_method": auth_status["auth_method"],
            "sdk_ready": True,
            "session_config": {
                "auto_auth": True,
                "validate_on_start": True,
                "error_handling": "strict",
            },
        }

        if auth_status["auth_method"] == "claude_code_cli":
            config["cli_config"] = {
                "command": "claude",
                "timeout": 30,
                "working_directory": os.getcwd(),
            }
        elif auth_status["auth_method"] == "oauth_token":
            config["oauth_config"] = {
                "token_validation": True,
                "auto_refresh": False,  # SDK handles this
            }

        return config

    async def create_sdk_session(self) -> Dict[str, Any]:
        """
        Create a new SDK session with proper authentication.

        Returns session configuration for SDK usage.
        """
        config = await self.get_sdk_config()

        session_config = {
            **config,
            "session_id": f"sdk_session_{datetime.now(timezone.utc).timestamp()}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "capabilities": [
                "tool_execution",
                "multi_turn_conversation",
                "error_recovery",
            ],
        }

        self._log_info(f"Created SDK session: {session_config['session_id']}")
        return session_config

    async def _check_claude_cli_auth(self) -> Dict[str, Any]:
        """Check Claude Code CLI authentication status."""
        import asyncio

        try:
            # Check if CLI is installed
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=2.0)

            if process.returncode != 0:
                return {
                    "installed": False,
                    "authenticated": False,
                    "error": "CLI not found or not working",
                }

            version = stdout.decode().strip()

            # Test authentication with a minimal command
            test_process = await asyncio.create_subprocess_exec(
                "claude",
                "--print",
                "test",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            test_stdout, test_stderr = await asyncio.wait_for(
                test_process.communicate(), timeout=5.0
            )
            test_output = test_stdout.decode() + test_stderr.decode()

            authenticated = (
                test_process.returncode == 0 or "limit" in test_output.lower()
            )

            return {
                "installed": True,
                "authenticated": authenticated,
                "version": version,
                "rate_limited": "limit" in test_output.lower(),
                "error": None if authenticated else "CLI not authenticated",
            }

        except asyncio.TimeoutError:
            return {"installed": True, "authenticated": False, "error": "CLI timeout"}
        except FileNotFoundError:
            return {
                "installed": False,
                "authenticated": False,
                "error": "CLI not installed",
            }
        except Exception as e:
            return {"installed": False, "authenticated": False, "error": str(e)}

    async def _check_oauth_token(self) -> Dict[str, Any]:
        """Check OAuth token validity."""
        api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not api_key:
            return {
                "valid": False,
                "error": "No ANTHROPIC_API_KEY environment variable",
            }

        # Check if it's an OAuth token (starts with sk-ant-oat)
        if not api_key.startswith("sk-ant-oat"):
            return {"valid": False, "error": "Not an OAuth token format"}

        # Basic format validation (OAuth tokens are longer)
        if len(api_key) < 100:
            return {"valid": False, "error": "Token appears too short for OAuth format"}

        # For SDK usage, we trust the token format
        # The SDK will handle actual validation during API calls
        return {
            "valid": True,
            "token_type": "oauth",
            "masked_token": f"{api_key[:10]}...{api_key[-4:]}",
        }

    async def _validate_auth_setup(self) -> None:
        """Validate that authentication is properly configured."""
        # Check environment variables
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if (
            api_key
            and not api_key.startswith("sk-ant-oat")
            and api_key != "your_anthropic_api_key_here"
        ):
            self._log_warning(
                "ANTHROPIC_API_KEY found but not in OAuth format. "
                "SDK prefers Claude Code CLI authentication."
            )

        # Initial auth check
        auth_status = await self.validate_auth()
        if not auth_status["authenticated"]:
            self._log_warning(
                "No valid Claude authentication found. "
                "SDK will not function properly."
            )

    def _is_cache_valid(self) -> bool:
        """Check if cached auth status is still valid."""
        if not self._auth_status or not self._last_check:
            return False

        age = (datetime.now(timezone.utc) - self._last_check).total_seconds()
        return age < self._cache_duration

    def invalidate_cache(self) -> None:
        """Invalidate authentication cache."""
        self._auth_status = None
        self._last_check = None
        self._log_info("Authentication cache invalidated")

    def _log_info(self, message: str) -> None:
        """Log info message with service name."""
        logger.info(f"[ClaudeSDKAuth] {message}")

    def _log_error(self, message: str, exc_info: bool = False) -> None:
        """Log error message with service name."""
        logger.error(f"[ClaudeSDKAuth] {message}", exc_info=exc_info)

    def _log_warning(self, message: str) -> None:
        """Log warning message with service name."""
        logger.warning(f"[ClaudeSDKAuth] {message}")
