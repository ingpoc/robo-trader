"""
Status Aggregation Coordinator

Focused coordinator for aggregating system components.
Extracted from StatusCoordinator for single responsibility.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.config import Config
from ...base_coordinator import BaseCoordinator


class StatusAggregationCoordinator(BaseCoordinator):
    """
    Coordinates status aggregation from focused coordinators.
    
    Responsibilities:
    - Aggregate system components
    - Get queue status
    - Transform status formats
    """
    
    def __init__(self, config, system_status_coordinator, ai_status_coordinator, portfolio_status_coordinator):
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
        self,
        scheduler_status: Dict[str, Any],
        claude_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate system components from focused coordinators."""
        # Get all components in parallel
        scheduler, database, websocket, resources, claude_agent, queue = await asyncio.gather(
            self.system_status_coordinator.get_scheduler_status(),
            self.system_status_coordinator.get_database_status(),
            self.system_status_coordinator.get_websocket_status(),
            self.system_status_coordinator.get_system_resources(),
            self.ai_status_coordinator.get_claude_agent_status(),
            self.get_queue_status(),
            return_exceptions=True
        )
        
        components = {
            "scheduler": scheduler if not isinstance(scheduler, Exception) else {"status": "error"},
            "database": database if not isinstance(database, Exception) else {"status": "error"},
            "websocket": websocket if not isinstance(websocket, Exception) else {"status": "error"},
            "resources": resources if not isinstance(resources, Exception) else {"status": "error"},
            "claudeAgent": claude_agent if not isinstance(claude_agent, Exception) else {"status": "error"},
            "queue": queue if not isinstance(queue, Exception) else {"status": "error"}
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

        return {
            "status": "error",
            "totalTasks": 0,
            "runningTasks": 0,
            "queuedTasks": 0,
            "completedTasks": 0,
            "failedTasks": 0,
            "lastCheck": datetime.now(timezone.utc).isoformat(),
            "error": "Queue coordinator unavailable",
        }

    def transform_queue_status(self, queue_status: Dict[str, Any]) -> Dict[str, Any]:
        """Transform queue coordinator status to component format."""
        stats = queue_status.get("stats", {}) if isinstance(queue_status, dict) else {}
        queues = queue_status.get("queues", {}) if isinstance(queue_status, dict) else {}
        normalized_queues = list(queues.values()) if isinstance(queues, dict) else list(queues or [])

        total_tasks = int(stats.get("totalTasks") or stats.get("total_tasks") or 0)
        running_tasks = int(stats.get("runningTasks") or stats.get("running_tasks") or 0)
        queued_tasks = int(stats.get("queuedTasks") or stats.get("queued_tasks") or 0)
        completed_tasks = int(stats.get("completedTasks") or stats.get("completed_tasks") or 0)
        failed_tasks = int(stats.get("failedTasks") or stats.get("failed_tasks") or stats.get("total_failed_tasks") or 0)

        total_queues = int(stats.get("totalQueues") or stats.get("total_queues") or len(normalized_queues))
        running_queues = int(stats.get("runningQueues") or stats.get("running_queues") or 0)
        if running_queues == 0 and normalized_queues:
            running_queues = sum(
                1
                for queue in normalized_queues
                if queue.get("running") or queue.get("status") in {"running", "active", "healthy"}
            )

        if failed_tasks == 0 and normalized_queues:
            failed_tasks = sum(int(queue.get("failed_tasks") or 0) for queue in normalized_queues)

        has_error_queue = any(queue.get("status") in {"error", "failed"} for queue in normalized_queues)
        if failed_tasks > 0 or has_error_queue:
            status = "error"
        elif total_queues == 0:
            status = "idle"
        elif running_queues > 0 or total_tasks > 0 or running_tasks > 0 or queued_tasks > 0:
            status = "healthy"
        else:
            status = "idle"

        return {
            "status": status,
            "totalTasks": total_tasks,
            "runningTasks": running_tasks,
            "queuedTasks": queued_tasks,
            "completedTasks": completed_tasks,
            "failedTasks": failed_tasks,
            "totalQueues": total_queues,
            "runningQueues": running_queues,
            "lastCheck": queue_status.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }
    
    async def cleanup(self) -> None:
        """Cleanup status aggregation coordinator resources."""
        self._log_info("StatusAggregationCoordinator cleanup complete")
