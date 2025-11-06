"""Scheduler task service for queue management."""

import logging
from typing import Any, Callable, Dict, List, Optional

from ...models.scheduler import (QueueName, QueueStatistics, SchedulerTask,
                                 TaskStatus, TaskType)
from ...stores.scheduler_task_store import SchedulerTaskStore

logger = logging.getLogger(__name__)


class SchedulerTaskService:
    """Manage scheduler tasks and queues."""

    def __init__(self, store: SchedulerTaskStore, execution_tracker=None):
        """Initialize service."""
        self.store = store
        self.execution_tracker = execution_tracker
        self._task_handlers: Dict[TaskType, Callable] = {}

    async def initialize(self) -> None:
        """Initialize the task service."""
        await self.store.initialize()

    def register_handler(self, task_type: TaskType, handler: Callable) -> None:
        """Register a task handler."""
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type.value}")

    async def create_task(
        self,
        queue_name: QueueName,
        task_type: TaskType,
        payload: Dict[str, Any],
        priority: int = 5,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> SchedulerTask:
        """Create new scheduler task."""
        task = await self.store.create_task(
            queue_name=queue_name,
            task_type=task_type,
            payload=payload,
            priority=priority,
            dependencies=dependencies,
            max_retries=max_retries,
        )
        logger.info(f"Created task: {task.task_id} in queue {queue_name.value}")
        return task

    async def get_task(self, task_id: str) -> Optional[SchedulerTask]:
        """Get task by ID."""
        return await self.store.get_task(task_id)

    async def get_queue_statistics(self, queue_name: QueueName) -> QueueStatistics:
        """Get queue statistics."""
        return await self.store.get_queue_statistics(queue_name)

    async def get_all_queue_statistics(self) -> Dict[str, QueueStatistics]:
        """Get statistics for all queues."""
        stats = {}
        for queue_name in QueueName:
            stats[queue_name.value] = await self.get_queue_statistics(queue_name)
        return stats

    async def get_pending_tasks(
        self, queue_name: QueueName, completed_task_ids: Optional[List[str]] = None
    ) -> List[SchedulerTask]:
        """Get pending tasks for queue that are ready to run."""
        completed = completed_task_ids or []
        all_pending = await self.store.get_pending_tasks(queue_name)
        logger.debug(
            f"get_pending_tasks() for {queue_name.value}: store returned {len(all_pending)} tasks"
        )

        # Filter by dependency satisfaction
        ready_tasks = [t for t in all_pending if t.is_ready_to_run(completed)]
        logger.debug(f"get_pending_tasks() filtered to {len(ready_tasks)} ready tasks")
        return ready_tasks

    async def mark_started(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as started."""
        task = await self.store.mark_started(task_id)
        logger.info(f"Task started: {task_id}")
        return task

    async def mark_completed(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as completed."""
        task = await self.store.mark_completed(task_id)
        logger.info(f"Task completed: {task_id}")
        return task

    async def mark_failed(self, task_id: str, error: str) -> Optional[SchedulerTask]:
        """Mark task as failed."""
        task = await self.store.mark_failed(task_id, error)

        if task and task.status == TaskStatus.RETRYING:
            logger.warning(f"Task failed, will retry: {task_id} - {error}")
        else:
            logger.error(f"Task failed (no more retries): {task_id} - {error}")

        return task

    async def retry_task(self, task_id: str) -> Optional[SchedulerTask]:
        """Retry a failed task."""
        task = await self.store.increment_retry(task_id)
        logger.info(f"Task queued for retry: {task_id} (attempt {task.retry_count})")
        return task

    async def execute_task(self, task: SchedulerTask) -> Dict[str, Any]:
        """Execute a task."""
        import asyncio

        # Mark started
        await self.mark_started(task.task_id)

        # Get handler
        handler = self._task_handlers.get(task.task_type)
        if not handler:
            error = f"No handler registered for task type: {task.task_type.value}"
            await self.mark_failed(task.task_id, error)
            return {"success": False, "error": error}

        # Execute with timeout (900 seconds = 15 minutes max per task)
        # AI analysis on large portfolios requires 5-10+ minutes
        try:
            result = await asyncio.wait_for(handler(task), timeout=900.0)
            await self.mark_completed(task.task_id)
            return {"success": True, "result": result}
        except asyncio.TimeoutError:
            error_msg = "Task execution timed out after 900 seconds"
            await self.mark_failed(task.task_id, error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            await self.mark_failed(task.task_id, error_msg)
            return {"success": False, "error": error_msg}

    async def cleanup_old_tasks(self, days_to_keep: int = 7) -> int:
        """Clean up old completed tasks."""
        deleted_count = await self.store.cleanup_old_tasks(days_to_keep)
        logger.info(f"Cleaned up {deleted_count} old tasks")
        return deleted_count
