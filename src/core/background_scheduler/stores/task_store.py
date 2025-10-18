"""
Task persistence layer for Background Scheduler.

Handles loading and saving background tasks to persistent storage.
"""

import json
from pathlib import Path
from typing import Dict

import aiofiles
from loguru import logger

from ..models import BackgroundTask, TaskType, TaskPriority


class TaskStore:
    """Manages task persistence with atomic writes."""

    @staticmethod
    async def load_tasks(state_dir: Path) -> Dict[str, BackgroundTask]:
        """Load all tasks from persistent storage.

        Args:
            state_dir: Directory containing scheduler_tasks.json

        Returns:
            Dictionary of task_id -> BackgroundTask
        """
        tasks = {}
        try:
            tasks_file = state_dir / "scheduler_tasks.json"
            if tasks_file.exists():
                async with aiofiles.open(tasks_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    tasks_data = json.loads(content)

                for task_data in tasks_data:
                    from datetime import datetime
                    task = BackgroundTask(
                        task_id=task_data["task_id"],
                        task_type=TaskType(task_data["task_type"]),
                        priority=TaskPriority(task_data["priority"]),
                        execute_at=datetime.fromisoformat(task_data["execute_at"]) if isinstance(task_data["execute_at"], str) else task_data["execute_at"],
                        interval_seconds=task_data.get("interval_seconds"),
                        metadata=task_data.get("metadata", {}),
                        is_active=task_data.get("is_active", True),
                        retry_count=task_data.get("retry_count", 0),
                        max_retries=task_data.get("max_retries", 3)
                    )

                    if task_data.get("last_executed"):
                        task.last_executed = datetime.fromisoformat(task_data["last_executed"]) if isinstance(task_data["last_executed"], str) else task_data["last_executed"]
                    if task_data.get("next_execution"):
                        task.next_execution = datetime.fromisoformat(task_data["next_execution"]) if isinstance(task_data["next_execution"], str) else task_data["next_execution"]

                    tasks[task.task_id] = task

                logger.info(f"Loaded {len(tasks)} tasks from storage")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

        return tasks

    @staticmethod
    async def save_all_tasks(state_dir: Path, tasks: Dict[str, BackgroundTask]) -> None:
        """Save all tasks to persistent storage with atomic write.

        Uses temp file + rename pattern for atomic writes as per project rules.

        Args:
            state_dir: Directory to store scheduler_tasks.json
            tasks: Dictionary of all tasks to persist
        """
        try:
            tasks_file = state_dir / "scheduler_tasks.json"
            temp_file = state_dir / "scheduler_tasks.json.tmp"

            tasks_data = []
            for t in tasks.values():
                task_dict = {
                    "task_id": t.task_id,
                    "task_type": t.task_type.value,
                    "priority": t.priority.value,
                    "execute_at": t.execute_at.isoformat() if hasattr(t.execute_at, 'isoformat') else t.execute_at,
                    "interval_seconds": t.interval_seconds,
                    "metadata": t.metadata,
                    "is_active": t.is_active,
                    "retry_count": t.retry_count,
                    "max_retries": t.max_retries
                }
                if t.last_executed:
                    task_dict["last_executed"] = t.last_executed.isoformat() if hasattr(t.last_executed, 'isoformat') else t.last_executed
                if t.next_execution:
                    task_dict["next_execution"] = t.next_execution.isoformat() if hasattr(t.next_execution, 'isoformat') else t.next_execution

                tasks_data.append(task_dict)

            async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(tasks_data, indent=2, ensure_ascii=False))

            import os
            os.replace(temp_file, tasks_file)

        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    @staticmethod
    async def save_task(state_dir: Path, tasks: Dict[str, BackgroundTask]) -> None:
        """Save all tasks to persistent storage.

        This is called after each task modification.

        Args:
            state_dir: Directory to store scheduler_tasks.json
            tasks: Dictionary of all tasks to persist
        """
        await TaskStore.save_all_tasks(state_dir, tasks)

    @staticmethod
    async def delete_task(state_dir: Path, tasks: Dict[str, BackgroundTask], task_id: str) -> None:
        """Delete a task from persistent storage.

        Args:
            state_dir: Directory containing scheduler_tasks.json
            tasks: Dictionary of all tasks
            task_id: ID of task to delete
        """
        if task_id in tasks:
            del tasks[task_id]
            await TaskStore.save_all_tasks(state_dir, tasks)
