"""Sequential queue manager for task execution.

This module implements the parallel queue, sequential task pattern:
- selected queues execute in parallel
- tasks within each queue execute sequentially (one-at-a-time per queue)

Architecture Pattern - NON-BLOCKING EXECUTION:
- Tasks execute in background threads via ThreadSafeQueueExecutor
- Main event loop remains responsive for HTTP/WebSocket
- Status updates callback to main event loop via run_coroutine_threadsafe()
- Graceful shutdown waits for all executor threads

Phase 3: Uses QueueStateRepository for status queries (single source of truth)
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...models.scheduler import QueueName, SchedulerTask, TaskStatus
from ...models.dto import QueueStatusDTO
from .task_service import SchedulerTaskService
from .thread_safe_queue_executor import ThreadSafeQueueExecutor

logger = logging.getLogger(__name__)


class SequentialQueueManager:
    """
    Manage queue execution with parallel queues and sequential tasks.

    Architecture Pattern:
    - selected queues execute in parallel
    - tasks within each queue execute sequentially (one-at-a-time per queue)

    This prevents:
    - Database contention (PORTFOLIO_SYNC tasks run sequentially)
    - Resource conflicts (each queue manages its own sequential execution)

    While allowing:
    - Parallel processing across different queue types
    - Better resource utilization
    - Independent queue execution

    Phase 3 Update:
    - Uses QueueStateRepository for status queries (single source of truth)
    - Returns unified DTOs consistent with REST API
    - Eliminates dual sources of truth
    """

    def __init__(self, task_service: SchedulerTaskService, queue_state_repository=None):
        """Initialize manager.

        Args:
            task_service: Task service for task operations
            queue_state_repository: Repository for status queries (Phase 3)
        """
        self.task_service = task_service
        self.queue_state_repository = queue_state_repository
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Thread-safe executors for each queue (3 parallel workers)
        self._executors: Dict[QueueName, ThreadSafeQueueExecutor] = {}

        # Execution tracking (for backward compatibility)
        self._execution_history: List[Dict[str, Any]] = []
        self._completed_task_ids: List[str] = []

    async def execute_queues(self) -> None:
        """
        Execute all queues in parallel using thread-safe executors.

        Architecture Pattern (NON-BLOCKING):
        - 3+ queues execute in PARALLEL using ThreadSafeQueueExecutor
        - Each executor runs tasks SEQUENTIALLY in a dedicated worker thread
        - Main event loop stays responsive for HTTP/WebSocket
        - Thread callbacks use run_coroutine_threadsafe() to update async state

        Execution Flow:
        1. Start executor for each queue (spawns worker thread)
        2. Each thread runs _run_queue_loop() to process tasks sequentially
        3. Task completion callbacks back to main event loop
        4. Main loop stays responsive for health checks and broadcasts
        5. Shutdown waits for all executor threads to finish gracefully
        """
        if self._running:
            logger.warning("Queue execution already in progress")
            return

        self._running = True
        # CRITICAL: Always get current event loop to prevent "Event loop is closed" errors
        self._loop = asyncio.get_running_loop()
        if not self._loop.is_running():
            raise RuntimeError("Event loop is not running - cannot start queue executors")
        logger.info("Starting parallel queue execution (NON-BLOCKING with ThreadSafeQueueExecutor)")

        try:
            # Reload completed tasks from today
            self._completed_task_ids = await self.task_service.store.get_completed_task_ids_today()

            # Keep startup manual-first: do not automatically attach AI-related
            # executors that could process stale queued research/analysis work.
            queue_names = [
                QueueName.PORTFOLIO_SYNC,
                QueueName.DATA_FETCHER,
                QueueName.PAPER_TRADING_EXECUTION
            ]
            logger.info(
                "AI_ANALYSIS, PORTFOLIO_ANALYSIS, and PAPER_TRADING_RESEARCH executors removed from startup path"
            )

            # Create and start executor for each queue
            for queue_name in queue_names:
                executor = ThreadSafeQueueExecutor(
                    queue_name=queue_name.value,
                    task_service=self.task_service,
                    loop=self._loop,
                    on_task_complete=self._on_task_complete,
                    on_task_failed=self._on_task_failed
                )
                self._executors[queue_name] = executor
                await executor.start()

            logger.info(f"Started {len(self._executors)} queue executors (all running in parallel)")

        except Exception as e:
            logger.error(f"Error starting queue execution: {e}")
            self._running = False

    async def _get_execution_tracker(self):
        """Get execution tracker from container (safe lazy loading)."""
        try:
            # Try to get from container if available
            from src.core.di import DependencyContainer
            if hasattr(self, '_container') and self._container:
                return await self._container.get("execution_tracker")
        except:
            pass
        return None

    async def _on_task_complete(self, task: SchedulerTask) -> None:
        """Callback when task completes (runs on main event loop).

        Args:
            task: Completed task
        """
        try:
            logger.info(f"Task completed callback: {task.task_id}")

            # CRITICAL: Mark task as completed in database
            await self.task_service.mark_completed(task.task_id)

            # Update execution_history to reflect actual completion (fixes stale status)
            try:
                execution_tracker = await self._get_execution_tracker()
                if execution_tracker:
                    await execution_tracker.update_execution_status(
                        task_id=task.task_id,
                        status="completed"
                    )
            except Exception as e:
                logger.warning(f"Failed to update execution_history for {task.task_id}: {e}")

            self._completed_task_ids.append(task.task_id)
            self._execution_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error in task complete callback: {e}")

    async def _on_task_failed(self, task: SchedulerTask, error_msg: str) -> None:
        """Callback when task fails (runs on main event loop).

        Args:
            task: Failed task
            error_msg: Error message
        """
        try:
            logger.error(f"Task failed callback: {task.task_id} - {error_msg}")

            # CRITICAL: Mark task as failed in database
            await self.task_service.mark_failed(task.task_id, error_msg)

            # Update execution_history to reflect actual failure (fixes stale status)
            try:
                execution_tracker = await self._get_execution_tracker()
                if execution_tracker:
                    await execution_tracker.update_execution_status(
                        task_id=task.task_id,
                        status="failed",
                        error_message=error_msg
                    )
            except Exception as e:
                logger.warning(f"Failed to update execution_history for {task.task_id}: {e}")

            self._execution_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": "failed",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error in task failed callback: {e}")

    async def stop(self, timeout_seconds: int = 30) -> None:
        """Stop all executors and wait for graceful shutdown.

        Args:
            timeout_seconds: Max seconds to wait for all threads
        """
        if not self._running:
            return

        logger.info(f"Stopping all {len(self._executors)} queue executors...")
        self._running = False

        # Stop all executors concurrently
        stop_tasks = [
            executor.stop(timeout_seconds=timeout_seconds)
            for executor in self._executors.values()
        ]

        results = await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Log results
        for i, (queue_name, executor) in enumerate(self._executors.items()):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Error stopping executor {queue_name.value}: {result}")
            else:
                logger.info(f"Queue {queue_name.value} executor stopped")

        logger.info("All queue executors stopped")

    def is_running(self) -> bool:
        """Check if queue execution is running."""
        return self._running

    def get_current_task(self) -> Optional[str]:
        """Get currently executing task ID (from any executor).

        Returns:
            Task ID of current task, or None if idle
        """
        for executor in self._executors.values():
            current = executor.get_current_task()
            if current:
                return current.task_id
        return None

    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution history from all executors.

        Args:
            limit: Max number of records

        Returns:
            Recent execution history
        """
        return self._execution_history[-limit:]

    async def get_status(self) -> Dict[str, Any]:
        """Get current queue status from all executors.

        Phase 3: Uses QueueStateRepository for consistent status data.

        Returns:
            Status dictionary with executor and queue DTOs
        """
        # Phase 3: Use repository as single source of truth
        if self.queue_state_repository:
            all_queue_states = await self.queue_state_repository.get_all_statuses()

            # Convert to DTOs (consistent with REST API)
            queue_dtos = []
            for queue_state in all_queue_states.values():
                dto = QueueStatusDTO.from_queue_state(queue_state)
                queue_dtos.append(dto.to_dict())
        else:
            # Fallback if repository not available
            queue_dtos = []

        # Get status from each executor (for backward compatibility)
        executor_status = {}
        for queue_name, executor in self._executors.items():
            executor_status[queue_name.value] = await executor.get_status()

        return {
            "running": self._running,
            "current_task": self.get_current_task(),
            "completed_tasks_today": len(self._completed_task_ids),
            "executors": executor_status,
            "queues": queue_dtos  # Phase 3: Unified DTOs (history available from repository)
        }
