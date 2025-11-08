"""Thread-safe queue executor for non-blocking task execution.

This module provides ThreadSafeQueueExecutor that executes tasks in background
threads while maintaining async coordination on the main event loop.

Architecture:
- Tasks execute in dedicated worker threads (one per queue)
- Status updates callback to main event loop via run_coroutine_threadsafe()
- Main event loop stays responsive for HTTP requests and WebSocket broadcasts
- Graceful shutdown waits for thread termination with timeout protection

This design prevents long-running tasks (e.g., 5-10 minute Claude analysis)
from blocking the entire FastAPI event loop.
"""

import asyncio
import logging
import threading
import traceback
from typing import Optional, Dict, Any, Callable, Coroutine
from datetime import datetime

from ...models.scheduler import SchedulerTask, TaskStatus
from .task_service import SchedulerTaskService

logger = logging.getLogger(__name__)


class ThreadSafeQueueExecutor:
    """Execute queue tasks in a background thread with async coordination.

    Pattern:
    1. Main event loop calls async start() to spawn worker thread
    2. Worker thread executes tasks sequentially (blocking is OK here)
    3. Task completion/failure triggers callback to main event loop
    4. Main event loop updates database/broadcast status without thread blocking
    5. Main event loop stays responsive for HTTP requests
    """

    def __init__(
        self,
        queue_name: str,
        task_service: SchedulerTaskService,
        loop: asyncio.AbstractEventLoop,
        on_task_complete: Optional[Callable[[SchedulerTask], Coroutine]] = None,
        on_task_failed: Optional[Callable[[SchedulerTask, str], Coroutine]] = None
    ):
        """Initialize executor.

        Args:
            queue_name: Name of queue (e.g., 'ai_analysis')
            task_service: Task service for task management
            loop: Event loop reference for callback scheduling
            on_task_complete: Optional callback when task completes
            on_task_failed: Optional callback when task fails
        """
        self.queue_name = queue_name
        self.task_service = task_service
        self.loop = loop
        self.on_task_complete = on_task_complete
        self.on_task_failed = on_task_failed

        # Thread management
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()

        # Current task tracking
        self._current_task: Optional[SchedulerTask] = None
        self._lock = threading.Lock()  # Thread-safe access to _current_task

        # Execution history
        self._execution_history: list = []
        self._history_lock = threading.Lock()

    async def start(self) -> None:
        """Start the executor thread asynchronously.

        Pattern:
        1. Create thread in background
        2. Thread runs _run_queue_loop() (blocking execution)
        3. Callbacks use run_coroutine_threadsafe() to return to async
        4. Main coroutine returns immediately (non-blocking)
        """
        if self._running:
            logger.warning(f"Executor for {self.queue_name} already running")
            return

        self._running = True
        self._stop_event.clear()

        # Start worker thread (runs _run_queue_loop synchronously)
        self._thread = threading.Thread(
            target=self._run_queue_loop,
            name=f"QueueExecutor-{self.queue_name}",
            daemon=False
        )
        self._thread.start()

        logger.info(f"Started queue executor for {self.queue_name} (thread: {self._thread.name})")

    async def stop(self, timeout_seconds: int = 30) -> None:
        """Stop the executor and wait for thread to finish.

        Args:
            timeout_seconds: Max seconds to wait for thread termination
        """
        if not self._running:
            return

        logger.info(f"Stopping queue executor for {self.queue_name}")

        # Signal thread to stop
        self._stop_event.set()
        self._running = False

        # Wait for thread with timeout
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)

            if self._thread.is_alive():
                logger.error(f"Queue executor thread {self.queue_name} did not stop within {timeout_seconds}s")
            else:
                logger.info(f"Queue executor thread {self.queue_name} stopped cleanly")

    def _run_queue_loop(self) -> None:
        """Execute queue tasks sequentially in worker thread (BLOCKING).

        This runs in a separate thread, so blocking operations are safe here.
        All async callbacks go back to main event loop via run_coroutine_threadsafe().
        """
        logger.debug(f"Queue loop started for {self.queue_name}")
        max_iterations = 1000
        iteration = 0

        try:
            while not self._stop_event.is_set() and iteration < max_iterations:
                iteration += 1

                try:
                    # Get pending tasks (blocking call in thread is OK)
                    pending_tasks = asyncio.run_coroutine_threadsafe(
                        self.task_service.get_pending_tasks(queue_name=self.queue_name),
                        self.loop
                    ).result(timeout=10.0)  # 10s timeout for async call

                    if not pending_tasks:
                        logger.debug(f"{self.queue_name}: No pending tasks, waiting...")
                        self._stop_event.wait(timeout=1.0)  # Check again in 1s
                        continue

                    # Execute first task (highest priority)
                    task = pending_tasks[0]
                    logger.info(f"{self.queue_name}: Executing task {task.task_id}")
                    self._execute_task_sync(task)

                except asyncio.TimeoutError:
                    logger.error(f"{self.queue_name}: Timeout fetching pending tasks")
                except Exception as e:
                    logger.error(f"{self.queue_name}: Error in queue loop: {e}")
                    traceback.print_exc()

        except Exception as e:
            logger.error(f"{self.queue_name}: Unexpected error in queue loop: {e}")
            traceback.print_exc()
        finally:
            logger.debug(f"Queue loop exited for {self.queue_name}")

    def _execute_task_sync(self, task: SchedulerTask) -> None:
        """Execute a single task synchronously (runs in worker thread).

        Args:
            task: Task to execute
        """
        with self._lock:
            self._current_task = task

        start_time = datetime.utcnow()

        try:
            logger.info(f"Executing task: {task.task_id} ({task.task_type.value}) in thread")

            # Execute task synchronously (blocking is OK in worker thread)
            result = asyncio.run_coroutine_threadsafe(
                self._execute_task_with_timeout(task),
                self.loop
            ).result(timeout=920.0)  # 900s task + 20s overhead

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Log execution
            with self._history_lock:
                self._execution_history.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "timestamp": end_time.isoformat()
                })

            logger.info(f"Task completed: {task.task_id} ({duration_ms}ms)")

            # Call on_complete callback if provided
            if self.on_task_complete:
                asyncio.run_coroutine_threadsafe(
                    self.on_task_complete(task),
                    self.loop
                )

        except asyncio.TimeoutError:
            logger.error(f"Task timeout: {task.task_id} (>900s)")
            self._schedule_callback_mark_failed(task, "Task execution timeout (>900s)")

            with self._history_lock:
                self._execution_history.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "status": "timeout",
                    "duration_ms": 900000,
                    "timestamp": datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Task execution error: {task.task_id} - {e}")
            traceback.print_exc()
            self._schedule_callback_mark_failed(task, str(e))

            with self._history_lock:
                self._execution_history.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

        finally:
            with self._lock:
                self._current_task = None

    async def _execute_task_with_timeout(self, task: SchedulerTask) -> Any:
        """Execute task with timeout protection.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        try:
            result = await asyncio.wait_for(
                self.task_service.execute_task(task),
                timeout=900.0  # 15 minutes max
            )
            return result
        except asyncio.TimeoutError:
            raise  # Re-raise for caller to handle
        except Exception as e:
            raise  # Re-raise for caller to handle

    def _schedule_callback_mark_failed(self, task: SchedulerTask, error_msg: str) -> None:
        """Schedule mark_failed callback to main event loop.

        Args:
            task: Task that failed
            error_msg: Error message
        """
        async def mark_failed():
            try:
                await self.task_service.mark_failed(task.task_id, error_msg)
                if self.on_task_failed:
                    await self.on_task_failed(task, error_msg)
            except Exception as e:
                logger.error(f"Error marking task failed: {e}")

        asyncio.run_coroutine_threadsafe(mark_failed(), self.loop)

    def get_current_task(self) -> Optional[SchedulerTask]:
        """Get currently executing task (thread-safe).

        Returns:
            Current task or None
        """
        with self._lock:
            return self._current_task

    def is_running(self) -> bool:
        """Check if executor is running.

        Returns:
            True if executor thread is running
        """
        return self._running and (self._thread is not None and self._thread.is_alive())

    def get_execution_history(self, limit: int = 100) -> list:
        """Get execution history (thread-safe).

        Args:
            limit: Max number of records to return

        Returns:
            Recent execution history
        """
        with self._history_lock:
            return self._execution_history[-limit:]

    async def get_status(self) -> Dict[str, Any]:
        """Get executor status.

        Returns:
            Status dictionary
        """
        return {
            "queue_name": self.queue_name,
            "running": self.is_running(),
            "current_task": self.get_current_task().task_id if self.get_current_task() else None,
            "thread_alive": self._thread is not None and self._thread.is_alive(),
            "recent_history": self.get_execution_history(limit=10)
        }
