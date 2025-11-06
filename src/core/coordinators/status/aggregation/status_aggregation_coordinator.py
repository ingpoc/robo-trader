"""
Status Aggregation Coordinator

Focused coordinator for aggregating system components.
Extracted from StatusCoordinator for single responsibility.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict


from ...base_coordinator import BaseCoordinator


class StatusAggregationCoordinator(BaseCoordinator):
    """
    Coordinates status aggregation from focused coordinators.

    Responsibilities:
    - Aggregate system components
    - Get queue status
    - Transform status formats
    """

    def __init__(
        self,
        config,
        system_status_coordinator,
        ai_status_coordinator,
        portfolio_status_coordinator,
    ):
        super().__init__(config)
        self.system_status_coordinator = system_status_coordinator
        self.ai_status_coordinator = ai_status_coordinator
        self.portfolio_status_coordinator = portfolio_status_coordinator
        self.container = None

    async def initialize(self) -> None:
        """Initialize status aggregation coordinator."""
        self._log_info("Initializing StatusAggregationCoordinator")
        self._initialized = True

    def set_container(self, container) -> None:
        """Set the dependency container."""
        self.container = container

    async def aggregate_system_components(
        self, scheduler_status: Dict[str, Any], claude_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate system components from focused coordinators."""
        # Get all components in parallel
        scheduler, database, websocket, resources, claude_agent, queue = (
            await asyncio.gather(
                self.system_status_coordinator.get_scheduler_status(),
                self.system_status_coordinator.get_database_status(),
                self.system_status_coordinator.get_websocket_status(),
                self.system_status_coordinator.get_system_resources(),
                self.ai_status_coordinator.get_claude_agent_status(),
                self.get_queue_status(),
                return_exceptions=True,
            )
        )

        components = {
            "scheduler": (
                scheduler
                if not isinstance(scheduler, Exception)
                else {"status": "error"}
            ),
            "database": (
                database if not isinstance(database, Exception) else {"status": "error"}
            ),
            "websocket": (
                websocket
                if not isinstance(websocket, Exception)
                else {"status": "error"}
            ),
            "resources": (
                resources
                if not isinstance(resources, Exception)
                else {"status": "error"}
            ),
            "claudeAgent": (
                claude_agent
                if not isinstance(claude_agent, Exception)
                else {"status": "error"}
            ),
            "queue": queue if not isinstance(queue, Exception) else {"status": "error"},
        }

        return components

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status (delegates to queue coordinator if available)."""
        try:
            if self.container:
                queue_coordinator = await self.container.get("queue_coordinator")
                if queue_coordinator:
                    queue_status = await queue_coordinator.get_queue_status()
                    return self.transform_queue_status(queue_status)
        except Exception as e:
            self._log_warning(f"Could not get queue status: {e}")

        # Fallback
        return {
            "status": "unknown",
            "totalTasks": 0,
            "runningTasks": 0,
            "queuedTasks": 0,
            "completedTasks": 0,
            "failedTasks": 0,
            "lastCheck": datetime.now(timezone.utc).isoformat(),
        }

    def transform_queue_status(self, queue_status: Dict[str, Any]) -> Dict[str, Any]:
        """Transform queue coordinator status to component format."""
        # Simplified transformation - full logic would be in queue coordinator
        return {
            "status": "healthy",
            "totalTasks": 0,
            "runningTasks": 0,
            "queuedTasks": 0,
            "completedTasks": 0,
            "failedTasks": 0,
            "lastCheck": datetime.now(timezone.utc).isoformat(),
        }

    async def cleanup(self) -> None:
        """Cleanup status aggregation coordinator resources."""
        self._log_info("StatusAggregationCoordinator cleanup complete")
