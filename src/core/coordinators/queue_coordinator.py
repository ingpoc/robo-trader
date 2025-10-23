"""
Queue Coordinator

Manages queue execution, event routing, and cross-queue coordination.
Follows core infrastructure patterns with proper DI and error handling.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ...config import Config
from ...core.di import DependencyContainer
from ...core.event_bus import EventBus, Event, EventType
from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from ...models.scheduler import QueueName, TaskType
from ...services.event_router_service import EventRouterService
from .base_coordinator import BaseCoordinator

logger = logging.getLogger(__name__)


class QueueCoordinator(BaseCoordinator):
    """
    Coordinates queue execution and event routing.

    Responsibilities:
    - Manage queue lifecycle (start/stop)
    - Coordinate cross-queue event routing
    - Handle queue execution strategies (sequential/concurrent)
    - Monitor queue health and performance
    - Provide queue management API
    """

    def __init__(self, config: Config, container: DependencyContainer):
        """Initialize queue coordinator."""
        super().__init__(config)
        self.container = container
        self.event_router_service: Optional[EventRouterService] = None
        self.event_bus: Optional[EventBus] = None
        self._queues_running = False

    async def initialize(self) -> None:
        """Initialize coordinator and dependencies."""
        self._log_info("Initializing QueueCoordinator")

        try:
            # Get dependencies from container
            self.event_router_service = await self.container.get("event_router_service")
            self.event_bus = await self.container.get("event_bus")

            # Subscribe to relevant events
            if self.event_bus:
                self.event_bus.subscribe(EventType.TASK_COMPLETED, self._handle_task_completed)
                self.event_bus.subscribe(EventType.MARKET_NEWS, self._handle_market_event)
                self.event_bus.subscribe(EventType.EARNINGS_ANNOUNCEMENT, self._handle_earnings_event)

            # Start event router service
            if self.event_router_service:
                await self.event_router_service.start()

            self._initialized = True
            self._log_info("QueueCoordinator initialized successfully")

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
            if self._queues_running:
                await self._stop_queues()

            # Stop event router service
            if self.event_router_service:
                await self.event_router_service.stop()

            # Unsubscribe from events
            if self.event_bus:
                self.event_bus.unsubscribe(EventType.TASK_COMPLETED)
                self.event_bus.unsubscribe(EventType.MARKET_NEWS)
                self.event_bus.unsubscribe(EventType.EARNINGS_ANNOUNCEMENT)

        except Exception as e:
            self._log_error(f"Error during QueueCoordinator cleanup: {e}")

    async def start_queues(self) -> None:
        """Start all queues."""
        if self._queues_running:
            self._log_warning("Queues already running")
            return

        if not self._initialized:
            await self.initialize()

        self._log_info("Starting queues")

        try:
            # Start individual queues through their services
            # Note: Queues are managed by their respective services now
            self._queues_running = True
            self._log_info("Queues started successfully")

        except Exception as e:
            self._log_error(f"Failed to start queues: {e}")
            raise TradingError(
                f"Queue startup failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def stop_queues(self) -> None:
        """Stop all queues."""
        if not self._queues_running:
            return

        await self._stop_queues()

    async def _stop_queues(self) -> None:
        """Internal method to stop queues."""
        self._log_info("Stopping queues")

        try:
            # Stop individual queues through their services
            # Note: Queues are managed by their respective services now
            self._queues_running = False
            self._log_info("Queues stopped successfully")

        except Exception as e:
            self._log_error(f"Error stopping queues: {e}")

    async def execute_queues_sequential(self) -> Dict[str, Any]:
        """Execute all queues in sequence."""
        if not self._queues_running:
            raise TradingError(
                "Queues not running",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

        self._log_info("Starting sequential queue execution")

        results = {}
        execution_order = [QueueName.PORTFOLIO_SYNC, QueueName.DATA_FETCHER, QueueName.AI_ANALYSIS]

        try:
            for queue_name in execution_order:
                self._log_info(f"Executing queue: {queue_name.value}")

                # Execute queue through its service
                # Note: This would delegate to the appropriate queue service
                queue_result = await self._execute_single_queue(queue_name)
                results[queue_name.value] = queue_result

                self._log_info(f"Completed queue: {queue_name.value}")

            self._log_info("Sequential queue execution completed")
            return {
                "success": True,
                "execution_mode": "sequential",
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log_error(f"Sequential queue execution failed: {e}")
            raise TradingError(
                f"Sequential execution failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def execute_queues_concurrent(self, max_concurrent: int = 2) -> Dict[str, Any]:
        """Execute queues concurrently with limited concurrency."""
        if not self._queues_running:
            raise TradingError(
                "Queues not running",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

        self._log_info(f"Starting concurrent queue execution (max_concurrent={max_concurrent})")

        try:
            import asyncio

            # Execute all queues concurrently with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            queue_names = [QueueName.PORTFOLIO_SYNC, QueueName.DATA_FETCHER, QueueName.AI_ANALYSIS]

            async def execute_with_semaphore(queue_name: QueueName):
                async with semaphore:
                    return await self._execute_single_queue(queue_name)

            tasks = [execute_with_semaphore(name) for name in queue_names]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            result_dict = {}
            for i, queue_name in enumerate(queue_names):
                result = results[i]
                if isinstance(result, Exception):
                    result_dict[queue_name.value] = {"error": str(result)}
                else:
                    result_dict[queue_name.value] = result

            self._log_info("Concurrent queue execution completed")
            return {
                "success": True,
                "execution_mode": "concurrent",
                "max_concurrent": max_concurrent,
                "results": result_dict,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log_error(f"Concurrent queue execution failed: {e}")
            raise TradingError(
                f"Concurrent execution failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def _execute_single_queue(self, queue_name: QueueName) -> Dict[str, Any]:
        """Execute a single queue."""
        try:
            # This would delegate to the appropriate queue service
            # For now, return mock result
            return {
                "queue_name": queue_name.value,
                "status": "completed",
                "tasks_processed": 5,
                "execution_time": 2.5,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log_error(f"Failed to execute queue {queue_name.value}: {e}")
            raise

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
            # For now, return mock task ID
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
            # This would aggregate status from all queue services
            return {
                "coordinator_running": self._initialized,
                "queues_running": self._queues_running,
                "event_router_status": (
                    self.event_router_service.get_status()
                    if self.event_router_service else "not_available"
                ),
                "timestamp": datetime.utcnow().isoformat()
            }

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
        if not self.event_router_service:
            raise TradingError(
                "Event router service not available",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=False
            )

        try:
            return await self.event_router_service.handle_event(event)

        except Exception as e:
            self._log_error(f"Event routing failed: {e}")
            raise TradingError(
                f"Event routing failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    # Event handlers

    async def _handle_task_completed(self, event: Event) -> None:
        """Handle task completion events."""
        try:
            task_data = event.data
            task_id = task_data.get("task_id")
            task_type = task_data.get("task_type")

            self._log_info(f"Task completed: {task_id} ({task_type})")

            # Trigger event routing
            if self.event_router_service:
                triggered_actions = await self.event_router_service.handle_event(event)
                if triggered_actions:
                    self._log_info(f"Triggered {len(triggered_actions)} actions from task completion")

        except Exception as e:
            self._log_error(f"Error handling task completion: {e}")

    async def _handle_market_event(self, event: Event) -> None:
        """Handle market news events."""
        try:
            symbol = event.data.get("symbol")
            impact_score = event.data.get("impact_score", 0)

            self._log_info(f"Market event for {symbol}: impact_score={impact_score}")

            # Trigger event routing for high-impact events
            if impact_score > 0.7 and self.event_router_service:
                triggered_actions = await self.event_router_service.handle_event(event)
                if triggered_actions:
                    self._log_info(f"Triggered {len(triggered_actions)} actions from market event")

        except Exception as e:
            self._log_error(f"Error handling market event: {e}")

    async def _handle_earnings_event(self, event: Event) -> None:
        """Handle earnings announcement events."""
        try:
            symbol = event.data.get("symbol")
            self._log_info(f"Earnings event for {symbol}")

            # Trigger event routing
            if self.event_router_service:
                triggered_actions = await self.event_router_service.handle_event(event)
                if triggered_actions:
                    self._log_info(f"Triggered {len(triggered_actions)} actions from earnings event")

        except Exception as e:
            self._log_error(f"Error handling earnings event: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            health_status = {
                "coordinator": "healthy" if self._initialized else "not_initialized",
                "queues": "running" if self._queues_running else "stopped",
                "event_router": "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Check event router service
            if self.event_router_service:
                router_status = self.event_router_service.get_status()
                health_status["event_router"] = "healthy" if router_status.get("running") else "stopped"

            return health_status

        except Exception as e:
            self._log_error(f"Health check failed: {e}")
            return {
                "coordinator": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }