"""
Market Monitor Agent

Monitors real-time market data and triggers alerts using Kite Connect.
"""

import json
from typing import Dict, List, Any, Optional

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..services.kite_connect_service import KiteConnectService


def create_market_monitor_tool(
    config: Config,
    state_manager: DatabaseStateManager,
    kite_service: Optional[KiteConnectService] = None
):
    """Create market monitor tool with dependencies via closure."""
    
    @tool("monitor_market", "Monitor market for alerts and triggers using real-time Kite Connect data", {"symbols": List[str]})
    async def monitor_market_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor market for alerts using real-time data."""
        try:
            symbols = args.get("symbols", [])

            if not kite_service:
                return {
                    "content": [{"type": "text", "text": "Error: Kite Connect service not available. Please authenticate with Zerodha first."}],
                    "is_error": True
                }

            if not symbols:
                return {
                    "content": [{"type": "text", "text": "Error: No symbols provided for monitoring"}],
                    "is_error": True
                }

            # Get real-time quotes from Kite Connect
            logger.info(f"Monitoring {len(symbols)} symbols for alerts")
            quotes = await kite_service.get_quotes(symbols)

            # Check for alerts based on real-time data
            alerts = _check_market_alerts(quotes, config)

            return {
                "content": [
                    {"type": "text", "text": f"Market monitoring completed using real-time Kite Connect data. {len(alerts)} alerts detected"},
                    {"type": "text", "text": json.dumps(alerts, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }
    
    return monitor_market_tool


def _check_market_alerts(
    quotes: Dict[str, Any],
    config: Config
) -> List[Dict[str, Any]]:
    """Check for market alerts based on real-time quotes."""
    alerts = []

    for symbol, quote_data in quotes.items():
        if not quote_data:
            continue

        last_price = quote_data.last_price
        change_percent = quote_data.change_percent
        volume = quote_data.volume
        ohlc = quote_data.ohlc

        # Alert: Large price movement
        if abs(change_percent) > 5.0:
            alerts.append({
                "symbol": symbol,
                "alert_type": "large_price_movement",
                "message": f"Price moved {change_percent:+.2f}% to ₹{last_price:.2f}",
                "action_required": "review_position",
                "severity": "high" if abs(change_percent) > 7.0 else "medium"
            })

        # Alert: Volume spike (if we have historical volume data)
        # For now, we'll check if volume is very high (this would need historical comparison)
        if volume and volume > 1000000:  # High volume threshold
            alerts.append({
                "symbol": symbol,
                "alert_type": "volume_spike",
                "message": f"High volume detected: {volume:,} shares",
                "action_required": "monitor",
                "severity": "medium"
            })

        # Alert: Price near day's high/low
        if ohlc:
            high = ohlc.get("high", 0)
            low = ohlc.get("low", 0)
            
            if high > 0 and low > 0:
                price_range = high - low
                if price_range > 0:
                    distance_from_high = ((high - last_price) / price_range) * 100
                    distance_from_low = ((last_price - low) / price_range) * 100

                    if distance_from_high < 2.0:  # Within 2% of day's high
                        alerts.append({
                            "symbol": symbol,
                            "alert_type": "near_day_high",
                            "message": f"Price near day's high: ₹{last_price:.2f} (high: ₹{high:.2f})",
                            "action_required": "review_position",
                            "severity": "low"
                        })
                    elif distance_from_low < 2.0:  # Within 2% of day's low
                        alerts.append({
                            "symbol": symbol,
                            "alert_type": "near_day_low",
                            "message": f"Price near day's low: ₹{last_price:.2f} (low: ₹{low:.2f})",
                            "action_required": "review_position",
                            "severity": "low"
                        })

    return alerts