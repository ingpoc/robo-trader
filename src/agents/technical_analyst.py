"""
Technical Analyst Agent

Computes technical indicators and generates trading signals.
"""

import json
from typing import Dict, List, Any
import random

from claude_agent_sdk import tool
from loguru import logger

from ..config import Config
from ..core.state import StateManager, Signal


def create_technical_analyst_tool(config: Config, state_manager: StateManager):
    """Create technical analyst tool with dependencies via closure."""
    
    @tool("technical_analysis", "Perform technical analysis on symbols", {"symbols": List[str], "timeframe": str})
    async def technical_analysis_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform technical analysis on given symbols."""
        try:
            symbols = args["symbols"]
            timeframe = args.get("timeframe", "15m")

            signals = {}
            for symbol in symbols:
                # Simulate technical analysis
                indicators = _calculate_indicators(symbol, timeframe)
                signal = _generate_signal(symbol, timeframe, indicators, config)
                signals[symbol] = signal.to_dict()

            return {
                "content": [
                    {"type": "text", "text": f"Technical analysis completed for {len(symbols)} symbols"},
                    {"type": "text", "text": json.dumps(signals, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Technical analysis failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }
    
    return technical_analysis_tool


def _calculate_indicators(symbol: str, timeframe: str) -> Dict[str, float]:
    """Calculate technical indicators (simplified)."""
    # Simulate indicator calculations
    return {
        "rsi": random.uniform(30, 70),
        "macd": random.uniform(-2, 2),
        "bollinger_upper": random.uniform(1500, 1600),
        "bollinger_lower": random.uniform(1400, 1500),
        "ema_9": random.uniform(1480, 1520),
        "ema_21": random.uniform(1470, 1510),
        "atr": random.uniform(10, 50)
    }


def _generate_signal(symbol: str, timeframe: str, indicators: Dict[str, float], config: Config) -> Signal:
    """Generate trading signal based on indicators."""
    rsi = indicators["rsi"]
    macd = indicators["macd"]

    # Simple signal logic
    if rsi < 30 and macd < 0:
        # Oversold with negative momentum - potential buy
        entry_price = indicators["bollinger_lower"] * 0.98
        stop_price = entry_price * 0.95
        targets = [entry_price * 1.05, entry_price * 1.10]
        confidence = 0.7
        rationale = f"RSI {rsi:.1f} oversold with MACD {macd:.2f} negative momentum"
    elif rsi > 70 and macd > 0:
        # Overbought with positive momentum - potential sell
        entry_price = indicators["bollinger_upper"] * 1.02
        stop_price = entry_price * 1.05
        targets = [entry_price * 0.95, entry_price * 0.90]
        confidence = 0.7
        rationale = f"RSI {rsi:.1f} overbought with MACD {macd:.2f} positive momentum"
    else:
        # Neutral
        entry_price = indicators["ema_9"]
        stop_price = entry_price * 0.97
        targets = [entry_price * 1.03]
        confidence = 0.4
        rationale = f"Neutral conditions - RSI {rsi:.1f}, MACD {macd:.2f}"

    return Signal(
        symbol=symbol,
        timeframe=timeframe,
        indicators=indicators,
        entry={"type": "limit", "price": round(entry_price, 2)},
        stop={"type": "hard", "price": round(stop_price, 2)},
        targets=[{"price": round(target, 2)} for target in targets],
        confidence=round(confidence, 2),
        rationale=rationale
    )