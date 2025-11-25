"""
Technical Analyst Agent

Computes technical indicators and generates trading signals using real market data from Kite Connect.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import Signal
from ..services.kite_connect_service import KiteConnectService
from ..services.technical_indicators_service import TechnicalIndicatorsService


def create_technical_analyst_tool(
    config: Config,
    state_manager: DatabaseStateManager,
    kite_service: Optional[KiteConnectService] = None,
    indicators_service: Optional[TechnicalIndicatorsService] = None
):
    """Create technical analyst tool with dependencies via closure."""
    
    @tool("technical_analysis", "Perform technical analysis on symbols using real market data", {"symbols": List[str], "timeframe": str})
    async def technical_analysis_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform technical analysis on given symbols using real Kite Connect data."""
        try:
            symbols = args["symbols"]
            timeframe = args.get("timeframe", "day")

            if not kite_service:
                return {
                    "content": [{"type": "text", "text": "Error: Kite Connect service not available. Please authenticate with Zerodha first."}],
                    "is_error": True
                }

            if not indicators_service:
                indicators_service = TechnicalIndicatorsService(config)

            signals = {}
            for symbol in symbols:
                try:
                    # Fetch real historical data from Kite Connect
                    indicators = await _calculate_indicators(
                        symbol, timeframe, kite_service, indicators_service
                    )
                    
                    if indicators:
                        signal = _generate_signal(symbol, timeframe, indicators, config)
                        signals[symbol] = signal.to_dict()
                    else:
                        signals[symbol] = {
                            "error": "Failed to calculate indicators - insufficient data or authentication issue"
                        }
                except Exception as e:
                    logger.error(f"Technical analysis failed for {symbol}: {e}")
                    signals[symbol] = {
                        "error": f"Analysis failed: {str(e)}"
                    }

            return {
                "content": [
                    {"type": "text", "text": f"Technical analysis completed for {len(symbols)} symbols using real Kite Connect data"},
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


async def _calculate_indicators(
    symbol: str,
    timeframe: str,
    kite_service: KiteConnectService,
    indicators_service: TechnicalIndicatorsService
) -> Optional[Dict[str, float]]:
    """Calculate technical indicators using real Kite Connect historical data."""
    try:
        # Map timeframe to Kite Connect interval
        timeframe_map = {
            "1m": "minute",
            "3m": "3minute",
            "5m": "5minute",
            "15m": "15minute",
            "30m": "30minute",
            "1h": "60minute",
            "day": "day",
            "week": "week",
            "month": "month"
        }
        
        interval = timeframe_map.get(timeframe, "day")
        
        # Calculate date range based on timeframe
        # For daily data, get last 60 days (enough for all indicators)
        # For intraday, get last 30 days
        if interval == "day":
            days_back = 60
        else:
            days_back = 30
            
        to_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Fetch historical data from Kite Connect
        logger.info(f"Fetching historical data for {symbol} from {from_date} to {to_date} (interval: {interval})")
        historical_data = await kite_service.get_historical_data(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )

        if not historical_data or len(historical_data) < 30:
            logger.warning(f"Insufficient historical data for {symbol}: {len(historical_data) if historical_data else 0} points")
            return None

        # Calculate all indicators
        indicators = indicators_service.calculate_all_indicators(historical_data)
        
        logger.info(f"Calculated indicators for {symbol}: RSI={indicators.get('rsi'):.2f}, MACD={indicators.get('macd'):.2f}")
        return indicators

    except Exception as e:
        logger.error(f"Failed to calculate indicators for {symbol}: {e}")
        return None


def _generate_signal(symbol: str, timeframe: str, indicators: Dict[str, Any], config: Config) -> Signal:
    """Generate trading signal based on real indicators."""
    rsi = indicators.get("rsi")
    macd = indicators.get("macd")
    current_price = indicators.get("current_price")
    bollinger_lower = indicators.get("bollinger_lower")
    bollinger_upper = indicators.get("bollinger_upper")
    ema_9 = indicators.get("ema_9")
    ema_21 = indicators.get("ema_21")
    atr = indicators.get("atr")

    # Use current price as fallback
    if not current_price:
        logger.warning(f"No current price available for {symbol}")
        current_price = 1000.0  # Fallback

    # Signal generation logic based on real indicators
    confidence = 0.4
    rationale_parts = []

    # RSI analysis
    if rsi is not None:
        if rsi < 30:
            rationale_parts.append(f"RSI {rsi:.1f} (oversold)")
            confidence += 0.2
        elif rsi > 70:
            rationale_parts.append(f"RSI {rsi:.1f} (overbought)")
            confidence += 0.2
        else:
            rationale_parts.append(f"RSI {rsi:.1f} (neutral)")
    else:
        rationale_parts.append("RSI unavailable")

    # MACD analysis
    if macd is not None:
        macd_signal = indicators.get("macd_signal", 0)
        if macd > macd_signal:
            rationale_parts.append("MACD bullish")
            confidence += 0.15
        else:
            rationale_parts.append("MACD bearish")
    else:
        rationale_parts.append("MACD unavailable")

    # EMA crossover
    if ema_9 is not None and ema_21 is not None:
        if ema_9 > ema_21:
            rationale_parts.append("EMA 9 > EMA 21 (bullish)")
            confidence += 0.1
        else:
            rationale_parts.append("EMA 9 < EMA 21 (bearish)")
    else:
        rationale_parts.append("EMA unavailable")

    # Determine entry, stop, and targets
    if rsi is not None and rsi < 30 and macd is not None and macd < 0:
        # Oversold with negative momentum - potential buy
        entry_price = bollinger_lower * 0.98 if bollinger_lower else current_price * 0.98
        stop_price = entry_price - (atr * 1.5 if atr else entry_price * 0.05)
        targets = [entry_price * 1.05, entry_price * 1.10]
        confidence = min(0.8, confidence)
    elif rsi is not None and rsi > 70 and macd is not None and macd > 0:
        # Overbought with positive momentum - potential sell
        entry_price = bollinger_upper * 1.02 if bollinger_upper else current_price * 1.02
        stop_price = entry_price + (atr * 1.5 if atr else entry_price * 0.05)
        targets = [entry_price * 0.95, entry_price * 0.90]
        confidence = min(0.8, confidence)
    else:
        # Neutral - use current price
        entry_price = current_price
        stop_price = entry_price - (atr * 2 if atr else entry_price * 0.02)
        targets = [entry_price * 1.03]
        confidence = max(0.3, min(0.5, confidence))

    rationale = " | ".join(rationale_parts) if rationale_parts else "Insufficient indicator data"

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