"""
System health monitoring service.

Monitors system and external service health.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable

from loguru import logger


class HealthMonitor:
    """Monitors system and service health."""

    def __init__(self):
        """Initialize health monitor."""
        self._get_claude_status: Optional[Callable] = None
        self._state_manager = None

    def set_claude_status_callback(self, callback: Callable) -> None:
        """Set callback to get Claude API status.

        Args:
            callback: Async callable that returns Claude status
        """
        self._get_claude_status = callback

    def set_state_manager(self, state_manager) -> None:
        """Set state manager for database health checks.

        Args:
            state_manager: State manager instance
        """
        self._state_manager = state_manager

    async def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health.

        Returns:
            Dictionary with health status for each component
        """
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy",
            "components": {}
        }

        claude_status = await self._check_claude_api()
        health_status["components"]["claude_api"] = claude_status

        db_status = await self._check_database()
        health_status["components"]["database"] = db_status

        if not all(status.get("healthy") for status in health_status["components"].values()):
            health_status["overall_status"] = "degraded"

        return health_status

    async def _check_claude_api(self) -> Dict[str, Any]:
        """Check Claude API connectivity.

        Returns:
            Status dictionary for Claude API
        """
        status = {
            "service": "claude_api",
            "healthy": True,
            "message": "Not checked",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            if self._get_claude_status:
                claude_status = await self._get_claude_status()
                status["healthy"] = True
                status["message"] = f"Connected - {claude_status}"
            else:
                logger.debug("Claude status callback not configured")
                status["message"] = "Callback not configured"
                status["healthy"] = True
        except Exception as e:
            logger.error(f"Claude API health check failed: {e}")
            status["message"] = f"Error: {str(e)}"
            status["healthy"] = False

        return status

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity.

        Returns:
            Status dictionary for database
        """
        status = {
            "service": "database",
            "healthy": False,
            "message": "Not checked",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            if self._state_manager:
                # Try to get portfolio to verify database is working
                portfolio = await self._state_manager.get_portfolio()
                status["healthy"] = True
                status["message"] = "Connected"
                logger.info("Database health check passed")
            else:
                logger.warning("State manager not configured for health check")
                status["message"] = "State manager not configured"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            status["message"] = f"Error: {str(e)}"
            status["healthy"] = False

        return status

    async def execute_system_health_check(self) -> Dict[str, Any]:
        """Execute comprehensive system health check.

        Returns:
            Detailed health check results
        """
        logger.info("Executing system health check")

        health_status = await self.check_system_health()

        logger.info(f"Health check completed - Status: {health_status['overall_status']}")

        return health_status

    async def execute_data_cleanup(self) -> Dict[str, Any]:
        """Execute data cleanup task.

        Returns:
            Cleanup results
        """
        result = {
            "status": "failed",
            "message": "No state manager configured",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            if self._state_manager:
                await self._state_manager.cleanup_old_data()
                result["status"] = "success"
                result["message"] = "Data cleanup completed successfully"
                logger.info("Data cleanup completed successfully")
            else:
                logger.warning("No state manager configured for data cleanup")
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            result["status"] = "failed"
            result["message"] = f"Error: {str(e)}"

        return result

    def get_health_summary(self, health_status: Dict[str, Any]) -> str:
        """Get human-readable health summary.

        Args:
            health_status: Health status dictionary

        Returns:
            Summary string
        """
        components = health_status.get("components", {})
        healthy_count = sum(1 for c in components.values() if c.get("healthy"))
        total_count = len(components)

        return f"System Health: {health_status.get('overall_status', 'unknown')} ({healthy_count}/{total_count} components healthy)"
