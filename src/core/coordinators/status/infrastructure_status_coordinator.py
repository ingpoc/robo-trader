"""
Infrastructure Status Coordinator

Focused coordinator for infrastructure component status (database, websocket, resources).
Extracted from SystemStatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, Any

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
        connection_manager = None
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
            connection = getattr(getattr(self.state_manager, "db", None), "_connection_pool", None)
            if connection is None:
                return {
                    "status": "error",
                    "connection_state": "disconnected",
                    "connections": 0,
                    "portfolioLoaded": False,
                    "lastCheck": datetime.now(timezone.utc).isoformat(),
                    "error": "Database connection pool is not initialized",
                }

            cursor = await connection.execute("SELECT 1")
            try:
                await cursor.fetchone()
            finally:
                await cursor.close()

            portfolio = await self.state_manager.get_portfolio()
            return {
                "status": "healthy",
                "connection_state": "connected",
                "connections": 1,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "portfolioLoaded": portfolio is not None
            }
        except Exception as e:
            return {
                "status": "error",
                "connection_state": "disconnected",
                "connections": 0,
                "portfolioLoaded": False,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    async def get_websocket_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status."""
        websocket_clients = 0
        websocket_status = "idle"
        connection_state = "idle"
        if self._connection_manager:
            try:
                websocket_clients = await self._connection_manager.get_connection_count()
                websocket_status = "healthy" if websocket_clients > 0 else "idle"
                connection_state = "connected" if websocket_clients > 0 else "idle"
            except Exception as e:
                self._log_warning(f"Failed to get WebSocket connection count: {e}")
                websocket_status = "error"
                connection_state = "error"

        return {
            "status": websocket_status,
            "connection_state": connection_state,
            "clients": websocket_clients,
            "lastCheck": datetime.now(timezone.utc).isoformat()
        }

    async def get_system_resources(self) -> Dict[str, Any]:
        """Get basic system resource metrics."""
        try:
            import psutil
            return {
                "status": "healthy",
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent,
                "lastCheck": datetime.now(timezone.utc).isoformat()
            }
        except ImportError:
            return {
                "status": "error",
                "cpu": None,
                "memory": None,
                "disk": None,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": "System resource metrics unavailable: psutil is not installed"
            }
        except Exception as e:
            self._log_warning(f"Failed to get system resources: {e}")
            return {
                "status": "error",
                "cpu": None,
                "memory": None,
                "disk": None,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    def set_connection_manager(self, connection_manager) -> None:
        """Set the connection manager dependency."""
        self._connection_manager = connection_manager
        self._log_info("Connection manager set for InfrastructureStatusCoordinator")

    async def cleanup(self) -> None:
        """Cleanup infrastructure status coordinator resources."""
        self._log_info("InfrastructureStatusCoordinator cleanup complete")
