"""
Session Coordinator (Refactored)

Thin orchestrator that delegates to focused session coordinators.
Refactored from 196-line monolith into focused coordinators.
"""

from typing import Optional

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from loguru import logger

from src.config import Config
from ....auth.claude_auth import ClaudeAuthStatus
from ..base_coordinator import BaseCoordinator
from .session_authentication_coordinator import SessionAuthenticationCoordinator
from .session_lifecycle_coordinator import SessionLifecycleCoordinator


class SessionCoordinator(BaseCoordinator):
    """
    Coordinates Claude SDK session lifecycle.

    Responsibilities:
    - Orchestrate session operations from focused coordinators
    - Provide unified session API
    - Track authentication and connection status
    """

    def __init__(
        self,
        config: Config,
        options: Optional[ClaudeAgentOptions] = None
    ):
        super().__init__(config)
        self.options = options
        
        # Focused coordinators
        self.auth_coordinator = SessionAuthenticationCoordinator(config)
        self.lifecycle_coordinator = SessionLifecycleCoordinator(config, options)
        self._broadcast_coordinator = None

    async def initialize(self) -> None:
        """Initialize session coordinator."""
        self._log_info("Initializing SessionCoordinator")
        
        await self.auth_coordinator.initialize()
        await self.lifecycle_coordinator.initialize()
        
        self._initialized = True

    def set_broadcast_coordinator(self, broadcast_coordinator) -> None:
        """Set broadcast coordinator for UI updates."""
        self._broadcast_coordinator = broadcast_coordinator
        self._log_info("Broadcast coordinator set for status updates")

    def set_options(self, options: ClaudeAgentOptions) -> None:
        """Set Claude agent options."""
        self.options = options
        self.lifecycle_coordinator.set_options(options)

    async def validate_authentication(self) -> ClaudeAuthStatus:
        """Validate Claude Agent SDK authentication."""
        return await self.auth_coordinator.validate_authentication()

    def is_authenticated(self) -> bool:
        """Check if Claude SDK authentication is valid and ready."""
        return self.auth_coordinator.is_authenticated()

    async def start_session(self) -> None:
        """Start an interactive session with Claude SDK."""
        await self.lifecycle_coordinator.start_session(self.is_authenticated())

    async def end_session(self) -> None:
        """End the current session and cleanup resources."""
        await self.lifecycle_coordinator.end_session()

    async def get_claude_status(self) -> Optional[ClaudeAuthStatus]:
        """Get current Claude Agent SDK status."""
        # Always refresh authentication status first
        if not self.auth_coordinator.get_auth_status():
            await self.validate_authentication()

        status = self.auth_coordinator.get_auth_status()
        
        # Check if we have a valid authentication status
        if status and status.is_valid:
            # Check if SDK client is actually connected to CLI process
            is_connected = self.lifecycle_coordinator.is_connected()

            # Update the status with actual connection state
            status = ClaudeAuthStatus(
                is_valid=True,
                api_key_present=status.api_key_present,
                account_info={
                    **status.account_info,
                    "sdk_connected": is_connected,
                    "cli_process_running": is_connected
                },
                checked_at=status.checked_at,
                rate_limit_info=status.rate_limit_info
            )

            # Broadcast status update to UI via broadcast coordinator
            if self._broadcast_coordinator:
                from datetime import datetime, timezone
                status_data = {
                    "status": "connected/idle" if is_connected else "authenticated",
                    "auth_method": status.account_info.get("auth_method"),
                    "sdk_connected": is_connected,
                    "cli_process_running": is_connected,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "account_info": status.account_info
                }
                await self._broadcast_coordinator.broadcast_claude_status_update(status_data)
        else:
            # Not authenticated - broadcast offline status
            if self._broadcast_coordinator:
                status_data = {
                    "status": "disconnected",
                    "auth_method": "none",
                    "sdk_connected": False,
                    "cli_process_running": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "account_info": {"error": "Not authenticated"}
                }
                await self._broadcast_coordinator.broadcast_claude_status_update(status_data)

        return status

    def get_client(self) -> Optional[ClaudeSDKClient]:
        """Get the active Claude SDK client."""
        return self.lifecycle_coordinator.get_client()

    async def cleanup(self) -> None:
        """Cleanup session coordinator resources."""
        await self.lifecycle_coordinator.cleanup()
        await self.auth_coordinator.cleanup()
        self._log_info("SessionCoordinator cleanup complete")
