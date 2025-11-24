"""Scheduler task service for queue management."""

import logging
import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta

from ...models.scheduler import SchedulerTask, QueueName, TaskType, TaskStatus, QueueStatistics
from ...stores.scheduler_task_store import SchedulerTaskStore

logger = logging.getLogger(__name__)


class TaskValidator:
    """Validate task payloads before execution (Phase 2-3: Early validation)."""

    @staticmethod
    def _validate_symbol(symbol: str, field_name: str = "symbol") -> None:
        """Validate a single symbol value.

        Args:
            symbol: Symbol to validate
            field_name: Name of field being validated (for error messages)

        Raises:
            ValueError: If validation fails
        """
        # Type check
        if not isinstance(symbol, str):
            raise ValueError(f"Invalid {field_name} type: expected str, got {type(symbol).__name__}")

        # Length check
        if not symbol or len(symbol) > 10:
            raise ValueError(f"Invalid {field_name} length: '{symbol}' (must be 1-10 chars)")

        # Format check (alphanumeric and dash only)
        if not symbol.replace("-", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid {field_name} format: '{symbol}' (must be alphanumeric, dash, or dot)")

    @staticmethod
    def validate_stock_analysis_task(task: 'SchedulerTask') -> None:
        """Validate STOCK_ANALYSIS task payload (supports both single and batch).

        Phase 3: Supports batch processing with 'symbols' array OR legacy 'symbol' field.

        Raises:
            ValueError: If validation fails
        """
        payload = task.payload or {}

        # Support both single symbol (legacy) and symbols array (Phase 3: batch)
        symbols = None

        # Priority: symbols array > symbol string
        if "symbols" in payload:
            symbols = payload.get("symbols")
            if not isinstance(symbols, list):
                raise ValueError("'symbols' must be a list of strings")
            if not symbols:
                raise ValueError("'symbols' list cannot be empty")
            if len(symbols) > 10:
                raise ValueError(f"'symbols' list too large: {len(symbols)} (max 10)")

            # Validate each symbol
            for i, symbol in enumerate(symbols):
                try:
                    TaskValidator._validate_symbol(symbol, f"symbols[{i}]")
                except ValueError as e:
                    raise ValueError(f"Invalid symbol in batch: {e}")

            logger.debug(f"Validated STOCK_ANALYSIS batch task: {len(symbols)} symbols")

        elif "symbol" in payload:
            # Legacy single-symbol mode
            symbol = payload.get("symbol")
            TaskValidator._validate_symbol(symbol, "symbol")
            logger.debug(f"Validated STOCK_ANALYSIS task: symbol='{symbol}'")

        else:
            raise ValueError("Missing required field: 'symbol' or 'symbols'")

    @staticmethod
    def validate_task(task: 'SchedulerTask') -> None:
        """Validate task based on task type.

        Raises:
            ValueError: If validation fails
        """
        task_type_value = task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type)

        # STOCK_ANALYSIS tasks require symbol validation
        if task_type_value in ["stock_analysis", "recommendation_generation", "comprehensive_stock_analysis"]:
            TaskValidator.validate_stock_analysis_task(task)


