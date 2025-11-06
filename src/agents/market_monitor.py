"""
Market Monitor Agent

Monitors real-time market data and triggers alerts.
"""

import json
from typing import Any, Dict, List

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config

from ..core.database_state import DatabaseStateManager


def create_market_monitor_tool(config: Config, state_manager: DatabaseStateManager):
    """Create market monitor tool with dependencies via closure."""

    @tool(
        "monitor_market",
        "Monitor market for alerts and triggers",
        {"symbols": List[str]},
    )
    async def monitor_market_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor market for alerts."""
        try:
            symbols = args.get("symbols", [])

            # Simulate market monitoring
            alerts = _simulate_market_alerts(symbols)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Market monitoring completed. {len(alerts)} alerts detected",
                    },
                    {"type": "text", "text": json.dumps(alerts, indent=2)},
                ]
            }

        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True,
            }

    return monitor_market_tool


def _simulate_market_alerts(symbols: List[str]) -> List[Dict[str, Any]]:
    """Simulate market alerts."""
    alerts = []

    # Simulate some alerts
    if "INFY" in symbols:
        alerts.append(
            {
                "symbol": "INFY",
                "alert_type": "stop_loss_trigger",
                "message": "Stop loss triggered at 1510",
                "action_required": "close_position",
            }
        )

    if "TCS" in symbols:
        alerts.append(
            {
                "symbol": "TCS",
                "alert_type": "breakout",
                "message": "Price broke above resistance at 3250",
                "action_required": "review_position",
            }
        )

    return alerts
