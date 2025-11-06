"""
Infrastructure Status Coordinator

Focused coordinator for infrastructure component status (database, websocket, resources).
Extracted from SystemStatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from src.config import Config

from ...database_state.database_state import DatabaseStateManager
from ..base_coordinator import BaseCoordinator


class InfrastructureStatusCoordinator(BaseCoordinator):
    """
    Coordinates infrastructure component status.

    Responsibilities:
    - Get database status
    - Get WebSocket status
    - Get system resources
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager,
        connection_manager=None,
    ):
        super().__init__(config)
        self.state_manager = state_manager
        self._connection_manager = connection_manager

    async def initialize(self) -> None:
        """Initialize infrastructure status coordinator."""
        self._log_info("Initializing InfrastructureStatusCoordinator")
        self._initialized = True

    async def get_database_status(self) -> Dict[str, Any]:
        """Get database connection status."""
        try:
            portfolio = await self.state_manager.get_portfolio()
            return {
                "status": "connected",
                "connections": 1,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "portfolioLoaded": portfolio is not None,
            }
        except Exception as e:
            return {
                "status": "error",
                "connections": 0,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

    async def get_websocket_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status."""
        websocket_clients = 0
        websocket_status = "disconnected"
        if self._connection_manager:
            try:
                websocket_clients = (
                    await self._connection_manager.get_connection_count()
                )
                websocket_status = "connected" if websocket_clients > 0 else "idle"
            except Exception as e:
                self._log_warning(f"Failed to get WebSocket connection count: {e}")
                websocket_status = "error"

        return {
            "status": websocket_status,
            "clients": websocket_clients,
            "lastCheck": datetime.now(timezone.utc).isoformat(),
        }

    async def get_system_resources(self) -> Dict[str, Any]:
        """Get basic system resource metrics."""
        try:
            import psutil

            return {
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
            }
        except ImportError:
            return {
                "cpu": 15.5,
                "memory": 45.2,
                "disk": 62.8,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "note": "psutil not available - mock data",
            }
        except Exception as e:
            self._log_warning(f"Failed to get system resources: {e}")
            return {
                "cpu": 0,
                "memory": 0,
                "disk": 0,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

    def set_connection_manager(self, connection_manager) -> None:
        """Set the connection manager dependency."""
        self._connection_manager = connection_manager
        self._log_info("Connection manager set for InfrastructureStatusCoordinator")

    async def cleanup(self) -> None:
        """Cleanup infrastructure status coordinator resources."""
        self._log_info("InfrastructureStatusCoordinator cleanup complete")
