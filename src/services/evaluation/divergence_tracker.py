"""
Divergence Tracker

Compares: research_score -> intended_action -> actual_action -> outcome
Flags divergences and aggregates statistics for calibration.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DivergenceTracker:
    """
    Tracks divergences between what the system recommended and what actually happened.

    Key questions this answers:
    - What % of BUY signals were actually executed?
    - What % of blocked signals would have been profitable?
    - Are there systematic biases in the stale data guard or risk limits?
    """

    def __init__(self, trade_lifecycle_store, research_ledger_store):
        self.lifecycle_store = trade_lifecycle_store
        self.ledger_store = research_ledger_store

    async def get_divergence_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate a divergence report for the last N days.

        Returns aggregated statistics about signal-to-execution divergences.
        """
        report = {
            "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_research_signals": 0,
            "buy_signals": 0,
            "executed_buys": 0,
            "blocked_buys": 0,
            "block_reasons": {},
            "execution_rate_pct": 0.0,
            "divergences": [],
        }

        try:
            # Get all recent BUY entries from research ledger
            all_latest = await self.ledger_store.get_all_latest(limit=200)
            buy_entries = [e for e in all_latest if e.get("action") == "BUY"]

            report["total_research_signals"] = len(all_latest)
            report["buy_signals"] = len(buy_entries)

            # For each BUY signal, check if it was executed or blocked
            for entry in buy_entries:
                symbol = entry.get("symbol", "")
                lifecycle = await self.lifecycle_store.get_recent_by_symbol(symbol, limit=10)

                if not lifecycle:
                    report["blocked_buys"] += 1
                    report["divergences"].append({
                        "symbol": symbol,
                        "type": "no_lifecycle",
                        "research_score": entry.get("score"),
                        "detail": "BUY signal had no corresponding lifecycle events",
                    })
                    continue

                stages = {event["stage"] for event in lifecycle}

                if "filled" in stages:
                    report["executed_buys"] += 1
                elif "blocked" in stages:
                    report["blocked_buys"] += 1
                    # Find block reason
                    for event in lifecycle:
                        if event["stage"] == "blocked":
                            reason = event.get("data", {}).get("reason", "unknown")
                            report["block_reasons"][reason] = report["block_reasons"].get(reason, 0) + 1
                            report["divergences"].append({
                                "symbol": symbol,
                                "type": "blocked",
                                "research_score": entry.get("score"),
                                "block_reason": reason,
                            })
                elif "rejected" in stages:
                    report["blocked_buys"] += 1
                    report["divergences"].append({
                        "symbol": symbol,
                        "type": "rejected",
                        "research_score": entry.get("score"),
                    })
                else:
                    # Has lifecycle but no terminal state
                    report["divergences"].append({
                        "symbol": symbol,
                        "type": "incomplete",
                        "research_score": entry.get("score"),
                        "stages_found": list(stages),
                    })

            # Calculate execution rate
            if report["buy_signals"] > 0:
                report["execution_rate_pct"] = round(
                    report["executed_buys"] / report["buy_signals"] * 100, 1
                )

        except Exception as e:
            logger.error(f"Failed to generate divergence report: {e}")
            report["error"] = str(e)

        return report
