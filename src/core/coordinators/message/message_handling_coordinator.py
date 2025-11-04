"""
Message Handling Coordinator

Focused coordinator for message type handlers.
Extracted from MessageCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from loguru import logger

from ...event_bus import EventBus, Event, EventType
from ..base_coordinator import BaseCoordinator
from ..message.agent_message import AgentMessage, MessageType


class MessageHandlingCoordinator(BaseCoordinator):
    """
    Coordinates message type handling.
    
    Responsibilities:
    - Handle different message types
    - Register default handlers
    - Process message content
    """

    def __init__(self, config: Any, event_bus: EventBus):
        super().__init__(config, "message_handling_coordinator")
        self.event_bus = event_bus

    async def initialize(self) -> None:
        """Initialize message handling coordinator."""
        logger.info("Initializing Message Handling Coordinator")
        self._initialized = True

    async def register_default_handlers(self, routing_coordinator) -> None:
        """Register default message handlers."""
        # Analysis response handler
        async def handle_analysis_response(message: AgentMessage) -> None:
            await self._handle_analysis_response(message)

        await routing_coordinator.register_handler(MessageType.ANALYSIS_RESPONSE, handle_analysis_response)

        # Decision proposal handler
        async def handle_decision_proposal(message: AgentMessage) -> None:
            await self._handle_decision_proposal(message)

        await routing_coordinator.register_handler(MessageType.DECISION_PROPOSAL, handle_decision_proposal)

        # Vote handler
        async def handle_vote(message: AgentMessage) -> None:
            await self._handle_vote(message)

        await routing_coordinator.register_handler(MessageType.VOTE, handle_vote)

        # Error report handler
        async def handle_error_report(message: AgentMessage) -> None:
            await self._handle_error_report(message)

        await routing_coordinator.register_handler(MessageType.ERROR_REPORT, handle_error_report)

        # Status update handler
        async def handle_status_update(message: AgentMessage) -> None:
            await self._handle_status_update(message)

        await routing_coordinator.register_handler(MessageType.STATUS_UPDATE, handle_status_update)

    async def _handle_analysis_response(self, message: AgentMessage) -> None:
        """Handle analysis response messages."""
        logger.debug(f"Analysis response from {message.sender_agent}: {len(str(message.content))} chars")

        # Store analysis result (would be handled by task coordinator)
        # For now, just emit an event
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "analysis_response_received",
                "agent": message.sender_agent,
                "correlation_id": message.correlation_id,
                "content_length": len(str(message.content)),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="message_handling_coordinator"
        ))

    async def _handle_decision_proposal(self, message: AgentMessage) -> None:
        """Handle decision proposal messages."""
        logger.debug(f"Decision proposal from {message.sender_agent}")

        # Emit event for task coordinator to handle
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "decision_proposal_received",
                "agent": message.sender_agent,
                "correlation_id": message.correlation_id,
                "proposal": message.content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="message_handling_coordinator"
        ))

    async def _handle_vote(self, message: AgentMessage) -> None:
        """Handle vote messages."""
        logger.debug(f"Vote from {message.sender_agent}: {message.content}")

        # Emit event for consensus handling
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "vote_received",
                "agent": message.sender_agent,
                "correlation_id": message.correlation_id,
                "vote": message.content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="message_handling_coordinator"
        ))

    async def _handle_error_report(self, message: AgentMessage) -> None:
        """Handle error report messages."""
        error_info = message.content
        logger.error(f"Agent error from {message.sender_agent}: {error_info}")

        # Emit error event
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "agent_error_reported",
                "agent": message.sender_agent,
                "correlation_id": message.correlation_id,
                "error": error_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="message_handling_coordinator"
        ))

    async def _handle_status_update(self, message: AgentMessage) -> None:
        """Handle status update messages."""
        status_info = message.content
        logger.debug(f"Status update from {message.sender_agent}: {status_info}")

        # Emit status event
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "agent_status_update",
                "agent": message.sender_agent,
                "correlation_id": message.correlation_id,
                "status": status_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="message_handling_coordinator"
        ))

    async def cleanup(self) -> None:
        """Cleanup message handling coordinator resources."""
        logger.info("MessageHandlingCoordinator cleanup complete")

