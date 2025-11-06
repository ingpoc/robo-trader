"""
Collaboration Coordinator Agent

Coordinates multi-agent collaboration for complex trading decisions.
Manages task assignment, result synthesis, and agent performance tracking.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from claude_agent_sdk import ClaudeSDKClient
from loguru import logger

from src.config import Config

from ..core.database_state import DatabaseStateManager
from ..core.event_bus import EventBus
from ..core.multi_agent_framework import (AgentMessage, AgentRole,
                                          CollaborationMode, CollaborationTask,
                                          MessageType, MultiAgentFramework)


class CollaborationCoordinator:
    """
    Coordinates complex multi-agent collaboration tasks.

    Key responsibilities:
    - Initiate collaborative analysis tasks
    - Synthesize results from multiple agents
    - Manage agent performance and specialization
    - Handle complex decision-making scenarios
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager,
        event_bus: EventBus,
        framework: MultiAgentFramework,
    ):
        self.config = config
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.framework = framework
        self.client: Optional[ClaudeSDKClient] = None

    async def initialize(self) -> None:
        """Initialize the collaboration coordinator."""
        logger.info("Initializing Collaboration Coordinator")
        logger.info("Collaboration Coordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up coordinator client: {e}")

    async def initiate_comprehensive_analysis(
        self, symbol: str, analysis_type: str = "full", urgency: str = "normal"
    ) -> Optional[CollaborationTask]:
        """
        Initiate comprehensive analysis using multiple specialized agents.

        Args:
            symbol: Stock symbol to analyze
            analysis_type: Type of analysis ("full", "technical", "fundamental", "risk")
            urgency: Urgency level ("high", "normal", "low")

        Returns:
            Collaboration task or None if failed
        """
        try:
            # Determine required agent roles based on analysis type
            required_roles = self._get_roles_for_analysis_type(analysis_type)

            # Choose collaboration mode based on urgency
            collaboration_mode = self._get_collaboration_mode_for_urgency(urgency)

            # Create task description
            description = f"Comprehensive {analysis_type} analysis for {symbol}"

            # Set deadline based on urgency
            deadline = self._calculate_deadline(urgency)

            # Create collaboration task
            task = await self.framework.create_collaboration_task(
                description=description,
                required_roles=required_roles,
                collaboration_mode=collaboration_mode,
                deadline=deadline,
            )

            if task:
                # Send initial analysis request to all assigned agents
                await self._send_initial_analysis_request(task, symbol, analysis_type)

                logger.info(
                    f"Initiated comprehensive analysis for {symbol}: task {task.task_id}"
                )
                return task

        except Exception as e:
            logger.error(f"Failed to initiate comprehensive analysis for {symbol}: {e}")

        return None

    async def coordinate_trading_decision(
        self, symbol: str, action_type: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Coordinate a complex trading decision using multiple agents.

        Args:
            symbol: Stock symbol
            action_type: Type of action ("buy", "sell", "hold")
            context: Decision context and constraints

        Returns:
            Coordinated decision result
        """
        try:
            # Create decision coordination task
            required_roles = [
                AgentRole.TECHNICAL_ANALYST,
                AgentRole.FUNDAMENTAL_SCREENER,
                AgentRole.RISK_MANAGER,
                AgentRole.STRATEGY_AGENT,
            ]

            task = await self.framework.create_collaboration_task(
                description=f"Trading decision coordination for {symbol} ({action_type})",
                required_roles=required_roles,
                collaboration_mode=CollaborationMode.VOTING,
                deadline=self._calculate_deadline("high"),
            )

            if not task:
                return {
                    "status": "failed",
                    "error": "Could not create coordination task",
                }

            # Send decision context to agents
            await self._send_decision_context(task, symbol, action_type, context)

            # Wait for results with timeout
            timeout = 120.0  # 2 minutes for urgent decisions
            result = await self._wait_for_task_completion(task.task_id, timeout)

            if result:
                # Process and return final decision
                final_decision = await self._process_decision_result(
                    result, symbol, action_type
                )
                return {
                    "status": "success",
                    "decision": final_decision,
                    "task_id": task.task_id,
                    "agents_involved": len(task.assigned_agents),
                }
            else:
                return {"status": "timeout", "error": "Decision coordination timed out"}

        except Exception as e:
            logger.error(f"Failed to coordinate trading decision for {symbol}: {e}")
            return {"status": "error", "error": str(e)}

    async def optimize_agent_performance(self) -> Dict[str, Any]:
        """
        Analyze and optimize agent performance based on collaboration history.

        Returns:
            Performance optimization recommendations
        """
        try:
            # Get all registered agents
            agent_performance = {}
            for agent_id in self.framework.registered_agents.keys():
                performance = await self.framework.get_agent_performance(agent_id)
                agent_performance[agent_id] = performance

            # Analyze collaboration patterns and effectiveness
            optimization_recommendations = (
                await self._analyze_agent_optimization_opportunities(agent_performance)
            )

            return {
                "status": "success",
                "agent_performance": agent_performance,
                "optimization_recommendations": optimization_recommendations,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to optimize agent performance: {e}")
            return {"status": "error", "error": str(e)}

    async def _send_initial_analysis_request(
        self, task: CollaborationTask, symbol: str, analysis_type: str
    ) -> None:
        """Send initial analysis request to all assigned agents."""
        analysis_context = {
            "symbol": symbol,
            "analysis_type": analysis_type,
            "timeframe": "comprehensive",
            "market_context": await self._get_market_context(),
            "portfolio_context": await self._get_portfolio_context(),
        }

        for agent_id in task.assigned_agents:
            message = AgentMessage(
                message_id=f"analysis_req_{task.task_id}_{agent_id}",
                sender_agent="coordinator",
                recipient_agent=agent_id,
                message_type=MessageType.ANALYSIS_REQUEST,
                content={
                    "task_id": task.task_id,
                    "analysis_context": analysis_context,
                    "expected_response_format": {
                        "confidence": "0-1 scale",
                        "analysis": "detailed analysis text",
                        "recommendations": ["list of recommendations"],
                        "risk_assessment": "risk level assessment",
                        "time_horizon": "short/medium/long term",
                    },
                },
                correlation_id=task.task_id,
                priority=8,
            )
            await self.framework.send_message(message)

    async def _send_decision_context(
        self,
        task: CollaborationTask,
        symbol: str,
        action_type: str,
        context: Dict[str, Any],
    ) -> None:
        """Send decision context to agents for voting."""
        decision_context = {
            "symbol": symbol,
            "proposed_action": action_type,
            "current_price": context.get("current_price"),
            "position_size": context.get("position_size"),
            "risk_tolerance": context.get("risk_tolerance"),
            "time_horizon": context.get("time_horizon"),
            "market_conditions": await self._get_market_context(),
            "portfolio_impact": await self._get_portfolio_impact(
                symbol, action_type, context
            ),
        }

        for agent_id in task.assigned_agents:
            message = AgentMessage(
                message_id=f"decision_req_{task.task_id}_{agent_id}",
                sender_agent="coordinator",
                recipient_agent=agent_id,
                message_type=MessageType.DECISION_PROPOSAL,
                content={
                    "task_id": task.task_id,
                    "decision_context": decision_context,
                    "voting_format": {
                        "vote": "approve/reject/modify",
                        "confidence": "0-1 scale",
                        "rationale": "brief explanation",
                        "modifications": "if vote is modify, suggested changes",
                    },
                },
                correlation_id=task.task_id,
                priority=9,
            )
            await self.framework.send_message(message)

    async def _wait_for_task_completion(
        self, task_id: str, timeout: float
    ) -> Optional[Dict[str, Any]]:
        """Wait for a collaboration task to complete."""
        start_time = datetime.now(timezone.utc)

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            result = await self.framework.get_collaboration_result(task_id)
            if result:
                return result
            await asyncio.sleep(1)

        return None

    async def _process_decision_result(
        self, result: Dict[str, Any], symbol: str, action_type: str
    ) -> Dict[str, Any]:
        """Process the final decision result from agent collaboration."""
        # Extract votes and analysis from result
        analysis_results = result.get("analysis_result", {})

        # Count votes
        votes = {"approve": 0, "reject": 0, "modify": 0}
        total_confidence = 0
        rationales = []

        for agent_id, analysis in analysis_results.items():
            vote = analysis.get("vote", "reject")
            if vote in votes:
                votes[vote] += 1

            confidence = analysis.get("confidence", 0)
            total_confidence += confidence

            if "rationale" in analysis:
                rationales.append(f"{agent_id}: {analysis['rationale']}")

        # Determine final decision
        avg_confidence = (
            total_confidence / len(analysis_results) if analysis_results else 0
        )

        if votes["approve"] > votes["reject"] and votes["approve"] > votes["modify"]:
            final_decision = "approved"
        elif votes["modify"] > votes["approve"] and votes["modify"] > votes["reject"]:
            final_decision = "modify"
        else:
            final_decision = "rejected"

        return {
            "action": action_type,
            "symbol": symbol,
            "final_decision": final_decision,
            "vote_breakdown": votes,
            "average_confidence": avg_confidence,
            "agent_rationales": rationales,
            "recommendations": self._extract_consensus_recommendations(
                analysis_results
            ),
        }

    async def _analyze_agent_optimization_opportunities(
        self, agent_performance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze opportunities to optimize agent performance."""
        recommendations = []

        # Identify underperforming agents
        for agent_id, performance in agent_performance.items():
            score = performance.get("performance_score", 0.5)
            completed_tasks = performance.get("completed_tasks", 0)

            if score < 0.6 and completed_tasks > 5:
                recommendations.append(
                    {
                        "agent_id": agent_id,
                        "issue": "low_performance_score",
                        "recommendation": "Consider retraining or specialization adjustment",
                        "current_score": score,
                        "tasks_completed": completed_tasks,
                    }
                )

        # Identify collaboration patterns
        # This could analyze which agent combinations work best together

        return recommendations

    def _get_roles_for_analysis_type(self, analysis_type: str) -> List[AgentRole]:
        """Get required agent roles for a specific analysis type."""
        role_mappings = {
            "full": [
                AgentRole.TECHNICAL_ANALYST,
                AgentRole.FUNDAMENTAL_SCREENER,
                AgentRole.RISK_MANAGER,
                AgentRole.PORTFOLIO_ANALYST,
            ],
            "technical": [AgentRole.TECHNICAL_ANALYST],
            "fundamental": [AgentRole.FUNDAMENTAL_SCREENER],
            "risk": [AgentRole.RISK_MANAGER],
            "market": [AgentRole.MARKET_MONITOR],
        }

        return role_mappings.get(analysis_type, role_mappings["full"])

    def _get_collaboration_mode_for_urgency(self, urgency: str) -> CollaborationMode:
        """Get appropriate collaboration mode for urgency level."""
        if urgency == "high":
            return CollaborationMode.PARALLEL
        elif urgency == "normal":
            return CollaborationMode.SEQUENTIAL
        else:  # low
            return CollaborationMode.CONSENSUS

    def _calculate_deadline(self, urgency: str) -> str:
        """Calculate task deadline based on urgency."""
        now = datetime.now(timezone.utc)

        if urgency == "high":
            deadline = now.replace(second=0, microsecond=0) + asyncio.timedelta(
                minutes=5
            )
        elif urgency == "normal":
            deadline = now.replace(second=0, microsecond=0) + asyncio.timedelta(
                minutes=15
            )
        else:  # low
            deadline = now.replace(second=0, microsecond=0) + asyncio.timedelta(hours=1)

        return deadline.isoformat()

    async def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context."""
        # This would integrate with market data services
        return {"volatility": "moderate", "trend": "bullish", "key_events": []}

    async def _get_portfolio_context(self) -> Dict[str, Any]:
        """Get current portfolio context."""
        # This would integrate with portfolio services
        return {
            "total_value": 100000.0,
            "risk_level": "moderate",
            "sector_allocation": {},
        }

    async def _get_portfolio_impact(
        self, symbol: str, action: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate portfolio impact of a potential trade."""
        # This would perform portfolio impact analysis
        return {
            "diversification_impact": "minimal",
            "risk_change": "slight_increase",
            "sector_exposure": "maintains_balance",
        }

    def _extract_consensus_recommendations(
        self, analysis_results: Dict[str, Any]
    ) -> List[str]:
        """Extract consensus recommendations from agent analyses."""
        all_recommendations = []

        for agent_analysis in analysis_results.values():
            recommendations = agent_analysis.get("recommendations", [])
            all_recommendations.extend(recommendations)

        # Find most common recommendations (simple consensus)
        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

        # Return recommendations mentioned by multiple agents
        consensus_recs = [
            rec
            for rec, count in recommendation_counts.items()
            if count > 1  # Mentioned by more than one agent
        ]

        return consensus_recs[:5]  # Limit to top 5
