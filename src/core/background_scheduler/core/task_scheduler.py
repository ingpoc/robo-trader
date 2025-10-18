"""
Core task scheduling engine for Background Scheduler.

Manages task lifecycle, queueing, priority-based execution, and timeouts.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Callable, Optional, List

from loguru import logger

from ..models import BackgroundTask, TaskPriority, TaskType
from ..stores.task_store import TaskStore


class TaskScheduler:
    """Manages background task scheduling and execution."""

    def __init__(
        self,
        state_dir,
        max_concurrent_tasks: int = 3,
        task_timeout_seconds: int = 300
    ):
        """Initialize task scheduler.

        Args:
            state_dir: Directory for persistent task storage
            max_concurrent_tasks: Maximum concurrent tasks to execute
            task_timeout_seconds: Timeout for individual tasks
        """
        self.state_dir = state_dir
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout_seconds = task_timeout_seconds
        self.is_running = False

        self._task_logic_handler: Optional[Callable] = None
        self._task_failure_handler: Optional[Callable] = None

    def set_task_logic_handler(self, handler: Callable) -> None:
        """Set handler for executing task logic.

        Args:
            handler: Callable(task: BackgroundTask) -> None
        """
        self._task_logic_handler = handler

    def set_task_failure_handler(self, handler: Callable) -> None:
        """Set handler for task failures.

        Args:
            handler: Callable(task: BackgroundTask, error: str) -> None
        """
        self._task_failure_handler = handler

    async def load_tasks(self) -> None:
        """Load all tasks from persistent storage."""
        self.tasks = await TaskStore.load_tasks(self.state_dir)
        logger.info(f"Loaded {len(self.tasks)} tasks into scheduler")

    async def schedule_task(
        self,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: int = 0,
        interval_seconds: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Schedule a new background task.

        Args:
            task_type: Type of task to schedule
            priority: Priority level (default: MEDIUM)
            delay_seconds: Delay before first execution
            interval_seconds: Repeat interval in seconds (None for one-time)
            metadata: Additional task metadata

        Returns:
            Task ID
        """
        task_id = f"{task_type.value}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        execute_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            execute_at=execute_at,
            interval_seconds=interval_seconds,
            metadata=metadata or {}
        )

        self.tasks[task_id] = task
        await TaskStore.save_task(self.state_dir, self.tasks)

        logger.info(f"Scheduled task: {task_id} ({task_type.value}) for {execute_at}")
        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if task was cancelled, False if not found
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.is_active = False
            await TaskStore.save_task(self.state_dir, self.tasks)

            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]

            logger.info(f"Cancelled task: {task_id}")
            return True

        return False

    async def get_due_tasks(self) -> List[BackgroundTask]:
        """Get list of tasks that are due for execution.

        Returns:
            List of due tasks, sorted by priority
        """
        now = datetime.now(timezone.utc)
        due_tasks = []

        for task in self.tasks.values():
            if (task.is_active and
                task.execute_at <= now and
                task.task_id not in self.running_tasks):

                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    if task.priority != TaskPriority.CRITICAL:
                        continue

                due_tasks.append(task)

        due_tasks.sort(key=lambda t: t.priority.value == 'critical', reverse=True)
        return due_tasks

    async def execute_due_tasks(self) -> None:
        """Find and execute all due tasks."""
        due_tasks = await self.get_due_tasks()
        available_slots = self.max_concurrent_tasks - len(self.running_tasks)

        for task in due_tasks[:available_slots]:
            await self._execute_task(task)

    async def _execute_task(self, task: BackgroundTask) -> None:
        """Execute a single task.

        Args:
            task: Task to execute
        """
        if task.task_id in self.running_tasks:
            return

        execution_task = asyncio.create_task(self._run_task_with_timeout(task))
        self.running_tasks[task.task_id] = execution_task

        task.last_executed = datetime.now(timezone.utc)
        if task.interval_seconds and task.is_active:
            task.next_execution = task.last_executed + timedelta(seconds=task.interval_seconds)
            task.execute_at = task.next_execution

        await TaskStore.save_task(self.state_dir, self.tasks)
        logger.info(f"Started execution of task: {task.task_id} ({task.task_type.value})")

    async def _run_task_with_timeout(self, task: BackgroundTask) -> None:
        """Run a task with timeout handling and error management.

        Args:
            task: Task to execute
        """
        execution_task = None
        try:
            if not self._task_logic_handler:
                logger.error(f"No task logic handler set for task {task.task_id}")
                return

            task_coro = self._task_logic_handler(task)
            execution_task = asyncio.create_task(task_coro)

            await asyncio.wait_for(execution_task, timeout=self.task_timeout_seconds)
            logger.info(f"Completed task: {task.task_id}")

        except asyncio.TimeoutError:
            if execution_task and not execution_task.done():
                execution_task.cancel()
                try:
                    await asyncio.wait_for(execution_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            logger.error(f"Task timeout: {task.task_id}")
            if self._task_failure_handler:
                await self._task_failure_handler(task, "timeout")

        except Exception as e:
            logger.error(f"Task execution error: {task.task_id} - {e}")
            if self._task_failure_handler:
                await self._task_failure_handler(task, str(e))

        finally:
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]

    def count_tasks_by_type(self) -> Dict[str, int]:
        """Count active tasks by type.

        Returns:
            Dictionary with task type counts
        """
        counts = {}
        for task in self.tasks.values():
            if task.is_active:
                task_type = task.task_type.value
                counts[task_type] = counts.get(task_type, 0) + 1
        return counts

    def count_tasks_by_priority(self) -> Dict[str, int]:
        """Count active tasks by priority.

        Returns:
            Dictionary with priority counts
        """
        counts = {}
        for task in self.tasks.values():
            if task.is_active:
                priority = task.priority.value
                counts[priority] = counts.get(priority, 0) + 1
        return counts

    def get_running_task_ids(self) -> List[str]:
        """Get list of currently running task IDs.

        Returns:
            List of running task IDs
        """
        return list(self.running_tasks.keys())

    async def cancel_all_running_tasks(self) -> None:
        """Cancel all running tasks gracefully."""
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
        self.running_tasks.clear()
        logger.info("All running tasks cancelled")

    async def update_next_execution(self, task_id: str, interval_seconds: int) -> None:
        """Update next execution time for a task.

        Args:
            task_id: ID of task to update
            interval_seconds: New interval in seconds
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.interval_seconds = interval_seconds
            task.next_execution = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
            task.execute_at = task.next_execution
            await TaskStore.save_task(self.state_dir, self.tasks)
