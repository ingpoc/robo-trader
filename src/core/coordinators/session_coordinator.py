"""
Session Coordinator

Manages Claude SDK client lifecycle, session start/stop, and authentication.
Extracted from RoboTraderOrchestrator lines 223-279, 659-661.
"""

import asyncio
from typing import Optional

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from loguru import logger

from src.config import Config
from ...auth.claude_auth import ClaudeAuthStatus, validate_claude_sdk_auth
from .base_coordinator import BaseCoordinator


class SessionCoordinator(BaseCoordinator):
    """
    Coordinates Claude SDK session lifecycle.

    Responsibilities:
    - Authenticate Claude API
    - Start/stop Claude SDK sessions
    - Manage client lifecycle
    - Track authentication status
    """

    def __init__(
        self,
        config: Config,
        options: Optional[ClaudeAgentOptions] = None
    ):
        super().__init__(config)
        self.options = options
        self.client: Optional[ClaudeSDKClient] = None
        self.claude_sdk_status: Optional[ClaudeAuthStatus] = None

    async def initialize(self) -> None:
        """Initialize session coordinator."""
        self._log_info("Initializing SessionCoordinator")
        self._initialized = True

    async def validate_authentication(self) -> ClaudeAuthStatus:
        """
        Validate Claude Agent SDK authentication (non-blocking, graceful degradation).

        Returns:
            ClaudeAuthStatus with validation results

        Note: This method does NOT raise exceptions on auth failure.
              It logs warnings and allows the system to continue in degraded mode.
        """
        self.claude_sdk_status = await validate_claude_sdk_auth()
        if not self.claude_sdk_status.is_valid:
            error_msg = f"Claude Agent SDK authentication unavailable: {self.claude_sdk_status.error}"
            self._log_warning(error_msg)
            self._log_warning("System will continue in paper trading mode without AI features")
            # DO NOT RAISE - allow system to continue with degraded functionality
        else:
            auth_method = self.claude_sdk_status.account_info.get('auth_method', 'unknown')
            self._log_info(f"Claude Agent SDK authenticated successfully via {auth_method}")

        return self.claude_sdk_status

    def is_authenticated(self) -> bool:
        """Check if Claude SDK authentication is valid and ready."""
        return (
            self.claude_sdk_status is not None
            and self.claude_sdk_status.is_valid
        )

    async def start_session(self) -> None:
        """
        Start an interactive session with Claude SDK (gracefully handles auth failures).

        For web applications, this maintains a long-lived client.
        For CLI applications, prefer using the session context manager.

        Note: If authentication is not available, this method logs a warning
        but does not raise an exception - the system continues in degraded mode.
        """
        # Skip if not authenticated - allow graceful degradation
        if not self.is_authenticated():
            self._log_warning("Skipping Claude SDK session start - authentication unavailable")
            self._log_info("System will operate in paper trading mode without AI features")
            return

        if not self.options:
            raise RuntimeError("ClaudeAgentOptions not set. Initialize orchestrator first.")

        try:
            self.client = ClaudeSDKClient(options=self.options)
            await self.client.__aenter__()
            self._log_info("Claude SDK client initialized successfully")
        except Exception as e:
            self._log_error(f"Failed to initialize Claude SDK client: {e}", exc_info=True)
            self.client = None
            self.claude_sdk_status = ClaudeAuthStatus(
                is_valid=False,
                api_key_present=False,
                account_info={
                    "auth_method": "failed",
                    "note": f"SDK initialization failed: {str(e)}"
                }
            )

    async def end_session(self) -> None:
        """End the current session and cleanup resources."""
        self._log_info("Ending session and cleaning up resources")

        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
                self._log_info("Client cleaned up successfully")
            except Exception as e:
                self._log_warning(f"Error during client cleanup: {e}")
            finally:
                self.client = None

    async def get_claude_status(self) -> Optional[ClaudeAuthStatus]:
        """Get current Claude Agent SDK status."""
        return self.claude_sdk_status

    def get_client(self) -> Optional[ClaudeSDKClient]:
        """Get the active Claude SDK client."""
        return self.client

    async def cleanup(self) -> None:
        """Cleanup session coordinator resources."""
        await self.end_session()
        self._log_info("SessionCoordinator cleanup complete")
