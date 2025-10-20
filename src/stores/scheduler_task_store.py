"""Data store for scheduler tasks and queues."""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import aiosqlite
import json

from ..models.scheduler import SchedulerTask, QueueName, TaskStatus, TaskType, QueueStatistics

logger = logging.getLogger(__name__)


class SchedulerTaskStore:
    """Async store for scheduler tasks."""

    def __init__(self, db_path: str):
        """Initialize store with database path."""
        self.db_path = db_path

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
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()
        deps = json.dumps(dependencies or [])

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scheduler_tasks (
                    task_id, queue_name, task_type, priority, payload, dependencies,
                    status, retry_count, max_retries, scheduled_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id, queue_name.value, task_type.value, priority,
                    json.dumps(payload), deps,
                    TaskStatus.PENDING.value, 0, max_retries, now, now
                )
            )
            await db.commit()

        logger.info(f"Created task: {task_id} ({task_type.value})")
        return await self.get_task(task_id)

    async def get_task(self, task_id: str) -> Optional[SchedulerTask]:
        """Get task by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM scheduler_tasks WHERE task_id = ?",
                (task_id,)
            )
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['payload'] = json.loads(data['payload'])
                data['dependencies'] = json.loads(data['dependencies'] or '[]')
                data['queue_name'] = QueueName(data['queue_name'])
                data['task_type'] = TaskType(data['task_type'])
                data['status'] = TaskStatus(data['status'])
                return SchedulerTask(**data)
        return None

    async def get_pending_tasks(self, queue_name: QueueName, limit: int = 100) -> List[SchedulerTask]:
        """Get pending tasks for a queue, ordered by priority."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM scheduler_tasks
                WHERE queue_name = ? AND status IN (?, ?)
                ORDER BY priority DESC, scheduled_at ASC
                LIMIT ?
                """,
                (queue_name.value, TaskStatus.PENDING.value, TaskStatus.RETRYING.value, limit)
            )
            rows = await cursor.fetchall()

        tasks = []
        for row in rows:
            data = dict(row)
            data['payload'] = json.loads(data['payload'])
            data['dependencies'] = json.loads(data['dependencies'] or '[]')
            data['queue_name'] = QueueName(data['queue_name'])
            data['task_type'] = TaskType(data['task_type'])
            data['status'] = TaskStatus(data['status'])
            tasks.append(SchedulerTask(**data))

        return tasks

    async def mark_started(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as started."""
        now = datetime.utcnow().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE scheduler_tasks
                SET status = ?, started_at = ?
                WHERE task_id = ?
                """,
                (TaskStatus.RUNNING.value, now, task_id)
            )
            await db.commit()

        return await self.get_task(task_id)

    async def mark_completed(self, task_id: str) -> Optional[SchedulerTask]:
        """Mark task as completed."""
        now = datetime.utcnow().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE scheduler_tasks
                SET status = ?, completed_at = ?
                WHERE task_id = ?
                """,
                (TaskStatus.COMPLETED.value, now, task_id)
            )
            await db.commit()

        return await self.get_task(task_id)

    async def mark_failed(self, task_id: str, error: str) -> Optional[SchedulerTask]:
        """Mark task as failed."""
        task = await self.get_task(task_id)
        if not task:
            return None

        # Determine if we should retry
        if task.retry_count < task.max_retries:
            new_status = TaskStatus.RETRYING
        else:
            new_status = TaskStatus.FAILED

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE scheduler_tasks
                SET status = ?, error_message = ?
                WHERE task_id = ?
                """,
                (new_status.value, error, task_id)
            )
            await db.commit()

        return await self.get_task(task_id)

    async def increment_retry(self, task_id: str) -> Optional[SchedulerTask]:
        """Increment retry counter and reset status to pending."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE scheduler_tasks
                SET retry_count = retry_count + 1, status = ?, started_at = NULL, error_message = NULL
                WHERE task_id = ?
                """,
                (TaskStatus.PENDING.value, task_id)
            )
            await db.commit()

        return await self.get_task(task_id)

    async def get_queue_statistics(self, queue_name: QueueName) -> QueueStatistics:
        """Get statistics for a queue."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Count tasks by status
            cursor = await db.execute(
                """
                SELECT
                    COUNT(CASE WHEN status = ? THEN 1 END) as pending,
                    COUNT(CASE WHEN status = ? THEN 1 END) as running,
                    COUNT(CASE WHEN status = ? THEN 1 END) as failed,
                    COUNT(CASE WHEN status = ? THEN 1 END) as completed_today
                FROM scheduler_tasks
                WHERE queue_name = ? AND created_at >= date('now')
                """,
                (
                    TaskStatus.PENDING.value, TaskStatus.RUNNING.value,
                    TaskStatus.FAILED.value, TaskStatus.COMPLETED.value,
                    queue_name.value
                )
            )
            stats_row = await cursor.fetchone()

            # Get last completed task
            cursor = await db.execute(
                """
                SELECT task_id, completed_at FROM scheduler_tasks
                WHERE queue_name = ? AND status = ?
                ORDER BY completed_at DESC
                LIMIT 1
                """,
                (queue_name.value, TaskStatus.COMPLETED.value)
            )
            last_completed = await cursor.fetchone()

            # Calculate average duration
            cursor = await db.execute(
                """
                SELECT AVG(CAST((julianday(completed_at) - julianday(started_at)) * 86400000 AS INTEGER)) as avg_ms
                FROM scheduler_tasks
                WHERE queue_name = ? AND status = ? AND completed_at IS NOT NULL
                """,
                (queue_name.value, TaskStatus.COMPLETED.value)
            )
            duration_row = await cursor.fetchone()

        return QueueStatistics(
            queue_name=queue_name,
            pending_count=stats_row['pending'] if stats_row else 0,
            running_count=stats_row['running'] if stats_row else 0,
            completed_today=stats_row['completed_today'] if stats_row else 0,
            failed_count=stats_row['failed'] if stats_row else 0,
            average_duration_ms=duration_row['avg_ms'] or 0.0 if duration_row else 0.0,
            last_completed_task_id=last_completed['task_id'] if last_completed else None,
            last_completed_at=last_completed['completed_at'] if last_completed else None
        )

    async def get_completed_task_ids_today(self) -> List[str]:
        """Get all completed task IDs from today."""
        today = datetime.utcnow().strftime("%Y-%m-%d")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT task_id FROM scheduler_tasks
                WHERE status = ? AND created_at >= ?
                """,
                (TaskStatus.COMPLETED.value, today)
            )
            rows = await cursor.fetchall()

        return [row[0] for row in rows]

    async def cleanup_old_tasks(self, days_to_keep: int = 7) -> int:
        """Delete old completed tasks."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM scheduler_tasks
                WHERE status = ? AND completed_at < datetime('now', '-' || ? || ' days')
                """,
                (TaskStatus.COMPLETED.value, days_to_keep)
            )
            await db.commit()
            return cursor.rowcount
