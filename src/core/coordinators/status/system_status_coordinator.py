"""
System Status Coordinator

Thin orchestrator that delegates to focused status coordinators.
Extracted from 209-line coordinator into focused coordinators.
"""

from typing import Dict, Any

from src.config import Config
from ..base_coordinator import BaseCoordinator
from .scheduler_status_coordinator import SchedulerStatusCoordinator
from .infrastructure_status_coordinator import InfrastructureStatusCoordinator


class SystemStatusCoordinator(BaseCoordinator):
    """
    Coordinates system component status aggregation.
    
    Responsibilities:
    - Orchestrate status aggregation from focused coordinators
    - Provide unified system status interface
    """

    def __init__(
        self,
        config: Config,
        scheduler_status_coordinator: SchedulerStatusCoordinator,
        infrastructure_status_coordinator: InfrastructureStatusCoordinator
    ):
        super().__init__(config)
        self.scheduler_status_coordinator = scheduler_status_coordinator
        self.infrastructure_status_coordinator = infrastructure_status_coordinator

    async def initialize(self) -> None:
        """Initialize system status coordinator."""
        self._log_info("Initializing SystemStatusCoordinator")
        self._initialized = True

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status information."""
        return await self.scheduler_status_coordinator.get_scheduler_status()

    async def get_database_status(self) -> Dict[str, Any]:
        """Get database connection status."""
        return await self.infrastructure_status_coordinator.get_database_status()

    async def get_websocket_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status."""
        return await self.infrastructure_status_coordinator.get_websocket_status()

    async def get_system_resources(self) -> Dict[str, Any]:
        """Get basic system resource metrics."""
        return await self.infrastructure_status_coordinator.get_system_resources()

    def set_connection_manager(self, connection_manager) -> None:
        """Set the connection manager for infrastructure coordinator."""
        self.infrastructure_status_coordinator.set_connection_manager(connection_manager)

    async def cleanup(self) -> None:
        """Cleanup system status coordinator resources."""
        self._log_info("SystemStatusCoordinator cleanup complete")

