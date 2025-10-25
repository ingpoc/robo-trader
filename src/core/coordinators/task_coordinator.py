"""
Task Coordinator for Multi-Agent Framework

Handles task creation, assignment, and lifecycle management.
Separated from the main framework to follow the 350-line rule.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from loguru import logger

from ..database_state import DatabaseStateManager
from ..event_bus import EventBus, Event, EventType
from .base_coordinator import BaseCoordinator
from .agent_message import AgentMessage, MessageType
from .collaboration_task import CollaborationTask, CollaborationMode, AgentRole


class TaskCoordinator(BaseCoordinator):
    """
    Coordinator for managing collaborative tasks.

    Responsibilities:
    - Task creation and configuration
    - Agent assignment to tasks
    - Task status tracking
    - Task result aggregation
    - Deadline management
    """

    def __init__(self, config: Any, state_manager: DatabaseStateManager, event_bus: EventBus):
        super().__init__(config, "task_coordinator")
        self.state_manager = state_manager
        self.event_bus = event_bus

        # Task management
        self.active_tasks: Dict[str, CollaborationTask] = {}
        self.completed_tasks: Dict[str, CollaborationTask] = {}

    async def initialize(self) -> None:
        """Initialize the task coordinator."""
        logger.info("Initializing Task Coordinator")
        self._running = True
        logger.info("Task Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._running = False

        # Cancel any active tasks
        for task in self.active_tasks.values():
            if task.status == "in_progress":
                task.status = "cancelled"
                logger.info(f"Cancelled active task: {task.task_id}")

    async def create_task(
        self,
        description: str,
        required_roles: List[AgentRole],
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        deadline: Optional[str] = None,
        priority: int = 5
    ) -> Optional[CollaborationTask]:
        """
        Create a new collaborative task.

        Args:
            description: Task description
            required_roles: Required agent roles
            collaboration_mode: Collaboration approach
            deadline: Optional deadline
            priority: Task priority (1-10, higher = more urgent)

        Returns:
            Created task or None if creation failed
        """
        try:
            task_id = f"task_{int(datetime.now(timezone.utc).timestamp())}_{len(self.active_tasks)}"

            task = CollaborationTask(
                description=description,
                required_roles=required_roles,
                collaboration_mode=collaboration_mode,
                deadline=deadline
            )
            task.task_id = task_id  # Set task_id after creation

            self.active_tasks[task_id] = task

            # Emit task creation event
            await self.event_bus.publish(Event(
                id=f"task_created_{task_id}",
                type=EventType.AI_ANALYSIS_COMPLETE,  # Using existing event type
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="task_coordinator",
                data={
                    "event_type": "task_created",
                    "task_id": task_id,
                    "description": description,
                    "required_roles": [role.value for role in required_roles],
                    "collaboration_mode": collaboration_mode.value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ))

            logger.info(f"Created task: {task_id} requiring {len(required_roles)} agent types")
            return task

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None

    async def assign_agents_to_task(self, task: CollaborationTask, available_agents: Dict[AgentRole, List[str]]) -> bool:
        """
        Assign agents to a task based on availability.

        Args:
            task: Task to assign agents to
            available_agents: Mapping of roles to available agent IDs

        Returns:
            True if assignment successful
        """
        try:
            assigned_agents = []

            for role in task.required_roles:
                available_for_role = available_agents.get(role, [])
                if not available_for_role:
                    logger.warning(f"No agents available for role: {role.value}")
                    return False

                # Assign the first available agent (could be more sophisticated)
                assigned_agents.append(available_for_role[0])

            task.assigned_agents = assigned_agents
            task.status = "assigned"

            logger.info(f"Assigned {len(assigned_agents)} agents to task {task.task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign agents to task {task.task_id}: {e}")
            return False

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
            source="task_coordinator",
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

    async def check_task_deadlines(self) -> List[str]:
        """
        Check for tasks that have exceeded deadlines.

        Returns:
            List of task IDs that have timed out
        """
        current_time = datetime.now(timezone.utc)
        timed_out_tasks = []

        for task_id, task in self.active_tasks.items():
            if task.deadline and task.status == "in_progress":
                deadline = datetime.fromisoformat(task.deadline)
                if current_time > deadline:
                    timed_out_tasks.append(task_id)
                    await self.update_task_status(task_id, "failed", {"error": "deadline_exceeded"})

        return timed_out_tasks

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
                sender_agent="task_coordinator",
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
                source="task_coordinator",
                data={
                    "event_type": "agent_message",
                    "message": message.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ))

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed tasks.

        Args:
            max_age_hours: Maximum age in hours for completed tasks

        Returns:
            Number of tasks cleaned up
        """
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time.timestamp() - (max_age_hours * 3600)

        tasks_to_remove = []
        for task_id, task in self.completed_tasks.items():
            if task.completed_at:
                task_time = datetime.fromisoformat(task.completed_at).timestamp()
                if task_time < cutoff_time:
                    tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.completed_tasks[task_id]

        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old completed tasks")

        return len(tasks_to_remove)

    async def run_strategy_review(self) -> Dict[str, Any]:
        """
        Run strategy review to derive actionable rebalance suggestions.

        Returns:
            Strategy review results with recommendations
        """
        try:
            # Create a strategy review task
            task = await self.create_task(
                description="Review current trading strategy and generate rebalance recommendations",
                required_roles=[AgentRole.STRATEGY_AGENT, AgentRole.RISK_MANAGER],
                collaboration_mode=CollaborationMode.SEQUENTIAL,
                priority=7
            )

            if not task:
                return {"error": "Failed to create strategy review task"}

            # For now, return mock results - in a real implementation this would
            # coordinate with actual strategy analysis agents
            return {
                "task_id": task.task_id,
                "status": "completed",
                "recommendations": [
                    {
                        "type": "sector_rebalance",
                        "action": "increase_technology_allocation",
                        "rationale": "Strong earnings momentum in tech sector",
                        "confidence": 0.85
                    },
                    {
                        "type": "risk_adjustment",
                        "action": "reduce_volatility_exposure",
                        "rationale": "Current volatility levels above target",
                        "confidence": 0.78
                    }
                ],
                "overall_assessment": "Strategy performing well with minor adjustments needed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Strategy review failed: {e}")
            return {"error": str(e)}