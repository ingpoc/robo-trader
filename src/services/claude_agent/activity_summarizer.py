"""
Activity Summarizer Service

Creates comprehensive daily summaries of AI trading activities, providing
clients with clear insights into what Claude accomplished, learned, and
plans for the next trading day.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from ...stores.claude_strategy_store import ClaudeStrategyStore

logger = logging.getLogger(__name__)


@dataclass
class DailyActivitySummary:
    """Comprehensive summary of daily AI trading activities."""

    summary_id: str
    date: str
    account_type: str

    # Session activities
    sessions_completed: int
    total_token_usage: int
    total_cost_usd: float

    # Trading activities
    trades_executed: int
    trades_successful: int
    total_pnl: float
    best_performing_strategy: str
    worst_performing_strategy: str

    # Research activities
    research_sessions: int
    symbols_analyzed: int
    key_findings: List[str]

    # Learning activities
    strategies_evaluated: int
    refinements_recommended: int
    confidence_score: float

    # Market insights
    market_conditions: Dict[str, Any]
    sector_performance: Dict[str, float]

    # Tomorrow's plan
    planned_activities: List[str]
    risk_adjustments: List[str]

    # Overall assessment
    day_rating: str  # 'excellent', 'good', 'neutral', 'challenging'
    key_achievements: List[str]
    areas_for_improvement: List[str]

    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WeeklyActivitySummary:
    """Weekly summary of AI trading activities."""

    summary_id: str
    week_start_date: str
    week_end_date: str
    account_type: str

    # Weekly totals
    total_sessions: int
    total_trades: int
    total_pnl: float
    total_token_usage: int
    total_cost_usd: float

    # Performance trends
    win_rate_trend: List[float]
    pnl_trend: List[float]
    strategy_performance: Dict[str, Any]

    # Learning progress
    strategies_improved: int
    new_strategies_discovered: int
    key_learnings: List[str]

    # Market analysis
    market_themes: List[str]
    sector_rotation: Dict[str, Any]

    # Next week outlook
    market_outlook: str
    strategy_adjustments: List[str]

    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ActivitySummarizer:
    """
    Creates comprehensive summaries of AI trading activities.

    Provides clients with clear insights into:
    - Daily accomplishments and learnings
    - Strategy performance and improvements
    - Market analysis and insights
    - Future plans and adjustments
    """

    def __init__(self, strategy_store: ClaudeStrategyStore):
        self.strategy_store = strategy_store

    async def create_daily_summary(
        self,
        account_type: str,
        date: Optional[str] = None
    ) -> DailyActivitySummary:
        """Create a comprehensive daily activity summary."""

        if not date:
            date = datetime.now(timezone.utc).date().isoformat()

        logger.info(f"Creating daily activity summary for {account_type} on {date}")

        # Gather data from various sources
        session_data = await self._gather_session_data(account_type, date)
        trading_data = await self._gather_trading_data(account_type, date)
        research_data = await self._gather_research_data(account_type, date)
        learning_data = await self._gather_learning_data(account_type, date)
        market_data = await self._gather_market_data(date)

        # Generate insights and assessments
        key_findings = await self._generate_key_findings(research_data, trading_data)
        planned_activities = await self._generate_tomorrow_plan(trading_data, learning_data)
        risk_adjustments = await self._generate_risk_adjustments(trading_data, market_data)

        # Calculate day rating
        day_rating = self._calculate_day_rating(trading_data, learning_data)

        # Identify achievements and improvements
        key_achievements = await self._identify_achievements(trading_data, learning_data)
        areas_for_improvement = await self._identify_improvements(trading_data, learning_data)

        # Create summary
        summary = DailyActivitySummary(
            summary_id=f"daily_summary_{int(datetime.now(timezone.utc).timestamp())}_{account_type}",
            date=date,
            account_type=account_type,
            sessions_completed=session_data["count"],
            total_token_usage=session_data["tokens"],
            total_cost_usd=session_data["cost"],
            trades_executed=trading_data["executed"],
            trades_successful=trading_data["successful"],
            total_pnl=trading_data["pnl"],
            best_performing_strategy=trading_data["best_strategy"],
            worst_performing_strategy=trading_data["worst_strategy"],
            research_sessions=research_data["sessions"],
            symbols_analyzed=research_data["symbols"],
            key_findings=key_findings,
            strategies_evaluated=learning_data["evaluated"],
            refinements_recommended=learning_data["refinements"],
            confidence_score=learning_data["confidence"],
            market_conditions=market_data["conditions"],
            sector_performance=market_data["sectors"],
            planned_activities=planned_activities,
            risk_adjustments=risk_adjustments,
            day_rating=day_rating,
            key_achievements=key_achievements,
            areas_for_improvement=areas_for_improvement
        )

        # Save summary
        await self._save_daily_summary(summary)

        logger.info(f"Daily activity summary created for {account_type}: {day_rating} day")

        return summary

    async def create_weekly_summary(
        self,
        account_type: str,
        week_end_date: Optional[str] = None
    ) -> WeeklyActivitySummary:
        """Create a comprehensive weekly activity summary."""

        if not week_end_date:
            week_end_date = datetime.now(timezone.utc).date().isoformat()

        week_end = datetime.fromisoformat(week_end_date)
        week_start = week_end - timedelta(days=6)

        logger.info(f"Creating weekly activity summary for {account_type} ({week_start.date()} to {week_end.date()})")

        # Gather weekly data
        weekly_data = await self._gather_weekly_data(account_type, week_start, week_end)

        # Analyze trends
        win_rate_trend = weekly_data["win_rate_trend"]
        pnl_trend = weekly_data["pnl_trend"]
        strategy_performance = weekly_data["strategy_performance"]

        # Generate insights
        key_learnings = await self._generate_weekly_learnings(weekly_data)
        market_themes = await self._generate_market_themes(weekly_data)
        sector_rotation = weekly_data["sector_rotation"]

        # Generate outlook
        market_outlook = await self._generate_market_outlook(weekly_data)
        strategy_adjustments = await self._generate_strategy_adjustments(weekly_data)

        # Create summary
        summary = WeeklyActivitySummary(
            summary_id=f"weekly_summary_{int(datetime.now(timezone.utc).timestamp())}_{account_type}",
            week_start_date=week_start.date().isoformat(),
            week_end_date=week_end_date,
            account_type=account_type,
            total_sessions=weekly_data["total_sessions"],
            total_trades=weekly_data["total_trades"],
            total_pnl=weekly_data["total_pnl"],
            total_token_usage=weekly_data["total_tokens"],
            total_cost_usd=weekly_data["total_cost"],
            win_rate_trend=win_rate_trend,
            pnl_trend=pnl_trend,
            strategy_performance=strategy_performance,
            strategies_improved=weekly_data["strategies_improved"],
            new_strategies_discovered=weekly_data["new_strategies"],
            key_learnings=key_learnings,
            market_themes=market_themes,
            sector_rotation=sector_rotation,
            market_outlook=market_outlook,
            strategy_adjustments=strategy_adjustments
        )

        # Save summary
        await self._save_weekly_summary(summary)

        logger.info(f"Weekly activity summary created for {account_type}")

        return summary

    async def _gather_session_data(self, account_type: str, date: str) -> Dict[str, Any]:
        """Gather session activity data for the day."""

        # This would query the database for session data
        # For now, return simulated data
        return {
            "count": 2,  # morning + evening sessions
            "tokens": 4500,
            "cost": 0.15
        }

    async def _gather_trading_data(self, account_type: str, date: str) -> Dict[str, Any]:
        """Gather trading activity data for the day."""

        # This would query the database for trading data
        # For now, return simulated data
        return {
            "executed": 3,
            "successful": 2,
            "pnl": 2450.0,
            "best_strategy": "rsi_momentum",
            "worst_strategy": "breakout_momentum"
        }

    async def _gather_research_data(self, account_type: str, date: str) -> Dict[str, Any]:
        """Gather research activity data for the day."""

        # This would query the database for research data
        # For now, return simulated data
        return {
            "sessions": 1,
            "symbols": 15,
            "findings": ["Market showing signs of consolidation", "Technology sector outperforming"]
        }

    async def _gather_learning_data(self, account_type: str, date: str) -> Dict[str, Any]:
        """Gather learning activity data for the day."""

        # This would query the database for learning data
        # For now, return simulated data
        return {
            "evaluated": 4,
            "refinements": 2,
            "confidence": 0.75
        }

    async def _gather_market_data(self, date: str) -> Dict[str, Any]:
        """Gather market condition data."""

        # This would query market data services
        # For now, return simulated data
        return {
            "conditions": {
                "volatility": "moderate",
                "trend": "bullish",
                "volume": "above_average"
            },
            "sectors": {
                "technology": 2.1,
                "finance": -0.3,
                "healthcare": 1.5,
                "energy": -1.2
            }
        }

    async def _generate_key_findings(self, research_data: Dict, trading_data: Dict) -> List[str]:
        """Generate key findings from research and trading data."""

        findings = []

        if research_data.get("findings"):
            findings.extend(research_data["findings"])

        # Add trading insights
        if trading_data["pnl"] > 0:
            findings.append(f"Positive day with ₹{trading_data['pnl']:.0f} profit")
        else:
            findings.append(f"Challenging day with ₹{trading_data['pnl']:.0f} loss")

        findings.append(f"Best performing strategy: {trading_data['best_strategy']}")
        findings.append(f"Executed {trading_data['executed']} trades with {trading_data['successful']} successful")

        return findings

    async def _generate_tomorrow_plan(self, trading_data: Dict, learning_data: Dict) -> List[str]:
        """Generate planned activities for tomorrow."""

        plan = [
            "Morning market analysis and opportunity identification",
            "Execute planned trades based on today's learnings",
            "Monitor open positions and risk levels"
        ]

        if learning_data["refinements"] > 0:
            plan.append(f"Implement {learning_data['refinements']} strategy refinements")

        if trading_data["pnl"] < 0:
            plan.append("Focus on risk management and position sizing")

        return plan

    async def _generate_risk_adjustments(self, trading_data: Dict, market_data: Dict) -> List[str]:
        """Generate risk adjustments for tomorrow."""

        adjustments = []

        if market_data["conditions"]["volatility"] == "high":
            adjustments.append("Increase stop loss buffers due to high volatility")

        if trading_data["pnl"] < -1000:
            adjustments.append("Reduce position sizes to manage risk")

        if len(adjustments) == 0:
            adjustments.append("Maintain current risk parameters")

        return adjustments

    def _calculate_day_rating(self, trading_data: Dict, learning_data: Dict) -> str:
        """Calculate overall day rating."""

        pnl_score = 1.0 if trading_data["pnl"] > 0 else 0.0
        success_score = trading_data["successful"] / trading_data["executed"] if trading_data["executed"] > 0 else 0.0
        learning_score = learning_data["confidence"]

        overall_score = (pnl_score * 0.4) + (success_score * 0.3) + (learning_score * 0.3)

        if overall_score >= 0.8:
            return "excellent"
        elif overall_score >= 0.6:
            return "good"
        elif overall_score >= 0.4:
            return "neutral"
        else:
            return "challenging"

    async def _identify_achievements(self, trading_data: Dict, learning_data: Dict) -> List[str]:
        """Identify key achievements of the day."""

        achievements = []

        if trading_data["pnl"] > 1000:
            achievements.append(f"Generated ₹{trading_data['pnl']:.0f} in profits")

        if trading_data["successful"] / trading_data["executed"] > 0.6:
            achievements.append(f"Achieved {trading_data['successful']}/{trading_data['executed']} successful trades")

        if learning_data["refinements"] > 0:
            achievements.append(f"Identified {learning_data['refinements']} strategy improvements")

        if not achievements:
            achievements.append("Completed all planned trading activities")

        return achievements

    async def _identify_improvements(self, trading_data: Dict, learning_data: Dict) -> List[str]:
        """Identify areas for improvement."""

        improvements = []

        if trading_data["successful"] / trading_data["executed"] < 0.5:
            improvements.append("Improve trade selection criteria")

        if trading_data["pnl"] < 0:
            improvements.append("Review risk management procedures")

        if learning_data["confidence"] < 0.7:
            improvements.append("Increase research depth for better decisions")

        if not improvements:
            improvements.append("Continue current approach with minor optimizations")

        return improvements

    async def _gather_weekly_data(self, account_type: str, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Gather weekly activity data."""

        # This would query the database for weekly data
        # For now, return simulated data
        return {
            "total_sessions": 14,
            "total_trades": 21,
            "total_pnl": 8750.0,
            "total_tokens": 31500,
            "total_cost": 1.05,
            "win_rate_trend": [0.65, 0.70, 0.55, 0.75, 0.60, 0.80, 0.65],
            "pnl_trend": [1200, 1800, -800, 2500, 900, 3200, 950],
            "strategy_performance": {
                "rsi_momentum": {"win_rate": 0.68, "pnl": 3200},
                "macd_divergence": {"win_rate": 0.72, "pnl": 2800},
                "bollinger_mean_reversion": {"win_rate": 0.55, "pnl": 1200},
                "breakout_momentum": {"win_rate": 0.62, "pnl": 1550}
            },
            "strategies_improved": 2,
            "new_strategies": 0,
            "sector_rotation": {
                "technology": "gaining_momentum",
                "finance": "neutral",
                "healthcare": "losing_momentum",
                "energy": "neutral"
            }
        }

    async def _generate_weekly_learnings(self, weekly_data: Dict) -> List[str]:
        """Generate key learnings from weekly data."""

        learnings = [
            "RSI momentum strategy showing consistent performance",
            "MACD divergence works well in trending markets",
            "Bollinger Band strategy needs refinement for ranging markets",
            "Technology sector showing strong momentum"
        ]

        return learnings

    async def _generate_market_themes(self, weekly_data: Dict) -> List[str]:
        """Generate market themes from weekly data."""

        themes = [
            "Technology sector leadership continuing",
            "Interest rate sensitivity affecting financial stocks",
            "Defensive sectors showing relative strength",
            "Market breadth improving with more stocks participating"
        ]

        return themes

    async def _generate_market_outlook(self, weekly_data: Dict) -> str:
        """Generate market outlook for next week."""

        # Analyze trends to generate outlook
        pnl_trend = weekly_data["pnl_trend"]
        recent_performance = sum(pnl_trend[-3:])  # Last 3 days

        if recent_performance > 2000:
            return "Bullish momentum building - maintain exposure"
        elif recent_performance > 0:
            return "Neutral to positive - selective approach"
        else:
            return "Cautious environment - focus on risk management"

    async def _generate_strategy_adjustments(self, weekly_data: Dict) -> List[str]:
        """Generate strategy adjustments for next week."""

        adjustments = []

        strategy_perf = weekly_data["strategy_performance"]

        # Find best and worst performers
        best_strategy = max(strategy_perf.items(), key=lambda x: x[1]["pnl"])
        worst_strategy = min(strategy_perf.items(), key=lambda x: x[1]["pnl"])

        adjustments.append(f"Increase allocation to {best_strategy[0]} (₹{best_strategy[1]['pnl']} profit)")
        adjustments.append(f"Review and refine {worst_strategy[0]} strategy")

        return adjustments

    async def _save_daily_summary(self, summary: DailyActivitySummary) -> None:
        """Save daily summary to database."""

        # This would save to a dedicated daily_summaries table
        # For now, we'll log the summary data
        summary_data = summary.to_dict()

        logger.info(f"Daily activity summary saved: {summary.summary_id}")
        logger.debug(f"Summary data: {json.dumps(summary_data, indent=2)}")

    async def _save_weekly_summary(self, summary: WeeklyActivitySummary) -> None:
        """Save weekly summary to database."""

        # This would save to a dedicated weekly_summaries table
        # For now, we'll log the summary data
        summary_data = summary.to_dict()

        logger.info(f"Weekly activity summary saved: {summary.summary_id}")
        logger.debug(f"Summary data: {json.dumps(summary_data, indent=2)}")

    async def get_daily_summaries(
        self,
        account_type: Optional[str] = None,
        limit: int = 30
    ) -> List[DailyActivitySummary]:
        """Get historical daily summaries."""

        # This would query the database for stored daily summaries
        # For now, return empty list
        return []

    async def get_weekly_summaries(
        self,
        account_type: Optional[str] = None,
        limit: int = 12
    ) -> List[WeeklyActivitySummary]:
        """Get historical weekly summaries."""

        # This would query the database for stored weekly summaries
        # For now, return empty list
        return []