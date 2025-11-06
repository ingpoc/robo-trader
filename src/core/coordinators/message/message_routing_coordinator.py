"""
Message Routing Coordinator

Focused coordinator for message routing and processing.
Extracted from MessageCoordinator for single responsibility.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from ...event_bus import Event, EventBus, EventType
from ..base_coordinator import BaseCoordinator
from ..message.agent_message import AgentMessage, MessageType


class MessageRoutingCoordinator(BaseCoordinator):
    """
    Coordinates message routing and processing.

    Responsibilities:
    - Message queuing and delivery
    - Message routing logic
    - Request-response pattern
    - Message processing loop
    """

    def __init__(self, config: Any, event_bus: EventBus):
        super().__init__(config, "message_routing_coordinator")
        self.event_bus = event_bus

        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[MessageType, List[callable]] = defaultdict(list)
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self._processing_task = None

    async def initialize(self) -> None:
        """Initialize message routing coordinator."""
        logger.info("Initializing Message Routing Coordinator")

        # Start message processing
        self._running = True
        self._processing_task = asyncio.create_task(self._process_messages())

        logger.info("Message Routing Coordinator initialized successfully")

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

        # Emit event for monitoring
        await self.event_bus.publish(
            Event(
                event_type=EventType.TASK_COMPLETED,
                data={
                    "event_type": "message_sent",
                    "message_id": message.message_id,
                    "message_type": message.message_type.value,
                    "sender": message.sender_agent,
                    "recipient": message.recipient_agent,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                source="message_routing_coordinator",
            )
        )

    async def register_handler(
        self, message_type: MessageType, handler: callable
    ) -> None:
        """
        Register a handler for a message type.

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type.value}")

    async def send_request_response(
        self, request: AgentMessage, timeout: float = 30.0
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

    async def _process_messages(self) -> None:
        """Main message processing loop."""
        logger.info("Message processing started")

        while self._running:
            try:
                # Get message with timeout
                try:
                    message = await asyncio.wait_for(
                        self.message_queue.get(), timeout=1.0
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
        logger.debug(
            f"Routing message: {message.message_type.value} from {message.sender_agent}"
        )

        # Check if this is a response to a pending request
        if message.correlation_id and message.correlation_id in self.pending_responses:
            future = self.pending_responses[message.correlation_id]
            if not future.done():
                future.set_result(message)
            return

        # Route to registered handlers
        handlers = self.message_handlers.get(message.message_type, [])
        if not handlers:
            logger.warning(
                f"No handlers registered for message type: {message.message_type.value}"
            )
            return

        # Call all handlers for this message type
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.message_type.value}: {e}")
