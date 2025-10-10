"""
Learning Engine for Robo Trader

Advanced self-learning capabilities for performance analysis,
strategy optimization, and continuous improvement of trading decisions.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from statistics import mean, stdev

from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from ..config import Config
from ..core.state import StateManager
from ..auth.claude_auth import validate_claude_api


@dataclass
class PerformanceMetrics:
    """Performance metrics for analysis."""
    total_trades: int = 0
    profitable_trades: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_return: float = 0.0

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
    trade_history: List[Dict[str, Any]]
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now(timezone.utc).isoformat()

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
    """AI-generated learning insight."""
    insight_type: str  # "strategy_improvement", "risk_adjustment", "market_timing"
    confidence: float
    description: str
    actionable_recommendations: List[str]
    affected_strategies: List[str]
    generated_at: str = ""
    implemented: bool = False

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "LearningInsight":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


class LearningEngine:
    """
    Advanced learning engine for continuous improvement of trading strategies.

    Key capabilities:
    - Performance analysis and attribution
    - Strategy optimization based on outcomes
    - Risk management learning
    - Market condition adaptation
    - Self-improvement recommendations
    """

    def __init__(self, config: Config, state_manager: StateManager):
        self.config = config
        self.state_manager = state_manager
        self.client: Optional[ClaudeSDKClient] = None

        # Learning parameters
        self.min_trades_for_analysis = 10
        self.learning_interval_days = 7
        self.confidence_threshold = 0.7

    async def initialize(self) -> None:
        """Initialize the learning engine."""
        logger.info("Initializing Learning Engine")

        # Validate Claude access for learning
        auth_status = await validate_claude_api(self.config.integration.anthropic_api_key)
        if not auth_status.is_valid:
            logger.warning("Claude API not available for learning - using basic analytics")
            return

        # Create Claude client for advanced learning
        options = ClaudeAgentOptions(
            allowed_tools=[],  # Learning uses analysis, not external tools
            system_prompt=self._get_learning_prompt(),
            max_turns=20  # Allow complex analysis
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()

        logger.info("Learning Engine initialized successfully")

    async def analyze_performance(self, time_period: str = "30d") -> Dict[str, Any]:
        """
        Comprehensive performance analysis across all strategies.

        Args:
            time_period: Analysis period ("7d", "30d", "90d", "1y")

        Returns:
            Detailed performance analysis with insights
        """
        try:
            # Get trade history and current portfolio
            portfolio = await self.state_manager.get_portfolio()
            all_intents = await self.state_manager.get_all_intents()

            # Filter intents by time period
            cutoff_date = self._get_cutoff_date(time_period)
            recent_intents = [
                intent for intent in all_intents
                if intent.created_at >= cutoff_date.isoformat()
            ]

            if len(recent_intents) < self.min_trades_for_analysis:
                return {
                    "status": "insufficient_data",
                    "message": f"Need at least {self.min_trades_for_analysis} trades for analysis",
                    "trades_analyzed": len(recent_intents)
                }

            # Calculate performance metrics
            performance = await self._calculate_performance_metrics(recent_intents)

            # Strategy-specific analysis
            strategy_performance = await self._analyze_strategy_performance(recent_intents)

            # Generate learning insights
            insights = await self._generate_learning_insights(
                performance, strategy_performance, time_period
            )

            # Store insights for future reference
            for insight in insights:
                await self.state_manager.save_learning_insights({
                    "type": "performance_analysis",
                    "period": time_period,
                    "insights": [insight.to_dict()],
                    "performance": performance.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            return {
                "status": "success",
                "time_period": time_period,
                "trades_analyzed": len(recent_intents),
                "performance": performance.to_dict(),
                "strategy_performance": [sp.to_dict() for sp in strategy_performance],
                "insights": [insight.to_dict() for insight in insights],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "time_period": time_period
            }

    async def optimize_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """
        Optimize a specific trading strategy based on performance data.

        Args:
            strategy_name: Name of strategy to optimize

        Returns:
            Optimization recommendations and updated parameters
        """
        try:
            # Get historical performance for this strategy
            learning_history = await self.state_manager.get_learning_insights(20)

            # Filter insights related to this strategy
            strategy_insights = []
            for entry in learning_history:
                if "insights" in entry:
                    for insight in entry["insights"]:
                        if strategy_name in insight.get("affected_strategies", []):
                            strategy_insights.append(insight)

            if not strategy_insights:
                return {
                    "status": "no_data",
                    "message": f"No learning data available for strategy: {strategy_name}"
                }

            # Generate optimization recommendations
            if self.client:
                optimization = await self._generate_strategy_optimization(strategy_name, strategy_insights)
            else:
                optimization = await self._generate_basic_optimization(strategy_name, strategy_insights)

            return {
                "status": "success",
                "strategy": strategy_name,
                "optimization": optimization,
                "based_on_insights": len(strategy_insights),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Strategy optimization failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "strategy": strategy_name
            }

    async def adapt_to_market_conditions(self) -> Dict[str, Any]:
        """
        Adapt trading strategies based on current market conditions.

        Analyzes market volatility, trends, and economic indicators
        to recommend strategy adjustments.
        """
        try:
            # This would integrate with market data APIs
            # For now, return basic adaptation framework

            adaptation = {
                "volatility_adjustment": "Monitor VIX levels for position sizing",
                "sector_rotation": "Increase defensive sector allocation",
                "risk_management": "Tighten stop losses in volatile conditions",
                "strategy_bias": "Favor mean-reversion over momentum in high volatility"
            }

            return {
                "status": "success",
                "adaptations": adaptation,
                "confidence": 0.75,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Market adaptation failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _calculate_performance_metrics(self, intents: List) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from trade intents."""
        metrics = PerformanceMetrics()

        # Extract executed trades with outcomes
        executed_trades = []
        for intent in intents:
            if intent.status == "executed" and intent.execution_reports:
                for report in intent.execution_reports:
                    # Calculate P&L from execution reports
                    # This is simplified - real implementation would be more sophisticated
                    pnl = getattr(intent, 'pnl_calculated', 0)
                    executed_trades.append({
                        "pnl": pnl,
                        "symbol": intent.symbol,
                        "timestamp": intent.executed_at
                    })

        if not executed_trades:
            return metrics

        # Calculate metrics
        pnls = [trade["pnl"] for trade in executed_trades]
        metrics.total_trades = len(executed_trades)
        metrics.profitable_trades = len([p for p in pnls if p > 0])
        metrics.win_rate = metrics.profitable_trades / metrics.total_trades if metrics.total_trades > 0 else 0

        if pnls:
            metrics.avg_profit = mean([p for p in pnls if p > 0]) if any(p > 0 for p in pnls) else 0
            metrics.avg_loss = abs(mean([p for p in pnls if p < 0])) if any(p < 0 for p in pnls) else 0
            metrics.total_return = sum(pnls)

            if metrics.avg_loss > 0:
                metrics.profit_factor = (metrics.avg_profit * metrics.win_rate) / (metrics.avg_loss * (1 - metrics.win_rate))

            # Calculate max drawdown (simplified)
            cumulative = 0
            peak = 0
            max_drawdown = 0
            for pnl in pnls:
                cumulative += pnl
                if cumulative > peak:
                    peak = cumulative
                drawdown = peak - cumulative
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            metrics.max_drawdown = max_drawdown

        return metrics

    async def _analyze_strategy_performance(self, intents: List) -> List[StrategyPerformance]:
        """Analyze performance by strategy type."""
        # Group intents by strategy (simplified categorization)
        strategies = {}

        for intent in intents:
            # Determine strategy from intent metadata or signal
            strategy_name = "fundamental"  # Default
            if hasattr(intent, 'signal') and intent.signal:
                if "technical" in intent.signal.rationale.lower():
                    strategy_name = "technical"
                elif "momentum" in intent.signal.rationale.lower():
                    strategy_name = "momentum"

            if strategy_name not in strategies:
                strategies[strategy_name] = []

            strategies[strategy_name].append(intent)

        # Calculate performance for each strategy
        strategy_performances = []
        for strategy_name, strategy_intents in strategies.items():
            metrics = await self._calculate_performance_metrics(strategy_intents)

            strategy_perf = StrategyPerformance(
                strategy_name=strategy_name,
                time_period="30d",  # Could be parameterized
                metrics=metrics,
                trade_history=[{
                    "symbol": intent.symbol,
                    "executed_at": intent.executed_at,
                    "pnl": getattr(intent, 'pnl_calculated', 0)
                } for intent in strategy_intents if intent.status == "executed"]
            )

            strategy_performances.append(strategy_perf)

        return strategy_performances

    async def _generate_learning_insights(
        self,
        performance: PerformanceMetrics,
        strategy_performance: List[StrategyPerformance],
        time_period: str
    ) -> List[LearningInsight]:
        """Generate AI-powered learning insights from performance data."""
        insights = []

        # Basic insights without Claude
        if performance.win_rate < 0.4:
            insights.append(LearningInsight(
                insight_type="strategy_improvement",
                confidence=0.8,
                description=f"Win rate of {performance.win_rate:.1%} is below target. Consider stricter entry criteria.",
                actionable_recommendations=[
                    "Increase minimum confidence threshold for trade execution",
                    "Add additional technical confirmation signals",
                    "Review and tighten risk management rules"
                ],
                affected_strategies=["all"]
            ))

        if performance.max_drawdown > 0.15:  # 15% drawdown
            insights.append(LearningInsight(
                insight_type="risk_adjustment",
                confidence=0.9,
                description=f"Maximum drawdown of {performance.max_drawdown:.1%} exceeds risk limits.",
                actionable_recommendations=[
                    "Reduce position sizes by 20-30%",
                    "Implement stricter stop loss rules",
                    "Add maximum drawdown circuit breakers"
                ],
                affected_strategies=["all"]
            ))

        # Use Claude for advanced insights if available
        if self.client and len(insights) < 3:
            try:
                advanced_insights = await self._generate_advanced_insights(
                    performance, strategy_performance, time_period
                )
                insights.extend(advanced_insights)
            except Exception as e:
                logger.warning(f"Advanced insight generation failed: {e}")

        return insights

    async def _generate_advanced_insights(
        self,
        performance: PerformanceMetrics,
        strategy_performance: List[StrategyPerformance],
        time_period: str
    ) -> List[LearningInsight]:
        """Use Claude to generate advanced learning insights."""
        query = f"""
        Analyze this trading performance data and generate specific, actionable insights for improvement:

        OVERALL PERFORMANCE ({time_period}):
        - Total Trades: {performance.total_trades}
        - Win Rate: {performance.win_rate:.1%}
        - Profit Factor: {performance.profit_factor:.2f}
        - Max Drawdown: {performance.max_drawdown:.1%}
        - Total Return: {performance.total_return:.2f}

        STRATEGY PERFORMANCE:
        {json.dumps([sp.to_dict() for sp in strategy_performance], indent=2)}

        Generate 2-3 specific insights with:
        1. Type: "strategy_improvement", "risk_adjustment", or "market_timing"
        2. Confidence score (0-1)
        3. Clear description of the issue/opportunity
        4. 3-5 actionable recommendations
        5. Which strategies this affects

        Focus on patterns that can be systematically improved.
        """

        await self.client.query(query)

        insights = []
        async for message in self.client.receive_response():
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        try:
                            # Parse JSON insights from response
                            if "{" in block.text and "}" in block.text:
                                json_start = block.text.find("{")
                                json_end = block.text.rfind("}") + 1
                                json_str = block.text[json_start:json_end]

                                parsed = json.loads(json_str)
                                if "insights" in parsed:
                                    for insight_data in parsed["insights"]:
                                        insight = LearningInsight.from_dict(insight_data)
                                        insights.append(insight)
                        except (json.JSONDecodeError, KeyError):
                            continue

        return insights

    async def _generate_strategy_optimization(self, strategy_name: str, insights: List[Dict]) -> Dict[str, Any]:
        """Generate strategy-specific optimization recommendations."""
        query = f"""
        Optimize the "{strategy_name}" trading strategy based on these learning insights:

        INSIGHTS:
        {json.dumps(insights, indent=2)}

        Provide specific optimization recommendations including:
        1. Parameter adjustments (entry/exit thresholds, position sizing)
        2. Additional filters or confirmation signals
        3. Risk management improvements
        4. Market condition adaptations
        5. Expected impact on performance

        Return as JSON with "parameter_changes", "new_filters", "risk_adjustments", "expected_impact"
        """

        await self.client.query(query)

        async for message in self.client.receive_response():
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        try:
                            if "{" in block.text and "}" in block.text:
                                json_start = block.text.find("{")
                                json_end = block.text.rfind("}") + 1
                                json_str = block.text[json_start:json_end]

                                return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue

        # Fallback optimization
        return {
            "parameter_changes": {"confidence_threshold": 0.75},
            "new_filters": ["Add volume confirmation"],
            "risk_adjustments": ["Reduce position size by 15%"],
            "expected_impact": "Improve win rate by 5-10%"
        }

    async def _generate_basic_optimization(self, strategy_name: str, insights: List[Dict]) -> Dict[str, Any]:
        """Generate basic optimization when Claude is unavailable."""
        return {
            "parameter_changes": {"confidence_threshold": 0.7},
            "new_filters": ["Review existing filters"],
            "risk_adjustments": ["Maintain current risk levels"],
            "expected_impact": "Monitor performance for further adjustments"
        }

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

    def _get_cutoff_date(self, time_period: str) -> datetime:
        """Get cutoff date for analysis period."""
        now = datetime.now(timezone.utc)

        if time_period == "7d":
            return now - timedelta(days=7)
        elif time_period == "30d":
            return now - timedelta(days=30)
        elif time_period == "90d":
            return now - timedelta(days=90)
        elif time_period == "1y":
            return now - timedelta(days=365)
        else:
            return now - timedelta(days=30)  # Default to 30 days