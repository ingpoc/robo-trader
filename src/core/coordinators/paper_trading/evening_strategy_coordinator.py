"""
Evening Strategy Coordinator

Handles strategy evaluation and learning for the evening review session:
- Analyzing strategy performance (top vs underperforming)
- Generating recommendations for strategy allocation
- Producing learning insights for strategy evolution
"""

from typing import Dict, Any, List

from src.config import Config
from src.core.event_bus import EventBus
from ..base_coordinator import BaseCoordinator


class EveningStrategyCoordinator(BaseCoordinator):
    """Evaluates strategies and generates learning insights."""

    def __init__(self, config: Config, event_bus: EventBus):
        super().__init__(config, event_bus)

    async def initialize(self) -> None:
        """Initialize strategy coordinator (stateless, no services needed)."""
        self._initialized = True

    async def analyze_strategy_performance(
        self, strategy_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze and evaluate strategy performance."""
        try:
            analysis: Dict[str, Any] = {
                "top_strategies": [],
                "underperforming_strategies": [],
                "recommendations": []
            }

            sorted_strategies = sorted(
                strategy_performance.items(),
                key=lambda x: x[1].get("total_pnl", 0),
                reverse=True
            )

            for strategy, metrics in sorted_strategies:
                strategy_info = {
                    "strategy": strategy,
                    "pnl": metrics.get("total_pnl", 0),
                    "trades": metrics.get("trades", 0),
                    "win_rate": metrics.get("win_rate", 0)
                }

                if metrics.get("total_pnl", 0) > 0 and metrics.get("win_rate", 0) > 60:
                    analysis["top_strategies"].append(strategy_info)
                elif metrics.get("total_pnl", 0) < 0 or metrics.get("win_rate", 0) < 40:
                    analysis["underperforming_strategies"].append(strategy_info)

            if analysis["top_strategies"]:
                names = ", ".join(s["strategy"] for s in analysis["top_strategies"][:2])
                analysis["recommendations"].append(f"Increase allocation to top performers: {names}")

            if analysis["underperforming_strategies"]:
                names = ", ".join(s["strategy"] for s in analysis["underperforming_strategies"][:2])
                analysis["recommendations"].append(f"Review or reduce usage of: {names}")

            if not analysis["top_strategies"] and not analysis["underperforming_strategies"]:
                analysis["recommendations"].append(
                    "No clear strategy differentiation - consider longer evaluation period"
                )

            return analysis

        except Exception as e:
            self._log_error(f"Failed to analyze strategy performance: {e}")
            return {
                "top_strategies": [],
                "underperforming_strategies": [],
                "recommendations": ["Strategy analysis failed - check logs"]
            }

    async def generate_learning_insights(
        self,
        performance_metrics: Dict[str, Any],
        trading_insights: List[str],
        strategy_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate learning insights for strategy evolution."""
        try:
            learnings = []

            daily_pnl = performance_metrics.get("daily_pnl", 0)
            win_rate = performance_metrics.get("win_rate", 0)

            if daily_pnl > 0 and win_rate > 60:
                learnings.append("Strong performance day - document successful patterns for replication")
            elif daily_pnl < 0 and win_rate < 40:
                learnings.append("Poor performance day - identify and address systematic issues")
            elif win_rate < 50:
                learnings.append("Low win rate suggests need for stricter entry criteria")
            elif daily_pnl < 0 and win_rate > 60:
                learnings.append("Win rate good but P&L negative - review risk/reward ratios")

            top_strategies = strategy_analysis.get("top_strategies", [])
            if top_strategies:
                learnings.append(
                    f"Top performing strategy: {top_strategies[0]['strategy']} - analyze key success factors"
                )

            if "market conditions" in strategy_analysis:
                learnings.append("Document market conditions impact on strategy performance")

            return learnings[:3]

        except Exception as e:
            self._log_error(f"Failed to generate learning insights: {e}")
            return ["Learning analysis failed - check system logs"]

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("EveningStrategyCoordinator cleanup complete")
