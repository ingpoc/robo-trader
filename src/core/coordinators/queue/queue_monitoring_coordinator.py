"""
Queue Monitoring Coordinator

Focused coordinator for queue monitoring and status.
Extracted from QueueCoordinator for single responsibility.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.config import Config
from ..base_coordinator import BaseCoordinator

logger = logging.getLogger(__name__)


class QueueMonitoringCoordinator(BaseCoordinator):
    """
    Coordinates queue monitoring and status.
    
    Responsibilities:
    - Get queue status
    - Perform health checks
    - Monitor queue metrics
    """

    def __init__(
        self,
        config: Config,
        sequential_queue_manager = None,
        queue_management_service = None
    ):
        super().__init__(config)
        self._sequential_queue_manager = sequential_queue_manager
        self._queue_management_service = queue_management_service
        self._queues_running = False
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize queue monitoring coordinator."""
        self._log_info("Initializing QueueMonitoringCoordinator")
        self._initialized = True

    def set_sequential_queue_manager(self, manager) -> None:
        """Set sequential queue manager."""
        self._sequential_queue_manager = manager

    def set_queue_management_service(self, service) -> None:
        """Set queue management service."""
        self._queue_management_service = service

    def set_queues_running(self, running: bool) -> None:
        """Set queues running state."""
        self._queues_running = running

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get status of all queues."""
        try:
            status_data = {
                "coordinator_running": self._initialized,
                "queues_running": self._queues_running,
                "timestamp": datetime.utcnow().isoformat()
            }

            queues = {}
            total_queues = 0
            running_queues = 0

            # Add coordinator status
            queues["coordinator"] = {
                "running": self._queues_running,
                "status": "healthy" if self._initialized else "not_initialized",
                "type": "coordinator"
            }
            total_queues += 1
            if self._queues_running:
                running_queues += 1

            # Add SequentialQueueManager status if available
            if self._sequential_queue_manager:
                try:
                    queue_status = await self._sequential_queue_manager.get_status()
                    is_running = queue_status.get("running", False)
                    queues["sequential_queue_manager"] = {
                        "running": is_running,
                        "status": "healthy" if is_running else "stopped",
                        "type": "sequential_queue_manager",
                        "details": queue_status
                    }
                    total_queues += 1
                    if is_running:
                        running_queues += 1
                except Exception as e:
                    self._log_warning(f"Could not get SequentialQueueManager status: {e}")

            # Add queue management service status if available
            if self._queue_management_service:
                try:
                    service_status = await self._queue_management_service.get_status()
                    for queue_name, queue_info in service_status.get("queues", {}).items():
                        queues[queue_name] = {
                            "running": queue_info.get("running", False),
                            "status": queue_info.get("status", "unknown"),
                            "type": "queue_service",
                            "details": queue_info
                        }
                        total_queues += 1
                        if queue_info.get("running", False):
                            running_queues += 1
                except Exception as e:
                    self._log_warning(f"Could not get queue service status: {e}")

            stats = {
                "total_queues": total_queues,
                "running_queues": running_queues,
                "timestamp": status_data["timestamp"]
            }

            status_data["queues"] = queues
            status_data["stats"] = stats

            return status_data

        except Exception as e:
            self._log_error(f"Failed to get queue status: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            health_status = {
                "coordinator": "healthy" if self._initialized else "not_initialized",
                "queues": "running" if self._queues_running else "stopped",
                "timestamp": datetime.utcnow().isoformat()
            }

            return health_status

        except Exception as e:
            self._log_error(f"Health check failed: {e}")
            return {
                "coordinator": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def cleanup(self) -> None:
        """Cleanup queue monitoring coordinator resources."""
        self._log_info("QueueMonitoringCoordinator cleanup complete")

