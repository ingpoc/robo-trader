"""
AI Status Coordinator

Focused coordinator for AI and Claude agent status.
Extracted from StatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.config import Config
from ..base_coordinator import BaseCoordinator
from ...ai_planner import AIPlanner
from ..core.session_coordinator import SessionCoordinator


class AIStatusCoordinator(BaseCoordinator):
    """
    Coordinates AI and Claude agent status.
    
    Responsibilities:
    - Get AI status
    - Get Claude agent status
    - Get AI analysis status
    """

    def __init__(
        self,
        config: Config,
        ai_planner: AIPlanner,
        session_coordinator: SessionCoordinator
    ):
        super().__init__(config)
        self.ai_planner = ai_planner
        self.session_coordinator = session_coordinator

    async def initialize(self) -> None:
        """Initialize AI status coordinator."""
        self._log_info("Initializing AIStatusCoordinator")
        self._initialized = True

    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        return await self.ai_planner.get_current_task_status()

    async def get_claude_agent_status(self) -> Dict[str, Any]:
        """Get Claude agent status."""
        claude_status = await self.session_coordinator.get_claude_status()
        
        if claude_status and claude_status.is_valid:
            sdk_connected = claude_status.account_info.get("sdk_connected", False)
            cli_process_running = claude_status.account_info.get("cli_process_running", False)
            if sdk_connected and cli_process_running:
                return {
                    "status": "active",
                    "authMethod": claude_status.account_info.get("auth_method", "unknown"),
                    "tasksCompleted": claude_status.account_info.get("tasks_completed", 0),
                    "lastActivity": claude_status.account_info.get("last_activity", datetime.now(timezone.utc).isoformat())
                }
            else:
                return {
                    "status": "authenticated",
                    "authMethod": claude_status.account_info.get("auth_method", "unknown"),
                    "tasksCompleted": 0,
                    "lastActivity": datetime.now(timezone.utc).isoformat()
                }
        else:
            return {
                "status": "inactive",
                "authMethod": "none",
                "tasksCompleted": 0,
                "lastActivity": None
            }

    def get_ai_analysis_status(self) -> str:
        """Get current AI analysis scheduler status."""
        try:
            from ...services.portfolio_intelligence_analyzer import PortfolioIntelligenceAnalyzer
            status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
            return status_info.get("status", "idle")
        except Exception as e:
            self._log_warning(f"Could not get AI analysis status: {e}")
            return "idle"
    
    def get_ai_analysis_last_run(self) -> str:
        """Get last run time for AI analysis."""
        try:
            status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
            last_activity = status_info.get("last_activity")
            if last_activity:
                return last_activity
            from datetime import timedelta
            return (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        except Exception:
            return (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    
    def get_ai_analysis_active_task(self) -> Optional[Dict[str, Any]]:
        """Get active AI analysis task details."""
        try:
            status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
            current_task = status_info.get("current_task")
            if current_task:
                return {
                    "agent_name": current_task.get("agent_name"),
                    "symbols_count": current_task.get("symbols_count", 0),
                    "started_at": current_task.get("started_at")
                }
            return None
        except Exception:
            return None

    async def cleanup(self) -> None:
        """Cleanup AI status coordinator resources."""
        self._log_info("AIStatusCoordinator cleanup complete")

