"""Sequential queue manager for task execution."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...models.scheduler import QueueName, SchedulerTask, TaskStatus
from .task_service import SchedulerTaskService

logger = logging.getLogger(__name__)


class SequentialQueueManager:
    """Manage sequential execution of queues."""

    def __init__(self, task_service: SchedulerTaskService):
        """Initialize manager."""
        self.task_service = task_service
        self._running = False
        self._current_task: Optional[SchedulerTask] = None
        self._completed_task_ids: List[str] = []
        self._execution_history: List[Dict[str, Any]] = []

    async def execute_queues(self) -> None:
        """Execute all queues in order: portfolio_sync → data_fetcher → ai_analysis."""
        if self._running:
            logger.warning("Queue execution already in progress")
            return

        self._running = True
        logger.info("Starting sequential queue execution")

        try:
            # Reload completed tasks from today
            self._completed_task_ids = await self.task_service.store.get_completed_task_ids_today()

            # Execute each queue
            for queue_name in [QueueName.PORTFOLIO_SYNC, QueueName.DATA_FETCHER, QueueName.AI_ANALYSIS]:
                logger.info(f"Starting queue: {queue_name.value}")

                await self._execute_queue(queue_name)

                logger.info(f"Completed queue: {queue_name.value}")

        except Exception as e:
            logger.error(f"Error in queue execution: {e}")
        finally:
            self._running = False
            logger.info("Sequential queue execution complete")

    async def _execute_queue(self, queue_name: QueueName) -> None:
        """Execute all tasks in a queue sequentially."""
        max_iterations = 1000  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Get next pending task
            pending_tasks = await self.task_service.get_pending_tasks(
                queue_name=queue_name,
                completed_task_ids=self._completed_task_ids
            )

            if not pending_tasks:
                logger.info(f"No more pending tasks in {queue_name.value}")
                break

            # Execute first task (highest priority)
            task = pending_tasks[0]
            await self._execute_single_task(task)

            # Add to completed list
            if task.status == TaskStatus.COMPLETED:
                self._completed_task_ids.append(task.task_id)

    async def _execute_single_task(self, task: SchedulerTask) -> None:
        """Execute a single task with error handling."""
        self._current_task = task
        start_time = datetime.utcnow()

        logger.info(f"Executing task: {task.task_id} ({task.task_type.value})")

        try:
            # Set timeout for task execution (max 5 minutes)
            result = await asyncio.wait_for(
                self.task_service.execute_task(task),
                timeout=300.0  # 5 minutes
            )

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Record in history
            self._execution_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": "completed",
                "duration_ms": duration_ms,
                "timestamp": end_time.isoformat()
            })

            logger.info(f"Task completed: {task.task_id} ({duration_ms}ms)")

        except asyncio.TimeoutError:
            logger.error(f"Task timeout: {task.task_id}")
            await self.task_service.mark_failed(task.task_id, "Task execution timeout (>300s)")
            self._execution_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": "timeout",
                "duration_ms": 300000,
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Task execution error: {task.task_id} - {e}")
            await self.task_service.mark_failed(task.task_id, str(e))
            self._execution_history.append({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

        finally:
            self._current_task = None

    def is_running(self) -> bool:
        """Check if queue execution is running."""
        return self._running

    def get_current_task(self) -> Optional[SchedulerTask]:
        """Get currently executing task."""
        return self._current_task

    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return self._execution_history[-limit:]

    async def get_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        stats = await self.task_service.get_all_queue_statistics()

        return {
            "running": self._running,
            "current_task": self._current_task.task_id if self._current_task else None,
            "completed_tasks_today": len(self._completed_task_ids),
            "queue_statistics": {k: v.to_dict() for k, v in stats.items()},
            "recent_history": self.get_execution_history(limit=10)
        }
