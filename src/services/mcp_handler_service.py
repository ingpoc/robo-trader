"""
MCP Task Handler Registration Service

Registers MCP task handlers with the scheduler task service.
This service integrates the MCP task handlers with the SequentialQueueManager.
"""

import logging
from typing import Dict, Any

from ..mcp.mcp_task_handlers import (
    MCPResearchHandler,
    MCPTradeExecutionHandler,
    MCPAnalysisHandler
)
from ...models.scheduler import TaskType
from ...core.event_bus import EventHandler, Event, EventType

logger = logging.getLogger(__name__)


class MCPHandlerRegistrationService(EventHandler):
    """
    Service for registering MCP task handlers with the task service.

    This service acts as a bridge between the MCP task handlers and the
    SequentialQueueManager, ensuring that MCP-initiated tasks are properly
    routed and executed through the queue system.
    """

    def __init__(self, task_service, container):
        """Initialize MCP handler registration service."""
        self.task_service = task_service
        self.container = container
        self._initialized = False
        self._handlers: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize MCP handler registration service."""
        if self._initialized:
            return

        try:
            # Initialize MCP handlers
            research_handler = MCPResearchHandler(self.container)
            trade_handler = MCPTradeExecutionHandler(self.container)
            analysis_handler = MCPAnalysisHandler(self.container)

            # Store handlers for cleanup
            self._handlers = {
                "research": research_handler,
                "trade": trade_handler,
                "analysis": analysis_handler
            }

            # Register task handlers with task service
            await self._register_task_handlers()

            self._initialized = True
            logger.info("MCP Handler Registration Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MCP Handler Registration Service: {e}")
            raise

    async def _register_task_handlers(self) -> None:
        """Register MCP task handlers with the task service."""

        # Register portfolio analysis task handlers
        self.task_service.register_handler(
            TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS,
            self._handlers["analysis"].handle_portfolio_analysis_task
        )

        self.task_service.register_handler(
            TaskType.PROMPT_TEMPLATE_OPTIMIZATION,
            self._handlers["analysis"].handle_prompt_optimization_task
        )

        # Register paper trading task handlers
        self.task_service.register_handler(
            TaskType.MARKET_RESEARCH_PERPLEXITY,
            self._handlers["research"].handle_market_research_task
        )

        self.task_service.register_handler(
            TaskType.PAPER_TRADE_EXECUTION,
            self._handlers["trade"].handle_trade_execution_task
        )

        logger.info("Registered MCP task handlers with task service")

    async def cleanup(self) -> None:
        """Cleanup MCP handler registration service."""
        if not self._initialized:
            return

        try:
            # Cleanup handlers
            for handler_name, handler in self._handlers.items():
                if hasattr(handler, 'cleanup'):
                    await handler.cleanup()
                logger.debug(f"Cleaned up MCP handler: {handler_name}")

            self._handlers.clear()
            self._initialized = False
            logger.info("MCP Handler Registration Service cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during MCP handler registration cleanup: {e}")

    async def handle_event(self, event: Event) -> None:
        """Handle events from the event bus."""
        try:
            # Handle MCP-related events if needed
            if event.type == EventType.MCP_TASK_CREATED:
                await self._handle_mcp_task_created(event)
            elif event.type == EventType.MCP_TASK_COMPLETED:
                await self._handle_mcp_task_completed(event)
            elif event.type == EventType.MCP_TASK_FAILED:
                await self._handle_mcp_task_failed(event)

        except Exception as e:
            logger.error(f"Error handling MCP event {event.type}: {e}")

    async def _handle_mcp_task_created(self, event: Event) -> None:
        """Handle MCP task creation event."""
        data = event.data
        task_type = data.get("task_type")
        task_id = data.get("task_id")

        logger.info(f"MCP task created: {task_id} ({task_type})")

    async def _handle_mcp_task_completed(self, event: Event) -> None:
        """Handle MCP task completion event."""
        data = event.data
        task_id = data.get("task_id")
        task_type = data.get("task_type")

        logger.info(f"MCP task completed: {task_id} ({task_type})")

    async def _handle_mcp_task_failed(self, event: Event) -> None:
        """Handle MCP task failure event."""
        data = event.data
        task_id = data.get("task_id")
        task_type = data.get("task_type")
        error = data.get("error", "Unknown error")

        logger.error(f"MCP task failed: {task_id} ({task_type}) - {error}")

    def get_handler_status(self) -> Dict[str, Any]:
        """Get status of registered handlers."""
        return {
            "initialized": self._initialized,
            "registered_handlers": list(self._handlers.keys()),
            "handler_details": {
                name: {
                    "class": type(handler).__name__,
                    "initialized": getattr(handler, '_initialized', False)
                }
                for name, handler in self._handlers.items()
            }
        }