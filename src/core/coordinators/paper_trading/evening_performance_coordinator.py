"""Evening Performance Coordinator - AI insights, watchlists, and safeguard updates."""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List

from claude_agent_sdk import ClaudeAgentOptions

from src.config import Config
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.event_bus import EventBus
from src.core.sdk_helpers import query_with_timeout
from ..base_coordinator import BaseCoordinator


class EveningPerformanceCoordinator(BaseCoordinator):
    """Generates AI insights, watchlists, and updates safeguards."""

    _JSON_RE = re.compile(r"\{.*\}|\[.*\]", flags=re.DOTALL)

    def __init__(self, config: Config, event_bus: EventBus, container: Any):
        super().__init__(config, event_bus)
        self.container = container

    async def initialize(self) -> None:
        """Initialize with required services."""
        self.state_manager = await self.container.get("state_manager")
        self.paper_trading_state = self.state_manager.paper_trading

        try:
            self.safeguards = await self.container.get("autonomous_trading_safeguards")
        except ValueError:
            self._log_warning("autonomous_trading_safeguards not registered - safeguards disabled")
            self.safeguards = None

        self._initialized = True

    async def generate_trading_insights(
        self,
        performance_metrics: Dict[str, Any],
        open_positions: List[Any],
    ) -> List[str]:
        """Generate trading insights with Claude based on internal performance context."""
        context = {
            "daily_performance": {
                "pnl": performance_metrics.get("daily_pnl", 0.0),
                "pnl_percent": performance_metrics.get("daily_pnl_percent", 0.0),
                "win_rate": performance_metrics.get("win_rate", 0.0),
                "trades_count": len(performance_metrics.get("trades_reviewed", [])),
            },
            "open_positions": len(open_positions),
            "strategy_breakdown": performance_metrics.get("strategy_performance", {}),
            "closed_trade_examples": performance_metrics.get("trades_reviewed", [])[:6],
        }
        prompt = (
            "Review this paper-trading session and produce 3 to 5 concise operator insights.\n"
            "Focus on what worked, what failed, risk management observations, and what should change tomorrow.\n"
            "Use only the provided context. Do not invent market events.\n"
            "Return JSON only in this shape:\n"
            '{"insights":["...", "..."]}\n\n'
            f"Context:\n{json.dumps(context, indent=2)}"
        )

        try:
            manager = await ClaudeSDKClientManager.get_instance()
            client_type = "evening_performance_insights"
            options = ClaudeAgentOptions(
                allowed_tools=[],
                max_turns=1,
                model="haiku",
                system_prompt=(
                    "You are Robo Trader's evening performance reviewer. "
                    "Produce concise, operator-usable post-trade insights from supplied metrics only."
                ),
            )
            client = await manager.get_client(client_type, options, force_recreate=True)
            try:
                response = await query_with_timeout(client, prompt, timeout=45.0)
            finally:
                await manager.cleanup_client(client_type)

            insights = self._parse_insights(response)
            if insights:
                return insights[:5]
        except Exception as exc:
            self._log_warning(f"Claude evening insight generation failed: {exc}")

        fallback = []
        if performance_metrics.get("daily_pnl", 0) > 0:
            fallback.append("Positive day - review which setups produced clean follow-through and size them consistently.")
        else:
            fallback.append("Negative day - inspect loss concentration and tighten entries that lacked confirmation.")
        if performance_metrics.get("win_rate", 0) < 50:
            fallback.append("Win rate below 50% - improve selectivity and exit discipline before scaling risk.")
        return fallback[:5]

    async def prepare_next_day_watchlist(
        self,
        performance_metrics: Dict[str, Any],
        open_positions: List[Any],
    ) -> List[Dict[str, Any]]:
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
                watchlist.append(
                    {
                        "symbol": symbol,
                        "reason": "Active trading or high potential",
                        "priority": "HIGH" if symbol in position_symbols else "MEDIUM",
                        "source": "trading_activity",
                    }
                )
            return watchlist

        except Exception as exc:
            self._log_error(f"Failed to prepare next day watchlist: {exc}")
            return []

    async def update_safeguards(self, performance_metrics: Dict[str, Any]) -> None:
        """Update trading safeguards with daily performance."""
        if not self.safeguards:
            self._log_warning("Safeguards service not available - skipping safeguard update")
            return
        try:
            await self.safeguards.update_daily_pnl(performance_metrics.get("daily_pnl", 0))
        except Exception as exc:
            self._log_error(f"Failed to update safeguards: {exc}")

    def _format_strategy_performance(self, strategy_performance: Dict[str, Any]) -> str:
        """Format strategy performance for display."""
        lines = []
        for strategy, metrics in strategy_performance.items():
            pnl = metrics.get("total_pnl", 0)
            win_rate = metrics.get("win_rate", 0)
            trades = metrics.get("trades", 0)
            lines.append(f"  {strategy}: ₹{pnl:.2f} ({win_rate:.1f}% win rate, {trades} trades)")
        return "\n".join(lines) if lines else "No strategy data available"

    @classmethod
    def _parse_insights(cls, response: str) -> List[str]:
        """Parse a JSON insights response from Claude."""
        text = (response or "").strip()
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        elif text.startswith("```"):
            text = text[len("```"):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        match = cls._JSON_RE.search(text)
        if match:
            text = match.group(0)

        payload = json.loads(text)
        if isinstance(payload, dict):
            items = payload.get("insights", [])
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        return [item.strip() for item in items if isinstance(item, str) and item.strip()]

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("EveningPerformanceCoordinator cleanup complete")
