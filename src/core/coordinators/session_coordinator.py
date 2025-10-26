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
        self._broadcast_coordinator = None

    async def initialize(self) -> None:
        """Initialize session coordinator."""
        self._log_info("Initializing SessionCoordinator")
        self._initialized = True

    def set_broadcast_coordinator(self, broadcast_coordinator) -> None:
        """Set broadcast coordinator for UI updates."""
        self._broadcast_coordinator = broadcast_coordinator
        self._log_info("Broadcast coordinator set for status updates")

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
        # Always refresh authentication status first
        if not self.claude_sdk_status:
            await self.validate_authentication()

        # Check if we have a valid authentication status
        if self.claude_sdk_status and self.claude_sdk_status.is_valid:
            # Check if SDK client is actually connected to CLI process
            is_connected = False
            if self.client and hasattr(self.client, '_transport') and hasattr(self.client, '_query'):
                is_connected = (
                    self.client._transport is not None and
                    self.client._query is not None and
                    hasattr(self.client._transport, 'is_ready') and
                    self.client._transport.is_ready()
                )

            # Update the status with actual connection state
            self.claude_sdk_status = ClaudeAuthStatus(
                is_valid=True,  # Authentication is valid, connection state separate
                api_key_present=self.claude_sdk_status.api_key_present,
                account_info={
                    **self.claude_sdk_status.account_info,
                    "sdk_connected": is_connected,
                    "cli_process_running": is_connected
                },
                checked_at=self.claude_sdk_status.checked_at,
                rate_limit_info=self.claude_sdk_status.rate_limit_info
            )

            # Broadcast status update to UI via broadcast coordinator
            if hasattr(self, '_broadcast_coordinator') and self._broadcast_coordinator:
                from datetime import datetime, timezone
                status_data = {
                    "status": "connected/idle" if is_connected else "authenticated",
                    "auth_method": self.claude_sdk_status.account_info.get("auth_method"),
                    "sdk_connected": is_connected,
                    "cli_process_running": is_connected,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "account_info": self.claude_sdk_status.account_info
                }
                await self._broadcast_coordinator.broadcast_claude_status_update(status_data)
        else:
            # Not authenticated - broadcast offline status
            if hasattr(self, '_broadcast_coordinator') and self._broadcast_coordinator:
                from datetime import datetime, timezone
                status_data = {
                    "status": "disconnected",
                    "auth_method": "none",
                    "sdk_connected": False,
                    "cli_process_running": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "account_info": {"error": "Not authenticated"}
                }
                await self._broadcast_coordinator.broadcast_claude_status_update(status_data)

        return self.claude_sdk_status

    def get_client(self) -> Optional[ClaudeSDKClient]:
        """Get the active Claude SDK client."""
        return self.client

    async def cleanup(self) -> None:
        """Cleanup session coordinator resources."""
        await self.end_session()
        self._log_info("SessionCoordinator cleanup complete")
