"""
Task persistence layer for Background Scheduler.

Handles loading and saving background tasks to the database.
Migrated from file-based storage to database storage.
"""

import json
from datetime import datetime
from typing import Dict
from pathlib import Path

from loguru import logger

from ..models import BackgroundTask, TaskType, TaskPriority


class TaskStore:
    """Manages task persistence with database storage."""

    def __init__(self, db_connection):
        """Initialize store with database connection.

        Args:
            db_connection: Active database connection
        """
        self.db = db_connection

    @staticmethod
    def _to_datetime(value):
        """Convert value to datetime if it's a string, otherwise return as-is."""
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                logger.warning(f"Failed to parse datetime string: {value}")
                return value
        return value

    @staticmethod
    async def load_tasks(db_connection) -> Dict[str, BackgroundTask]:
        """Load all tasks from database storage.

        Args:
            db_connection: Active database connection

        Returns:
            Dictionary of task_id -> BackgroundTask
        """
        tasks = {}
        try:
            query = """
                SELECT task_id, task_type, priority, execute_at, interval_seconds,
                       max_retries, retry_count, last_executed, next_execution,
                       is_active, metadata
                FROM scheduler_background_tasks
                WHERE is_active = TRUE
                ORDER BY execute_at ASC
            """

            cursor = await db_connection.execute(query)
            rows = await cursor.fetchall()

            for row in rows:
                task = BackgroundTask(
                    task_id=row[0],
                    task_type=TaskType(row[1]),
                    priority=TaskPriority(row[2]),
                    execute_at=TaskStore._to_datetime(row[3]),
                    interval_seconds=row[4],
                    max_retries=row[5] or 3,
                    retry_count=row[6] or 0,
                    last_executed=TaskStore._to_datetime(row[7]) if row[7] else None,
                    next_execution=TaskStore._to_datetime(row[8]) if row[8] else None,
                    is_active=row[9],
                    metadata=row[10] or {}
                )
                tasks[task.task_id] = task

            logger.info(f"Loaded {len(tasks)} tasks from database")
        except Exception as e:
            logger.error(f"Failed to load tasks from database: {e}")

        return tasks

    @staticmethod
    async def save_all_tasks(db_connection, tasks: Dict[str, BackgroundTask]) -> None:
        """Save all tasks to database storage.

        Args:
            db_connection: Active database connection
            tasks: Dictionary of all tasks to persist
        """
        try:
            # Clear existing tasks
            await db_connection.execute("DELETE FROM scheduler_background_tasks")

            # Insert all tasks
            for task in tasks.values():
                query = """
                    INSERT INTO scheduler_background_tasks (
                        task_id, task_type, priority, execute_at, interval_seconds,
                        max_retries, retry_count, last_executed, next_execution,
                        is_active, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                await db_connection.execute(
                    query,
                    (
                        task.task_id,
                        task.task_type.value,
                        task.priority.value,
                        task.execute_at.isoformat() if hasattr(task.execute_at, 'isoformat') else task.execute_at,
                        task.interval_seconds,
                        task.max_retries,
                        task.retry_count,
                        task.last_executed.isoformat() if task.last_executed and hasattr(task.last_executed, 'isoformat') else task.last_executed,
                        task.next_execution.isoformat() if task.next_execution and hasattr(task.next_execution, 'isoformat') else task.next_execution,
                        task.is_active,
                        json.dumps(task.metadata),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ),
                )

            await db_connection.commit()
            logger.info(f"Saved {len(tasks)} tasks to database")

        except Exception as e:
            logger.error(f"Failed to save tasks to database: {e}")
            await db_connection.rollback()

    @staticmethod
    async def save_task(db_connection, tasks: Dict[str, BackgroundTask]) -> None:
        """Save all tasks to database storage.

        This is called after each task modification.

        Args:
            db_connection: Active database connection
            tasks: Dictionary of all tasks to persist
        """
        await TaskStore.save_all_tasks(db_connection, tasks)

    @staticmethod
    async def delete_task(db_connection, tasks: Dict[str, BackgroundTask], task_id: str) -> None:
        """Delete a task from database storage.

        Args:
            db_connection: Active database connection
            tasks: Dictionary of all tasks
            task_id: ID of task to delete
        """
        try:
            if task_id in tasks:
                del tasks[task_id]

            query = "DELETE FROM scheduler_background_tasks WHERE task_id = ?"
            await db_connection.execute(query, (task_id,))
            await db_connection.commit()

            logger.info(f"Deleted task {task_id} from database")
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            await db_connection.rollback()