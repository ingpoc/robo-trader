"""Database store for scheduler tasks and queues."""

import logging
import asyncio
import aiosqlite
import json
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
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the store."""
        await self.initialize_schema()

    async def initialize_schema(self) -> None:
        """Initialize database schema if it doesn't exist."""
        async with self._lock:
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
        async with self._lock:
            task_id = f"{queue_name.value}_{task_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

            query = """
                INSERT INTO queue_tasks (
                    task_id, queue_name, task_type, priority, payload, dependencies,
                    max_retries, scheduled_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
            """

            dependencies_json = json.dumps(dependencies or [])
            payload_json = json.dumps(payload or {})

            self.db_connection.row_factory = aiosqlite.Row
            await self.db_connection.execute(
                query, (task_id, queue_name.value, task_type.value,
                       priority, payload_json, dependencies_json, max_retries)
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

    async def _get_task_unlocked(self, task_id: str) -> Optional[SchedulerTask]:
        """Get task by ID (assumes lock is already held)."""
        query = """
            SELECT task_id, queue_name, task_type, priority, payload, dependencies,
                   status, retry_count, max_retries, scheduled_at, started_at,
                   completed_at, error_message, created_at, updated_at
            FROM queue_tasks
            WHERE task_id = ?
        """

        cursor = await self.db_connection.execute(query, (task_id,))
        row = await cursor.fetchone()

        if not row:
            return None

        # Handle payload - database returns as string, from_dict will parse it
        payload = row[4]
        if payload is None:
            payload = "{}"

        # Handle dependencies - database returns as string, from_dict will parse it
        dependencies = row[5]
        if dependencies is None:
            dependencies = "[]"

        return SchedulerTask.from_dict({
            "task_id": row[0],
            "queue_name": row[1],
            "task_type": row[2],
            "priority": row[3],
            "payload": payload,
            "dependencies": dependencies,
            "status": row[6],
            "retry_count": row[7],
            "max_retries": row[8],
            "scheduled_at": row[9],
            "started_at": row[10],
            "completed_at": row[11],
            "error_message": row[12],
            "created_at": row[13],
        })

    async def get_task(self, task_id: str) -> Optional[SchedulerTask]:
        """Get task by ID."""
        async with self._lock:
            return await self._get_task_unlocked(task_id)

    async def get_pending_tasks(self, queue_name: QueueName) -> List[SchedulerTask]:
        """Get all pending tasks for a queue."""
        async with self._lock:
            query = """
                SELECT task_id, queue_name, task_type, priority, payload, dependencies,
                       status, retry_count, max_retries, scheduled_at, started_at,
                       completed_at, error_message, created_at, updated_at
                FROM queue_tasks
                WHERE queue_name = ? AND status IN ('pending', 'retrying')
                ORDER BY priority DESC, created_at ASC
            """

            cursor = await self.db_connection.execute(query, (queue_name.value,))
            rows = await cursor.fetchall()
            tasks = []

            for row in rows:
                # Handle payload - database returns as string, from_dict will parse it
                payload = row[4]
                if payload is None:
                    payload = "{}"

                # Handle dependencies - database returns as string, from_dict will parse it
                dependencies = row[5]
                if dependencies is None:
                    dependencies = "[]"

                task = SchedulerTask.from_dict({
                    "task_id": row[0],
                    "queue_name": row[1],
                    "task_type": row[2],
                    "priority": row[3],
                    "payload": payload,
                    "dependencies": dependencies,
                    "status": row[6],
                    "retry_count": row[7],
                    "max_retries": row[8],
                    "scheduled_at": row[9],
                    "started_at": row[10],
                    "completed_at": row[11],
                    "error_message": row[12],
                    "created_at": row[13],
                })
                tasks.append(task)

            return tasks

    async def mark_started(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as started."""
        async with self._lock:
            query = """
                UPDATE queue_tasks
                SET status = 'running', started_at = datetime('now'), updated_at = datetime('now')
                WHERE task_id = ?
            """

            await self.db_connection.execute(query, (task_id,))
            await self.db_connection.commit()

            task = await self._get_task_unlocked(task_id)
            if task:
                logger.info(f"Marked task as started: {task_id}")
            return task

    async def mark_completed(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as completed."""
        async with self._lock:
            query = """
                UPDATE queue_tasks
                SET status = 'completed', completed_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE task_id = ?
            """

            await self.db_connection.execute(query, (task_id,))
            await self.db_connection.commit()

            task = await self._get_task_unlocked(task_id)
            if task:
                logger.info(f"Marked task as completed: {task_id}")
            return task

    async def mark_failed(self, task_id: str, error: str) -> Optional[SchedulerTask]:
        """Mark task as failed."""
        async with self._lock:
            query = """
                UPDATE queue_tasks
                SET status = 'failed', error_message = ?, completed_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE task_id = ?
            """

            await self.db_connection.execute(query, (error, task_id))
            await self.db_connection.commit()

            task = await self._get_task_unlocked(task_id)
            if task:
                logger.info(f"Marked task as failed: {task_id}")
            return task

    async def increment_retry(self, task_id: str) -> Optional[SchedulerTask]:
        """Increment retry count and reset task for retry."""
        async with self._lock:
            query = """
                UPDATE queue_tasks
                SET retry_count = retry_count + 1, status = 'pending',
                    started_at = NULL, error_message = NULL, updated_at = datetime('now')
                WHERE task_id = ? AND retry_count < max_retries
            """

            await self.db_connection.execute(query, (task_id,))
            await self.db_connection.commit()

            task = await self._get_task_unlocked(task_id)
            if task:
                logger.info(f"Incremented retry for task: {task_id} (attempt {task.retry_count})")
            return task

    async def get_queue_statistics(self, queue_name: QueueName) -> QueueStatistics:
        """Get statistics for a queue."""
        async with self._lock:
            # Get pending tasks count
            pending_query = """
                SELECT COUNT(*) FROM queue_tasks
                WHERE queue_name = ? AND status = 'pending'
            """
            cursor = await self.db_connection.execute(pending_query, (queue_name.value,))
            pending_row = await cursor.fetchone()
            pending_count = pending_row[0] if pending_row else 0

            # Get running tasks count
            running_query = """
                SELECT COUNT(*) FROM queue_tasks
                WHERE queue_name = ? AND status = 'running'
            """
            cursor = await self.db_connection.execute(running_query, (queue_name.value,))
            running_row = await cursor.fetchone()
            running_count = running_row[0] if running_row else 0

            # Get completed tasks today
            completed_query = """
                SELECT COUNT(*) FROM queue_tasks
                WHERE queue_name = ? AND status = 'completed'
                  AND DATE(completed_at) = DATE('now')
            """
            cursor = await self.db_connection.execute(completed_query, (queue_name.value,))
            completed_row = await cursor.fetchone()
            completed_today = completed_row[0] if completed_row else 0

            # Get failed tasks count
            failed_query = """
                SELECT COUNT(*) FROM queue_tasks
                WHERE queue_name = ? AND status = 'failed'
            """
            cursor = await self.db_connection.execute(failed_query, (queue_name.value,))
            failed_row = await cursor.fetchone()
            failed_count = failed_row[0] if failed_row else 0

            # Get last completed task info
            last_completed_query = """
                SELECT task_id, completed_at FROM queue_tasks
                WHERE queue_name = ? AND status = 'completed'
                ORDER BY completed_at DESC LIMIT 1
            """
            cursor = await self.db_connection.execute(last_completed_query, (queue_name.value,))
            last_completed_row = await cursor.fetchone()
            last_completed_task_id = last_completed_row[0] if last_completed_row else None
            last_completed_at = last_completed_row[1] if last_completed_row else None

            return QueueStatistics(
                queue_name=queue_name,
                pending_count=pending_count,
                running_count=running_count,
                completed_today=completed_today,
                failed_count=failed_count,
                average_duration_ms=0.0,  # TODO: Calculate average duration
                last_completed_task_id=last_completed_task_id,
                last_completed_at=last_completed_at
            )

    async def get_completed_task_ids_today(self) -> List[str]:
        """Get IDs of tasks completed today."""
        async with self._lock:
            query = """
                SELECT task_id
                FROM queue_tasks
                WHERE status = 'completed'
                  AND DATE(completed_at) = DATE('now')
            """

            cursor = await self.db_connection.execute(query)
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def cleanup_old_tasks(self, days_to_keep: int = 7) -> int:
        """Clean up old completed tasks."""
        async with self._lock:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            query = """
                DELETE FROM queue_tasks
                WHERE status IN ('completed', 'failed')
                  AND completed_at < ?
            """

            cursor = await self.db_connection.execute(query, (cutoff_date.isoformat(),))
            await self.db_connection.commit()

            deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            logger.info(f"Cleaned up {deleted_count} old tasks older than {days_to_keep} days")
            return deleted_count

    async def get_failed_tasks_for_retry(self, max_age_hours: int = 1) -> List[SchedulerTask]:
        """Get failed tasks that can be retried."""
        async with self._lock:
            query = """
                SELECT task_id, queue_name, task_type, priority, payload, dependencies,
                       status, retry_count, max_retries, scheduled_at, started_at,
                       completed_at, error_message, created_at, updated_at
                FROM queue_tasks
                WHERE status = 'failed'
                  AND retry_count < max_retries
                  AND completed_at > datetime('now', '-' || ? || ' hours')
                ORDER BY priority DESC, completed_at ASC
            """

            cursor = await self.db_connection.execute(query, (max_age_hours,))
            rows = await cursor.fetchall()
            tasks = []

            for row in rows:
                # Handle payload - database returns as string, from_dict will parse it
                payload = row[4]
                if payload is None:
                    payload = "{}"

                # Handle dependencies - database returns as string, from_dict will parse it
                dependencies = row[5]
                if dependencies is None:
                    dependencies = "[]"

                task = SchedulerTask.from_dict({
                    "task_id": row[0],
                    "queue_name": row[1],
                    "task_type": row[2],
                    "priority": row[3],
                    "payload": payload,
                    "dependencies": dependencies,
                    "status": row[6],
                    "retry_count": row[7],
                    "max_retries": row[8],
                    "scheduled_at": row[9],
                    "started_at": row[10],
                    "completed_at": row[11],
                    "error_message": row[12],
                    "created_at": row[13],
                })
                tasks.append(task)

            return tasks