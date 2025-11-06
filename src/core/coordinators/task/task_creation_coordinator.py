"""
Task Creation Coordinator

Focused coordinator for task creation and agent assignment.
Extracted from TaskCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ...event_bus import Event, EventBus, EventType
from ..base_coordinator import BaseCoordinator
from .collaboration_task import AgentRole, CollaborationMode, CollaborationTask


class TaskCreationCoordinator(BaseCoordinator):
    """
    Coordinates task creation and agent assignment.

    Responsibilities:
    - Create new collaborative tasks
    - Assign agents to tasks
    - Emit task creation events
    """

    def __init__(self, config: Any, event_bus: EventBus):
        super().__init__(config, "task_creation_coordinator")
        self.event_bus = event_bus

    async def initialize(self) -> None:
        """Initialize task creation coordinator."""
        logger.info("Initializing Task Creation Coordinator")
        self._initialized = True

    async def create_task(
        self,
        description: str,
        required_roles: List[AgentRole],
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        deadline: Optional[str] = None,
        priority: int = 5,
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
            task_id = f"task_{int(datetime.now(timezone.utc).timestamp())}_{id(self)}"

            task = CollaborationTask(
                description=description,
                required_roles=required_roles,
                collaboration_mode=collaboration_mode,
                deadline=deadline,
            )
            task.task_id = task_id  # Set task_id after creation

            # Emit task creation event
            await self.event_bus.publish(
                Event(
                    id=f"task_created_{task_id}",
                    type=EventType.AI_ANALYSIS_COMPLETE,  # Using existing event type
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="task_creation_coordinator",
                    data={
                        "event_type": "task_created",
                        "task_id": task_id,
                        "description": description,
                        "required_roles": [role.value for role in required_roles],
                        "collaboration_mode": collaboration_mode.value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

            logger.info(
                f"Created task: {task_id} requiring {len(required_roles)} agent types"
            )
            return task

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None

    async def assign_agents_to_task(
        self, task: CollaborationTask, available_agents: Dict[AgentRole, List[str]]
    ) -> bool:
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

            logger.info(
                f"Assigned {len(assigned_agents)} agents to task {task.task_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to assign agents to task {task.task_id}: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup task creation coordinator resources."""
        logger.info("TaskCreationCoordinator cleanup complete")
