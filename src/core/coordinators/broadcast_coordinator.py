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

    async def broadcast_claude_status_update(self, status_data: Dict[str, Any]) -> None:
        """
        Broadcast Claude SDK status updates to UI.

        Args:
            status_data: Claude status information from session coordinator
        """
        message = {
            "type": "claude_status_update",
            "status": status_data.get("status", "unknown"),
            "auth_method": status_data.get("auth_method"),
            "sdk_connected": status_data.get("sdk_connected", False),
            "cli_process_running": status_data.get("cli_process_running", False),
            "timestamp": status_data.get("timestamp"),
            "data": status_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"Claude status broadcast: {status_data.get('status', 'unknown')}")

    async def broadcast_system_health_update(self, health_data: Dict[str, Any]) -> None:
        """
        Broadcast system health updates to UI.

        Args:
            health_data: System health information
        """
        message = {
            "type": "system_health_update",
            "components": health_data.get("components", {}),
            "status": health_data.get("status", "unknown"),
            "timestamp": health_data.get("timestamp"),
            "data": health_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"System health broadcast: {health_data.get('status', 'unknown')}")

    async def broadcast_queue_status_update(self, queue_data: Dict[str, Any]) -> None:
        """
        Broadcast queue status updates to UI.

        Args:
            queue_data: Queue status information
        """
        message = {
            "type": "queue_status_update",
            "queues": queue_data.get("queues", {}),
            "stats": queue_data.get("stats", {}),
            "timestamp": queue_data.get("timestamp"),
            "data": queue_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"Queue status broadcast: {len(queue_data.get('queues', {}))} queues")

    async def cleanup(self) -> None:
        """Cleanup broadcast coordinator resources."""
        self._broadcast_callback = None
        self._log_info("BroadcastCoordinator cleanup complete")
