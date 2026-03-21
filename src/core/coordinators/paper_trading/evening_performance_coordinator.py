"""
Evening Performance Coordinator - AI insights, watchlists, and safeguard updates.
"""

from typing import Dict, Any, List

from src.config import Config
from src.core.event_bus import EventBus
from ..base_coordinator import BaseCoordinator


class EveningPerformanceCoordinator(BaseCoordinator):
    """Generates AI insights, watchlists, and updates safeguards."""

    def __init__(self, config: Config, event_bus: EventBus, container: Any):
        super().__init__(config, event_bus)
        self.container = container

    async def initialize(self) -> None:
        """Initialize with required services."""
        self.state_manager = await self.container.get("state_manager")
        self.paper_trading_state = self.state_manager.paper_trading

        try:
            self.perplexity = await self.container.get("perplexity_service")
        except ValueError:
            self._log_warning("perplexity_service not registered - analysis disabled")
            self.perplexity = None

        try:
            self.safeguards = await self.container.get("autonomous_trading_safeguards")
        except ValueError:
            self._log_warning("autonomous_trading_safeguards not registered - safeguards disabled")
            self.safeguards = None

        self._initialized = True

    async def generate_trading_insights(self, performance_metrics: Dict[str, Any],
                                        open_positions: List[Any]) -> List[str]:
        """Generate trading insights using Perplexity API."""
        try:
            context = {
                "daily_performance": {
                    "pnl": performance_metrics.get("daily_pnl", 0.0),
                    "pnl_percent": performance_metrics.get("daily_pnl_percent", 0.0),
                    "win_rate": performance_metrics.get("win_rate", 0.0),
                    "trades_count": len(performance_metrics.get("trades_reviewed", []))
                },
                "open_positions": len(open_positions),
                "strategy_breakdown": performance_metrics.get("strategy_performance", {})
            }

            query = (
                "Analyze today's paper trading performance and provide actionable insights:\n\n"
                f"Daily P&L: ₹{performance_metrics.get('daily_pnl', 0):.2f} "
                f"({performance_metrics.get('daily_pnl_percent', 0):.2f}%)\n"
                f"Win Rate: {performance_metrics.get('win_rate', 0):.1f}%\n"
                f"Total Trades: {len(performance_metrics.get('trades_reviewed', []))}\n"
                f"Open Positions: {len(open_positions)}\n\n"
                f"Strategy Performance:\n"
                f"{self._format_strategy_performance(performance_metrics.get('strategy_performance', {}))}\n\n"
                "Provide 3-5 key insights about:\n"
                "1. What worked well today\n"
                "2. What didn't work and why\n"
                "3. Risk management observations\n"
                "4. Market condition impacts\n"
                "5. Recommendations for tomorrow"
            )

            insights = []
            if self.perplexity:
                response = await self.perplexity.query_perplexity(
                    query=query, context=context, max_tokens=500
                )
                if response and "content" in response:
                    for line in response["content"].split('\n'):
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith('-')):
                            insight = line.lstrip('0123456789.- ').strip()
                            if insight:
                                insights.append(insight)
            else:
                self._log_warning("Perplexity service not available - skipping AI insights")

            if not insights:
                if performance_metrics.get("daily_pnl", 0) > 0:
                    insights.append("Positive day - consider analyzing winning trades for patterns")
                else:
                    insights.append("Negative day - review loss management and entry criteria")
                if performance_metrics.get("win_rate", 0) < 50:
                    insights.append("Win rate below 50% - tighten entry criteria or improve exit timing")

            return insights[:5]

        except Exception as e:
            self._log_error(f"Failed to generate trading insights: {e}")
            return ["Insights generation failed - please check system logs"]

    async def prepare_next_day_watchlist(self, performance_metrics: Dict[str, Any],
                                         open_positions: List[Any]) -> List[Dict[str, Any]]:
        """Prepare watchlist for next trading day."""
        try:
            traded_symbols = {
                trade["symbol"] for trade in performance_metrics.get("trades_reviewed", [])
            }
            position_symbols = {pos.symbol for pos in open_positions}
            watch_symbols = traded_symbols.union(position_symbols)

            discovery_watchlist = await self.paper_trading_state.get_discovery_watchlist(limit=20)
            for item in discovery_watchlist:
                if item["recommendation"] in ["BUY", "STRONG_BUY"]:
                    watch_symbols.add(item["symbol"])

            watchlist = []
            for symbol in list(watch_symbols)[:15]:
                watchlist.append({
                    "symbol": symbol,
                    "reason": "Active trading or high potential",
                    "priority": "HIGH" if symbol in position_symbols else "MEDIUM",
                    "source": "trading_activity"
                })
            return watchlist

        except Exception as e:
            self._log_error(f"Failed to prepare next day watchlist: {e}")
            return []

    async def update_safeguards(self, performance_metrics: Dict[str, Any]) -> None:
        """Update trading safeguards with daily performance."""
        if not self.safeguards:
            self._log_warning("Safeguards service not available - skipping safeguard update")
            return
        try:
            await self.safeguards.update_daily_pnl(performance_metrics.get("daily_pnl", 0))
        except Exception as e:
            self._log_error(f"Failed to update safeguards: {e}")

    def _format_strategy_performance(self, strategy_performance: Dict[str, Any]) -> str:
        """Format strategy performance for display."""
        lines = []
        for strategy, metrics in strategy_performance.items():
            pnl = metrics.get("total_pnl", 0)
            win_rate = metrics.get("win_rate", 0)
            trades = metrics.get("trades", 0)
            lines.append(f"  {strategy}: ₹{pnl:.2f} ({win_rate:.1f}% win rate, {trades} trades)")
        return "\n".join(lines) if lines else "No strategy data available"

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("EveningPerformanceCoordinator cleanup complete")
