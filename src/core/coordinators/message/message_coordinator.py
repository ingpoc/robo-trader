"""
Message Coordinator (Refactored)

Thin orchestrator that delegates to focused message coordinators.
Refactored from 333-line monolith into focused coordinators.
"""

from collections import defaultdict
from typing import Any, Dict, Optional

from loguru import logger

from src.config import Config

from ...database_state.database_state import DatabaseStateManager
from ...event_bus import EventBus
from ..base_coordinator import BaseCoordinator
from .agent_message import AgentMessage, MessageType
from .message_handling_coordinator import MessageHandlingCoordinator
from .message_routing_coordinator import MessageRoutingCoordinator


class MessageCoordinator(BaseCoordinator):
    """
    Coordinator for managing inter-agent communication.

    Responsibilities:
    - Orchestrate message operations from focused coordinators
    - Provide unified message management API
    - Track message statistics
    """

    def __init__(
        self, config: Config, state_manager: DatabaseStateManager, event_bus: EventBus
    ):
        super().__init__(config)
        self.state_manager = state_manager
        self.event_bus = event_bus

        # Focused coordinators
        self.routing_coordinator = MessageRoutingCoordinator(config, event_bus)
        self.handling_coordinator = MessageHandlingCoordinator(config, event_bus)

        # Message statistics
        self.message_counts: Dict[str, int] = defaultdict(int)

    async def initialize(self) -> None:
        """Initialize the message coordinator."""
        logger.info("Initializing Message Coordinator")

        # Initialize focused coordinators
        await self.routing_coordinator.initialize()
        await self.handling_coordinator.initialize()

        # Register default handlers
        await self.handling_coordinator.register_default_handlers(
            self.routing_coordinator
        )

        logger.info("Message Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        await self.routing_coordinator.cleanup()
        await self.handling_coordinator.cleanup()

    async def send_message(self, message: AgentMessage) -> None:
        """Send a message to the coordinator for routing."""
        # Update statistics
        self.message_counts[message.message_type.value] += 1

        await self.routing_coordinator.send_message(message)

    async def register_handler(
        self, message_type: MessageType, handler: callable
    ) -> None:
        """Register a handler for a message type."""
        await self.routing_coordinator.register_handler(message_type, handler)

    async def send_request_response(
        self, request: AgentMessage, timeout: float = 30.0
    ) -> Optional[AgentMessage]:
        """Send a request and wait for response."""
        return await self.routing_coordinator.send_request_response(request, timeout)

    async def get_message_statistics(self) -> Dict[str, Any]:
        """
        Get message handling statistics.

        Returns:
            Statistics about message processing
        """
        return {
            "total_messages": sum(self.message_counts.values()),
            "messages_by_type": dict(self.message_counts),
            "pending_responses": len(self.routing_coordinator.pending_responses),
            "active_handlers": sum(
                len(handlers)
                for handlers in self.routing_coordinator.message_handlers.values()
            ),
        }
