"""
Multi-Agent Collaboration Framework for Robo Trader

Refactored to use coordinators and follow the 350-line rule.
Provides high-level coordination while delegating to specialized coordinators.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from loguru import logger

from src.config import Config

from ..core.database_state import DatabaseStateManager
from ..core.event_bus import EventBus
from .coordinators.agent.agent_profile import AgentRole
from .coordinators.message.agent_message import AgentMessage
from .coordinators.task.collaboration_task import (CollaborationMode,
                                                   CollaborationTask)

if TYPE_CHECKING:
    from .coordinators.agent.agent_coordinator import AgentCoordinator
    from .coordinators.agent.agent_profile import AgentRole
    from .coordinators.message.agent_message import AgentMessage
    from .coordinators.message.message_coordinator import MessageCoordinator
    from .coordinators.task.collaboration_task import CollaborationTask
    from .coordinators.task.task_coordinator import TaskCoordinator


class MultiAgentFramework:
    """
    Framework for coordinating multiple specialized agents.

    Now uses a coordinator pattern to stay under the 350-line limit.
    Provides high-level orchestration while delegating to specialized coordinators.
    """

    def __init__(
        self, config: Config, state_manager: DatabaseStateManager, event_bus: EventBus
    ):
        self.config = config
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.client: Optional[ClaudeSDKClient] = None

        # Coordinators
        self.agent_coordinator: Optional[AgentCoordinator] = None
        self.task_coordinator: Optional[TaskCoordinator] = None
        self.message_coordinator: Optional[MessageCoordinator] = None

        # Framework state
        self._running = False

    async def initialize(self) -> None:
        """Initialize the multi-agent framework."""
        logger.info("Initializing Multi-Agent Framework")

        # Initialize coordinators
        self.agent_coordinator = AgentCoordinator(
            self.config, self.state_manager, self.event_bus
        )
        self.task_coordinator = TaskCoordinator(
            self.config, self.state_manager, self.event_bus
        )
        self.message_coordinator = MessageCoordinator(
            self.config, self.state_manager, self.event_bus
        )

        # Initialize all coordinators
        await self.agent_coordinator.initialize()
        await self.task_coordinator.initialize()
        await self.message_coordinator.initialize()

        self._running = True

        logger.info("Multi-Agent Framework initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup framework resources."""
        self._running = False

        # Cleanup coordinators in reverse order
        if self.message_coordinator:
            await self.message_coordinator.cleanup()
        if self.task_coordinator:
            await self.task_coordinator.cleanup()
        if self.agent_coordinator:
            await self.agent_coordinator.cleanup()

        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up framework client: {e}")

    async def create_collaboration_task(
        self,
        description: str,
        required_roles: List[AgentRole],
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        deadline: Optional[str] = None,
    ) -> Optional[CollaborationTask]:
        """
        Create a new collaborative task.

        Args:
            description: Description of the task
            required_roles: Roles needed for the task
            collaboration_mode: How agents should collaborate
            deadline: Optional deadline for completion

        Returns:
            Created task or None if creation failed
        """
        if not self.task_coordinator:
            logger.error("Task coordinator not initialized")
            return None

        # Create the task
        task = await self.task_coordinator.create_task(
            description=description,
            required_roles=required_roles,
            collaboration_mode=collaboration_mode,
            deadline=deadline,
        )

        if not task:
            return None

        # Get available agents for assignment
        available_agents = {}
        for role in required_roles:
            agents = await self.agent_coordinator.get_available_agents(role)
            available_agents[role] = agents

        # Assign agents to task
        success = await self.task_coordinator.assign_agents_to_task(
            task, available_agents
        )

        if success:
            # Start the task
            await self.task_coordinator.start_task(task)
            return task
        else:
            logger.error(f"Failed to assign agents to task {task.task_id}")
            return None

    async def get_collaboration_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a completed collaboration task.

        Args:
            task_id: ID of the task

        Returns:
            Task result or None if not completed
        """
        if not self.task_coordinator:
            return None

        return await self.task_coordinator.get_task_result(task_id)

    async def send_message(self, message: AgentMessage) -> None:
        """
        Send a message between agents.

        Args:
            message: Message to send
        """
        if not self.message_coordinator:
            logger.error("Message coordinator not initialized")
            return

        await self.message_coordinator.send_message(message)

    async def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Performance metrics
        """
        if not self.agent_coordinator:
            return {"error": "Agent coordinator not initialized"}

        return await self.agent_coordinator.get_agent_performance(agent_id)

    async def register_agent(self, agent_profile) -> bool:
        """
        Register a new agent (legacy method for backward compatibility).

        Args:
            agent_profile: Profile of the agent to register

        Returns:
            True if registered successfully
        """
        if not self.agent_coordinator:
            logger.error("Agent coordinator not initialized")
            return False

        # Convert to coordinator's expected format if needed
        return await self.agent_coordinator.register_agent(agent_profile)

    async def check_system_health(self) -> Dict[str, Any]:
        """
        Check the health of the multi-agent system.

        Returns:
            Health status information
        """
        health_status = {
            "framework_running": self._running,
            "coordinators": {},
            "active_tasks": 0,
            "registered_agents": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Check coordinators
        if self.agent_coordinator:
            health_status["coordinators"]["agent"] = "initialized"
        else:
            health_status["coordinators"]["agent"] = "not_initialized"

        if self.task_coordinator:
            health_status["coordinators"]["task"] = "initialized"
            active_tasks = await self.task_coordinator.get_active_tasks()
            health_status["active_tasks"] = len(active_tasks)
        else:
            health_status["coordinators"]["task"] = "not_initialized"

        if self.message_coordinator:
            health_status["coordinators"]["message"] = "initialized"
            stats = await self.message_coordinator.get_message_statistics()
            health_status["message_stats"] = stats
        else:
            health_status["coordinators"]["message"] = "not_initialized"

        # Get agent count
        if self.agent_coordinator:
            # Count registered agents (simplified)
            health_status["registered_agents"] = len(
                self.agent_coordinator.registered_agents
            )

        return health_status

    async def _ensure_client(self) -> None:
        """Lazy initialization of Claude SDK client."""
        if self.client is None:
            options = ClaudeAgentOptions(
                allowed_tools=[],
                system_prompt=self._get_collaboration_prompt(),
                max_turns=15,
            )
            # Use client manager instead of direct creation
            from src.core.claude_sdk_client_manager import \
                ClaudeSDKClientManager

            client_manager = await ClaudeSDKClientManager.get_instance()
            self.client = await client_manager.get_client("trading", options)
            logger.info("Multi-Agent Framework Claude client initialized via manager")

    def _get_collaboration_prompt(self) -> str:
        """Get the system prompt for agent collaboration."""
        return """
        You are an expert AI coordinator for multi-agent collaboration systems.

        Your role is to synthesize diverse analyses from specialized agents into coherent,
        actionable recommendations. Consider each agent's expertise and perspective while
        identifying consensus, conflicts, and optimal paths forward.

        Focus on:
        - Balancing different viewpoints
        - Identifying highest-confidence insights
        - Providing clear, actionable recommendations
        - Flagging areas needing further analysis
        """
