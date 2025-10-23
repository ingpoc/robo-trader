"""Database store for scheduler tasks and queues."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..core.database import execute_query, execute_update
from ..models.scheduler import (
    SchedulerTask, QueueName, TaskType, TaskStatus, QueueStatistics
)

logger = logging.getLogger(__name__)


class SchedulerTaskStore:
    """Database operations for scheduler tasks and queues."""

    def __init__(self, db_pool):
        """Initialize store with database pool."""
        self.db_pool = db_pool

    async def create_task(
        self,
        queue_name: QueueName,
        task_type: TaskType,
        payload: Dict[str, Any],
        priority: int = 5,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3
    ) -> SchedulerTask:
        """Create a new scheduler task."""
        task_id = f"{queue_name.value}_{task_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        query = """
            INSERT INTO queue_tasks (
                task_id, queue_name, task_type, priority, payload, dependencies,
                max_retries, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
            RETURNING task_id, created_at
        """

        dependencies_json = dependencies or []
        payload_json = payload or {}

        row = await execute_query(
            self.db_pool, query, task_id, queue_name.value, task_type.value,
            priority, payload_json, dependencies_json, max_retries, single=True
        )

        task = SchedulerTask(
            task_id=task_id,
            queue_name=queue_name,
            task_type=task_type,
            priority=priority,
            payload=payload,
            dependencies=dependencies or [],
            max_retries=max_retries,
            created_at=row['created_at'].isoformat() if row['created_at'] else None
        )

        logger.info(f"Created task in database: {task_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[SchedulerTask]:
        """Get task by ID."""
        query = """
            SELECT task_id, queue_name, task_type, priority, payload, dependencies,
                   status, retry_count, max_retries, scheduled_at, started_at,
                   completed_at, error_message, duration_ms, created_at, updated_at
            FROM queue_tasks
            WHERE task_id = $1
        """

        row = await execute_query(self.db_pool, query, task_id, single=True)
        if not row:
            return None

        return SchedulerTask.from_dict({
            "task_id": row["task_id"],
            "queue_name": row["queue_name"],
            "task_type": row["task_type"],
            "priority": row["priority"],
            "payload": row["payload"] or {},
            "dependencies": row["dependencies"] or [],
            "status": row["status"],
            "retry_count": row["retry_count"],
            "max_retries": row["max_retries"],
            "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            "error_message": row["error_message"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    async def get_pending_tasks(self, queue_name: QueueName) -> List[SchedulerTask]:
        """Get all pending tasks for a queue."""
        query = """
            SELECT task_id, queue_name, task_type, priority, payload, dependencies,
                   status, retry_count, max_retries, scheduled_at, started_at,
                   completed_at, error_message, duration_ms, created_at, updated_at
            FROM queue_tasks
            WHERE queue_name = $1 AND status IN ('PENDING', 'RETRYING')
            ORDER BY priority DESC, created_at ASC
        """

        rows = await execute_query(self.db_pool, query, queue_name.value)
        tasks = []

        for row in rows:
            task = SchedulerTask.from_dict({
                "task_id": row["task_id"],
                "queue_name": row["queue_name"],
                "task_type": row["task_type"],
                "priority": row["priority"],
                "payload": row["payload"] or {},
                "dependencies": row["dependencies"] or [],
                "status": row["status"],
                "retry_count": row["retry_count"],
                "max_retries": row["max_retries"],
                "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "error_message": row["error_message"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
            tasks.append(task)

        return tasks

    async def mark_started(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as started."""
        query = """
            UPDATE queue_tasks
            SET status = 'RUNNING', started_at = NOW(), updated_at = NOW()
            WHERE task_id = $1
            RETURNING task_id, started_at
        """

        row = await execute_query(self.db_pool, query, task_id, single=True)
        if row:
            task = await self.get_task(task_id)
            logger.info(f"Marked task as started: {task_id}")
            return task
        return None

    async def mark_completed(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as completed."""
        query = """
            UPDATE queue_tasks
            SET status = 'COMPLETED', completed_at = NOW(),
                duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000,
                updated_at = NOW()
            WHERE task_id = $1
            RETURNING task_id, completed_at, duration_ms
        """

        row = await execute_query(self.db_pool, query, task_id, single=True)
        if row:
            task = await self.get_task(task_id)
            logger.info(f"Marked task as completed: {task_id}")
            return task
        return None

    async def mark_failed(self, task_id: str, error: str) -> Optional[SchedulerTask]:
        """Mark task as failed."""
        query = """
            UPDATE queue_tasks
            SET status = 'FAILED', error_message = $2, completed_at = NOW(),
                duration_ms = CASE
                    WHEN started_at IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                    ELSE NULL
                END,
                updated_at = NOW()
            WHERE task_id = $1
            RETURNING task_id
        """

        row = await execute_query(self.db_pool, query, task_id, error, single=True)
        if row:
            task = await self.get_task(task_id)
            logger.info(f"Marked task as failed: {task_id}")
            return task
        return None

    async def increment_retry(self, task_id: str) -> Optional[SchedulerTask]:
        """Increment retry count and reset task for retry."""
        query = """
            UPDATE queue_tasks
            SET retry_count = retry_count + 1, status = 'PENDING',
                started_at = NULL, error_message = NULL, updated_at = NOW()
            WHERE task_id = $1 AND retry_count < max_retries
            RETURNING task_id, retry_count
        """

        row = await execute_query(self.db_pool, query, task_id, single=True)
        if row:
            task = await self.get_task(task_id)
            logger.info(f"Incremented retry for task: {task_id} (attempt {row['retry_count']})")
            return task
        return None

    async def get_queue_statistics(self, queue_name: QueueName) -> QueueStatistics:
        """Get statistics for a queue."""
        # Get task counts by status
        query = """
            SELECT status, COUNT(*) as count
            FROM queue_tasks
            WHERE queue_name = $1
            GROUP BY status
        """

        status_counts = await execute_query(self.db_pool, query, queue_name.value)
        status_dict = {row['status']: row['count'] for row in status_counts}

        # Get average duration for completed tasks
        duration_query = """
            SELECT AVG(duration_ms) as avg_duration,
                   MAX(completed_at) as last_completed_at
            FROM queue_tasks
            WHERE queue_name = $1 AND status = 'COMPLETED'
              AND completed_at >= CURRENT_DATE
        """

        duration_row = await execute_query(self.db_pool, duration_query, queue_name.value, single=True)

        # Get last completed task
        last_task_query = """
            SELECT task_id
            FROM queue_tasks
            WHERE queue_name = $1 AND status = 'COMPLETED'
            ORDER BY completed_at DESC
            LIMIT 1
        """

        last_task_row = await execute_query(self.db_pool, last_task_query, queue_name.value, single=True)

        return QueueStatistics(
            queue_name=queue_name,
            pending_count=status_dict.get('PENDING', 0) + status_dict.get('RETRYING', 0),
            running_count=status_dict.get('RUNNING', 0),
            completed_today=status_dict.get('COMPLETED', 0),  # This should be filtered by today
            failed_count=status_dict.get('FAILED', 0),
            average_duration_ms=duration_row['avg_duration'] or 0.0 if duration_row else 0.0,
            last_completed_task_id=last_task_row['task_id'] if last_task_row else None,
            last_completed_at=duration_row['last_completed_at'].isoformat() if duration_row and duration_row['last_completed_at'] else None
        )

    async def get_completed_task_ids_today(self) -> List[str]:
        """Get IDs of tasks completed today."""
        query = """
            SELECT task_id
            FROM queue_tasks
            WHERE status = 'COMPLETED'
              AND DATE(completed_at) = CURRENT_DATE
        """

        rows = await execute_query(self.db_pool, query)
        return [row['task_id'] for row in rows]

    async def cleanup_old_tasks(self, days_to_keep: int = 7) -> int:
        """Clean up old completed tasks."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        query = """
            DELETE FROM queue_tasks
            WHERE status IN ('COMPLETED', 'FAILED')
              AND completed_at < $1
        """

        result = await execute_update(self.db_pool, query, cutoff_date)
        logger.info(f"Cleaned up {result} old tasks older than {days_to_keep} days")
        return result

    async def get_failed_tasks_for_retry(self, max_age_hours: int = 1) -> List[SchedulerTask]:
        """Get failed tasks that can be retried."""
        query = """
            SELECT task_id, queue_name, task_type, priority, payload, dependencies,
                   status, retry_count, max_retries, scheduled_at, started_at,
                   completed_at, error_message, duration_ms, created_at, updated_at
            FROM queue_tasks
            WHERE status = 'FAILED'
              AND retry_count < max_retries
              AND completed_at > NOW() - INTERVAL '%s hours'
            ORDER BY priority DESC, completed_at ASC
        """ % max_age_hours

        rows = await execute_query(self.db_pool, query)
        tasks = []

        for row in rows:
            task = SchedulerTask.from_dict({
                "task_id": row["task_id"],
                "queue_name": row["queue_name"],
                "task_type": row["task_type"],
                "priority": row["priority"],
                "payload": row["payload"] or {},
                "dependencies": row["dependencies"] or [],
                "status": row["status"],
                "retry_count": row["retry_count"],
                "max_retries": row["max_retries"],
                "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "error_message": row["error_message"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
            tasks.append(task)

        return tasks