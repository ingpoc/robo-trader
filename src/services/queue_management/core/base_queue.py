"""Base Queue class for the Queue Management Service."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from ....models.scheduler import QueueName, TaskType, SchedulerTask, TaskStatus
from ....services.scheduler.task_service import SchedulerTaskService
from ....core.event_bus import EventBus

logger = logging.getLogger(__name__)


class BaseQueue:
    """Base class for all queue implementations in the Queue Management Service."""

    def __init__(
        self,
        queue_name: QueueName,
        task_service: SchedulerTaskService,
        event_bus: EventBus,
        execution_tracker=None
    ):
        """Initialize base queue."""
        self.queue_name = queue_name
        self.task_service = task_service
        self.event_bus = event_bus
        self.execution_tracker = execution_tracker

        self._running = False
        self._task_handlers: Dict[TaskType, Callable] = {}
        self._current_task: Optional[SchedulerTask] = None
        self._execution_lock = asyncio.Lock()

        # Metrics
        self.tasks_processed = 0
        self.tasks_failed = 0
        self.average_execution_time = 0.0

    async def record_execution(
        self,
        task_name: str,
        task_id: str,
        symbols: List[str] = None,
        status: str = "completed",
        error_message: str = None,
        execution_time: float = None
    ) -> None:
        """Record task execution in the execution tracker."""
        if self.execution_tracker:
            await self.execution_tracker.record_execution(
                task_name=task_name,
                task_id=task_id,
                execution_type="scheduled",
                user="queue_system",
                symbols=symbols,
                status=status,
                error_message=error_message,
                execution_time=execution_time
            )

    async def start(self) -> None:
        """Start the queue."""
        if self._running:
            return

        self._running = True
        logger.info(f"Started queue: {self.queue_name.value}")

    async def stop(self) -> None:
        """Stop the queue."""
        self._running = False

        # Cancel current task if running
        if self._current_task:
            await self.task_service.mark_failed(
                self._current_task.task_id,
                "Queue stopped"
            )

        logger.info(f"Stopped queue: {self.queue_name.value}")

    async def execute(self) -> None:
        """Execute all pending tasks in the queue."""
        if not self._running:
            logger.warning(f"Queue {self.queue_name.value} not running")
            return

        async with self._execution_lock:
            logger.info(f"Executing queue: {self.queue_name.value}")

            try:
                # Get pending tasks
                pending_tasks = await self.task_service.get_pending_tasks(
                    queue_name=self.queue_name
                )

                if not pending_tasks:
                    logger.info(f"No pending tasks in queue: {self.queue_name.value}")
                    return

                # Execute tasks sequentially
                for task in pending_tasks:
                    if not self._running:
                        break

                    try:
                        await self._execute_task(task)
                    except Exception as e:
                        logger.error(f"Failed to execute task {task.task_id}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error executing queue {self.queue_name.value}: {e}")

    async def _execute_task(self, task: SchedulerTask) -> None:
        """Execute a single task with error handling and retries."""
        self._current_task = task
        start_time = datetime.utcnow()

        logger.info(f"Executing task: {task.task_id} ({task.task_type.value})")

        try:
            # Mark task as running
            await self.task_service.mark_started(task.task_id)

            # Get task handler
            handler = self._task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.task_type.value}")

            # Execute with timeout (5 minutes default)
            timeout = task.payload.get("timeout_seconds", 300)
            result = await asyncio.wait_for(
                handler(task),
                timeout=timeout
            )

            # Mark as completed
            await self.task_service.mark_completed(task.task_id)

            # Update metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.tasks_processed += 1
            self._update_execution_metrics(execution_time)

            # Record successful execution
            symbols = task.payload.get("symbols", [])
            await self.record_execution(
                task_name=task.task_type.value,
                task_id=task.task_id,
                symbols=symbols,
                status="completed",
                execution_time=execution_time
            )

            logger.info(f"Task completed: {task.task_id} ({execution_time:.2f}s)")

        except asyncio.TimeoutError:
            error_msg = f"Task execution timeout ({timeout}s)"
            logger.error(f"Task timeout: {task.task_id}")
            await self.task_service.mark_failed(task.task_id, error_msg)

            # Record failed execution due to timeout
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            symbols = task.payload.get("symbols", [])
            await self.record_execution(
                task_name=task.task_type.value,
                task_id=task.task_id,
                symbols=symbols,
                status="failed",
                error_message=error_msg,
                execution_time=execution_time
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task execution error: {task.task_id} - {error_msg}")

            # Handle retries
            if task.retry_count < task.max_retries:
                await self.task_service.retry_task(task.task_id)
                logger.info(f"Task queued for retry: {task.task_id} (attempt {task.retry_count + 1})")
            else:
                await self.task_service.mark_failed(task.task_id, error_msg)
                self.tasks_failed += 1

                # Record failed execution
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                symbols = task.payload.get("symbols", [])
                await self.record_execution(
                    task_name=task.task_type.value,
                    task_id=task.task_id,
                    symbols=symbols,
                    status="failed",
                    error_message=error_msg,
                    execution_time=execution_time
                )

        finally:
            self._current_task = None

    def _update_execution_metrics(self, execution_time: float) -> None:
        """Update execution time metrics."""
        if self.tasks_processed == 1:
            self.average_execution_time = execution_time
        else:
            # Rolling average
            self.average_execution_time = (
                (self.average_execution_time * (self.tasks_processed - 1)) + execution_time
            ) / self.tasks_processed

    def register_task_handler(self, task_type: TaskType, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for {task_type.value} in queue {self.queue_name.value}")

    async def create_task(
        self,
        task_type: TaskType,
        payload: Dict[str, Any],
        priority: int = 5,
        dependencies: Optional[List[str]] = None
    ) -> SchedulerTask:
        """Create a new task in this queue."""
        return await self.task_service.create_task(
            queue_name=self.queue_name,
            task_type=task_type,
            payload=payload,
            priority=priority,
            dependencies=dependencies
        )

    def get_status(self) -> Dict[str, Any]:
        """Get queue status."""
        return {
            "queue_name": self.queue_name.value,
            "running": self._running,
            "current_task": self._current_task.task_id if self._current_task else None,
            "registered_handlers": len(self._task_handlers),
            "metrics": {
                "tasks_processed": self.tasks_processed,
                "tasks_failed": self.tasks_failed,
                "average_execution_time": self.average_execution_time,
                "success_rate": (
                    self.tasks_processed / (self.tasks_processed + self.tasks_failed)
                    if (self.tasks_processed + self.tasks_failed) > 0 else 0
                )
            },
            "queue_specific": self.get_queue_specific_status()
        }

    def get_queue_specific_status(self) -> Dict[str, Any]:
        """Get queue-specific status (to be overridden by subclasses)."""
        return {}

    async def health_check(self) -> str:
        """Perform health check."""
        try:
            # Check if queue can create tasks
            test_task = await self.create_task(
                task_type=list(self._task_handlers.keys())[0],
                payload={"test": True}
            )

            # Clean up test task
            await self.task_service.mark_failed(test_task.task_id, "Test task")

            return "healthy"
        except Exception as e:
            logger.error(f"Health check failed for queue {self.queue_name.value}: {e}")
            return f"unhealthy: {e}"

    def is_running(self) -> bool:
        """Check if queue is running."""
        return self._running

    def get_current_task(self) -> Optional[SchedulerTask]:
        """Get currently executing task."""
        return self._current_task