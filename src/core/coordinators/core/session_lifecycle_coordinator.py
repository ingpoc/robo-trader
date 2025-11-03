"""
Session Lifecycle Coordinator

Focused coordinator for session lifecycle management.
Extracted from SessionCoordinator for single responsibility.
"""

from typing import Optional

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from loguru import logger

from src.config import Config
from ....auth.claude_auth import ClaudeAuthStatus
from ...claude_sdk_client_manager import ClaudeSDKClientManager
from ..base_coordinator import BaseCoordinator


class SessionLifecycleCoordinator(BaseCoordinator):
    """
    Coordinates Claude SDK session lifecycle.
    
    Responsibilities:
    - Start/stop Claude SDK sessions
    - Manage client lifecycle
    - Track connection status
    """

    def __init__(self, config: Config, options: Optional[ClaudeAgentOptions] = None):
        super().__init__(config)
        self.options = options
        self.client: Optional[ClaudeSDKClient] = None

    async def initialize(self) -> None:
        """Initialize session lifecycle coordinator."""
        self._log_info("Initializing SessionLifecycleCoordinator")
        self._initialized = True

    def set_options(self, options: ClaudeAgentOptions) -> None:
        """Set Claude agent options."""
        self.options = options

    async def start_session(self, is_authenticated: bool) -> None:
        """
        Start an interactive session with Claude SDK.

        Args:
            is_authenticated: Whether authentication is valid
        """
        # Skip if not authenticated - allow graceful degradation
        if not is_authenticated:
            self._log_warning("Skipping Claude SDK session start - authentication unavailable")
            self._log_info("System will operate in paper trading mode without AI features")
            return

        if not self.options:
            raise RuntimeError("ClaudeAgentOptions not set. Initialize orchestrator first.")

        try:
            # Use client manager instead of direct creation
            client_manager = await ClaudeSDKClientManager.get_instance()
            self.client = await client_manager.get_client("trading", self.options)
            self._log_info("Claude SDK client initialized via manager")
        except Exception as e:
            self._log_error(f"Failed to initialize Claude SDK client: {e}", exc_info=True)
            self.client = None

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

    def get_client(self) -> Optional[ClaudeSDKClient]:
        """Get the active Claude SDK client."""
        return self.client

    def is_connected(self) -> bool:
        """Check if SDK client is connected to CLI process."""
        if not self.client:
            return False
        
        if not (hasattr(self.client, '_transport') and hasattr(self.client, '_query')):
            return False
        
        return (
            self.client._transport is not None and
            self.client._query is not None and
            hasattr(self.client._transport, 'is_ready') and
            self.client._transport.is_ready()
        )

    async def cleanup(self) -> None:
        """Cleanup session lifecycle coordinator resources."""
        await self.end_session()
        self._log_info("SessionLifecycleCoordinator cleanup complete")

