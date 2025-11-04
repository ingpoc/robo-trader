"""
Session Authentication Coordinator

Focused coordinator for authentication logic.
Extracted from SessionCoordinator for single responsibility.
"""

from typing import Optional

from loguru import logger

from src.config import Config
from ....auth.claude_auth import ClaudeAuthStatus, validate_claude_sdk_auth
from ..base_coordinator import BaseCoordinator


class SessionAuthenticationCoordinator(BaseCoordinator):
    """
    Coordinates Claude SDK authentication.
    
    Responsibilities:
    - Validate Claude SDK authentication
    - Track authentication status
    - Handle authentication errors gracefully
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.claude_sdk_status: Optional[ClaudeAuthStatus] = None

    async def initialize(self) -> None:
        """Initialize session authentication coordinator."""
        self._log_info("Initializing SessionAuthenticationCoordinator")
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

    def get_auth_status(self) -> Optional[ClaudeAuthStatus]:
        """Get current authentication status."""
        return self.claude_sdk_status

    async def cleanup(self) -> None:
        """Cleanup session authentication coordinator resources."""
        self._log_info("SessionAuthenticationCoordinator cleanup complete")

