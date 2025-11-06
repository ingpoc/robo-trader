"""
Task Coordinator (Refactored)

Thin orchestrator that delegates to focused task coordinators.
Refactored from 368-line monolith into focused coordinators.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ...database_state.database_state import DatabaseStateManager
from ...event_bus import EventBus
from ..base_coordinator import BaseCoordinator
from .collaboration_task import AgentRole, CollaborationMode, CollaborationTask
from .task_creation_coordinator import TaskCreationCoordinator
from .task_execution_coordinator import TaskExecutionCoordinator
from .task_maintenance_coordinator import TaskMaintenanceCoordinator


class TaskCoordinator(BaseCoordinator):
    """
    Coordinator for managing collaborative tasks.

    Responsibilities:
    - Orchestrate task operations from focused coordinators
    - Provide unified task management API
    """

    def __init__(
        self, config: Any, state_manager: DatabaseStateManager, event_bus: EventBus
    ):
        super().__init__(config, "task_coordinator")
        self.state_manager = state_manager
        self.event_bus = event_bus

        # Focused coordinators
        self.creation_coordinator = TaskCreationCoordinator(config, event_bus)
        self.execution_coordinator = TaskExecutionCoordinator(config, event_bus)
        self.maintenance_coordinator = TaskMaintenanceCoordinator(config, event_bus)

    async def initialize(self) -> None:
        """Initialize the task coordinator."""
        logger.info("Initializing Task Coordinator")

        await self.creation_coordinator.initialize()
        await self.execution_coordinator.initialize()
        await self.maintenance_coordinator.initialize()

        self._running = True
        logger.info("Task Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._running = False

        await self.creation_coordinator.cleanup()
        await self.execution_coordinator.cleanup()
        await self.maintenance_coordinator.cleanup()

    async def create_task(
        self,
        description: str,
        required_roles: List[AgentRole],
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        deadline: Optional[str] = None,
        priority: int = 5,
    ) -> Optional[CollaborationTask]:
        """Create a new collaborative task."""
        task = await self.creation_coordinator.create_task(
            description, required_roles, collaboration_mode, deadline, priority
        )

        if task:
            # Register task with execution coordinator
            self.execution_coordinator.register_task(task)

        return task

    async def assign_agents_to_task(
        self, task: CollaborationTask, available_agents: Dict[AgentRole, List[str]]
    ) -> bool:
        """Assign agents to a task based on availability."""
        return await self.creation_coordinator.assign_agents_to_task(
            task, available_agents
        )

    async def start_task(self, task: CollaborationTask) -> None:
        """Start execution of a task."""
        await self.execution_coordinator.start_task(task)

    async def update_task_status(
        self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update task status."""
        await self.execution_coordinator.update_task_status(task_id, status, result)

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed task."""
        return await self.execution_coordinator.get_task_result(task_id)

    async def check_task_deadlines(self) -> List[str]:
        """Check for tasks that have exceeded deadlines."""
        return await self.maintenance_coordinator.check_task_deadlines(
            self.execution_coordinator.active_tasks,
            self.execution_coordinator.update_task_status,
        )

    async def get_active_tasks(self) -> List[CollaborationTask]:
        """Get all active tasks."""
        return await self.execution_coordinator.get_active_tasks()

    async def get_task_by_id(self, task_id: str) -> Optional[CollaborationTask]:
        """Get task by ID."""
        return await self.execution_coordinator.get_task_by_id(task_id)

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks."""
        return await self.maintenance_coordinator.cleanup_old_tasks(
            self.execution_coordinator.completed_tasks, max_age_hours
        )

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
                priority=7,
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
                        "confidence": 0.85,
                    },
                    {
                        "type": "risk_adjustment",
                        "action": "reduce_volatility_exposure",
                        "rationale": "Current volatility levels above target",
                        "confidence": 0.78,
                    },
                ],
                "overall_assessment": "Strategy performing well with minor adjustments needed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Strategy review failed: {e}")
            return {"error": str(e)}
