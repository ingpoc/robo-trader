"""Sequential queue manager for task execution."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...models.scheduler import QueueName, SchedulerTask, TaskStatus
from .task_service import SchedulerTaskService

logger = logging.getLogger(__name__)


class SequentialQueueManager:
    """
    Manage queue execution with parallel queues and sequential tasks.
    
    Architecture Pattern:
    - 3 queues (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS) execute in PARALLEL
    - Tasks WITHIN each queue execute SEQUENTIALLY (one-at-a-time per queue)
    
    This prevents:
    - Turn limit exhaustion (AI_ANALYSIS tasks run sequentially)
    - Database contention (PORTFOLIO_SYNC tasks run sequentially)
    - Resource conflicts (each queue manages its own sequential execution)
    
    While allowing:
    - Parallel processing across different queue types
    - Better resource utilization
    - Independent queue execution
    """

    def __init__(self, task_service: SchedulerTaskService):
        """Initialize manager."""
        self.task_service = task_service
        self._running = False
        self._current_task: Optional[SchedulerTask] = None
        self._completed_task_ids: List[str] = []
        self._execution_history: List[Dict[str, Any]] = []

    async def execute_queues(self) -> None:
        """
        Execute all queues in parallel.
        
        Architecture Pattern:
        - 3 queues (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS) execute in PARALLEL
        - Tasks WITHIN each queue execute SEQUENTIALLY (one-at-a-time)
        
        This allows:
        - Portfolio sync, data fetching, and AI analysis to run simultaneously
        - Tasks within each queue execute in order (prevents turn limit exhaustion for AI)
        """
        if self._running:
            logger.warning("Queue execution already in progress")
            return

        self._running = True
        logger.info("Starting parallel queue execution (queues in parallel, tasks within queues sequential)")

        try:
            # Reload completed tasks from today
            self._completed_task_ids = await self.task_service.store.get_completed_task_ids_today()

            # Execute all queues in PARALLEL (not sequentially!)
            # Each queue processes its tasks sequentially internally
            queue_names = [
                QueueName.PORTFOLIO_SYNC,
                QueueName.DATA_FETCHER,
                QueueName.AI_ANALYSIS,
                # New workflow-specific queues
                QueueName.PORTFOLIO_ANALYSIS,
                QueueName.PAPER_TRADING_RESEARCH,
                QueueName.PAPER_TRADING_EXECUTION
            ]
            
            # Create tasks for parallel execution
            tasks = [self._execute_queue(queue_name) for queue_name in queue_names]
            
            # Execute all queues concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            for i, queue_name in enumerate(queue_names):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error(f"Queue {queue_name.value} failed: {result}")
                else:
                    logger.info(f"Queue {queue_name.value} completed successfully")

        except Exception as e:
            logger.error(f"Error in queue execution: {e}")
        finally:
            self._running = False
            logger.info("Parallel queue execution complete")

    async def _execute_queue(self, queue_name: QueueName) -> None:
        """Execute all tasks in a queue sequentially."""
        logger.debug(f"_execute_queue() called for {queue_name.value}")
        max_iterations = 1000  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Get next pending task
            pending_tasks = await self.task_service.get_pending_tasks(
                queue_name=queue_name,
                completed_task_ids=self._completed_task_ids
            )

            logger.debug(f"{queue_name.value}: Found {len(pending_tasks)} pending tasks")
            if not pending_tasks:
                logger.info(f"No more pending tasks in {queue_name.value}")
                break

            # Execute first task (highest priority)
            task = pending_tasks[0]
            logger.debug(f"{queue_name.value}: About to execute task {task.task_id}")
            logger.debug(f"{queue_name.value}: Task type={task.task_type.value}, payload keys={list(task.payload.keys())}")
            await self._execute_single_task(task)
            logger.debug(f"{queue_name.value}: Task execution completed for {task.task_id}")

            # Add to completed list
            if task.status == TaskStatus.COMPLETED:
                self._completed_task_ids.append(task.task_id)

    async def _execute_single_task(self, task: SchedulerTask) -> None:
        """Execute a single task with error handling."""
        logger.debug(f"_execute_single_task() ENTERED for {task.task_id}")
        self._current_task = task
        start_time = datetime.utcnow()

        logger.info(f"Executing task: {task.task_id} ({task.task_type.value})")

        try:
            logger.debug(f"About to call task_service.execute_task() for {task.task_id}")
            # Set timeout for task execution (max 15 minutes for AI analysis)
            # AI analysis on large portfolios can take 5-10+ minutes
            result = await asyncio.wait_for(
                self.task_service.execute_task(task),
                timeout=900.0  # 15 minutes
            )
            logger.debug(f"task_service.execute_task() COMPLETED for {task.task_id}")

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
            await self.task_service.mark_failed(task.task_id, "Task execution timeout (>900s)")
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
