"""
Message Coordinator for Multi-Agent Framework

Handles inter-agent communication and message routing.
Separated from the main framework to follow the 350-line rule.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict

from loguru import logger

from ..database_state import DatabaseStateManager
from ..event_bus import EventBus, Event, EventType
from .base_coordinator import BaseCoordinator
from .agent_message import AgentMessage, MessageType


class MessageCoordinator(BaseCoordinator):
    """
    Coordinator for managing inter-agent communication.

    Responsibilities:
    - Message routing between agents
    - Message queuing and delivery
    - Message persistence and history
    - Communication protocol enforcement
    - Message prioritization
    """

    def __init__(self, config: Any, state_manager: DatabaseStateManager, event_bus: EventBus):
        super().__init__(config, "message_coordinator")
        self.state_manager = state_manager
        self.event_bus = event_bus

        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[MessageType, List[callable]] = defaultdict(list)
        self.pending_responses: Dict[str, asyncio.Future] = {}

        # Message statistics
        self.message_counts: Dict[str, int] = defaultdict(int)

    async def initialize(self) -> None:
        """Initialize the message coordinator."""
        logger.info("Initializing Message Coordinator")

        # Register default message handlers
        self._register_default_handlers()

        # Start message processing
        self._running = True
        self._processing_task = asyncio.create_task(self._process_messages())

        logger.info("Message Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._running = False

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        # Cancel pending responses
        for future in self.pending_responses.values():
            if not future.done():
                future.cancel()

        self.pending_responses.clear()

    async def send_message(self, message: AgentMessage) -> None:
        """
        Send a message to the coordinator for routing.

        Args:
            message: Message to send
        """
        await self.message_queue.put(message)

        # Update statistics
        self.message_counts[message.message_type.value] += 1

        # Emit event for monitoring
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "message_sent",
                "message_id": message.message_id,
                "message_type": message.message_type.value,
                "sender": message.sender_agent,
                "recipient": message.recipient_agent,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="message_coordinator"
        ))

    async def register_handler(self, message_type: MessageType, handler: callable) -> None:
        """
        Register a handler for a message type.

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type.value}")

    async def send_request_response(
        self,
        request: AgentMessage,
        timeout: float = 30.0
    ) -> Optional[AgentMessage]:
        """
        Send a request and wait for response.

        Args:
            request: Request message
            timeout: Response timeout in seconds

        Returns:
            Response message or None if timeout
        """
        # Create a future for the response
        response_future = asyncio.Future()
        self.pending_responses[request.message_id] = response_future

        # Send the request
        await self.send_message(request)

        try:
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request {request.message_id} timed out")
            return None
        finally:
            # Clean up
            self.pending_responses.pop(request.message_id, None)

    async def get_message_statistics(self) -> Dict[str, Any]:
        """
        Get message handling statistics.

        Returns:
            Statistics about message processing
        """
        return {
            "total_messages": sum(self.message_counts.values()),
            "messages_by_type": dict(self.message_counts),
            "pending_responses": len(self.pending_responses),
            "active_handlers": sum(len(handlers) for handlers in self.message_handlers.values())
        }

    async def _process_messages(self) -> None:
        """Main message processing loop."""
        logger.info("Message processing started")

        while self._running:
            try:
                # Get message with timeout
                try:
                    message = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process the message
                await self._route_message(message)
                self.message_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)

        logger.info("Message processing stopped")

    async def _route_message(self, message: AgentMessage) -> None:
        """
        Route a message to appropriate handlers.

        Args:
            message: Message to route
        """
        logger.debug(f"Routing message: {message.message_type.value} from {message.sender_agent}")

        # Check if this is a response to a pending request
        if message.correlation_id and message.correlation_id in self.pending_responses:
            future = self.pending_responses[message.correlation_id]
            if not future.done():
                future.set_result(message)
            return

        # Route to registered handlers
        handlers = self.message_handlers.get(message.message_type, [])
        if not handlers:
            logger.warning(f"No handlers registered for message type: {message.message_type.value}")
            return

        # Call all handlers for this message type
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.message_type.value}: {e}")

    async def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        # Analysis response handler
        async def handle_analysis_response(message: AgentMessage) -> None:
            await self._handle_analysis_response(message)

        await self.register_handler(MessageType.ANALYSIS_RESPONSE, handle_analysis_response)

        # Decision proposal handler
        async def handle_decision_proposal(message: AgentMessage) -> None:
            await self._handle_decision_proposal(message)

        await self.register_handler(MessageType.DECISION_PROPOSAL, handle_decision_proposal)

        # Vote handler
        async def handle_vote(message: AgentMessage) -> None:
            await self._handle_vote(message)

        await self.register_handler(MessageType.VOTE, handle_vote)

        # Error report handler
        async def handle_error_report(message: AgentMessage) -> None:
            await self._handle_error_report(message)

        await self.register_handler(MessageType.ERROR_REPORT, handle_error_report)

        # Status update handler
        async def handle_status_update(message: AgentMessage) -> None:
            await self._handle_status_update(message)

        await self.register_handler(MessageType.STATUS_UPDATE, handle_status_update)

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
            source="message_coordinator"
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
            source="message_coordinator"
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
            source="message_coordinator"
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
            source="message_coordinator"
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
            source="message_coordinator"
        ))