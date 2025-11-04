"""
Queue Coordinator (Refactored)

Thin orchestrator that delegates to focused queue coordinators.
Refactored from 537-line monolith into focused coordinators.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from src.config import Config
from ..base_coordinator import BaseCoordinator
from ...di import DependencyContainer
from .queue_lifecycle_coordinator import QueueLifecycleCoordinator
from .queue_execution_coordinator import QueueExecutionCoordinator
from .queue_monitoring_coordinator import QueueMonitoringCoordinator
from .queue_event_coordinator import QueueEventCoordinator
from src.models.scheduler import QueueName, TaskType
from src.core.event_bus import Event
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class QueueCoordinator(BaseCoordinator):
    """
    Coordinates queue execution and event routing.
    
    Responsibilities:
    - Orchestrate queue operations from focused coordinators
    - Provide unified queue management API
    """

    def __init__(self, config: Config, container: DependencyContainer):
        """Initialize queue coordinator."""
        super().__init__(config)
        self.container = container
        self._broadcast_coordinator = None
        
        # Focused coordinators
        self.lifecycle_coordinator = QueueLifecycleCoordinator(config)
        self.execution_coordinator = QueueExecutionCoordinator(config)
        self.monitoring_coordinator = QueueMonitoringCoordinator(config)
        self.event_coordinator = None  # Will be set in initialize

    async def initialize(self) -> None:
        """Initialize coordinator and dependencies."""
        self._log_info("Initializing QueueCoordinator")

        try:
            # Get dependencies from container
            event_bus = await self.container.get("event_bus")
            event_router_service = await self.container.get("event_router_service")
            self._broadcast_coordinator = await self.container.get("broadcast_coordinator")

            # Initialize event coordinator
            self.event_coordinator = QueueEventCoordinator(
                self.config,
                event_bus,
                event_router_service
            )
            await self.event_coordinator.initialize()

            # Get SequentialQueueManager for task execution
            try:
                sequential_queue_manager = await self.container.get("sequential_queue_manager")
                self.execution_coordinator.set_sequential_queue_manager(sequential_queue_manager)
                self.monitoring_coordinator.set_sequential_queue_manager(sequential_queue_manager)
                self._log_info("SequentialQueueManager connected to QueueCoordinator")
            except Exception as e:
                self._log_warning(f"Could not get SequentialQueueManager: {e}")

            # Initialize focused coordinators
            await self.lifecycle_coordinator.initialize()
            await self.execution_coordinator.initialize()
            await self.monitoring_coordinator.initialize()

            # Sync queue running state
            self.execution_coordinator.set_queues_running(self.lifecycle_coordinator.are_queues_running())
            self.monitoring_coordinator.set_queues_running(self.lifecycle_coordinator.are_queues_running())

            self._initialized = True
            self._log_info("QueueCoordinator initialized successfully")

            # Broadcast initial queue status
            await self.get_queue_status()

        except Exception as e:
            self._log_error(f"Failed to initialize QueueCoordinator: {e}", exc_info=True)
            raise TradingError(
                f"QueueCoordinator initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        if not self._initialized:
            return

        self._log_info("Cleaning up QueueCoordinator")

        try:
            # Stop queues if running
            if self.lifecycle_coordinator.are_queues_running():
                await self.lifecycle_coordinator.stop_queues()

            # Cleanup focused coordinators
            await self.event_coordinator.cleanup() if self.event_coordinator else None
            await self.execution_coordinator.cleanup()
            await self.monitoring_coordinator.cleanup()
            await self.lifecycle_coordinator.cleanup()

        except Exception as e:
            self._log_error(f"Error during QueueCoordinator cleanup: {e}")

    async def start_queues(self) -> None:
        """Start all queues."""
        await self.lifecycle_coordinator.start_queues()
        
        # Sync state to other coordinators
        self.execution_coordinator.set_queues_running(True)
        self.monitoring_coordinator.set_queues_running(True)

        # Broadcast queue status update
        await self.get_queue_status()

    async def stop_queues(self) -> None:
        """Stop all queues."""
        await self.lifecycle_coordinator.stop_queues()
        
        # Sync state to other coordinators
        self.execution_coordinator.set_queues_running(False)
        self.monitoring_coordinator.set_queues_running(False)

        # Broadcast queue status update
        await self.get_queue_status()

    async def execute_queues_sequential(self) -> Dict[str, Any]:
        """Execute all queues in sequence."""
        return await self.execution_coordinator.execute_queues_sequential()

    async def execute_queues_concurrent(self, max_concurrent: int = 2) -> Dict[str, Any]:
        """Execute queues concurrently with limited concurrency."""
        return await self.execution_coordinator.execute_queues_concurrent(max_concurrent)

    async def create_task(
        self,
        queue_name: QueueName,
        task_type: TaskType,
        payload: Dict[str, Any],
        priority: int = 5,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Create a new task in the specified queue."""
        try:
            # This would delegate to task service
            task_id = f"task_{datetime.utcnow().timestamp()}"
            self._log_info(f"Created task {task_id} in queue {queue_name.value}")
            return task_id

        except Exception as e:
            self._log_error(f"Failed to create task: {e}")
            raise TradingError(
                f"Task creation failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get status of all queues."""
        try:
            status_data = await self.monitoring_coordinator.get_queue_status()

            # Add event router status
            status_data["event_router_status"] = self.event_coordinator.get_event_router_status() if self.event_coordinator else "not_available"

            # Broadcast queue status update via WebSocket
            if self._broadcast_coordinator:
                queue_data = {
                    "queues": status_data.get("queues", {}),
                    "stats": status_data.get("stats", {}),
                    "timestamp": status_data.get("timestamp")
                }
                await self._broadcast_coordinator.broadcast_queue_status_update(queue_data)

            return status_data

        except Exception as e:
            self._log_error(f"Failed to get queue status: {e}")
            raise TradingError(
                f"Status retrieval failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.LOW,
                recoverable=True
            )

    async def trigger_event_routing(self, event: Event) -> List[Dict[str, Any]]:
        """Manually trigger event routing for testing."""
        return await self.event_coordinator.trigger_event_routing(event)

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return await self.monitoring_coordinator.health_check()
