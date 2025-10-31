"""Database store for scheduler tasks and queues."""

import logging
import aiosqlite
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..models.scheduler import (
    SchedulerTask, QueueName, TaskType, TaskStatus, QueueStatistics
)

logger = logging.getLogger(__name__)


class SchedulerTaskStore:
    """Database operations for scheduler tasks and queues."""

    def __init__(self, db_connection):
        """Initialize store with database connection."""
        self.db_connection = db_connection

    async def initialize(self) -> None:
        """Initialize the store."""
        await self.initialize_schema()

    async def initialize_schema(self) -> None:
        """Initialize database schema if it doesn't exist."""
        # Create queue_tasks table
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS queue_tasks (
                task_id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                payload TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                scheduled_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes for performance
        await self.db_connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_tasks_queue_name
            ON queue_tasks(queue_name)
        """)

        await self.db_connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_tasks_status
            ON queue_tasks(status)
        """)

        await self.db_connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_tasks_scheduled_at
            ON queue_tasks(scheduled_at)
        """)

        await self.db_connection.commit()
        logger.info("Scheduler task store schema initialized")

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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """

        dependencies_json = dependencies or []
        payload_json = payload or {}

        self.db_connection.row_factory = aiosqlite.Row
        await self.db_connection.execute(
            query, (task_id, queue_name.value, task_type.value,
                   priority, str(payload_json), str(dependencies_json), max_retries)
        )
        await self.db_connection.commit()

        task = SchedulerTask(
            task_id=task_id,
            queue_name=queue_name,
            task_type=task_type,
            priority=priority,
            payload=payload,
            dependencies=dependencies or [],
            max_retries=max_retries,
            created_at=datetime.utcnow().isoformat()
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
        # For now, return default statistics since queue_tasks table may not exist
        # This is a simplified implementation for the monitoring API
        return QueueStatistics(
            queue_name=queue_name,
            pending_count=0,
            running_count=0,
            completed_today=0,
            failed_count=0,
            average_duration_ms=0.0,
            last_completed_task_id=None,
            last_completed_at=None
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