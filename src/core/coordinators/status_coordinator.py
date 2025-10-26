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
        broadcast_coordinator = None
    ):
        super().__init__(config)
        self.state_manager = state_manager
        self.ai_planner = ai_planner
        self.background_scheduler = background_scheduler
        self.session_coordinator = session_coordinator
        self._broadcast_coordinator = broadcast_coordinator

    async def initialize(self) -> None:
        """Initialize status coordinator."""
        self._log_info("Initializing StatusCoordinator")
        self._initialized = True

        # Start periodic health broadcasts
        await self.start_periodic_broadcasts()

    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        return await self.ai_planner.get_current_task_status()

    async def get_system_status(self) -> Dict[str, Any]:
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

        # Broadcast system health update via WebSocket
        if hasattr(self, '_broadcast_coordinator') and self._broadcast_coordinator:
            # Transform to frontend format for broadcasting
            components = {}

            # Scheduler status
            if scheduler_status and scheduler_status.get("running"):
                components["scheduler"] = {
                    "status": "healthy",
                    "lastRun": scheduler_status.get("last_run_time", "unknown")
                }
            else:
                components["scheduler"] = {
                    "status": "stopped",
                    "lastRun": scheduler_status.get("last_run_time", "unknown") if scheduler_status else "unknown"
                }

            # Database status (assume healthy if we got here)
            components["database"] = {
                "status": "connected",
                "connections": 1
            }

            # WebSocket status
            components["websocket"] = {
                "status": "connected",
                "clients": 0  # TODO: Get from connection_manager
            }

            # Claude agent status
            if claude_status and claude_status.is_valid:
                sdk_connected = claude_status.account_info.get("sdk_connected", False)
                cli_process_running = claude_status.account_info.get("cli_process_running", False)
                if sdk_connected and cli_process_running:
                    components["claudeAgent"] = {
                        "status": "active",
                        "tasksCompleted": 0
                    }
                else:
                    components["claudeAgent"] = {
                        "status": "authenticated",
                        "tasksCompleted": 0
                    }
            else:
                components["claudeAgent"] = {
                    "status": "inactive",
                    "tasksCompleted": 0
                }

            # Queue status - include queue information in system health updates
            # This provides comprehensive system status including queue health
            components["queue"] = {
                "status": "healthy",  # Assume healthy if system is running
                "totalTasks": 0  # Will be updated by queue_status_update messages
            }

            health_data = {
                "status": "healthy",
                "components": components,
                "timestamp": status_data["timestamp"]
            }

            await self._broadcast_coordinator.broadcast_system_health_update(health_data)

        return status_data

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

    async def start_periodic_broadcasts(self) -> None:
        """Start periodic broadcasting of system health."""
        import asyncio

        async def broadcast_loop():
            while True:
                try:
                    await self.get_system_status()  # This will trigger WebSocket broadcast
                    await asyncio.sleep(15)  # Broadcast every 15 seconds
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._log_error(f"Error in periodic health broadcast: {e}", exc_info=True)
                    await asyncio.sleep(30)

        self._broadcast_task = asyncio.create_task(broadcast_loop())
        self._log_info("Started periodic system health broadcasts")

    async def stop_periodic_broadcasts(self) -> None:
        """Stop periodic broadcasting."""
        if hasattr(self, '_broadcast_task') and self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._log_info("Stopped periodic system health broadcasts")

    async def cleanup(self) -> None:
        """Cleanup status coordinator resources."""
        await self.stop_periodic_broadcasts()
        self._log_info("StatusCoordinator cleanup complete")
