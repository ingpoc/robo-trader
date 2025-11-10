"""
Broadcast Coordinator (Phase 3 Refactored)

Thin orchestrator that delegates to focused broadcast coordinators.
Uses repository layer for consistent data across WebSocket and REST API.
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

from loguru import logger

from src.config import Config
from src.models.dto import QueueStatusDTO
from ..base_coordinator import BaseCoordinator
from .broadcast_health_coordinator import BroadcastHealthCoordinator
from .broadcast_execution_coordinator import BroadcastExecutionCoordinator


class BroadcastCoordinator(BaseCoordinator):
    """
    Coordinates UI broadcasting with health monitoring.

    Phase 3 Update:
    - Uses QueueStateRepository for consistent data
    - Broadcasts unified DTOs (same schema as REST API)
    - Eliminates WebSocket vs REST format differences (fixes Issue #6)

    Responsibilities:
    - Orchestrate broadcast operations from focused coordinators
    - Provide unified broadcast API
    - Track broadcast metrics
    """

    def __init__(self, config: Config, queue_state_repository=None):
        """Initialize broadcast coordinator.

        Args:
            config: Application configuration
            queue_state_repository: QueueStateRepository for consistent data (Phase 3)
        """
        super().__init__(config)

        # Focused coordinators
        self.health_coordinator = BroadcastHealthCoordinator(config)
        self.execution_coordinator = BroadcastExecutionCoordinator(config, self.health_coordinator)

        # Phase 3: Repository for consistent data
        self.queue_state_repository = queue_state_repository

    async def initialize(self) -> None:
        """Initialize broadcast coordinator."""
        self._log_info("Initializing BroadcastCoordinator (Phase 3 - with repository)")

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
        self._log_debug(f"Claude status broadcast: {status_data.get('status', 'unknown')}")

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
        self._log_debug(f"System health broadcast: {health_data.get('status', 'unknown')}")

    async def broadcast_queue_status_update(self, queue_data: Dict[str, Any] = None) -> None:
        """Broadcast queue status updates to UI.

        Phase 3: Uses QueueStateRepository for consistent data.
        WebSocket message now has IDENTICAL schema to REST API response.

        Args:
            queue_data: Optional pre-fetched queue data (legacy support)
        """
        try:
            # Phase 3: Get fresh data from repository if available
            if self.queue_state_repository:
                # Get all queue statuses (efficient - 1-2 queries)
                all_queue_states = await self.queue_state_repository.get_all_statuses()
                summary = await self.queue_state_repository.get_queue_statistics_summary()

                # Convert to DTOs (same as REST API)
                queue_dtos = []
                for queue_name, queue_state in all_queue_states.items():
                    dto = QueueStatusDTO.from_queue_state(queue_state)
                    queue_dtos.append(dto.to_dict())

                # Build stats (same format as REST API)
                stats = {
                    "total_queues": summary["total_queues"],
                    "total_pending_tasks": summary["total_pending"],
                    "total_active_tasks": summary["total_running"],
                    "total_completed_tasks": summary["total_completed_today"],
                    "total_failed_tasks": summary["total_failed"],
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }

                # ✅ WebSocket message now IDENTICAL to REST API response
                message = {
                    "type": "queue_status_update",
                    "queues": queue_dtos,  # ✅ Array of DTOs (same as REST)
                    "stats": stats,        # ✅ Same format as REST
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await self.broadcast_to_ui(message)
                self._log_debug(f"Queue status broadcast (Phase 3): {len(queue_dtos)} queues with unified schema")

            elif queue_data:
                # Legacy fallback if repository not available
                message = {
                    "type": "queue_status_update",
                    "queues": queue_data.get("queues", {}),
                    "stats": queue_data.get("stats", {}),
                    "timestamp": queue_data.get("timestamp"),
                    "data": queue_data
                }

                await self.broadcast_to_ui(message)
                self._log_info(f"Queue status broadcast (legacy): {len(queue_data.get('queues', {}))} queues")
            else:
                self._log_warning("No queue data available and repository not configured")

        except Exception as e:
            self._log_error(f"Failed to broadcast queue status: {e}")
            import traceback
            # Use direct logger to avoid format string issues
            logger.error(f"[{self.__class__.__name__}] Traceback: {traceback.format_exc()}")

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
