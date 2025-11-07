"""
MCP Integration Service.

Manages the integration between MCP server, SequentialQueueManager,
and workflow services. Handles task registration, routing, and status monitoring
for MCP-initiated operations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger

from src.core.event_bus import EventBus, Event, EventType
from src.models.scheduler import TaskType, TaskStatus
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class MCPIntegrationService:
    """
    Service for managing MCP integration with the Robo Trader system.

    Handles:
    - MCP server lifecycle management
    - Task registration and routing
    - Status monitoring and reporting
    - Error handling and recovery
    - Performance metrics tracking
    """

    def __init__(self, task_service, workflow_manager, container):
        """Initialize MCP integration service."""
        self.task_service = task_service
        self.workflow_manager = workflow_manager
        self.container = container
        self.event_bus = None
        self._mcp_server = None
        self._initialized = False

        # Performance tracking
        self._metrics = {
            "total_tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_completion_time_ms": 0.0,
            "last_task_completion": None,
            "active_tasks": 0
        }

    async def initialize(self) -> None:
        """Initialize MCP integration service."""
        if self._initialized:
            return

        try:
            # Get dependencies
            self.event_bus = await self.container.get("event_bus")
            mcp_server_data = await self.container.get("enhanced_paper_trading_mcp_server")

            # Extract server and discovery manager
            self._mcp_server = mcp_server_data["server"]
            self._discovery_manager = mcp_server_data["discovery_manager"]

            # Subscribe to task service events
            await self._subscribe_to_events()

            self._initialized = True
            logger.info("MCP Integration Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MCP Integration Service: {e}")
            raise TradingError(
                f"MCP Integration Service initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events for monitoring."""
        # Subscribe to task events
        self.event_bus.subscribe(EventType.TASK_CREATED, self)
        self.event_bus.subscribe(EventType.TASK_COMPLETED, self)
        self.event_bus.subscribe(EventType.TASK_FAILED, self)

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events from the event bus."""
        try:
            if event.type == EventType.TASK_CREATED:
                await self._handle_task_created(event)
            elif event.type == EventType.TASK_COMPLETED:
                await self._handle_task_completed(event)
            elif event.type == EventType.TASK_FAILED:
                await self._handle_task_failed(event)

        except Exception as e:
            logger.error(f"Error handling MCP event {event.type}: {e}")

    async def _handle_task_created(self, event: Event) -> None:
        """Handle task creation event."""
        data = event.data
        task_id = data.get("task_id")
        task_type = data.get("task_type")

        # Check if this is an MCP-initiated task
        if task_id and self._is_mcp_task(task_type):
            self._metrics["total_tasks_created"] += 1
            self._metrics["active_tasks"] += 1

            logger.info(f"MCP task created: {task_id} ({task_type})")

            # Update discovery context based on task type
            if self._discovery_manager:
                await self._update_discovery_context_from_task(task_type, data)

            # Emit MCP-specific event
            await self._emit_mcp_event("task_created", {
                "task_id": task_id,
                "task_type": task_type,
                "timestamp": datetime.utcnow().isoformat()
            })

    async def _update_discovery_context_from_task(self, task_type: str, task_data: Dict[str, Any]) -> None:
        """Update discovery context based on task creation."""
        if not self._discovery_manager:
            return

        context_updates = {}

        # Map task types to workflow stages
        task_stage_mapping = {
            TaskType.MARKET_RESEARCH_PERPLEXITY: "research",
            TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS: "analysis",
            TaskType.PAPER_TRADE_EXECUTION: "execution",
            TaskType.PROMPT_TEMPLATE_OPTIMIZATION: "optimization"
        }

        if task_type in task_stage_mapping:
            context_updates["workflow_stage"] = task_stage_mapping[task_type]

        # Update portfolio value if available
        if task_type == TaskType.PAPER_TRADE_EXECUTION:
            # This indicates trading activity, could update portfolio value
            context_updates["trades_executed"] = self._metrics["total_tasks_created"]

        # Update discovery context
        if context_updates:
            await self._discovery_manager.update_discovery_context(context_updates)

    async def _handle_task_completed(self, event: Event) -> None:
        """Handle task completion event."""
        data = event.data
        task_id = data.get("task_id")
        task_type = data.get("task_type")
        duration_ms = data.get("duration_ms", 0)

        # Check if this is an MCP-initiated task
        if task_id and self._is_mcp_task(task_type):
            self._metrics["tasks_completed"] += 1
            self._metrics["active_tasks"] = max(0, self._metrics["active_tasks"] - 1)
            self._metrics["last_task_completion"] = datetime.utcnow()

            # Update average completion time
            if self._metrics["tasks_completed"] > 0:
                total_time = self._metrics["avg_completion_time_ms"] * (self._metrics["tasks_completed"] - 1) + duration_ms
                self._metrics["avg_completion_time_ms"] = total_time / self._metrics["tasks_completed"]

            logger.info(f"MCP task completed: {task_id} ({task_type}) in {duration_ms}ms")

            # Emit MCP-specific event
            await self._emit_mcp_event("task_completed", {
                "task_id": task_id,
                "task_type": task_type,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat()
            })

    async def _handle_task_failed(self, event: Event) -> None:
        """Handle task failure event."""
        data = event.data
        task_id = data.get("task_id")
        task_type = data.get("task_type")
        error = data.get("error", "Unknown error")

        # Check if this is an MCP-initiated task
        if task_id and self._is_mcp_task(task_type):
            self._metrics["tasks_failed"] += 1
            self._metrics["active_tasks"] = max(0, self._metrics["active_tasks"] - 1)

            logger.error(f"MCP task failed: {task_id} ({task_type}) - {error}")

            # Emit MCP-specific event
            await self._emit_mcp_event("task_failed", {
                "task_id": task_id,
                "task_type": task_type,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })

    def _is_mcp_task(self, task_type: str) -> bool:
        """Check if a task type is MCP-initiated."""
        mcp_task_types = {
            TaskType.MARKET_RESEARCH_PERPLEXITY,
            TaskType.PAPER_TRADE_EXECUTION,
            TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS,
            TaskType.PROMPT_TEMPLATE_OPTIMIZATION
        }
        return task_type in mcp_task_types

    async def _emit_mcp_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit MCP-specific event."""
        try:
            # Map MCP event types to standard EventType enum
            event_type_mapping = {
                "task_created": EventType.MCP_TASK_CREATED,
                "task_completed": EventType.MCP_TASK_COMPLETED,
                "task_failed": EventType.MCP_TASK_FAILED
            }

            mapped_event_type = event_type_mapping.get(event_type, EventType.SYSTEM_HEALTH_CHECK)

            event = Event(
                id=f"mcp_{event_type}_{datetime.utcnow().timestamp()}",
                type=mapped_event_type,
                source="mcp_integration",
                data={
                    "event_type": event_type,
                    "service": "mcp_integration",
                    **data
                },
                correlation_id=data.get("task_id"),
                timestamp=datetime.utcnow()
            )
            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error emitting MCP event {event_type}: {e}")

    async def get_mcp_status(self) -> Dict[str, Any]:
        """Get current MCP integration status."""
        try:
            # Check if MCP server is healthy
            if self._mcp_server:
                workflow_health = await self._workflow_manager.get_all_workflow_health()
            else:
                workflow_health = {}

            return {
                "initialized": self._initialized,
                "server_status": "running" if self._mcp_server else "stopped",
                "metrics": self._metrics.copy(),
                "workflow_health": workflow_health,
                "active_tasks": self._metrics["active_tasks"],
                "last_activity": self._metrics["last_task_completion"].isoformat() if self._metrics["last_task_completion"] else None
            }

        except Exception as e:
            logger.error(f"Error getting MCP status: {e}")
            return {
                "initialized": False,
                "server_status": "error",
                "error": str(e),
                "metrics": self._metrics.copy()
            }

    async def get_mcp_metrics(self) -> Dict[str, Any]:
        """Get detailed MCP performance metrics."""
        return {
            "task_metrics": {
                "total_created": self._metrics["total_tasks_created"],
                "completed": self._metrics["tasks_completed"],
                "failed": self._metrics["tasks_failed"],
                "active": self._metrics["active_tasks"],
                "success_rate": (
                    self._metrics["tasks_completed"] / max(1, self._metrics["total_tasks_created"])
                ) * 100
            },
            "performance_metrics": {
                "avg_completion_time_ms": self._metrics["avg_completion_time_ms"],
                "last_completion": self._metrics["last_task_completion"].isoformat() if self._metrics["last_task_completion"] else None
            },
            "queue_status": await self._get_queue_status()
        }

    async def _get_queue_status(self) -> Dict[str, Any]:
        """Get status of MCP-related queues."""
        try:
            # Get queue statistics for MCP queues
            stats = await self.task_service.get_all_queue_statistics()

            mcp_queues = [
                "portfolio_analysis",
                "paper_trading_research",
                "paper_trading_execution"
            ]

            queue_status = {}
            for queue_name in mcp_queues:
                if queue_name in stats:
                    stat = stats[queue_name]
                    queue_status[queue_name] = {
                        "pending_count": stat.pending_count,
                        "running_count": stat.running_count,
                        "completed_today": stat.completed_today,
                        "failed_count": stat.failed_count
                    }

            return queue_status

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {}

    async def get_discovery_analytics(self) -> Dict[str, Any]:
        """Get discovery analytics from the discovery manager."""
        try:
            if not self._discovery_manager:
                return {"error": "Discovery manager not available"}

            analytics = await self._discovery_manager.get_discovery_analytics()

            # Add MCP integration metrics
            analytics["mcp_integration"] = {
                "total_tasks_created": self._metrics["total_tasks_created"],
                "tasks_completed": self._metrics["tasks_completed"],
                "tasks_failed": self._metrics["tasks_failed"],
                "active_tasks": self._metrics["active_tasks"],
                "avg_completion_time_ms": self._metrics["avg_completion_time_ms"],
                "success_rate": (
                    self._metrics["tasks_completed"] / max(1, self._metrics["total_tasks_created"])
                ) * 100
            }

            return analytics

        except Exception as e:
            logger.error(f"Error getting discovery analytics: {e}")
            return {"error": str(e), "mcp_integration": self._metrics}

    async def update_discovery_context(self, context_updates: Dict[str, Any]) -> None:
        """Update discovery context manually."""
        try:
            if self._discovery_manager:
                await self._discovery_manager.update_discovery_context(context_updates)
                logger.info(f"Updated discovery context: {context_updates}")

        except Exception as e:
            logger.error(f"Error updating discovery context: {e}")

    async def cleanup(self) -> None:
        """Cleanup MCP integration resources."""
        try:
            # Cleanup discovery manager
            if self._discovery_manager:
                await self._discovery_manager.cleanup()

            # Stop MCP server if running
            if self._mcp_server:
                await self._mcp_server.cleanup()

            # Unsubscribe from events
            if self.event_bus:
                # Unsubscribe from all events (implementation depends on event bus)
                pass

            self._initialized = False
            logger.info("MCP Integration Service cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during MCP cleanup: {e}")