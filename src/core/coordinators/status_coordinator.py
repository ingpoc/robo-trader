"""
Status Coordinator

Aggregates system status, AI status, and agent status.
Extracted from RoboTraderOrchestrator lines 388-422, 596-657.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from loguru import logger

from src.config import Config
from ...core.database_state import DatabaseStateManager
from ...core.ai_planner import AIPlanner
from ...core.background_scheduler import BackgroundScheduler
from .base_coordinator import BaseCoordinator
from .session_coordinator import SessionCoordinator


class StatusCoordinator(BaseCoordinator):
    """
    Coordinates status aggregation and reporting.

    Responsibilities:
    - Get AI status
    - Get system status
    - Get agent status
    - Get portfolio status
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager,
        ai_planner: AIPlanner,
        background_scheduler: BackgroundScheduler,
        session_coordinator: SessionCoordinator,
        broadcast_coordinator = None,
        connection_manager = None
    ):
        super().__init__(config)
        self.state_manager = state_manager
        self.ai_planner = ai_planner
        self.background_scheduler = background_scheduler
        self.session_coordinator = session_coordinator
        self._broadcast_coordinator = broadcast_coordinator
        self._connection_manager = connection_manager
        self._last_broadcast_state = {}  # Track last broadcasted state for change detection
        self._broadcast_metrics = {
            "total_broadcasts": 0,
            "successful_broadcasts": 0,
            "failed_broadcasts": 0,
            "state_changes": 0,
            "last_broadcast_time": None,
            "last_error": None
        }

    def set_connection_manager(self, connection_manager) -> None:
        """Set the connection manager dependency after initialization."""
        self._connection_manager = connection_manager
        self._log_info("Connection manager set for StatusCoordinator")

    def set_container(self, container) -> None:
        """Set the dependency container for accessing services."""
        self.container = container
        self._log_info("Dependency container set for StatusCoordinator")

    async def initialize(self) -> None:
        """Initialize status coordinator."""
        self._log_info("Initializing StatusCoordinator")
        self._initialized = True

        # Broadcast initial status once
        await self.get_system_status(force_broadcast=True)
        self._log_info("StatusCoordinator initialized with event-driven broadcasting")

    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        return await self.ai_planner.get_current_task_status()

    async def get_system_status(self, force_broadcast: bool = False) -> Dict[str, Any]:
        """Get comprehensive system status for monitoring."""
        ai_status = await self.get_ai_status()
        scheduler_status = await self.background_scheduler.get_scheduler_status()
        claude_status = await self.session_coordinator.get_claude_status()

        status_data = {
            "ai_status": ai_status,
            "scheduler_status": scheduler_status,
            "claude_status": claude_status.to_dict() if claude_status else None,
            "portfolio_status": await self._get_portfolio_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Get real system health components
        components = await self._get_system_components(scheduler_status, claude_status)

        # Check if state has changed
        current_state_hash = self._compute_state_hash(components)
        state_changed = current_state_hash != self._last_broadcast_state.get("hash")

        # Only broadcast if state changed or forced
        if (state_changed or force_broadcast) and self._broadcast_coordinator:
            health_data = {
                "status": self._compute_overall_status(components),
                "components": components,
                "timestamp": status_data["timestamp"],
                "metrics": self._broadcast_metrics
            }

            await self._broadcast_system_health_with_tracking(health_data)

            if state_changed:
                self._last_broadcast_state = {
                    "hash": current_state_hash,
                    "timestamp": status_data["timestamp"],
                    "components": components
                }
                self._broadcast_metrics["state_changes"] += 1

        return status_data

    async def _get_system_components(self, scheduler_status: Dict[str, Any], claude_status) -> Dict[str, Any]:
        """Get real system component status from actual sources."""
        import hashlib
        import json

        components = {}

        # Scheduler status - real data
        if scheduler_status and scheduler_status.get("running"):
            components["scheduler"] = {
                "status": "healthy",
                "lastRun": scheduler_status.get("last_run_time", "unknown"),
                "activeJobs": scheduler_status.get("active_jobs", 0),
                "completedJobs": scheduler_status.get("completed_jobs", 0)
            }
        else:
            components["scheduler"] = {
                "status": "stopped",
                "lastRun": scheduler_status.get("last_run_time", "unknown") if scheduler_status else "unknown",
                "activeJobs": 0,
                "completedJobs": 0
            }

        # Database status - check actual connection
        try:
            # Try a simple database operation to verify connection
            portfolio = await self.state_manager.get_portfolio()
            components["database"] = {
                "status": "connected",
                "connections": 1,  # Could be enhanced to get actual connection count
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "portfolioLoaded": portfolio is not None
            }
        except Exception as e:
            components["database"] = {
                "status": "error",
                "connections": 0,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

        # WebSocket status - get actual connection count
        websocket_clients = 0
        websocket_status = "disconnected"
        if self._connection_manager:
            try:
                websocket_clients = await self._connection_manager.get_connection_count()
                websocket_status = "connected" if websocket_clients > 0 else "idle"
            except Exception as e:
                self._log_warning(f"Failed to get WebSocket connection count: {e}")
                websocket_status = "error"

        components["websocket"] = {
            "status": websocket_status,
            "clients": websocket_clients,
            "lastCheck": datetime.now(timezone.utc).isoformat()
        }

        # Claude agent status - enhanced with real data
        if claude_status and claude_status.is_valid:
            sdk_connected = claude_status.account_info.get("sdk_connected", False)
            cli_process_running = claude_status.account_info.get("cli_process_running", False)
            if sdk_connected and cli_process_running:
                components["claudeAgent"] = {
                    "status": "active",
                    "authMethod": claude_status.account_info.get("auth_method", "unknown"),
                    "tasksCompleted": claude_status.account_info.get("tasks_completed", 0),
                    "lastActivity": claude_status.account_info.get("last_activity", datetime.now(timezone.utc).isoformat())
                }
            else:
                components["claudeAgent"] = {
                    "status": "authenticated",
                    "authMethod": claude_status.account_info.get("auth_method", "unknown"),
                    "tasksCompleted": 0,
                    "lastActivity": datetime.now(timezone.utc).isoformat()
                }
        else:
            components["claudeAgent"] = {
                "status": "inactive",
                "authMethod": "none",
                "tasksCompleted": 0,
                "lastActivity": None
            }

        # Queue status - get real queue data if available
        components["queue"] = await self._get_queue_health()

        # System resources - basic metrics
        components["resources"] = await self._get_system_resources()

        return components

    async def _get_queue_health(self) -> Dict[str, Any]:
        """Get real queue health status."""
        try:
            # Try to get queue management service if available
            if hasattr(self, 'container') and self.container:
                queue_service = await self.container.get("queue_management_service")
                if queue_service:
                    queue_stats = await queue_service.get_queue_stats()
                    return {
                        "status": "healthy" if queue_stats.get("total_queues", 0) > 0 else "idle",
                        "totalTasks": queue_stats.get("total_tasks", 0),
                        "runningQueues": queue_stats.get("running_queues", 0),
                        "totalQueues": queue_stats.get("total_queues", 0),
                        "lastCheck": datetime.now(timezone.utc).isoformat()
                    }
        except Exception as e:
            self._log_debug(f"Could not get queue health: {e}")

        # Fallback - assume healthy if system is running
        return {
            "status": "healthy",
            "totalTasks": 0,
            "runningQueues": 0,
            "totalQueues": 0,
            "lastCheck": datetime.now(timezone.utc).isoformat()
        }

    async def _get_system_resources(self) -> Dict[str, Any]:
        """Get basic system resource metrics."""
        try:
            import psutil
            return {
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent,
                "lastCheck": datetime.now(timezone.utc).isoformat()
            }
        except ImportError:
            # psutil not available - return mock data
            return {
                "cpu": 15.5,
                "memory": 45.2,
                "disk": 62.8,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "note": "psutil not available - mock data"
            }
        except Exception as e:
            self._log_warning(f"Failed to get system resources: {e}")
            return {
                "cpu": 0,
                "memory": 0,
                "disk": 0,
                "lastCheck": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    def _compute_state_hash(self, components: Dict[str, Any]) -> str:
        """Compute hash of component states for change detection."""
        import hashlib
        import json

        # Create a normalized JSON representation for consistent hashing
        normalized = json.dumps(components, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()

    def _compute_overall_status(self, components: Dict[str, Any]) -> str:
        """Compute overall system status from component statuses."""
        status_counts = {"healthy": 0, "degraded": 0, "error": 0, "stopped": 0, "inactive": 0, "idle": 0}

        for component in components.values():
            status = component.get("status", "unknown")
            if status in status_counts:
                status_counts[status] += 1

        # Determine overall status
        if status_counts["error"] > 0:
            return "error"
        elif status_counts["stopped"] > 0:
            return "degraded"
        elif status_counts["inactive"] > 0:
            return "degraded"
        elif status_counts["healthy"] > 0:
            return "healthy"
        else:
            return "idle"

    async def _broadcast_system_health_with_tracking(self, health_data: Dict[str, Any]) -> None:
        """Broadcast system health with error tracking and metrics."""
        try:
            self._broadcast_metrics["total_broadcasts"] += 1
            self._broadcast_metrics["last_broadcast_time"] = datetime.now(timezone.utc).isoformat()

            await self._broadcast_coordinator.broadcast_system_health_update(health_data)

            self._broadcast_metrics["successful_broadcasts"] += 1
            self._broadcast_metrics["last_error"] = None

        except Exception as e:
            self._broadcast_metrics["failed_broadcasts"] += 1
            self._broadcast_metrics["last_error"] = str(e)
            self._log_error(f"Failed to broadcast system health: {e}")

    async def _get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio health status."""
        try:
            portfolio = await self.state_manager.get_portfolio()
            if portfolio:
                return {
                    "holdings_count": len(portfolio.holdings),
                    "total_value": portfolio.exposure_total,
                    "last_updated": getattr(portfolio, 'last_updated', None)
                }
            return {"status": "no_portfolio"}
        except Exception:
            return {"status": "error"}

    async def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        agents = {
            "portfolio_analyzer": {
                "name": "Portfolio Analyzer",
                "active": True,
                "status": "idle",
                "tools": ["analyze_portfolio"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "technical_analyst": {
                "name": "Technical Analyst",
                "active": True,
                "status": "idle",
                "tools": ["technical_analysis"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "fundamental_screener": {
                "name": "Fundamental Screener",
                "active": True,
                "status": "idle",
                "tools": ["fundamental_screening"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "risk_manager": {
                "name": "Risk Manager",
                "active": True,
                "status": "idle",
                "tools": ["risk_assessment"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "execution_agent": {
                "name": "Execution Agent",
                "active": True,
                "status": "idle",
                "tools": ["execute_trade"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "market_monitor": {
                "name": "Market Monitor",
                "active": True,
                "status": "idle",
                "tools": ["monitor_market"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "educational_agent": {
                "name": "Educational Agent",
                "active": True,
                "status": "idle",
                "tools": ["explain_concept", "explain_decision", "explain_portfolio"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "alert_agent": {
                "name": "Alert Agent",
                "active": True,
                "status": "idle",
                "tools": ["create_alert_rule", "list_alert_rules", "check_alerts", "delete_alert_rule"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
        }

        return agents

    async def on_scheduler_status_changed(self) -> None:
        """Event handler for scheduler status changes."""
        self._log_info("Scheduler status changed - broadcasting update")
        await self.get_system_status(force_broadcast=True)

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

    async def cleanup(self) -> None:
        """Cleanup status coordinator resources."""
        self._log_info("StatusCoordinator cleanup complete")
        # Log final metrics
        self._log_info(f"Final broadcast metrics: {self._broadcast_metrics}")
