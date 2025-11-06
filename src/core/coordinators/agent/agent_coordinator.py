"""
Agent Coordinator (Refactored)

Thin orchestrator that delegates to focused agent coordinators.
Refactored from 276-line monolith into focused coordinators.
"""

from typing import Any, Dict, List

from loguru import logger

from src.config import Config

from ...database_state.database_state import DatabaseStateManager
from ...event_bus import EventBus
from ..base_coordinator import BaseCoordinator
from ..message.agent_message import AgentMessage
from .agent_communication_coordinator import AgentCommunicationCoordinator
from .agent_profile import AgentProfile, AgentRole
from .agent_registration_coordinator import AgentRegistrationCoordinator


class AgentCoordinator(BaseCoordinator):
    """
    Coordinator for managing agent lifecycle and basic operations.

    Responsibilities:
    - Orchestrate agent operations from focused coordinators
    - Provide unified agent management API
    """

    def __init__(
        self, config: Config, state_manager: DatabaseStateManager, event_bus: EventBus
    ):
        super().__init__(config)
        self.state_manager = state_manager
        self.event_bus = event_bus

        # Focused coordinators
        self.registration_coordinator = AgentRegistrationCoordinator(
            config, state_manager, event_bus
        )
        self.communication_coordinator = (
            None  # Will be set after registration coordinator initializes
        )

    async def initialize(self) -> None:
        """Initialize the agent coordinator."""
        logger.info("Initializing Agent Coordinator")

        # Initialize registration coordinator first
        await self.registration_coordinator.initialize()

        # Register built-in agents
        await self.registration_coordinator._register_builtin_agents()

        # Initialize communication coordinator with registered agents
        self.communication_coordinator = AgentCommunicationCoordinator(
            self.config, self.event_bus, self.registration_coordinator.registered_agents
        )
        await self.communication_coordinator.initialize()

        logger.info("Agent Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        if self.communication_coordinator:
            await self.communication_coordinator.cleanup()
        await self.registration_coordinator.cleanup()

    async def register_agent(self, agent_profile: AgentProfile) -> bool:
        """Register a new agent."""
        return await self.registration_coordinator.register_agent(agent_profile)

    async def get_available_agents(self, role: AgentRole) -> List[str]:
        """Get available agents for a specific role."""
        return await self.registration_coordinator.get_available_agents(role)

    async def update_agent_status(self, agent_id: str, is_active: bool) -> None:
        """Update agent active status."""
        await self.registration_coordinator.update_agent_status(agent_id, is_active)

    async def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """Get performance metrics for an agent."""
        return await self.registration_coordinator.get_agent_performance(agent_id)

    async def send_agent_message(self, message: AgentMessage) -> None:
        """Send a message to an agent."""
        await self.communication_coordinator.send_agent_message(message)