class RetryScheduler:
    """Manages automatic task retries with exponential backoff."""

    def __init__(self):
        """Initialize retry scheduler."""
        self._pending_retries: Dict[str, float] = {}  # task_id -> retry_time_unix
        self._retry_monitor_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the retry monitor."""
        if self._running:
            return
        self._running = True
        self._retry_monitor_task = asyncio.create_task(self._monitor_retries())
        logger.info("RetryScheduler started")

    async def stop(self) -> None:
        """Stop the retry monitor."""
        self._running = False
        if self._retry_monitor_task:
            self._retry_monitor_task.cancel()
            try:
                await self._retry_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("RetryScheduler stopped")

    async def schedule_retry(self, task_id: str, retry_count: int) -> None:
        """Schedule a task for retry with exponential backoff."""
        # Exponential backoff: 1s → 5s → 30s → 300s
        backoff_seconds = min(300, 2 ** (retry_count - 1))
        retry_time = datetime.utcnow().timestamp() + backoff_seconds
        self._pending_retries[task_id] = retry_time
        logger.info(f"Task {task_id} scheduled for retry in {backoff_seconds}s (attempt {retry_count})")

    async def _monitor_retries(self) -> None:
        """Monitor and execute scheduled retries."""
        while self._running:
            try:
                now = datetime.utcnow().timestamp()
                ready_tasks = [
                    task_id for task_id, retry_time in self._pending_retries.items()
                    if retry_time <= now
                ]

                for task_id in ready_tasks:
                    del self._pending_retries[task_id]
                    # Signal that this task is ready for retry (service will pick it up)
                    logger.debug(f"Retry timer expired for task: {task_id}")

                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry monitor: {e}")
                await asyncio.sleep(5)


class SchedulerTaskService:
    """Manage scheduler tasks and queues."""

    def __init__(self, store: SchedulerTaskStore, execution_tracker=None):
        """Initialize service."""
        self.store = store
        self.execution_tracker = execution_tracker
        self._task_handlers: Dict[TaskType, Callable] = {}
        self._retry_scheduler = RetryScheduler()

    async def initialize(self) -> None:
        """Initialize the task service."""
        await self.store.initialize()
        await self._retry_scheduler.start()

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        await self._retry_scheduler.stop()

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
        max_retries: int = 3
    ) -> SchedulerTask:
        """Create new scheduler task."""
        task = await self.store.create_task(
            queue_name=queue_name,
            task_type=task_type,
            payload=payload,
            priority=priority,
            dependencies=dependencies,
            max_retries=max_retries
        )
        # Handle both enum and string inputs for robustness
        queue_value = queue_name.value if hasattr(queue_name, 'value') else str(queue_name)
        logger.info(f"Created task: {task.task_id} in queue {queue_value}")
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
            queue_value = queue_name.value if hasattr(queue_name, 'value') else str(queue_name)
            stats[queue_value] = await self.get_queue_statistics(queue_name)
        return stats

    async def get_pending_tasks(
        self,
        queue_name: QueueName,
        completed_task_ids: Optional[List[str]] = None
    ) -> List[SchedulerTask]:
        """Get pending tasks for queue that are ready to run."""
        completed = completed_task_ids or []
        all_pending = await self.store.get_pending_tasks(queue_name)
        queue_value = queue_name.value if hasattr(queue_name, 'value') else str(queue_name)
        logger.debug(f"get_pending_tasks() for {queue_value}: store returned {len(all_pending)} tasks")

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
        """Mark task as failed and schedule retry if applicable."""
        task = await self.store.mark_failed(task_id, error)

        # Auto-schedule retry if max retries not exceeded
        if task and task.retry_count < task.max_retries:
            logger.warning(f"Task failed, scheduling retry: {task_id} - {error}")
            # Increment retry counter and reset task to pending
            task = await self.store.increment_retry(task_id)
            if task:
                # Schedule the retry with exponential backoff
                await self._retry_scheduler.schedule_retry(task_id, task.retry_count)
                return task
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

        # Validate task payload early (Phase 2: Fail-fast on bad payloads)
        try:
            TaskValidator.validate_task(task)
        except ValueError as e:
            error_msg = f"Task validation failed: {e}"
            logger.error(f"Validation error for {task.task_id}: {error_msg}")
            await self.mark_failed(task.task_id, error_msg)
            return {"success": False, "error": error_msg}

        # Get handler
        handler = self._task_handlers.get(task.task_type)
        if not handler:
            task_type_value = task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type)
            error = f"No handler registered for task type: {task_type_value}"
            await self.mark_failed(task.task_id, error)
            return {"success": False, "error": error}

        # Execute with timeout (180 seconds = 3 minutes max per task)
        # Reduced from 900s to enable fail-fast detection
        # Single stock analysis should complete in 2-3 minutes
        try:
            result = await asyncio.wait_for(handler(task), timeout=180.0)
            await self.mark_completed(task.task_id)
            return {"success": True, "result": result}
        except asyncio.TimeoutError:
            error_msg = f"Task execution timed out after 180 seconds"
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
