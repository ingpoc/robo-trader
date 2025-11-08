"""Task repository for individual task queries.

Provides detailed task-level queries that complement QueueStateRepository.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from .base_repository import BaseRepository
from ..models.domain import TaskState
from ..models.scheduler import TaskStatus, QueueName

logger = logging.getLogger(__name__)


class TaskRepository(BaseRepository[TaskState]):
    """Repository for task-level queries.

    Responsibilities:
    - Query individual tasks
    - Get task lists with filtering
    - Task history and analytics

    Note: Task creation/updates still go through SchedulerTaskStore
          This repository is READ-ONLY for status queries.
    """

    async def initialize(self) -> None:
        """Initialize repository."""
        await super().initialize()
        logger.info("TaskRepository initialized (read-only queries)")

    async def get_task(self, task_id: str) -> Optional[TaskState]:
        """Get single task by ID.

        Args:
            task_id: Task identifier

        Returns:
            TaskState or None if not found
        """
        query = """
            SELECT *
            FROM scheduler_tasks
            WHERE task_id = :task_id
        """

        row = await self._fetch_one(query, {"task_id": task_id})

        if not row:
            return None

        return TaskState.from_db_row(row)

    async def get_pending_tasks(
        self,
        queue_name: str,
        limit: int = 10
    ) -> List[TaskState]:
        """Get pending tasks for a queue, ordered by priority.

        Args:
            queue_name: Queue name
            limit: Maximum number of tasks

        Returns:
            List of pending TaskState objects, highest priority first
        """
        query = """
            SELECT *
            FROM scheduler_tasks
            WHERE queue_name = :queue_name
              AND status = 'pending'
            ORDER BY priority DESC, scheduled_at ASC
            LIMIT :limit
        """

        rows = await self._fetch_all(
            query,
            {"queue_name": queue_name, "limit": limit}
        )

        return [TaskState.from_db_row(row) for row in rows]

    async def get_running_tasks(
        self,
        queue_name: Optional[str] = None
    ) -> List[TaskState]:
        """Get all currently running tasks.

        Args:
            queue_name: Optional queue filter

        Returns:
            List of running TaskState objects
        """
        if queue_name:
            query = """
                SELECT *
                FROM scheduler_tasks
                WHERE queue_name = :queue_name
                  AND status = 'running'
                ORDER BY started_at ASC
            """
            params = {"queue_name": queue_name}
        else:
            query = """
                SELECT *
                FROM scheduler_tasks
                WHERE status = 'running'
                ORDER BY started_at ASC
            """
            params = {}

        rows = await self._fetch_all(query, params)
        return [TaskState.from_db_row(row) for row in rows]

    async def get_tasks_by_status(
        self,
        status: str,
        queue_name: Optional[str] = None,
        limit: int = 100
    ) -> List[TaskState]:
        """Get tasks filtered by status.

        Args:
            status: Task status (pending, running, completed, failed)
            queue_name: Optional queue filter
            limit: Maximum number of tasks

        Returns:
            List of TaskState objects
        """
        if queue_name:
            query = """
                SELECT *
                FROM scheduler_tasks
                WHERE queue_name = :queue_name
                  AND status = :status
                ORDER BY scheduled_at DESC
                LIMIT :limit
            """
            params = {"queue_name": queue_name, "status": status, "limit": limit}
        else:
            query = """
                SELECT *
                FROM scheduler_tasks
                WHERE status = :status
                ORDER BY scheduled_at DESC
                LIMIT :limit
            """
            params = {"status": status, "limit": limit}

        rows = await self._fetch_all(query, params)
        return [TaskState.from_db_row(row) for row in rows]

    async def get_task_history(
        self,
        queue_name: Optional[str] = None,
        task_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[TaskState]:
        """Get task execution history with filters.

        Args:
            queue_name: Optional queue filter
            task_type: Optional task type filter
            hours: Look back period in hours
            limit: Maximum number of tasks

        Returns:
            List of TaskState objects, most recent first
        """
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Build dynamic query based on filters
        conditions = ["scheduled_at >= :since"]
        params: Dict[str, Any] = {"since": since, "limit": limit}

        if queue_name:
            conditions.append("queue_name = :queue_name")
            params["queue_name"] = queue_name

        if task_type:
            conditions.append("task_type = :task_type")
            params["task_type"] = task_type

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT *
            FROM scheduler_tasks
            WHERE {where_clause}
            ORDER BY scheduled_at DESC
            LIMIT :limit
        """

        rows = await self._fetch_all(query, params)
        return [TaskState.from_db_row(row) for row in rows]

    async def get_task_statistics(
        self,
        queue_name: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get aggregated task statistics.

        Args:
            queue_name: Optional queue filter
            hours: Look back period in hours

        Returns:
            Dictionary with statistics:
            - total_tasks: Total tasks in period
            - completed_tasks: Completed count
            - failed_tasks: Failed count
            - avg_duration_ms: Average duration
            - success_rate: Percentage successful
        """
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        if queue_name:
            query = """
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks,
                    AVG(CASE
                        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400000
                        ELSE NULL
                    END) as avg_duration_ms
                FROM scheduler_tasks
                WHERE queue_name = :queue_name
                  AND scheduled_at >= :since
            """
            params = {"queue_name": queue_name, "since": since}
        else:
            query = """
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks,
                    AVG(CASE
                        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400000
                        ELSE NULL
                    END) as avg_duration_ms
                FROM scheduler_tasks
                WHERE scheduled_at >= :since
            """
            params = {"since": since}

        result = await self._fetch_one(query, params)

        if not result or result['total_tasks'] == 0:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "avg_duration_ms": 0.0,
                "success_rate": 0.0
            }

        total = result['total_tasks']
        completed = result['completed_tasks'] or 0
        failed = result['failed_tasks'] or 0
        finished = completed + failed

        success_rate = (completed / finished * 100.0) if finished > 0 else 0.0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "avg_duration_ms": result['avg_duration_ms'] or 0.0,
            "success_rate": success_rate
        }

    async def count_tasks_by_status(
        self,
        queue_name: Optional[str] = None
    ) -> Dict[str, int]:
        """Count tasks grouped by status.

        Args:
            queue_name: Optional queue filter

        Returns:
            Dictionary mapping status -> count
        """
        if queue_name:
            query = """
                SELECT status, COUNT(*) as count
                FROM scheduler_tasks
                WHERE queue_name = :queue_name
                GROUP BY status
            """
            params = {"queue_name": queue_name}
        else:
            query = """
                SELECT status, COUNT(*) as count
                FROM scheduler_tasks
                GROUP BY status
            """
            params = {}

        rows = await self._fetch_all(query, params)

        # Build status counts
        counts = {
            TaskStatus.PENDING.value: 0,
            TaskStatus.RUNNING.value: 0,
            TaskStatus.COMPLETED.value: 0,
            TaskStatus.FAILED.value: 0,
            TaskStatus.RETRYING.value: 0
        }

        for row in rows:
            counts[row['status']] = row['count']

        return counts
