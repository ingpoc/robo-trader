"""
Daily Strategy Evaluator Service

Evaluates and refines trading strategies daily, providing complete transparency
into Claude's learning process, strategy improvements, and performance analysis.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from ...stores.claude_strategy_store import ClaudeStrategyStore
from ...services.paper_trading.performance_calculator import PerformanceCalculator

logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformanceMetrics:
    """Performance metrics for a trading strategy."""

    strategy_name: str
    evaluation_date: str
    period_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_return: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    volatility: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyRefinement:
    """A strategy refinement recommendation."""

    refinement_id: str
    strategy_name: str
    refinement_type: str  # 'parameter_adjustment', 'rule_change', 'new_condition', 'risk_adjustment'
    description: str
    current_value: Any
    proposed_value: Any
    expected_impact: str
    confidence_score: float
    implementation_priority: str = "medium"  # 'low', 'medium', 'high'
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyStrategyReport:
    """Daily strategy evaluation and refinement report."""

    report_id: str
    evaluation_date: str
    account_type: str
    strategies_evaluated: List[str]
    performance_summary: Dict[str, Any]
    refinements_recommended: List[StrategyRefinement]
    market_conditions: Dict[str, Any]
    key_insights: List[str]
    next_evaluation_date: str
    confidence_score: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['refinements_recommended'] = [r.to_dict() for r in self.refinements_recommended]
        return data


class DailyStrategyEvaluator:
    """
    Evaluates and refines trading strategies daily.

    Provides complete transparency into:
    - Daily strategy performance analysis
    - Automated refinement recommendations
    - Learning progress tracking
    - Strategy evolution insights
    """

    def __init__(self, strategy_store: ClaudeStrategyStore, performance_calculator: PerformanceCalculator):
        self.strategy_store = strategy_store
        self.performance_calculator = performance_calculator
        self.active_strategies = {}  # Cache of strategy configurations

    async def evaluate_daily_strategies(
        self,
        account_type: str,
        evaluation_date: Optional[str] = None
    ) -> DailyStrategyReport:
        """Perform daily evaluation of all strategies for an account type."""

        if not evaluation_date:
            evaluation_date = datetime.now(timezone.utc).date().isoformat()

        logger.info(f"Starting daily strategy evaluation for {account_type} on {evaluation_date}")

        # Get strategies for this account type
        strategies = await self._get_account_strategies(account_type)

        # Evaluate each strategy
        performance_summaries = {}
        all_refinements = []

        for strategy_name in strategies:
            try:
                # Evaluate performance
                performance = await self._evaluate_strategy_performance(strategy_name, account_type, evaluation_date)
                performance_summaries[strategy_name] = performance.to_dict()

                # Generate refinements
                refinements = await self._generate_strategy_refinements(strategy_name, performance)
                all_refinements.extend(refinements)

            except Exception as e:
                logger.error(f"Failed to evaluate strategy {strategy_name}: {e}")
                continue

        # Analyze market conditions
        market_conditions = await self._analyze_market_conditions()

        # Generate key insights
        key_insights = await self._generate_key_insights(performance_summaries, all_refinements)

        # Calculate overall confidence
        confidence_score = self._calculate_overall_confidence(performance_summaries)

        # Create daily report
        report = DailyStrategyReport(
            report_id=f"daily_eval_{int(datetime.now(timezone.utc).timestamp())}_{account_type}",
            evaluation_date=evaluation_date,
            account_type=account_type,
            strategies_evaluated=list(strategies),
            performance_summary=performance_summaries,
            refinements_recommended=all_refinements,
            market_conditions=market_conditions,
            key_insights=key_insights,
            next_evaluation_date=(datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
            confidence_score=confidence_score
        )

        # Save report
        await self._save_daily_report(report)

        logger.info(f"Completed daily strategy evaluation for {account_type}: {len(all_refinements)} refinements recommended")

        return report

    async def _evaluate_strategy_performance(
        self,
        strategy_name: str,
        account_type: str,
        evaluation_date: str
    ) -> StrategyPerformanceMetrics:
        """Evaluate performance of a specific strategy."""

        # Get trades for this strategy over the last 30 days
        end_date = datetime.fromisoformat(evaluation_date)
        start_date = end_date - timedelta(days=30)

        # This would query the database for trades tagged with this strategy
        # For now, simulate performance data
        trades = await self._get_strategy_trades(strategy_name, account_type, start_date, end_date)

        if not trades:
            return StrategyPerformanceMetrics(
                strategy_name=strategy_name,
                evaluation_date=evaluation_date,
                period_days=30,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                total_return=0.0
            )

        # Calculate performance metrics using PerformanceCalculator
        performance_data = self.performance_calculator.calculate_account_performance(
            initial_balance=100000,  # Would get from account
            current_balance=100000,  # Would calculate
            closed_trades=trades,
            open_trades=[],
            current_prices={}
        )

        return StrategyPerformanceMetrics(
            strategy_name=strategy_name,
            evaluation_date=evaluation_date,
            period_days=30,
            total_trades=performance_data["total_trades"],
            winning_trades=performance_data["winning_trades"],
            losing_trades=performance_data["losing_trades"],
            win_rate=performance_data["win_rate"],
            avg_win=performance_data["avg_win"],
            avg_loss=performance_data["avg_loss"],
            profit_factor=performance_data["profit_factor"],
            total_return=performance_data["total_pnl_percentage"],
            sharpe_ratio=performance_data.get("sharpe_ratio"),
            max_drawdown=performance_data.get("max_drawdown_percentage", 0.0),
            volatility=0.0  # Would calculate
        )

    async def _generate_strategy_refinements(
        self,
        strategy_name: str,
        performance: StrategyPerformanceMetrics
    ) -> List[StrategyRefinement]:
        """Generate refinement recommendations based on performance."""

        refinements = []

        # Analyze win rate
        if performance.win_rate < 0.4:
            refinements.append(StrategyRefinement(
                refinement_id=f"ref_{strategy_name}_{int(datetime.now(timezone.utc).timestamp())}_win_rate",
                strategy_name=strategy_name,
                refinement_type="parameter_adjustment",
                description="Win rate below 40% - consider tightening entry conditions",
                current_value=f"{performance.win_rate:.1%}",
                proposed_value="Improve entry filters",
                expected_impact="Higher quality trades with better win rate",
                confidence_score=0.7,
                implementation_priority="high"
            ))

        # Analyze profit factor
        if performance.profit_factor < 1.2:
            refinements.append(StrategyRefinement(
                refinement_id=f"ref_{strategy_name}_{int(datetime.now(timezone.utc).timestamp())}_profit_factor",
                strategy_name=strategy_name,
                refinement_type="risk_adjustment",
                description="Profit factor below 1.2 - consider adjusting risk management",
                current_value=f"{performance.profit_factor:.2f}",
                proposed_value="Implement stricter stop losses",
                expected_impact="Better risk-reward ratio",
                confidence_score=0.8,
                implementation_priority="high"
            ))

        # Analyze drawdown
        if performance.max_drawdown > 15.0:
            refinements.append(StrategyRefinement(
                refinement_id=f"ref_{strategy_name}_{int(datetime.now(timezone.utc).timestamp())}_drawdown",
                strategy_name=strategy_name,
                refinement_type="rule_change",
                description="Maximum drawdown exceeds 15% - implement position size limits",
                current_value=f"{performance.max_drawdown:.1f}%",
                proposed_value="Reduce max position size to 3%",
                expected_impact="Lower portfolio volatility",
                confidence_score=0.9,
                implementation_priority="high"
            ))

        # Positive performance refinements
        if performance.win_rate > 0.6 and performance.profit_factor > 1.5:
            refinements.append(StrategyRefinement(
                refinement_id=f"ref_{strategy_name}_{int(datetime.now(timezone.utc).timestamp())}_scale_up",
                strategy_name=strategy_name,
                refinement_type="parameter_adjustment",
                description="Strong performance - consider scaling up position sizes",
                current_value="Current sizing",
                proposed_value="Increase position size by 25%",
                expected_impact="Higher returns while maintaining risk profile",
                confidence_score=0.6,
                implementation_priority="medium"
            ))

        return refinements

    async def _analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions for strategy evaluation."""

        # This would analyze current market data
        # For now, return simulated market conditions
        return {
            "volatility": "moderate",
            "trend": "sideways",
            "sector_performance": {
                "technology": 2.1,
                "finance": -0.5,
                "healthcare": 1.8
            },
            "key_levels": {
                "nifty_support": 19500,
                "nifty_resistance": 20500
            },
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _generate_key_insights(
        self,
        performance_summaries: Dict[str, Any],
        refinements: List[StrategyRefinement]
    ) -> List[str]:
        """Generate key insights from the evaluation."""

        insights = []

        # Analyze overall performance
        total_strategies = len(performance_summaries)
        profitable_strategies = sum(1 for p in performance_summaries.values() if p["total_return"] > 0)

        if profitable_strategies > total_strategies * 0.6:
            insights.append(f"{profitable_strategies}/{total_strategies} strategies are profitable - portfolio performing well")
        elif profitable_strategies < total_strategies * 0.3:
            insights.append(f"Only {profitable_strategies}/{total_strategies} strategies profitable - review strategy selection")

        # Analyze refinements needed
        high_priority_refinements = [r for r in refinements if r.implementation_priority == "high"]
        if high_priority_refinements:
            insights.append(f"{len(high_priority_refinements)} high-priority refinements recommended")

        # Market condition insights
        insights.append("Market conditions suggest cautious approach with focus on risk management")

        return insights

    def _calculate_overall_confidence(self, performance_summaries: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the evaluation."""

        if not performance_summaries:
            return 0.0

        # Average win rate across strategies
        avg_win_rate = sum(p["win_rate"] for p in performance_summaries.values()) / len(performance_summaries)

        # Average profit factor
        avg_profit_factor = sum(p["profit_factor"] for p in performance_summaries.values()) / len(performance_summaries)

        # Calculate confidence based on performance
        confidence = (avg_win_rate * 0.4) + (min(avg_profit_factor / 2, 1.0) * 0.6)

        return min(confidence, 1.0)

    async def get_daily_reports(
        self,
        account_type: Optional[str] = None,
        limit: int = 30
    ) -> List[DailyStrategyReport]:
        """Get historical daily strategy reports."""

        # This would query the database for stored daily reports
        # For now, return empty list
        return []

    async def get_strategy_evolution_timeline(
        self,
        strategy_name: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """Get evolution timeline for a strategy."""

        # Get historical performance data
        reports = await self.get_daily_reports()

        # Filter for strategy
        strategy_reports = [r for r in reports if strategy_name in r.strategies_evaluated]

        # Build evolution timeline
        timeline = []
        for report in strategy_reports[-days:]:
            if strategy_name in report.performance_summary:
                perf = report.performance_summary[strategy_name]
                timeline.append({
                    "date": report.evaluation_date,
                    "win_rate": perf["win_rate"],
                    "profit_factor": perf["profit_factor"],
                    "total_return": perf["total_return"],
                    "refinements": len([r for r in report.refinements_recommended if r.strategy_name == strategy_name])
                })

        return {
            "strategy_name": strategy_name,
            "timeline": timeline,
            "total_evaluations": len(timeline),
            "avg_win_rate": sum(t["win_rate"] for t in timeline) / len(timeline) if timeline else 0,
            "avg_profit_factor": sum(t["profit_factor"] for t in timeline) / len(timeline) if timeline else 0,
            "total_refinements": sum(t["refinements"] for t in timeline)
        }

    async def _get_account_strategies(self, account_type: str) -> List[str]:
        """Get list of strategies for an account type."""

        # This would query the database for active strategies
        # For now, return default strategies
        return [
            "rsi_momentum",
            "macd_divergence",
            "bollinger_mean_reversion",
            "breakout_momentum"
        ]

    async def _get_strategy_trades(self, strategy_name: str, account_type: str, start_date: datetime, end_date: datetime) -> List:
        """Get trades for a specific strategy."""

        # This would query the database for trades tagged with this strategy
        # For now, return empty list (would be populated with actual trade data)
        return []

    async def _save_daily_report(self, report: DailyStrategyReport) -> None:
        """Save daily strategy report to database."""

        # This would save to a dedicated daily_reports table
        # For now, we'll log the report data
        report_data = report.to_dict()

        logger.info(f"Daily strategy report saved: {report.report_id}")
        logger.debug(f"Report data: {json.dumps(report_data, indent=2)}")

    async def cleanup_old_reports(self, days_to_keep: int = 90) -> int:
        """Clean up old daily reports."""

        # This would delete old reports from database
        # For now, just log
        logger.info(f"Would clean up daily reports older than {days_to_keep} days")

        return 0