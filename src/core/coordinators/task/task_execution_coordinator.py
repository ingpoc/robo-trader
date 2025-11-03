"""
Task Execution Coordinator

Focused coordinator for task execution and status management.
Extracted from TaskCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from loguru import logger

from ...event_bus import EventBus, Event, EventType
from ..base_coordinator import BaseCoordinator
from ..message.agent_message import AgentMessage, MessageType
from .collaboration_task import CollaborationTask


class TaskExecutionCoordinator(BaseCoordinator):
    """
    Coordinates task execution and status management.
    
    Responsibilities:
    - Start task execution
    - Update task status
    - Get task results
    - Notify agents of tasks
    """

    def __init__(self, config: Any, event_bus: EventBus):
        super().__init__(config, "task_execution_coordinator")
        self.event_bus = event_bus
        self.active_tasks: Dict[str, CollaborationTask] = {}
        self.completed_tasks: Dict[str, CollaborationTask] = {}

    async def initialize(self) -> None:
        """Initialize task execution coordinator."""
        logger.info("Initializing Task Execution Coordinator")
        self._initialized = True

    def register_task(self, task: CollaborationTask) -> None:
        """Register a task for execution."""
        self.active_tasks[task.task_id] = task

    async def start_task(self, task: CollaborationTask) -> None:
        """
        Start execution of a task.

        Args:
            task: Task to start
        """
        if task.status != "assigned":
            logger.warning(f"Cannot start task {task.task_id} with status: {task.status}")
            return

        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc).isoformat()

        # Notify assigned agents
        await self._notify_agents_of_task(task)

        logger.info(f"Started task: {task.task_id}")

    async def update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> None:
        """
        Update task status.

        Args:
            task_id: ID of the task
            status: New status
            result: Optional result data
        """
        task = self.active_tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return

        old_status = task.status
        task.status = status

        if result:
            task.result = result

        if status in ["completed", "failed", "cancelled"]:
            task.completed_at = datetime.now(timezone.utc).isoformat()
            # Move to completed tasks
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]

        # Emit status change event
        await self.event_bus.publish(Event(
            id=f"task_status_{task_id}_{status}",
            type=EventType.AI_ANALYSIS_COMPLETE,  # Using existing event type
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="task_execution_coordinator",
            data={
                "event_type": "task_status_changed",
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "has_result": result is not None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ))

        logger.info(f"Task {task_id} status changed: {old_status} -> {status}")

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get result of a completed task.

        Args:
            task_id: ID of the task

        Returns:
            Task result or None
        """
        # Check active tasks first
        task = self.active_tasks.get(task_id)
        if task and task.status == "completed":
            return task.result

        # Check completed tasks
        task = self.completed_tasks.get(task_id)
        if task and task.status == "completed":
            return task.result

        return None

    async def get_active_tasks(self) -> List[CollaborationTask]:
        """Get all active tasks."""
        return list(self.active_tasks.values())

    async def get_task_by_id(self, task_id: str) -> Optional[CollaborationTask]:
        """Get task by ID."""
        return self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)

    async def _notify_agents_of_task(self, task: CollaborationTask) -> None:
        """
        Notify assigned agents about a task.

        Args:
            task: Task to notify agents about
        """
        for agent_id in task.assigned_agents:
            message = AgentMessage(
                message_id=f"task_assign_{task.task_id}_{agent_id}",
                sender_agent="task_execution_coordinator",
                recipient_agent=agent_id,
                message_type=MessageType.TASK_ASSIGNMENT,
                content={
                    "task": task.to_dict(),
                    "action": "start_task",
                    "priority": task.priority
                },
                correlation_id=task.task_id,
                priority=task.priority
            )

            # Emit message event (would be handled by agent coordinator)
            await self.event_bus.publish(Event(
                id=f"agent_message_{message.message_id}",
                type=EventType.AI_ANALYSIS_COMPLETE,  # Using existing event type
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="task_execution_coordinator",
                data={
                    "event_type": "agent_message",
                    "message": message.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ))

    async def cleanup(self) -> None:
        """Cleanup task execution coordinator resources."""
        self._running = False

        # Cancel any active tasks
        for task in self.active_tasks.values():
            if task.status == "in_progress":
                task.status = "cancelled"
                logger.info(f"Cancelled active task: {task.task_id}")

        logger.info("TaskExecutionCoordinator cleanup complete")

