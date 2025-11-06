"""
Agent Registration Coordinator

Focused coordinator for agent registration and management.
Extracted from AgentCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from loguru import logger

from src.config import Config

from ...database_state.database_state import DatabaseStateManager
from ...event_bus import Event, EventBus, EventType
from ..base_coordinator import BaseCoordinator
from .agent_profile import AgentProfile, AgentRole


class AgentRegistrationCoordinator(BaseCoordinator):
    """
    Coordinates agent registration and profiling.

    Responsibilities:
    - Agent registration
    - Agent availability tracking
    - Agent performance monitoring
    """

    def __init__(
        self, config: Config, state_manager: DatabaseStateManager, event_bus: EventBus
    ):
        super().__init__(config)
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.registered_agents: Dict[str, AgentProfile] = {}

    async def initialize(self) -> None:
        """Initialize agent registration coordinator."""
        logger.info("Initializing Agent Registration Coordinator")
        self._initialized = True

    async def register_agent(self, agent_profile: AgentProfile) -> bool:
        """
        Register a new agent.

        Args:
            agent_profile: Profile of the agent to register

        Returns:
            True if registered successfully
        """
        if agent_profile.agent_id in self.registered_agents:
            logger.warning(f"Agent {agent_profile.agent_id} already registered")
            return False

        self.registered_agents[agent_profile.agent_id] = agent_profile

        # Emit registration event
        await self.event_bus.publish(
            Event(
                event_type=EventType.TASK_COMPLETED,
                data={
                    "event_type": "agent_registered",
                    "agent_id": agent_profile.agent_id,
                    "role": agent_profile.role.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                source="agent_registration_coordinator",
            )
        )

        logger.info(
            f"Registered agent: {agent_profile.agent_id} ({agent_profile.role.value})"
        )
        return True

    async def get_available_agents(self, role: AgentRole) -> List[str]:
        """
        Get available agents for a specific role.

        Args:
            role: Required agent role

        Returns:
            List of available agent IDs
        """
        available = [
            agent_id
            for agent_id, profile in self.registered_agents.items()
            if profile.role == role and profile.is_active
        ]
        return available

    async def update_agent_status(self, agent_id: str, is_active: bool) -> None:
        """
        Update agent active status.

        Args:
            agent_id: ID of the agent
            is_active: New active status
        """
        if agent_id in self.registered_agents:
            self.registered_agents[agent_id].is_active = is_active
            self.registered_agents[agent_id].last_active = datetime.now(
                timezone.utc
            ).isoformat()
            logger.info(f"Agent {agent_id} status updated: active={is_active}")

    async def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Performance metrics
        """
        agent = self.registered_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        return {
            "agent_id": agent_id,
            "role": agent.role.value,
            "performance_score": agent.performance_score,
            "completed_tasks": len(agent.collaboration_history),
            "specializations": agent.specialization_areas,
            "is_active": agent.is_active,
            "last_active": agent.last_active,
        }

    async def _register_builtin_agents(self) -> None:
        """Register the built-in specialized agents."""
        builtin_agents = [
            AgentProfile(
                agent_id="technical_analyst",
                role=AgentRole.TECHNICAL_ANALYST,
                capabilities=[
                    "chart_analysis",
                    "pattern_recognition",
                    "technical_indicators",
                ],
                specialization_areas=[
                    "trend_analysis",
                    "momentum_signals",
                    "support_resistance",
                ],
            ),
            AgentProfile(
                agent_id="fundamental_screener",
                role=AgentRole.FUNDAMENTAL_SCREENER,
                capabilities=[
                    "financial_statement_analysis",
                    "valuation_metrics",
                    "earnings_analysis",
                ],
                specialization_areas=[
                    "growth_stocks",
                    "value_investing",
                    "earnings_quality",
                ],
            ),
            AgentProfile(
                agent_id="risk_manager",
                role=AgentRole.RISK_MANAGER,
                capabilities=[
                    "portfolio_risk_assessment",
                    "position_sizing",
                    "stop_loss_calculation",
                ],
                specialization_areas=[
                    "volatility_management",
                    "drawdown_control",
                    "correlation_analysis",
                ],
            ),
            AgentProfile(
                agent_id="portfolio_analyzer",
                role=AgentRole.PORTFOLIO_ANALYST,
                capabilities=[
                    "portfolio_optimization",
                    "sector_analysis",
                    "diversification_check",
                ],
                specialization_areas=[
                    "asset_allocation",
                    "rebalancing",
                    "performance_attribution",
                ],
            ),
            AgentProfile(
                agent_id="market_monitor",
                role=AgentRole.MARKET_MONITOR,
                capabilities=[
                    "market_data_collection",
                    "news_analysis",
                    "sentiment_tracking",
                ],
                specialization_areas=[
                    "market_trends",
                    "economic_indicators",
                    "news_impact",
                ],
            ),
            AgentProfile(
                agent_id="strategy_agent",
                role=AgentRole.STRATEGY_AGENT,
                capabilities=["strategy_design", "backtesting", "optimization"],
                specialization_areas=[
                    "swing_trading",
                    "momentum_strategies",
                    "mean_reversion",
                ],
            ),
        ]

        for agent in builtin_agents:
            await self.register_agent(agent)

    async def cleanup(self) -> None:
        """Cleanup agent registration coordinator resources."""
        logger.info("AgentRegistrationCoordinator cleanup complete")
