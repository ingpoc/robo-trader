"""
Status Coordinator (Refactored)

Thin orchestrator that delegates to focused status coordinators.
Refactored from 261-line orchestrator into focused coordinators.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from src.config import Config
from ..base_coordinator import BaseCoordinator
from .system_status_coordinator import SystemStatusCoordinator
from .ai_status_coordinator import AIStatusCoordinator
from .agent_status_coordinator import AgentStatusCoordinator
from .portfolio_status_coordinator import PortfolioStatusCoordinator
from .broadcast.status_broadcast_coordinator import StatusBroadcastCoordinator
from .aggregation.status_aggregation_coordinator import StatusAggregationCoordinator


class StatusCoordinator(BaseCoordinator):
    """
    Coordinates status aggregation and reporting.
    
    Responsibilities:
    - Orchestrate status aggregation from focused coordinators
    - Handle broadcasting and change detection
    - Provide unified status interface
    """
    
    def __init__(
        self,
        config: Config,
        system_status_coordinator: SystemStatusCoordinator,
        ai_status_coordinator: AIStatusCoordinator,
        agent_status_coordinator: AgentStatusCoordinator,
        portfolio_status_coordinator: PortfolioStatusCoordinator,
        broadcast_coordinator = None
    ):
        super().__init__(config)
        self.system_status_coordinator = system_status_coordinator
        self.ai_status_coordinator = ai_status_coordinator
        self.agent_status_coordinator = agent_status_coordinator
        self.portfolio_status_coordinator = portfolio_status_coordinator

        # Store the main broadcast coordinator for direct access
        self.main_broadcast_coordinator = broadcast_coordinator

        # Focused coordinators
        self.aggregation_coordinator = StatusAggregationCoordinator(
            config,
            system_status_coordinator,
            ai_status_coordinator,
            portfolio_status_coordinator
        )
        self.broadcast_coordinator_internal = StatusBroadcastCoordinator(config, broadcast_coordinator)

        # Pass broadcast coordinator to AI status coordinator for Claude status updates
        if broadcast_coordinator:
            self.ai_status_coordinator.set_broadcast_coordinator(broadcast_coordinator)

        # NOTE: Background task removed - using event-driven approach now
        # AIStatusCoordinator subscribes to CLAUDE_ANALYSIS_STARTED/COMPLETED events
    
    async def initialize(self) -> None:
        """Initialize status coordinator."""
        self._log_info("Initializing StatusCoordinator")

        await self.aggregation_coordinator.initialize()
        await self.broadcast_coordinator_internal.initialize()

        # NOTE: Claude status polling loop removed - now using event-driven approach
        # AIStatusCoordinator handles CLAUDE_ANALYSIS_STARTED/COMPLETED events
        # No need for continuous polling anymore

        self._initialized = True
        self._log_info("StatusCoordinator initialized - using event-driven Claude status tracking")
    
    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status."""
        return await self.ai_status_coordinator.get_ai_status()
    
    async def get_system_status(self, force_broadcast: bool = False) -> Dict[str, Any]:
        """Get comprehensive system status for monitoring."""
        # Get all statuses in parallel for better performance
        ai_status, scheduler_status_data, claude_status_data, portfolio_status = await asyncio.gather(
            self.get_ai_status(),
            self.system_status_coordinator.get_scheduler_status(),
            self.ai_status_coordinator.get_claude_agent_status(),
            self.portfolio_status_coordinator.get_portfolio_status(),
            return_exceptions=True
        )

        # Get system components
        components = await self.aggregation_coordinator.aggregate_system_components(
            scheduler_status_data if not isinstance(scheduler_status_data, Exception) else {},
            claude_status_data if not isinstance(claude_status_data, Exception) else {}
        )

        status_data = {
            "ai_status": ai_status if not isinstance(ai_status, Exception) else {},
            "scheduler_status": scheduler_status_data if not isinstance(scheduler_status_data, Exception) else {},
            "claude_status": claude_status_data if not isinstance(claude_status_data, Exception) else {},
            "portfolio_status": portfolio_status if not isinstance(portfolio_status, Exception) else {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Broadcast if state changed or forced
        timestamp = status_data["timestamp"]
        await self.broadcast_coordinator_internal.broadcast_system_health(
            components, timestamp, force=force_broadcast
        )

        # Also broadcast Claude status based on active analysis tasks
        # This ensures the icon pulsates whenever Claude is analyzing (manual or automatic)
        await self.ai_status_coordinator.broadcast_claude_status_based_on_analysis()

        return status_data
    
    async def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        return await self.agent_status_coordinator.get_agents_status()
    
    def set_container(self, container) -> None:
        """Set the dependency container."""
        self.aggregation_coordinator.set_container(container)
    
    def set_connection_manager(self, connection_manager) -> None:
        """Set the connection manager for system status coordinator."""
        self.system_status_coordinator.set_connection_manager(connection_manager)
    
    async def on_scheduler_status_changed(self) -> None:
        """Event handler for scheduler status changes."""
        self._log_info("Scheduler status changed - broadcasting update")
    
    async def on_claude_status_changed(self) -> None:
        """Event handler for Claude status changes."""
        self._log_info("Claude status changed - broadcasting update")
        await self.get_system_status(force_broadcast=True)
    
    async def on_queue_status_changed(self) -> None:
        """Event handler for queue status changes."""
        self._log_info("Queue status changed - broadcasting update")
        await self.get_system_status(force_broadcast=True)
    
    async def on_system_error(self, error: Exception, context: str = None) -> None:
        """Event handler for system errors."""
        self._log_error(f"System error in {context}: {error}")
        await self.get_system_status(force_broadcast=True)
    
    async def broadcast_status_change(self, component: str, status: str) -> None:
        """Broadcast a specific component status change."""
        self._log_info(f"Component {component} status changed to {status}")
        await self.get_system_status(force_broadcast=True)

    async def get_claude_status(self) -> Dict[str, Any]:
        """Get Claude agent status and broadcast it to connected clients."""
        try:
            claude_status_data = await self.ai_status_coordinator.get_claude_agent_status()

            # Broadcast the current Claude status to all connected WebSocket clients
            if self.main_broadcast_coordinator and claude_status_data:
                # Map Claude status data to broadcast format
                broadcast_data = {
                    "status": claude_status_data.get("status", "inactive"),
                    "auth_method": claude_status_data.get("authMethod", claude_status_data.get("auth_method", "claude_code")),
                    "sdk_connected": claude_status_data.get("sdk_connected", False),
                    "cli_process_running": claude_status_data.get("cli_process_running", False),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "tasks_completed": claude_status_data.get("tasksCompleted", 0),
                        "last_activity": claude_status_data.get("lastActivity")
                    }
                }

                # Use the main broadcast coordinator to send the status
                await self.main_broadcast_coordinator.broadcast_claude_status_update(broadcast_data)
                self._log_debug(f"Claude status broadcasted: {broadcast_data['status']}")

            return claude_status_data

        except Exception as e:
            self._log_error(f"Failed to get and broadcast Claude status: {e}")
            return {}

    # NOTE: _broadcast_claude_status_loop method removed - now using event-driven approach
    # AIStatusCoordinator handles CLAUDE_ANALYSIS_STARTED/COMPLETED events in real-time
    # No polling needed anymore - more efficient and immediate updates

    async def cleanup(self) -> None:
        """Cleanup status coordinator resources."""
        # NOTE: Background broadcast task cleanup removed - using event-driven approach now
        # AIStatusCoordinator handles event subscription/unsubscription automatically

        await self.aggregation_coordinator.cleanup()
        await self.broadcast_coordinator_internal.cleanup()
        self._log_info("StatusCoordinator cleanup complete - event-driven Claude status tracking")
