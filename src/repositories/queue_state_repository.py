"""Queue state repository for efficient queue status queries.

Single source of truth for all queue status information.
Uses optimized SQL queries to aggregate task data into QueueState objects.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta

from .base_repository import BaseRepository
from ..models.domain import QueueState, QueueStatus
from ..models.scheduler import QueueName

logger = logging.getLogger(__name__)


class QueueStateRepository(BaseRepository[QueueState]):
    """Repository for queue state queries.

    Responsibilities:
    - Aggregate task data into queue status
    - Provide single source of truth for queue state
    - Optimize queries for performance (single query for all queues)

    Pattern:
        All queue status queries go through this repository.
        No in-memory state tracking - always query database.
    """

    async def initialize(self) -> None:
        """Initialize repository (tables created by SchedulerTaskStore)."""
        await super().initialize()
        logger.info("QueueStateRepository initialized (uses existing scheduler_tasks table)")

    async def get_status(self, queue_name: str) -> QueueState:
        """Get current status for a specific queue.

        Single efficient query that aggregates all task counts.

        Args:
            queue_name: Name of queue (e.g., "ai_analysis")

        Returns:
            QueueState with current status snapshot

        Raises:
            Exception: If query fails
        """
        self._log_query("get_status", f"Getting status for queue: {queue_name}")

        today_start = self._get_today_start().isoformat()
        snapshot_ts = self._get_timestamp()

        # Single aggregation query for all counts
        query = """
            SELECT
                -- Task counts by status
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count,
                SUM(CASE WHEN status = 'completed' AND completed_at >= :today_start
                    THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,

                -- Performance metrics
                AVG(CASE
                    WHEN status = 'completed' AND completed_at >= :today_start
                    THEN (julianday(completed_at) - julianday(started_at)) * 86400000
                    ELSE NULL
                END) as avg_duration_ms,

                -- Last activity timestamp
                MAX(CASE WHEN completed_at IS NOT NULL THEN completed_at ELSE NULL END) as last_activity
            FROM scheduler_tasks
            WHERE queue_name = :queue_name
        """

        result = await self._fetch_one(
            query,
            {"queue_name": queue_name, "today_start": today_start}
        )

        if not result:
            # Queue has no tasks yet - return empty state
            return QueueState.from_aggregation(
                queue_name=queue_name,
                pending=0,
                running=0,
                completed=0,
                failed=0,
                avg_duration=None,
                last_activity=None,
                snapshot_ts=snapshot_ts
            )

        # Get current running task (if any)
        current_task = await self._get_current_task(queue_name)

        return QueueState.from_aggregation(
            queue_name=queue_name,
            pending=result['pending_count'] or 0,
            running=result['running_count'] or 0,
            completed=result['completed_count'] or 0,
            failed=result['failed_count'] or 0,
            avg_duration=result['avg_duration_ms'],
            last_activity=result['last_activity'],
            current_task=current_task,
            snapshot_ts=snapshot_ts
        )

    async def get_all_statuses(self) -> Dict[str, QueueState]:
        """Get status for ALL queues in a single optimized query.

        This is the most efficient method for getting queue status.
        Uses single query with GROUP BY instead of N queries.

        Returns:
            Dictionary mapping queue_name -> QueueState

        Performance:
            - 1 query for all queue aggregations
            - 1 query for all current tasks
            Total: 2 queries regardless of number of queues
        """
        self._log_query("get_all_statuses", "Getting status for all queues")

        today_start = self._get_today_start().isoformat()
        snapshot_ts = self._get_timestamp()

        # Single aggregation query for ALL queues
        query = """
            SELECT
                queue_name,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count,
                SUM(CASE WHEN status = 'completed' AND completed_at >= :today_start
                    THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                AVG(CASE
                    WHEN status = 'completed' AND completed_at >= :today_start
                    THEN (julianday(completed_at) - julianday(started_at)) * 86400000
                    ELSE NULL
                END) as avg_duration_ms,
                MAX(CASE WHEN completed_at IS NOT NULL THEN completed_at ELSE NULL END) as last_activity
            FROM scheduler_tasks
            GROUP BY queue_name
        """

        rows = await self._fetch_all(query, {"today_start": today_start})

        # Get all current tasks in single query
        current_tasks = await self._get_all_current_tasks()

        # Build QueueState objects
        states: Dict[str, QueueState] = {}

        # Add states for queues with tasks
        for row in rows:
            queue_name = row['queue_name']
            current_task = current_tasks.get(queue_name)

            states[queue_name] = QueueState.from_aggregation(
                queue_name=queue_name,
                pending=row['pending_count'] or 0,
                running=row['running_count'] or 0,
                completed=row['completed_count'] or 0,
                failed=row['failed_count'] or 0,
                avg_duration=row['avg_duration_ms'],
                last_activity=row['last_activity'],
                current_task=current_task,
                snapshot_ts=snapshot_ts
            )

        # Add empty states for queues with no tasks
        for queue_enum in QueueName:
            queue_name = queue_enum.value
            if queue_name not in states:
                states[queue_name] = QueueState.from_aggregation(
                    queue_name=queue_name,
                    pending=0,
                    running=0,
                    completed=0,
                    failed=0,
                    avg_duration=None,
                    last_activity=None,
                    snapshot_ts=snapshot_ts
                )

        return states

    async def get_queue_statistics_summary(self) -> Dict[str, int]:
        """Get high-level statistics across all queues.

        Returns:
            Dictionary with summary statistics:
            - total_queues: Number of queues
            - total_pending: Total pending tasks across all queues
            - total_running: Total running tasks
            - total_completed_today: Total completed today
            - total_failed: Total failed tasks
        """
        today_start = self._get_today_start().isoformat()

        query = """
            SELECT
                COUNT(DISTINCT queue_name) as total_queues,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as total_pending,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as total_running,
                SUM(CASE WHEN status = 'completed' AND completed_at >= :today_start
                    THEN 1 ELSE 0 END) as total_completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as total_failed
            FROM scheduler_tasks
        """

        result = await self._fetch_one(query, {"today_start": today_start})

        if not result:
            return {
                "total_queues": 0,
                "total_pending": 0,
                "total_running": 0,
                "total_completed_today": 0,
                "total_failed": 0
            }

        return {
            "total_queues": result['total_queues'] or 0,
            "total_pending": result['total_pending'] or 0,
            "total_running": result['total_running'] or 0,
            "total_completed_today": result['total_completed'] or 0,
            "total_failed": result['total_failed'] or 0
        }

    async def _get_current_task(self, queue_name: str) -> Optional[Dict[str, str]]:
        """Get currently running task for a queue.

        Args:
            queue_name: Queue name

        Returns:
            Dictionary with task details or None
        """
        query = """
            SELECT task_id, task_type, started_at
            FROM scheduler_tasks
            WHERE queue_name = :queue_name
              AND status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """

        result = await self._fetch_one(query, {"queue_name": queue_name})
        return result

    async def _get_all_current_tasks(self) -> Dict[str, Dict[str, str]]:
        """Get all currently running tasks across all queues.

        Returns:
            Dictionary mapping queue_name -> task details
        """
        query = """
            SELECT queue_name, task_id, task_type, started_at
            FROM scheduler_tasks
            WHERE status = 'running'
            ORDER BY started_at DESC
        """

        rows = await self._fetch_all(query)

        # Build mapping (only keep first task per queue)
        current_tasks: Dict[str, Dict[str, str]] = {}
        for row in rows:
            queue_name = row['queue_name']
            if queue_name not in current_tasks:
                current_tasks[queue_name] = {
                    'task_id': row['task_id'],
                    'task_type': row['task_type'],
                    'started_at': row['started_at']
                }

        return current_tasks

    async def get_recent_completed_tasks(
        self,
        queue_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, any]]:
        """Get recently completed tasks for analysis.

        Args:
            queue_name: Optional queue name filter
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries
        """
        if queue_name:
            query = """
                SELECT task_id, task_type, queue_name,
                       started_at, completed_at,
                       (julianday(completed_at) - julianday(started_at)) * 86400000 as duration_ms
                FROM scheduler_tasks
                WHERE queue_name = :queue_name
                  AND status = 'completed'
                ORDER BY completed_at DESC
                LIMIT :limit
            """
            params = {"queue_name": queue_name, "limit": limit}
        else:
            query = """
                SELECT task_id, task_type, queue_name,
                       started_at, completed_at,
                       (julianday(completed_at) - julianday(started_at)) * 86400000 as duration_ms
                FROM scheduler_tasks
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT :limit
            """
            params = {"limit": limit}

        return await self._fetch_all(query, params)

    async def get_failed_tasks(
        self,
        queue_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, any]]:
        """Get failed tasks for debugging.

        Args:
            queue_name: Optional queue name filter
            limit: Maximum number of tasks to return

        Returns:
            List of failed task dictionaries
        """
        if queue_name:
            query = """
                SELECT task_id, task_type, queue_name, status,
                       started_at, error_message, retry_count
                FROM scheduler_tasks
                WHERE queue_name = :queue_name
                  AND status = 'failed'
                ORDER BY started_at DESC
                LIMIT :limit
            """
            params = {"queue_name": queue_name, "limit": limit}
        else:
            query = """
                SELECT task_id, task_type, queue_name, status,
                       started_at, error_message, retry_count
                FROM scheduler_tasks
                WHERE status = 'failed'
                ORDER BY started_at DESC
                LIMIT :limit
            """
            params = {"limit": limit}

        return await self._fetch_all(query, params)
