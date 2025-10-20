"""Context builders for token-optimized Claude sessions."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build token-optimized contexts for Claude Agent SDK."""

    def __init__(self, token_limit: int = 2000):
        """Initialize builder."""
        self.token_limit = token_limit

    async def build_morning_context(
        self,
        account_data: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        market_data: Optional[Dict[str, Any]] = None,
        earnings_today: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Build token-optimized morning context.

        Token optimization techniques:
        1. Compact field names (s=symbol, q=quantity, p=price)
        2. Only essential fields (omit descriptions, colors, metadata)
        3. Truncate to recent/most important data
        4. Use arrays instead of objects where possible
        """
        context = {
            "ts": datetime.utcnow().isoformat(),
            "acct": {
                "bal": account_data.get("current_balance", 0),
                "bp": account_data.get("buying_power", 0),
                "type": account_data.get("account_type", "swing")
            }
        }

        # Compact positions format
        if open_positions:
            context["pos"] = [
                {
                    "s": p.get("symbol"),
                    "q": p.get("quantity"),
                    "e": p.get("entry_price"),
                    "t": p.get("target_price"),
                    "sl": p.get("stop_loss")
                }
                for p in open_positions[:5]  # Limit to 5
            ]

        # Market data (if available)
        if market_data:
            context["mkt"] = {
                "open": market_data.get("market_open"),
                "vol": market_data.get("volume"),
                "senti": market_data.get("sentiment")
            }

        # Earnings today (if available)
        if earnings_today:
            context["earn"] = [
                {"s": e.get("symbol"), "t": e.get("time")}
                for e in earnings_today[:3]  # Limit to 3
            ]

        logger.debug(f"Built morning context (~{self._estimate_tokens(context)} tokens)")
        return context

    async def build_evening_context(
        self,
        account_data: Dict[str, Any],
        today_trades: List[Dict[str, Any]],
        daily_pnl: float,
        strategy_effectiveness: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build token-optimized evening context."""
        context = {
            "ts": datetime.utcnow().isoformat(),
            "acct": account_data.get("account_type", "swing"),
            "pnl": daily_pnl,
            "n_trades": len(today_trades)
        }

        # Compact trades format (only essential fields)
        if today_trades:
            context["trades"] = [
                {
                    "s": t.get("symbol"),
                    "a": t.get("action"),
                    "q": t.get("quantity"),
                    "p": t.get("price"),
                    "pnl": t.get("pnl")
                }
                for t in today_trades[:10]
            ]

        # Strategy effectiveness
        if strategy_effectiveness:
            context["strat"] = {
                "worked": strategy_effectiveness.get("what_worked", [])[:3],
                "failed": strategy_effectiveness.get("what_failed", [])[:3]
            }

        logger.debug(f"Built evening context (~{self._estimate_tokens(context)} tokens)")
        return context

    async def build_analysis_context(
        self,
        symbol: str,
        latest_news: List[Dict[str, Any]],
        earnings_data: Optional[Dict[str, Any]] = None,
        fundamentals: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build context for stock analysis recommendations."""
        context = {
            "s": symbol,
            "ts": datetime.utcnow().isoformat()
        }

        # News (compact format, recent only)
        if latest_news:
            context["news"] = [
                {
                    "h": n.get("headline"),
                    "sent": n.get("sentiment"),
                    "d": n.get("date")
                }
                for n in latest_news[:3]
            ]

        # Earnings (if available)
        if earnings_data:
            context["earn"] = {
                "eps_e": earnings_data.get("eps_estimate"),
                "eps_a": earnings_data.get("eps_actual"),
                "surp": earnings_data.get("surprise_pct"),
                "rev": earnings_data.get("revenue"),
                "guid": earnings_data.get("guidance")
            }

        # Fundamentals (only key metrics)
        if fundamentals:
            context["fund"] = {
                "pe": fundamentals.get("pe_ratio"),
                "roe": fundamentals.get("roe"),
                "de": fundamentals.get("debt_equity"),
                "rg": fundamentals.get("revenue_growth"),
                "eg": fundamentals.get("earnings_growth")
            }

        logger.debug(f"Built analysis context (~{self._estimate_tokens(context)} tokens)")
        return context

    def _estimate_tokens(self, obj: Any) -> int:
        """
        Rough token estimation.

        Claude tokenizer: roughly 4 characters per token (conservative estimate)
        JSON serialization adds ~10% overhead
        """
        json_str = json.dumps(obj)
        return int((len(json_str) / 4) * 1.1)

    async def truncate_context(
        self,
        context: Dict[str, Any],
        target_tokens: int
    ) -> Dict[str, Any]:
        """Truncate context to fit token budget."""
        if self._estimate_tokens(context) <= target_tokens:
            return context

        # Progressively remove elements
        truncated = context.copy()

        # Remove positions beyond first 3
        if "pos" in truncated and len(truncated["pos"]) > 3:
            truncated["pos"] = truncated["pos"][:3]

        # Remove trades beyond first 5
        if "trades" in truncated and len(truncated["trades"]) > 5:
            truncated["trades"] = truncated["trades"][:5]

        # Remove news beyond first 1
        if "news" in truncated and len(truncated["news"]) > 1:
            truncated["news"] = truncated["news"][:1]

        logger.debug(f"Truncated context to ~{self._estimate_tokens(truncated)} tokens")
        return truncated

    @staticmethod
    def serialize_for_prompt(context: Dict[str, Any]) -> str:
        """Serialize context for insertion into prompt."""
        return json.dumps(context, indent=2)
