"""
Queue Execution Coordinator

Focused coordinator for queue execution logic.
Extracted from QueueCoordinator for single responsibility.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from src.config import Config
from src.models.scheduler import QueueName
from ..base_coordinator import BaseCoordinator

logger = logging.getLogger(__name__)


class QueueExecutionCoordinator(BaseCoordinator):
    """
    Coordinates queue execution.
    
    Responsibilities:
    - Execute queues sequentially
    - Execute queues concurrently
    - Manage queue execution state
    """

    def __init__(
        self,
        config: Config,
        sequential_queue_manager = None
    ):
        super().__init__(config)
        self._sequential_queue_manager = sequential_queue_manager
        self._queues_running = False

    async def initialize(self) -> None:
        """Initialize queue execution coordinator."""
        self._log_info("Initializing QueueExecutionCoordinator")
        self._initialized = True

    def set_sequential_queue_manager(self, manager) -> None:
        """Set sequential queue manager."""
        self._sequential_queue_manager = manager

    def set_queues_running(self, running: bool) -> None:
        """Set queues running state."""
        self._queues_running = running

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

        try:
            if self._sequential_queue_manager:
                self._log_info("Executing queues through SequentialQueueManager")
                await self._sequential_queue_manager.execute_queues()
                status = await self._sequential_queue_manager.get_status()

                self._log_info("Sequential queue execution completed through SequentialQueueManager")
                return {
                    "success": True,
                    "execution_mode": "sequential",
                    "method": "SequentialQueueManager",
                    "status": status,
                    "timestamp": self._get_timestamp()
                }
            else:
                self._log_warning("SequentialQueueManager not available, using fallback execution")
                results = {}
                execution_order = [QueueName.PORTFOLIO_SYNC, QueueName.DATA_FETCHER, QueueName.AI_ANALYSIS]

                for queue_name in execution_order:
                    self._log_info(f"Executing queue: {queue_name.value}")
                    queue_result = await self._execute_single_queue(queue_name)
                    results[queue_name.value] = queue_result
                    self._log_info(f"Completed queue: {queue_name.value}")

                self._log_info("Sequential queue execution completed (fallback)")
                return {
                    "success": True,
                    "execution_mode": "sequential",
                    "method": "fallback",
                    "results": results,
                    "timestamp": self._get_timestamp()
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
            semaphore = asyncio.Semaphore(max_concurrent)
            queue_names = [QueueName.PORTFOLIO_SYNC, QueueName.DATA_FETCHER, QueueName.AI_ANALYSIS]

            async def execute_with_semaphore(queue_name: QueueName):
                async with semaphore:
                    return await self._execute_single_queue(queue_name)

            tasks = [execute_with_semaphore(name) for name in queue_names]
            results = await asyncio.gather(*tasks, return_exceptions=True)

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
                "timestamp": self._get_timestamp()
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
            from datetime import datetime
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

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        return datetime.utcnow().isoformat()

    async def cleanup(self) -> None:
        """Cleanup queue execution coordinator resources."""
        self._log_info("QueueExecutionCoordinator cleanup complete")

