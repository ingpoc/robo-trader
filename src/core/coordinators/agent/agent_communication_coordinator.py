"""
Agent Communication Coordinator

Focused coordinator for agent message processing.
Extracted from AgentCoordinator for single responsibility.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict

from loguru import logger

from ...event_bus import Event, EventBus, EventType
from ..base_coordinator import BaseCoordinator
from ..message.agent_message import AgentMessage, MessageType
from .agent_profile import AgentProfile


class AgentCommunicationCoordinator(BaseCoordinator):
    """
    Coordinates agent communication and message processing.

    Responsibilities:
    - Process agent messages
    - Handle status updates
    - Handle error reports
    - Update agent activity tracking
    """

    def __init__(
        self, config, event_bus: EventBus, registered_agents: Dict[str, AgentProfile]
    ):
        super().__init__(config, "agent_communication_coordinator")
        self.event_bus = event_bus
        self.registered_agents = registered_agents
        self.agent_message_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task = None

    async def initialize(self) -> None:
        """Initialize agent communication coordinator."""
        logger.info("Initializing Agent Communication Coordinator")

        # Start message processing
        self._running = True
        self._processing_task = asyncio.create_task(self._process_agent_messages())

        logger.info("Agent Communication Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._running = False

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

    async def send_agent_message(self, message: AgentMessage) -> None:
        """
        Send a message to an agent.

        Args:
            message: Message to send
        """
        await self.agent_message_queue.put(message)

        # Emit event for monitoring
        await self.event_bus.publish(
            Event(
                event_type=EventType.TASK_COMPLETED,
                data={
                    "event_type": "agent_message",
                    "message": message.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                source="agent_communication_coordinator",
            )
        )

    async def _process_agent_messages(self) -> None:
        """Process agent messages."""
        logger.info("Agent message processing started")

        while self._running:
            try:
                # Process messages with timeout
                try:
                    message = await asyncio.wait_for(
                        self.agent_message_queue.get(), timeout=1.0
                    )
                    await self._handle_agent_message(message)
                    self.agent_message_queue.task_done()
                except asyncio.TimeoutError:
                    continue

            except Exception as e:
                logger.error(f"Error processing agent message: {e}")
                await asyncio.sleep(1)

        logger.info("Agent message processing stopped")

    async def _handle_agent_message(self, message: AgentMessage) -> None:
        """
        Handle an agent message.

        Args:
            message: Message to handle
        """
        logger.debug(
            f"Processing agent message: {message.message_type.value} from {message.sender_agent}"
        )

        # Update agent last active time
        if message.sender_agent in self.registered_agents:
            self.registered_agents[message.sender_agent].last_active = datetime.now(
                timezone.utc
            ).isoformat()

        # Route based on message type
        if message.message_type == MessageType.STATUS_UPDATE:
            await self._handle_status_update(message)
        elif message.message_type == MessageType.ERROR_REPORT:
            await self._handle_error_report(message)

    async def _handle_status_update(self, message: AgentMessage) -> None:
        """Handle agent status update."""
        agent_id = message.sender_agent
        status_info = message.content

        if agent_id in self.registered_agents:
            # Update agent performance if provided
            if "performance_score" in status_info:
                self.registered_agents[agent_id].performance_score = status_info[
                    "performance_score"
                ]

            logger.debug(f"Status update for agent {agent_id}: {status_info}")

    async def _handle_error_report(self, message: AgentMessage) -> None:
        """Handle agent error report."""
        agent_id = message.sender_agent
        error_info = message.content

        logger.error(f"Agent error reported by {agent_id}: {error_info}")

        # Could implement error recovery logic here

    async def cleanup(self) -> None:
        """Cleanup agent communication coordinator resources."""
        self._running = False
        logger.info("AgentCommunicationCoordinator cleanup complete")
