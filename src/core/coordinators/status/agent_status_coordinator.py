"""
Agent Status Coordinator

Focused coordinator for trading agent status.
Extracted from StatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from src.config import Config
from ..base_coordinator import BaseCoordinator


class AgentStatusCoordinator(BaseCoordinator):
    """
    Coordinates trading agent status.
    
    Responsibilities:
    - Get status of all trading agents
    """

    def __init__(self, config: Config):
        super().__init__(config)

    async def initialize(self) -> None:
        """Initialize agent status coordinator."""
        self._log_info("Initializing AgentStatusCoordinator")
        self._initialized = True

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

    async def cleanup(self) -> None:
        """Cleanup agent status coordinator resources."""
        self._log_info("AgentStatusCoordinator cleanup complete")

