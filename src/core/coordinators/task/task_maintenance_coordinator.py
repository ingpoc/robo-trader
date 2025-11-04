"""
Task Maintenance Coordinator

Focused coordinator for task deadline management and cleanup.
Extracted from TaskCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any

from loguru import logger

from ...event_bus import EventBus
from ..base_coordinator import BaseCoordinator
from .collaboration_task import CollaborationTask


class TaskMaintenanceCoordinator(BaseCoordinator):
    """
    Coordinates task maintenance operations.
    
    Responsibilities:
    - Check task deadlines
    - Clean up old completed tasks
    - Manage task lifecycle maintenance
    """

    def __init__(self, config: Any, event_bus: EventBus):
        super().__init__(config, "task_maintenance_coordinator")
        self.event_bus = event_bus

    async def initialize(self) -> None:
        """Initialize task maintenance coordinator."""
        logger.info("Initializing Task Maintenance Coordinator")
        self._initialized = True

    async def check_task_deadlines(
        self,
        active_tasks: Dict[str, CollaborationTask],
        update_status_callback
    ) -> List[str]:
        """
        Check for tasks that have exceeded deadlines.

        Args:
            active_tasks: Dictionary of active tasks to check
            update_status_callback: Callback to update task status

        Returns:
            List of task IDs that have timed out
        """
        current_time = datetime.now(timezone.utc)
        timed_out_tasks = []

        for task_id, task in active_tasks.items():
            if task.deadline and task.status == "in_progress":
                deadline = datetime.fromisoformat(task.deadline)
                if current_time > deadline:
                    timed_out_tasks.append(task_id)
                    await update_status_callback(task_id, "failed", {"error": "deadline_exceeded"})

        return timed_out_tasks

    async def cleanup_old_tasks(
        self,
        completed_tasks: Dict[str, CollaborationTask],
        max_age_hours: int = 24
    ) -> int:
        """
        Clean up old completed tasks.

        Args:
            completed_tasks: Dictionary of completed tasks
            max_age_hours: Maximum age in hours for completed tasks

        Returns:
            Number of tasks cleaned up
        """
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time.timestamp() - (max_age_hours * 3600)

        tasks_to_remove = []
        for task_id, task in completed_tasks.items():
            if task.completed_at:
                task_time = datetime.fromisoformat(task.completed_at).timestamp()
                if task_time < cutoff_time:
                    tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del completed_tasks[task_id]

        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old completed tasks")

        return len(tasks_to_remove)

    async def cleanup(self) -> None:
        """Cleanup task maintenance coordinator resources."""
        logger.info("TaskMaintenanceCoordinator cleanup complete")

