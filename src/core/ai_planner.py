"""
AI Planner for Robo Trader

Implements intelligent planning and decision-making capabilities using Claude SDK.
Provides multi-day planning, market condition assessment, and adaptive strategies.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from src.config import Config
from ..core.database_state import DatabaseStateManager


@dataclass
class MultiDayPlan:
    """Multi-day trading plan with risk-adjusted allocations."""
    planning_horizon_days: int
    risk_adjusted_allocations: Dict[str, float]  # day_1: 0.8, day_2: 0.7, etc.
    market_condition_forecasts: Dict[str, str]  # day_1: "bullish_moderate_volatility"
    strategic_adjustments: List[Dict[str, Any]]
    contingency_plans: Dict[str, Dict[str, Any]]
    learning_adaptations: List[str]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "MultiDayPlan":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MarketAdaptation:
    """Market condition adaptation recommendations."""
    volatility_adaptation: Dict[str, Any]
    trend_adaptation: Dict[str, Any]
    risk_adaptation: Dict[str, Any]
    confidence: float
    recommended_actions: List[str]

    @classmethod
    def from_dict(cls, data: Dict) -> "MarketAdaptation":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskAlgorithm:
    """Risk-adjusted planning algorithm."""
    position_sizing_algorithm: Dict[str, Any]
    portfolio_rebalancing: Dict[str, Any]
    risk_limits: Dict[str, Any]
    overall_score: float
    changes: List[str] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = []

    @classmethod
    def from_dict(cls, data: Dict) -> "RiskAlgorithm":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PlanningHeuristics:
    """Planning heuristics and parameters."""
    risk_algorithms: Dict[str, Any]
    last_updated: str
    performance_score: float
    api_budget_reserve: int = 5
    risk_multiplier: float = 1.0
    sector_focus_adjusted: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "PlanningHeuristics":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


class AIPlanner:
    """
    Advanced AI planning engine for trading operations.

    Key capabilities:
    - Multi-day strategic planning
    - Market condition assessment and adaptation
    - Risk-adjusted algorithm generation
    - Learning-based planning optimization
    - Concurrent request management
    """

    def __init__(self, config: Config, state_manager: DatabaseStateManager):
        self.config = config
        self.state_manager = state_manager
        self.client: Optional[ClaudeSDKClient] = None

        # Planning parameters
        self.daily_api_limit = 50
        self.reserve_budget = 5
        self.max_concurrent_requests = 3
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # Planning state
        self.current_plan: Optional[MultiDayPlan] = None
        self.market_conditions: Dict[str, Any] = {}
        self.planning_heuristics: Optional[PlanningHeuristics] = None

    async def initialize(self) -> None:
        """Initialize the AI planner."""
        logger.info("Initializing AI Planner")
        await self._ensure_client()
        await self._load_planning_state()
        logger.info("AI Planner initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup planner resources."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up planner client: {e}")

    async def generate_multi_day_plan(
        self,
        horizon_days: int = 5,
        market_conditions: Optional[Dict[str, Any]] = None,
        portfolio_state: Optional[Any] = None,
        learning_insights: Optional[List[Dict]] = None
    ) -> Optional[MultiDayPlan]:
        """
        Generate a strategic multi-day trading plan.

        Args:
            horizon_days: Number of days to plan for
            market_conditions: Current market conditions
            portfolio_state: Current portfolio state
            learning_insights: Recent learning insights

        Returns:
            Multi-day plan or None if generation fails
        """
        try:
            # Get market conditions if not provided
            if market_conditions is None:
                market_conditions = await self._assess_market_conditions()

            # Get learning insights if not provided
            if learning_insights is None:
                learning_insights = await self._get_recent_learning_insights()

            # Generate plan using Claude
            plan_data = await self._generate_multi_day_plan_data(
                horizon_days, market_conditions, portfolio_state, learning_insights
            )

            if plan_data:
                plan = MultiDayPlan.from_dict(plan_data)
                self.current_plan = plan

                # Store plan
                await self._store_plan(plan)

                logger.info(f"Generated {horizon_days}-day trading plan")
                return plan

            return None

        except Exception as e:
            logger.error(f"Multi-day plan generation failed: {e}")
            return None

    async def adapt_to_market_conditions(self) -> Optional[MarketAdaptation]:
        """
        Generate market condition adaptations.

        Returns:
            Market adaptation recommendations
        """
        try:
            # Assess current conditions
            conditions = await self._assess_market_conditions()

            # Extract key metrics
            volatility = conditions.get("volatility", "moderate")
            trend = conditions.get("trend", "sideways")
            risk_level = conditions.get("risk_level", "medium")

            # Generate adaptations
            adaptations = await self._generate_market_adaptations(volatility, trend, risk_level)

            # Update planning parameters
            await self._update_planning_parameters(adaptations)

            logger.info("Generated market condition adaptations")
            return adaptations

        except Exception as e:
            logger.error(f"Market adaptation generation failed: {e}")
            return None

    async def optimize_risk_algorithms(
        self,
        sharpe_ratio: float,
        max_drawdown: float,
        value_at_risk: float
    ) -> Optional[RiskAlgorithm]:
        """
        Generate risk-adjusted planning algorithms.

        Args:
            sharpe_ratio: Current Sharpe ratio
            max_drawdown: Maximum drawdown percentage
            value_at_risk: Value at risk percentage

        Returns:
            Risk-adjusted algorithms
        """
        try:
            algorithms = await self._generate_risk_adjusted_algorithms(
                sharpe_ratio, max_drawdown, value_at_risk
            )

            # Update planning heuristics
            await self._update_planning_heuristics(algorithms)

            logger.info("Generated risk-adjusted planning algorithms")
            return algorithms

        except Exception as e:
            logger.error(f"Risk algorithm optimization failed: {e}")
            return None

    async def learn_from_planning_effectiveness(self) -> Dict[str, Any]:
        """
        Learn from the effectiveness of past planning decisions.

        Returns:
            Learning insights from planning effectiveness
        """
        try:
            # Get historical planning data
            planning_data = await self._get_historical_planning_data()

            if not planning_data:
                return {"status": "no_data", "message": "No historical planning data available"}

            # Analyze planning outcomes
            outcomes = await self._analyze_planning_outcomes(planning_data)

            # Generate learning insights
            insights = await self._generate_planning_learning_insights(outcomes)

            # Update planning models
            await self._update_planning_models(insights)

            return {
                "status": "success",
                "outcomes": outcomes,
                "insights": insights,
                "improvement_potential": insights.get("improvement_potential", 0.0)
            }

        except Exception as e:
            logger.error(f"Planning effectiveness learning failed: {e}")
            return {"status": "error", "message": str(e)}

    async def get_planning_status(self) -> Dict[str, Any]:
        """
        Get current planning status and metrics.

        Returns:
            Planning status information
        """
        status = {
            "has_active_plan": self.current_plan is not None,
            "api_budget_remaining": self.daily_api_limit - self.reserve_budget,
            "market_conditions": self.market_conditions,
            "last_plan_generated": None,
            "planning_heuristics_score": None
        }

        if self.current_plan:
            status["last_plan_generated"] = self.current_plan.created_at
            status["planning_horizon"] = self.current_plan.planning_horizon_days

        if self.planning_heuristics:
            status["planning_heuristics_score"] = self.planning_heuristics.performance_score

        return status

    async def get_current_task_status(self) -> Dict[str, Any]:
        """
        Get current AI task status for UI display.

        Returns:
            Current task status information
        """
        try:
            # Get planning status as base
            planning_status = await self.get_planning_status()

            # Add current task information
            current_task = {
                "status": "idle",
                "description": "No active AI tasks",
                "progress": 0,
                "estimated_completion": None,
                "current_activity": "Monitoring market conditions"
            }

            # If we have an active plan, show planning activity
            if planning_status.get("has_active_plan"):
                current_task.update({
                    "status": "planning",
                    "description": f"Executing {planning_status.get('planning_horizon', 5)}-day trading plan",
                    "progress": 0.3,  # Mock progress
                    "current_activity": "Analyzing market conditions and generating recommendations"
                })

            # Combine planning status with task status
            status = {
                **planning_status,
                "current_task": current_task,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return status

        except Exception as e:
            logger.error(f"Failed to get current task status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "current_task": {
                    "status": "error",
                    "description": "Unable to retrieve task status",
                    "progress": 0,
                    "current_activity": "Error state"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _generate_multi_day_plan_data(
        self,
        horizon_days: int,
        market_conditions: Dict[str, Any],
        portfolio_state: Any,
        learning_insights: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Generate multi-day planning data using Claude."""
        async with self.request_semaphore:
            if not self.client:
                await self._ensure_client()

            query = f"""
            Create a strategic multi-day planning horizon for trading operations.

            PLANNING HORIZON: {horizon_days} days
            CURRENT MARKET CONDITIONS: {json.dumps(market_conditions, indent=2)}
            PORTFOLIO STATE: {len(portfolio_state.holdings) if portfolio_state else 0} holdings
            RECENT LEARNING INSIGHTS: {len(learning_insights)} insights

            Create a MultiDayPlan JSON with this structure:
            {{
              "planning_horizon_days": {horizon_days},
              "risk_adjusted_allocations": {{
                "day_1": 0.8,
                "day_2": 0.7,
                "day_3": 0.9,
                "day_4": 0.6,
                "day_5": 0.8
              }},
              "market_condition_forecasts": {{
                "day_1": "bullish_moderate_volatility",
                "day_2": "bullish_high_volatility",
                "day_3": "sideways_low_volatility",
                "day_4": "bearish_moderate_volatility",
                "day_5": "bullish_low_volatility"
              }},
              "strategic_adjustments": [
                {{
                  "day": 1,
                  "adjustment_type": "sector_rotation",
                  "description": "Increase technology sector allocation",
                  "rationale": "Strong earnings momentum expected"
                }}
              ],
              "contingency_plans": {{
                "high_volatility_spike": {{
                  "trigger_conditions": ["VIX > 25", "market_drop > 2%"],
                  "response_actions": ["Reduce position sizes by 30%", "Switch to defensive sectors"],
                  "time_horizon": "1-2 days"
                }},
                "earnings_surprise_negative": {{
                  "trigger_conditions": ["earnings_miss > 5%", "stock_drop > 10%"],
                  "response_actions": ["Immediate position reduction", "Stop loss activation"],
                  "time_horizon": "immediate"
                }}
              }},
              "learning_adaptations": [
                "Increase focus on volatility-based position sizing",
                "Add more defensive sector options to portfolio",
                "Implement stricter risk limits during high volatility"
              ]
            }}

            Guidelines:
            1. Risk allocations should be 0.0-1.0 (higher = more aggressive)
            2. Include realistic market condition forecasts
            3. Strategic adjustments should be actionable
            4. Contingency plans should have clear triggers and responses
            5. Learning adaptations should address recent insights
            """

            try:
                # Claude Agent SDK best practices: Use proper async context
                async with self.client:
                    await asyncio.wait_for(self.client.query(query), timeout=45.0)

                    async for message in self.client.receive_response():
                        if hasattr(message, 'content'):
                            for block in message.content:
                                if hasattr(block, 'text'):
                                    try:
                                        return json.loads(block.text)
                                    except json.JSONDecodeError:
                                        continue

                return None
            except asyncio.TimeoutError:
                logger.error("Multi-day planning query timed out")
                return None
            except Exception as e:
                logger.error(f"Claude SDK query failed: {e}")
                return None

    async def _assess_market_conditions(self) -> Dict[str, Any]:
        """Assess current market conditions for planning."""
        # This would integrate with market data services
        # For now, return mock data that should be replaced with real market data
        return {
            "volatility": "moderate",
            "trend": "bullish",
            "risk_level": "medium",
            "sector_performance": {
                "technology": "strong",
                "financials": "moderate",
                "energy": "weak"
            },
            "economic_indicators": {
                "interest_rates": "stable",
                "inflation": "moderate",
                "gdp_growth": "positive"
            }
        }

    async def _generate_market_adaptations(
        self,
        volatility: str,
        trend: str,
        risk_level: str
    ) -> MarketAdaptation:
        """Generate market condition adaptations."""
        adaptations = {
            "volatility_adaptation": {},
            "trend_adaptation": {},
            "risk_adaptation": {},
            "confidence": 0.8,
            "recommended_actions": []
        }

        # Volatility adaptations
        if volatility == "high":
            adaptations["volatility_adaptation"] = {
                "position_sizing": "reduce_by_30_percent",
                "sector_focus": "defensive_sectors",
                "stop_loss_tightening": "15_percent_tighter",
                "options_strategy": "buy_puts_for_hedging"
            }
            adaptations["recommended_actions"].extend([
                "Reduce position sizes by 30%",
                "Increase allocation to defensive sectors",
                "Tighten stop losses by 15%"
            ])
        elif volatility == "low":
            adaptations["volatility_adaptation"] = {
                "position_sizing": "increase_by_20_percent",
                "sector_focus": "cyclical_sectors",
                "leverage_usage": "moderate_increase"
            }
            adaptations["recommended_actions"].extend([
                "Increase position sizes by 20%",
                "Focus on cyclical sectors",
                "Consider moderate leverage increase"
            ])

        # Trend adaptations
        if trend == "bullish":
            adaptations["trend_adaptation"] = {
                "momentum_bias": "increase",
                "sector_rotation": "growth_sectors",
                "risk_tolerance": "moderate_increase"
            }
            adaptations["recommended_actions"].extend([
                "Increase momentum bias in strategy",
                "Rotate towards growth sectors",
                "Moderate increase in risk tolerance"
            ])
        elif trend == "bearish":
            adaptations["trend_adaptation"] = {
                "defensive_positioning": "increase",
                "cash_allocation": "increase_to_30_percent",
                "short_strategies": "consider"
            }
            adaptations["recommended_actions"].extend([
                "Increase defensive positioning",
                "Raise cash allocation to 30%",
                "Consider short strategies"
            ])

        # Risk adaptations
        if risk_level == "high":
            adaptations["risk_adaptation"] = {
                "max_position_size": "reduce_to_5_percent",
                "diversification_requirement": "increase",
                "correlation_limits": "stricter"
            }
            adaptations["recommended_actions"].extend([
                "Limit maximum position size to 5%",
                "Increase diversification requirements",
                "Implement stricter correlation limits"
            ])

        return MarketAdaptation.from_dict(adaptations)

    async def _update_planning_parameters(self, adaptations: MarketAdaptation) -> Dict[str, Any]:
        """Update planning parameters based on adaptations."""
        # Update API budget based on volatility
        volatility_adapt = adaptations.volatility_adaptation
        if "reduce_by_30_percent" in str(volatility_adapt.get("position_sizing", "")):
            self.reserve_budget = max(self.reserve_budget, 8)  # Increase reserve

        # Update planning heuristics
        updated_params = {
            "api_budget_reserve": self.reserve_budget,
            "risk_multiplier": 0.8 if adaptations.confidence < 0.7 else 1.0,
            "sector_focus_adjusted": bool(adaptations.trend_adaptation.get("sector_rotation"))
        }

        return updated_params

    async def _generate_risk_adjusted_algorithms(
        self,
        sharpe_ratio: float,
        max_drawdown: float,
        value_at_risk: float
    ) -> RiskAlgorithm:
        """Generate risk-adjusted planning algorithms."""
        algorithms = {
            "position_sizing_algorithm": {},
            "portfolio_rebalancing": {},
            "risk_limits": {},
            "overall_score": 0.5,
            "changes": []
        }

        # Position sizing based on risk metrics
        if sharpe_ratio > 2.0:
            algorithms["position_sizing_algorithm"] = {
                "method": "aggressive",
                "max_position": "8_percent",
                "scaling_factor": 1.2
            }
        elif sharpe_ratio < 1.0:
            algorithms["position_sizing_algorithm"] = {
                "method": "conservative",
                "max_position": "3_percent",
                "scaling_factor": 0.7
            }
            algorithms["changes"].append("Reduce position sizes due to low Sharpe ratio")
        else:
            algorithms["position_sizing_algorithm"] = {
                "method": "moderate",
                "max_position": "5_percent",
                "scaling_factor": 1.0
            }

        # Risk limits based on drawdown
        if max_drawdown > 0.15:
            algorithms["risk_limits"] = {
                "max_drawdown_limit": "10_percent",
                "daily_loss_limit": "2_percent",
                "portfolio_var_limit": "3_percent"
            }
            algorithms["changes"].append("Implement stricter risk limits due to high drawdown")

        # Calculate overall score
        risk_score = min(sharpe_ratio / 2.0, 1.0)  # Normalize Sharpe
        drawdown_score = max(0, 1.0 - (max_drawdown / 0.20))  # Penalize high drawdown
        algorithms["overall_score"] = (risk_score + drawdown_score) / 2.0

        return RiskAlgorithm.from_dict(algorithms)

    async def _update_planning_heuristics(self, risk_algorithms: RiskAlgorithm) -> None:
        """Update planning heuristics based on risk algorithms."""
        # Store updated heuristics for future planning
        heuristics_update = PlanningHeuristics(
            risk_algorithms=risk_algorithms.to_dict(),
            last_updated=datetime.now(timezone.utc).isoformat(),
            performance_score=risk_algorithms.overall_score
        )

        self.planning_heuristics = heuristics_update
        await self.state_manager.save_planning_heuristics(heuristics_update.to_dict())

    async def _get_historical_planning_data(self) -> List[Dict[str, Any]]:
        """Get historical planning data for learning."""
        # This would retrieve past planning decisions and outcomes
        return []

    async def _analyze_planning_outcomes(self, historical_plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze outcomes of past planning decisions."""
        return {
            "planning_accuracy": 0.75,
            "api_efficiency": 0.82,
            "outcome_quality": 0.78
        }

    async def _generate_planning_learning_insights(self, outcomes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from planning outcomes."""
        insights = {
            "improvement_potential": 0.0,
            "recommended_changes": [],
            "key_findings": []
        }

        # Analyze each outcome metric
        for metric, score in outcomes.items():
            if score < 0.7:
                insights["improvement_potential"] += (0.7 - score)
                insights["recommended_changes"].append(f"Improve {metric.replace('_', ' ')}")
            else:
                insights["key_findings"].append(f"Good performance in {metric.replace('_', ' ')}")

        insights["improvement_potential"] = min(insights["improvement_potential"], 1.0)

        return insights

    async def _update_planning_models(self, insights: Dict[str, Any]) -> None:
        """Update planning models based on learning insights."""
        # Apply recommended changes to planning algorithms
        changes = insights.get("recommended_changes", [])

        if "Improve planning accuracy" in changes:
            self.daily_api_limit = max(self.daily_api_limit - 2, 15)  # Reduce budget slightly

        if "Improve api efficiency" in changes:
            self.reserve_budget = min(self.reserve_budget + 1, 8)  # Increase reserve

        logger.info(f"Updated planning models with {len(changes)} improvements")

    async def _get_recent_learning_insights(self) -> List[Dict]:
        """Get recent learning insights."""
        try:
            insights = await self.state_manager.get_learning_insights(limit=5)
            return insights
        except Exception:
            return []

    async def _store_plan(self, plan: MultiDayPlan) -> None:
        """Store generated plan."""
        # This would store the plan in the database
        pass

    async def _load_planning_state(self) -> None:
        """Load planning state from database."""
        # This would load saved planning state
        pass

    async def _ensure_client(self) -> None:
        """Lazy initialization of Claude SDK client following best practices."""
        if self.client is None:
            # Claude Agent SDK best practices: Use proper options configuration
            options = ClaudeAgentOptions(
                allowed_tools=[],  # No tools needed for planning queries
                system_prompt=self._get_planning_prompt(),
                max_turns=15,
                # SDK handles authentication automatically via Claude CLI or API key
                # No need to manually specify model - SDK uses optimal defaults
            )
            self.client = ClaudeSDKClient(options=options)
            await self.client.__aenter__()
            logger.info("AI Planner Claude client initialized with SDK best practices")

    def _get_planning_prompt(self) -> str:
        """Get the system prompt for AI planning."""
        return """
        You are an expert quantitative trading strategist and risk manager.

        Your role is to create sophisticated, adaptive trading plans that balance:
        - Risk-adjusted returns
        - Market condition awareness
        - Learning from historical performance
        - Systematic decision making

        Focus on plans that are:
        - Quantitatively sound
        - Risk-managed
        - Adaptable to changing conditions
        - Backed by clear rationale

        Always prioritize capital preservation while maximizing risk-adjusted returns.
        """