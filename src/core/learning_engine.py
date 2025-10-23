"""
Learning Engine for Robo Trader

Implements continuous learning and adaptation capabilities for trading strategies.
Uses Claude SDK for intelligent analysis and insight generation.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from statistics import mean, stdev

from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from src.config import Config
from ..core.database_state import DatabaseStateManager


@dataclass
class PerformanceMetrics:
    """Performance metrics for trading analysis."""
    total_trades: int = 0
    profitable_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    volatility: float = 0.0
    avg_trade_duration: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict) -> "PerformanceMetrics":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StrategyPerformance:
    """Performance data for a specific strategy."""
    strategy_name: str
    time_period: str
    metrics: PerformanceMetrics
    trade_history: List[Dict[str, Any]] = field(default_factory=list)
    market_conditions: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> "StrategyPerformance":
        if 'metrics' in data:
            data['metrics'] = PerformanceMetrics.from_dict(data['metrics'])
        return cls(**data)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['metrics'] = self.metrics.to_dict()
        return data


@dataclass
class LearningInsight:
    """An actionable insight generated through learning."""
    insight_type: str
    confidence: float
    description: str
    actionable_recommendations: List[str] = field(default_factory=list)
    affected_strategies: List[str] = field(default_factory=list)
    expected_impact: str = ""
    implemented: bool = False
    implementation_date: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "LearningInsight":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DailyReflection:
    """Daily reflection on trading performance and lessons learned."""
    date: str
    strategy_type: str
    what_worked_well: List[str] = field(default_factory=list)
    what_did_not_work: List[str] = field(default_factory=list)
    market_observations: List[str] = field(default_factory=list)
    tomorrow_focus: List[str] = field(default_factory=list)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    learning_insights: List[str] = field(default_factory=list)
    confidence_level: float = 0.5

    @classmethod
    def from_dict(cls, data: Dict) -> "DailyReflection":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PatternRecognition:
    """Recognized trading pattern with success metrics."""
    pattern_type: str
    pattern_name: str
    description: str
    confidence: float
    frequency: int
    success_rate: float
    avg_return: float
    last_observed: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "PatternRecognition":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


class LearningEngine:
    """
    Advanced learning engine for continuous trading strategy improvement.

    Key capabilities:
    - Performance analysis and metrics calculation
    - Pattern recognition in trading data
    - Strategy optimization recommendations
    - Market condition adaptation
    - Learning insight generation using Claude SDK
    """

    def __init__(self, config: Config, state_manager: DatabaseStateManager):
        self.config = config
        self.state_manager = state_manager
        self.client: Optional[ClaudeSDKClient] = None

        # Learning parameters
        self.min_trades_for_analysis = 10
        self.learning_interval_days = 7
        self.confidence_threshold = 0.7
        self.max_concurrent_requests = 3
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    async def initialize(self) -> None:
        """Initialize the learning engine."""
        logger.info("Initializing Learning Engine")
        await self._ensure_client()
        logger.info("Learning Engine initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup learning engine resources."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up learning client: {e}")

    async def analyze_performance(self, time_period: str = "30d") -> Dict[str, Any]:
        """
        Analyze trading performance over a time period.

        Args:
            time_period: Time period for analysis (e.g., "7d", "30d", "90d")

        Returns:
            Analysis results with insights and recommendations
        """
        try:
            # Get trading data
            portfolio = await self.state_manager.get_portfolio()
            intents = await self.state_manager.get_all_intents()

            if not intents or len(intents) < self.min_trades_for_analysis:
                return {
                    "status": "insufficient_data",
                    "trades_analyzed": len(intents) if intents else 0,
                    "message": f"Need at least {self.min_trades_for_analysis} trades for analysis"
                }

            # Calculate performance metrics
            metrics = await self._calculate_performance_metrics(intents)

            # Generate insights using Claude
            insights = await self._generate_performance_insights(metrics, time_period)

            # Store learning insights
            await self._store_learning_insights(insights)

            return {
                "status": "success",
                "trades_analyzed": len(intents),
                "metrics": metrics.to_dict(),
                "insights": [insight.to_dict() for insight in insights],
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {"status": "error", "message": str(e)}

    async def create_daily_reflection(
        self,
        strategy_type: str,
        performance_data: Dict[str, Any],
        market_conditions: Dict[str, Any]
    ) -> Optional[DailyReflection]:
        """
        Create a daily reflection on trading performance.

        Args:
            strategy_type: Type of strategy used
            performance_data: Performance metrics for the day
            market_conditions: Market conditions during trading

        Returns:
            Daily reflection object
        """
        try:
            if not self.client:
                await self._ensure_client()

            # Analyze what worked and what didn't
            analysis = await self._analyze_daily_performance(performance_data, market_conditions)

            reflection = DailyReflection(
                date=datetime.now(timezone.utc).date().isoformat(),
                strategy_type=strategy_type,
                what_worked_well=analysis.get("worked_well", []),
                what_did_not_work=analysis.get("did_not_work", []),
                market_observations=analysis.get("market_observations", []),
                tomorrow_focus=analysis.get("tomorrow_focus", []),
                performance_summary=performance_data,
                learning_insights=analysis.get("learning_insights", []),
                confidence_level=analysis.get("confidence_level", 0.5)
            )

            # Store reflection
            await self.state_manager.save_daily_reflection(reflection.to_dict())

            return reflection

        except Exception as e:
            logger.error(f"Daily reflection creation failed: {e}")
            return None

    async def analyze_strategy_effectiveness(self, strategy_name: str) -> Dict[str, Any]:
        """
        Analyze the effectiveness of a specific strategy.

        Args:
            strategy_name: Name of the strategy to analyze

        Returns:
            Effectiveness analysis
        """
        try:
            # Get strategy-specific data
            strategy_data = await self.state_manager.get_strategy_performance(strategy_name)

            if not strategy_data:
                return {
                    "status": "no_data",
                    "message": f"No performance data available for strategy: {strategy_name}"
                }

            # Analyze effectiveness
            effectiveness = await self._analyze_strategy_effectiveness(strategy_data)

            return {
                "status": "success",
                "strategy": strategy_name,
                "effectiveness_score": effectiveness.get("score", 0.0),
                "recommendations": effectiveness.get("recommendations", []),
                "risk_adjusted_return": effectiveness.get("risk_adjusted_return", 0.0)
            }

        except Exception as e:
            logger.error(f"Strategy effectiveness analysis failed: {e}")
            return {"status": "error", "message": str(e)}

    async def adapt_to_market_conditions(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt trading parameters based on current market conditions.

        Args:
            conditions: Current market conditions

        Returns:
            Adaptation recommendations
        """
        try:
            if not self.client:
                await self._ensure_client()

            # Generate adaptations using Claude
            adaptations = await self._generate_market_adaptations(conditions)

            return {
                "status": "success",
                "adaptations": adaptations,
                "confidence": adaptations.get("confidence", 0.5),
                "recommended_actions": adaptations.get("actions", [])
            }

        except Exception as e:
            logger.error(f"Market condition adaptation failed: {e}")
            return {"status": "error", "message": str(e)}

    async def recognize_patterns(self, historical_data: List[Dict[str, Any]]) -> List[PatternRecognition]:
        """
        Recognize patterns in historical trading data.

        Args:
            historical_data: Historical trading data

        Returns:
            List of recognized patterns
        """
        try:
            if not self.client:
                await self._ensure_client()

            patterns = await self._analyze_trading_patterns(historical_data)

            # Store patterns
            for pattern in patterns:
                await self.state_manager.save_pattern_recognition(pattern.to_dict())

            return patterns

        except Exception as e:
            logger.error(f"Pattern recognition failed: {e}")
            return []

    async def get_learning_history(self) -> Dict[str, Any]:
        """
        Retrieve learning history and insights.

        Returns:
            Learning history data
        """
        try:
            reflections = await self.state_manager.get_daily_reflections()
            insights = await self.state_manager.get_learning_insights()
            patterns = await self.state_manager.get_pattern_recognitions()

            return {
                "status": "success",
                "reflections": reflections or [],
                "insights": insights or [],
                "patterns": patterns or [],
                "total_insights": len(insights) if insights else 0,
                "total_patterns": len(patterns) if patterns else 0
            }

        except Exception as e:
            logger.error(f"Learning history retrieval failed: {e}")
            return {"status": "error", "message": str(e)}

    async def optimize_risk_adjusted_planning(
        self,
        risk_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Optimize planning parameters based on risk metrics.

        Args:
            risk_metrics: Current risk metrics (sharpe_ratio, max_drawdown, etc.)

        Returns:
            Optimized planning parameters
        """
        try:
            if not self.client:
                await self._ensure_client()

            # Generate risk-adjusted algorithms
            algorithms = await self._generate_risk_adjusted_algorithms(
                risk_metrics.get("sharpe_ratio", 1.0),
                risk_metrics.get("max_drawdown", 0.1),
                risk_metrics.get("value_at_risk", 0.05)
            )

            return {
                "status": "success",
                "algorithms": algorithms,
                "overall_score": algorithms.get("overall_score", 0.5),
                "recommended_changes": algorithms.get("changes", [])
            }

        except Exception as e:
            logger.error(f"Risk-adjusted planning optimization failed: {e}")
            return {"status": "error", "message": str(e)}

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

    async def _calculate_performance_metrics(self, intents: List[Any]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from trading intents."""
        total_trades = len(intents)
        profitable_trades = 0
        total_return = 0.0
        returns = []

        for intent in intents:
            if hasattr(intent, 'pnl_calculated') and intent.pnl_calculated:
                pnl = intent.pnl_calculated
                total_return += pnl
                returns.append(pnl)
                if pnl > 0:
                    profitable_trades += 1

        win_rate = profitable_trades / total_trades if total_trades > 0 else 0.0

        # Calculate additional metrics
        volatility = stdev(returns) if len(returns) > 1 else 0.0
        sharpe_ratio = (mean(returns) / volatility) if volatility > 0 else 0.0
        max_drawdown = min(returns) if returns else 0.0  # Simplified

        return PerformanceMetrics(
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            win_rate=win_rate,
            total_return=total_return,
            max_drawdown=abs(max_drawdown),
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            avg_trade_duration=0.0  # Would need actual duration data
        )

    async def _generate_performance_insights(
        self,
        metrics: PerformanceMetrics,
        time_period: str
    ) -> List[LearningInsight]:
        """Generate actionable insights from performance metrics."""
        async with self.request_semaphore:
            if not self.client:
                await self._ensure_client()

            query = f"""
            Analyze these trading performance metrics and generate actionable insights:

            TIME PERIOD: {time_period}
            PERFORMANCE METRICS:
            {json.dumps(metrics.to_dict(), indent=2)}

            Generate 3-5 specific, actionable insights for improving trading performance.
            Each insight should include:
            1. Type of insight (strategy_improvement, risk_management, market_timing, etc.)
            2. Confidence level (0.0-1.0)
            3. Clear description of the finding
            4. Specific actionable recommendations
            5. Expected impact on performance

            Return as JSON array of insight objects.
            """

            try:
                await asyncio.wait_for(self.client.query(query), timeout=30.0)
            except asyncio.TimeoutError:
                logger.error("Performance insights generation timed out")
                return []

            insights = []
            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            try:
                                insights_data = json.loads(block.text)
                                for insight_data in insights_data:
                                    insight = LearningInsight(
                                        insight_type=insight_data.get("type", "general"),
                                        confidence=insight_data.get("confidence", 0.5),
                                        description=insight_data.get("description", ""),
                                        actionable_recommendations=insight_data.get("recommendations", []),
                                        expected_impact=insight_data.get("impact", "")
                                    )
                                    insights.append(insight)
                            except json.JSONDecodeError:
                                continue

            return insights

    async def _analyze_daily_performance(
        self,
        performance_data: Dict[str, Any],
        market_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze daily performance to identify what worked and what didn't."""
        async with self.request_semaphore:
            if not self.client:
                await self._ensure_client()

            query = f"""
            Analyze this daily trading performance and market conditions:

            PERFORMANCE DATA:
            {json.dumps(performance_data, indent=2)}

            MARKET CONDITIONS:
            {json.dumps(market_conditions, indent=2)}

            Provide analysis in this JSON structure:
            {{
              "worked_well": ["list of things that worked well"],
              "did_not_work": ["list of things that didn't work"],
              "market_observations": ["key market observations"],
              "tomorrow_focus": ["focus areas for tomorrow"],
              "learning_insights": ["key lessons learned"],
              "confidence_level": 0.0-1.0
            }}
            """

            try:
                await asyncio.wait_for(self.client.query(query), timeout=25.0)
            except asyncio.TimeoutError:
                logger.error("Daily performance analysis timed out")
                return {
                    "worked_well": [],
                    "did_not_work": [],
                    "market_observations": [],
                    "tomorrow_focus": [],
                    "learning_insights": [],
                    "confidence_level": 0.5
                }

            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            try:
                                return json.loads(block.text)
                            except json.JSONDecodeError:
                                continue

            return {
                "worked_well": [],
                "did_not_work": [],
                "market_observations": [],
                "tomorrow_focus": [],
                "learning_insights": [],
                "confidence_level": 0.5
            }

    async def _analyze_strategy_effectiveness(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the effectiveness of a specific strategy."""
        # Simplified analysis - would use Claude for more sophisticated analysis
        metrics = strategy_data.get("metrics", {})
        win_rate = metrics.get("win_rate", 0.0)
        total_return = metrics.get("total_return", 0.0)

        score = (win_rate * 0.6) + (min(total_return / 1000, 1.0) * 0.4)  # Simplified scoring

        recommendations = []
        if win_rate < 0.5:
            recommendations.append("Improve entry timing and signal quality")
        if total_return < 0:
            recommendations.append("Review risk management and position sizing")

        return {
            "score": score,
            "recommendations": recommendations,
            "risk_adjusted_return": total_return / (abs(total_return) + 1) if total_return != 0 else 0.0
        }

    async def _generate_market_adaptations(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate market condition adaptations."""
        async with self.request_semaphore:
            if not self.client:
                await self._ensure_client()

            query = f"""
            Generate trading adaptations for these market conditions:

            MARKET CONDITIONS:
            {json.dumps(conditions, indent=2)}

            Provide adaptations in this JSON structure:
            {{
              "volatility_adaptation": {{
                "position_sizing": "strategy",
                "stop_loss_tightening": "amount",
                "options_strategy": "approach"
              }},
              "trend_adaptation": {{
                "momentum_bias": "direction",
                "sector_rotation": "approach"
              }},
              "risk_adaptation": {{
                "max_position_size": "limit",
                "diversification": "approach"
              }},
              "actions": ["list of specific actions to take"],
              "confidence": 0.0-1.0
            }}
            """

            try:
                await asyncio.wait_for(self.client.query(query), timeout=25.0)
            except asyncio.TimeoutError:
                logger.error("Market adaptation generation timed out")
                return {"actions": [], "confidence": 0.5}

            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            try:
                                return json.loads(block.text)
                            except json.JSONDecodeError:
                                continue

            return {"actions": [], "confidence": 0.5}

    async def _analyze_trading_patterns(self, historical_data: List[Dict[str, Any]]) -> List[PatternRecognition]:
        """Analyze historical data for trading patterns."""
        async with self.request_semaphore:
            if not self.client:
                await self._ensure_client()

            query = f"""
            Analyze this historical trading data for patterns:

            DATA SAMPLE (first 10 entries):
            {json.dumps(historical_data[:10], indent=2)}

            TOTAL ENTRIES: {len(historical_data)}

            Identify successful trading patterns and return as JSON array with:
            - pattern_type: "entry_signal", "exit_signal", "risk_management"
            - pattern_name: descriptive name
            - description: what the pattern represents
            - confidence: 0.0-1.0
            - frequency: how often observed
            - success_rate: win rate for this pattern
            - avg_return: average return
            - conditions: pattern conditions
            - recommendations: how to use this pattern
            """

            try:
                await asyncio.wait_for(self.client.query(query), timeout=35.0)
            except asyncio.TimeoutError:
                logger.error("Pattern analysis timed out")
                return []

            patterns = []
            async for message in self.client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            try:
                                patterns_data = json.loads(block.text)
                                for pattern_data in patterns_data:
                                    pattern = PatternRecognition(
                                        pattern_type=pattern_data.get("pattern_type", "unknown"),
                                        pattern_name=pattern_data.get("pattern_name", "Unknown Pattern"),
                                        description=pattern_data.get("description", ""),
                                        confidence=pattern_data.get("confidence", 0.5),
                                        frequency=pattern_data.get("frequency", 0),
                                        success_rate=pattern_data.get("success_rate", 0.0),
                                        avg_return=pattern_data.get("avg_return", 0.0),
                                        last_observed=datetime.now(timezone.utc).isoformat(),
                                        conditions=pattern_data.get("conditions", {}),
                                        recommendations=pattern_data.get("recommendations", [])
                                    )
                                    patterns.append(pattern)
                            except json.JSONDecodeError:
                                continue

            return patterns

    async def _store_learning_insights(self, insights: List[LearningInsight]) -> None:
        """Store learning insights in the database."""
        for insight in insights:
            await self.state_manager.save_learning_insight(insight.to_dict())

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

        logger.info(f"Updated planning models with {len(changes)} improvements")

    async def _generate_risk_adjusted_algorithms(
        self,
        sharpe_ratio: float,
        max_drawdown: float,
        value_at_risk: float
    ) -> Dict[str, Any]:
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

        return algorithms

    async def _ensure_client(self) -> None:
        """Lazy initialization of Claude SDK client."""
        if self.client is None:
            options = ClaudeAgentOptions(
                allowed_tools=[],
                system_prompt=self._get_learning_prompt(),
                max_turns=15
            )
            self.client = ClaudeSDKClient(options=options)
            await self.client.__aenter__()
            logger.info("Learning Engine Claude client initialized")

    def _get_learning_prompt(self) -> str:
        """Get the system prompt for learning analysis."""
        return """
        You are an expert trading strategy analyst and machine learning system for continuous improvement.

        Your role is to analyze trading performance data and generate actionable insights for:
        - Strategy optimization
        - Risk management improvement
        - Market condition adaptation
        - Performance enhancement

        Focus on systematic, measurable improvements that can be implemented and tested.
        Always provide specific, actionable recommendations with expected impact.
        """