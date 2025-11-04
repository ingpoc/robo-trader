"""
Broadcast Coordinator (Refactored)

Thin orchestrator that delegates to focused broadcast coordinators.
Refactored from 326-line monolith into focused coordinators.
"""

from typing import Dict, Any, Optional, Callable

from loguru import logger

from src.config import Config
from ..base_coordinator import BaseCoordinator
from .broadcast_health_coordinator import BroadcastHealthCoordinator
from .broadcast_execution_coordinator import BroadcastExecutionCoordinator


class BroadcastCoordinator(BaseCoordinator):
    """
    Coordinates UI broadcasting with health monitoring.

    Responsibilities:
    - Orchestrate broadcast operations from focused coordinators
    - Provide unified broadcast API
    - Track broadcast metrics
    """

    def __init__(self, config: Config):
        super().__init__(config)
        
        # Focused coordinators
        self.health_coordinator = BroadcastHealthCoordinator(config)
        self.execution_coordinator = BroadcastExecutionCoordinator(config, self.health_coordinator)

    async def initialize(self) -> None:
        """Initialize broadcast coordinator."""
        self._log_info("Initializing BroadcastCoordinator")

        await self.health_coordinator.initialize()
        await self.execution_coordinator.initialize()

        self._initialized = True

    def set_broadcast_callback(self, callback: Callable) -> None:
        """Set the broadcast callback function."""
        self.execution_coordinator.set_broadcast_callback(callback)

    async def broadcast_to_ui(self, message: Dict[str, Any]) -> bool:
        """Broadcast message to all connected WebSocket clients."""
        result = await self.execution_coordinator.broadcast_to_ui(
            message,
            self.health_coordinator.is_circuit_breaker_open
        )
        
        # Record metrics based on result
        if result:
            # Get broadcast time from message if available, otherwise use 0
            broadcast_time = message.get('_broadcast_time', 0.0)
            self.health_coordinator.record_broadcast_success(broadcast_time)
        else:
            # Create a generic error for metrics
            class BroadcastError(Exception):
                pass
            self.health_coordinator.record_broadcast_failure(BroadcastError("Broadcast failed"))
        
        return result

    async def broadcast_claude_status_update(self, status_data: Dict[str, Any]) -> None:
        """Broadcast Claude SDK status updates to UI."""
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
        """Broadcast system health updates to UI."""
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
        """Broadcast queue status updates to UI."""
        message = {
            "type": "queue_status_update",
            "queues": queue_data.get("queues", {}),
            "stats": queue_data.get("stats", {}),
            "timestamp": queue_data.get("timestamp"),
            "data": queue_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"Queue status broadcast: {len(queue_data.get('queues', {}))} queues")

    def get_health_metrics(self, monitor_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        return self.health_coordinator.get_health_metrics(monitor_metrics)

    async def cleanup(self) -> None:
        """Cleanup broadcast coordinator resources."""
        self._log_info("Cleaning up BroadcastCoordinator")

        await self.execution_coordinator.cleanup()
        await self.health_coordinator.cleanup()

        final_metrics = self.get_health_metrics()
        self._log_info(f"BroadcastCoordinator cleanup complete. Final metrics: {final_metrics}")
