"""
Agent Coordinator for Multi-Agent Framework

Handles agent registration, task assignment, and basic coordination.
Separated from the main framework to follow the 350-line rule.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from loguru import logger

from ..database_state import DatabaseStateManager
from ..event_bus import EventBus, Event, EventType
from .base_coordinator import BaseCoordinator
from .agent_message import AgentMessage, MessageType
from .agent_profile import AgentProfile, AgentRole


class AgentCoordinator(BaseCoordinator):
    """
    Coordinator for managing agent lifecycle and basic operations.

    Responsibilities:
    - Agent registration and profiling
    - Agent availability tracking
    - Basic agent communication routing
    - Agent performance monitoring
    """

    def __init__(self, config: Any, state_manager: DatabaseStateManager, event_bus: EventBus):
        super().__init__(config, "agent_coordinator")
        self.state_manager = state_manager
        self.event_bus = event_bus

        # Agent management
        self.registered_agents: Dict[str, AgentProfile] = {}
        self.agent_message_queue: asyncio.Queue = asyncio.Queue()

    async def initialize(self) -> None:
        """Initialize the agent coordinator."""
        logger.info("Initializing Agent Coordinator")

        # Register built-in agents
        await self._register_builtin_agents()

        # Start message processing
        self._running = True
        self._processing_task = asyncio.create_task(self._process_agent_messages())

        logger.info("Agent Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._running = False

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

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
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "agent_registered",
                "agent_id": agent_profile.agent_id,
                "role": agent_profile.role.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="agent_coordinator"
        ))

        logger.info(f"Registered agent: {agent_profile.agent_id} ({agent_profile.role.value})")
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
            agent_id for agent_id, profile in self.registered_agents.items()
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
            self.registered_agents[agent_id].last_active = datetime.now(timezone.utc).isoformat()

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
            "last_active": agent.last_active
        }

    async def send_agent_message(self, message: AgentMessage) -> None:
        """
        Send a message to an agent.

        Args:
            message: Message to send
        """
        await self.agent_message_queue.put(message)

        # Emit event for monitoring
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_COMPLETED,
            data={
                "event_type": "agent_message",
                "message": message.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            source="agent_coordinator"
        ))

    async def _register_builtin_agents(self) -> None:
        """Register the built-in specialized agents."""
        builtin_agents = [
            AgentProfile(
                agent_id="technical_analyst",
                role=AgentRole.TECHNICAL_ANALYST,
                capabilities=["chart_analysis", "pattern_recognition", "technical_indicators"],
                specialization_areas=["trend_analysis", "momentum_signals", "support_resistance"]
            ),
            AgentProfile(
                agent_id="fundamental_screener",
                role=AgentRole.FUNDAMENTAL_SCREENER,
                capabilities=["financial_statement_analysis", "valuation_metrics", "earnings_analysis"],
                specialization_areas=["growth_stocks", "value_investing", "earnings_quality"]
            ),
            AgentProfile(
                agent_id="risk_manager",
                role=AgentRole.RISK_MANAGER,
                capabilities=["portfolio_risk_assessment", "position_sizing", "stop_loss_calculation"],
                specialization_areas=["volatility_management", "drawdown_control", "correlation_analysis"]
            ),
            AgentProfile(
                agent_id="portfolio_analyzer",
                role=AgentRole.PORTFOLIO_ANALYST,
                capabilities=["portfolio_optimization", "sector_analysis", "diversification_check"],
                specialization_areas=["asset_allocation", "rebalancing", "performance_attribution"]
            ),
            AgentProfile(
                agent_id="market_monitor",
                role=AgentRole.MARKET_MONITOR,
                capabilities=["market_data_collection", "news_analysis", "sentiment_tracking"],
                specialization_areas=["market_trends", "economic_indicators", "news_impact"]
            ),
            AgentProfile(
                agent_id="strategy_agent",
                role=AgentRole.STRATEGY_AGENT,
                capabilities=["strategy_design", "backtesting", "optimization"],
                specialization_areas=["swing_trading", "momentum_strategies", "mean_reversion"]
            )
        ]

        for agent in builtin_agents:
            await self.register_agent(agent)

    async def _process_agent_messages(self) -> None:
        """Process agent messages."""
        logger.info("Agent message processing started")

        while self._running:
            try:
                # Process messages with timeout
                try:
                    message = await asyncio.wait_for(
                        self.agent_message_queue.get(),
                        timeout=1.0
                    )
                    await self._handle_agent_message(message)
                    self.agent_message_queue.task_done()
                except asyncio.TimeoutError:
                    continue

            except Exception as e:
                logger.error(f"Error processing agent message: {e}")
                await asyncio.sleep(1)

        logger.info("Agent message processing stopped")

    async def _handle_agent_message(self, message: AgentMessage) -> None:
        """
        Handle an agent message.

        Args:
            message: Message to handle
        """
        logger.debug(f"Processing agent message: {message.message_type.value} from {message.sender_agent}")

        # Update agent last active time
        if message.sender_agent in self.registered_agents:
            self.registered_agents[message.sender_agent].last_active = datetime.now(timezone.utc).isoformat()

        # Route based on message type
        if message.message_type == MessageType.STATUS_UPDATE:
            await self._handle_status_update(message)
        elif message.message_type == MessageType.ERROR_REPORT:
            await self._handle_error_report(message)

    async def _handle_status_update(self, message: AgentMessage) -> None:
        """Handle agent status update."""
        agent_id = message.sender_agent
        status_info = message.content

        if agent_id in self.registered_agents:
            # Update agent performance if provided
            if "performance_score" in status_info:
                self.registered_agents[agent_id].performance_score = status_info["performance_score"]

            logger.debug(f"Status update for agent {agent_id}: {status_info}")

    async def _handle_error_report(self, message: AgentMessage) -> None:
        """Handle agent error report."""
        agent_id = message.sender_agent
        error_info = message.content

        logger.error(f"Agent error reported by {agent_id}: {error_info}")

        # Could implement error recovery logic here