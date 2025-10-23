"""
Broadcast Coordinator

Manages broadcasting messages to WebSocket clients.
Extracted from RoboTraderOrchestrator lines 592-594.
"""

from typing import Dict, Any, Optional, Callable

from loguru import logger

from src.config import Config
from .base_coordinator import BaseCoordinator


class BroadcastCoordinator(BaseCoordinator):
    """
    Coordinates UI broadcasting.

    Responsibilities:
    - Broadcast messages to WebSocket clients
    - Track broadcast callback
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self._broadcast_callback: Optional[Callable] = None

    async def initialize(self) -> None:
        """Initialize broadcast coordinator."""
        self._log_info("Initializing BroadcastCoordinator")
        self._initialized = True

    def set_broadcast_callback(self, callback: Callable) -> None:
        """
        Set the broadcast callback function.

        Args:
            callback: Async function to call for broadcasting
        """
        self._broadcast_callback = callback
        self._log_info("Broadcast callback registered")

    async def broadcast_to_ui(self, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all connected WebSocket clients.

        Args:
            message: Message dict to broadcast
        """
        if not self._broadcast_callback:
            self._log_warning("Broadcast callback not set - message not sent")
            return

        message_type = message.get('type', 'unknown')
        self._log_info(f"UI Broadcast: {message_type}")

        try:
            await self._broadcast_callback(message)
        except Exception as e:
            self._log_error(f"Failed to broadcast message: {e}", exc_info=True)

    async def cleanup(self) -> None:
        """Cleanup broadcast coordinator resources."""
        self._broadcast_callback = None
        self._log_info("BroadcastCoordinator cleanup complete")
