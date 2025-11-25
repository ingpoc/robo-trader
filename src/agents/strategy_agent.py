"""
Strategy Agent - Claude-Powered Trading Strategy Generator

Uses Claude Agent SDK to analyze market conditions and generate trading strategies.
Leverages MCP servers, skills, and tools for comprehensive market analysis.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..services.kite_connect_service import KiteConnectService
from ..services.technical_indicators_service import TechnicalIndicatorsService
from ..services.fundamental_service import FundamentalService


def create_strategy_tools(
    config: Config,
    state_manager: DatabaseStateManager,
    kite_service: Optional[KiteConnectService] = None,
    indicators_service: Optional[TechnicalIndicatorsService] = None,
    fundamental_service: Optional[FundamentalService] = None
) -> List:
    """Create strategy tools with dependencies via closure."""
    
    @tool(
        "analyze_market_conditions",
        "Analyze current market conditions and generate trading strategy using Claude AI",
        {
            "symbols": List[str],
            "analysis_depth": str  # "quick", "standard", "deep"
        }
    )
    async def analyze_market_conditions_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market conditions and generate trading strategy.
        
        Uses Claude Agent SDK with multiple tools:
        - Technical analysis (RSI, MACD, Bollinger Bands)
        - Fundamental screening
        - Market monitoring
        - Portfolio analysis
        """
        try:
            symbols = args.get("symbols", [])
            analysis_depth = args.get("analysis_depth", "standard")
            
            if not symbols:
                return {
                    "content": [{"type": "text", "text": "Error: No symbols provided for analysis"}],
                    "is_error": True
                }

            logger.info(f"Analyzing market conditions for {len(symbols)} symbols (depth: {analysis_depth})")

            # Collect market data using available services
            market_analysis = await _collect_market_data(
                symbols, kite_service, indicators_service, fundamental_service, analysis_depth
            )

            # Generate strategy recommendations
            strategy = await _generate_strategy(market_analysis, config)

            return {
                "content": [
                    {"type": "text", "text": f"Market analysis completed for {len(symbols)} symbols"},
                    {"type": "text", "text": json.dumps(strategy, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }

    @tool(
        "generate_trading_strategy",
        "Generate comprehensive trading strategy based on market analysis",
        {
            "account_id": str,
            "available_capital": float,
            "risk_tolerance": str  # "conservative", "moderate", "aggressive"
        }
    )
    async def generate_trading_strategy_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading strategy for paper trading account.
        
        Claude will:
        1. Analyze current portfolio
        2. Review market opportunities
        3. Generate buy/sell recommendations
        4. Provide position sizing
        5. Set stop-loss and targets
        """
        try:
            account_id = args.get("account_id")
            available_capital = args.get("available_capital", 100000.0)
            risk_tolerance = args.get("risk_tolerance", "moderate")

            if not account_id:
                return {
                    "content": [{"type": "text", "text": "Error: Account ID required"}],
                    "is_error": True
                }

            logger.info(f"Generating trading strategy for account {account_id} (capital: ₹{available_capital}, risk: {risk_tolerance})")

            # Get current portfolio
            portfolio = await state_manager.get_portfolio()
            open_positions = await _get_open_positions(account_id, state_manager)

            # Analyze market opportunities
            market_opportunities = await _find_market_opportunities(
                kite_service, indicators_service, fundamental_service, config
            )

            # Generate strategy
            strategy = await _create_strategy_plan(
                account_id,
                available_capital,
                risk_tolerance,
                portfolio,
                open_positions,
                market_opportunities,
                config
            )

            return {
                "content": [
                    {"type": "text", "text": f"Trading strategy generated for account {account_id}"},
                    {"type": "text", "text": json.dumps(strategy, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }

    @tool(
        "evaluate_strategy_performance",
        "Evaluate strategy performance and suggest improvements",
        {
            "account_id": str,
            "period_days": int
        }
    )
    async def evaluate_strategy_performance_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate strategy performance using Claude AI.
        
        Claude will:
        1. Analyze trade history
        2. Calculate performance metrics
        3. Identify winning/losing patterns
        4. Suggest strategy improvements
        """
        try:
            account_id = args.get("account_id")
            period_days = args.get("period_days", 30)

            if not account_id:
                return {
                    "content": [{"type": "text", "text": "Error: Account ID required"}],
                    "is_error": True
                }

            logger.info(f"Evaluating strategy performance for account {account_id} (period: {period_days} days)")

            # Get trade history
            trade_history = await _get_trade_history(account_id, period_days, state_manager)

            # Calculate performance metrics
            performance = await _calculate_performance_metrics(trade_history, state_manager)

            # Generate evaluation and recommendations
            evaluation = await _generate_evaluation(performance, trade_history, config)

            return {
                "content": [
                    {"type": "text", "text": f"Strategy evaluation completed for account {account_id}"},
                    {"type": "text", "text": json.dumps(evaluation, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Strategy evaluation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }

    return [
        analyze_market_conditions_tool,
        generate_trading_strategy_tool,
        evaluate_strategy_performance_tool
    ]


async def _collect_market_data(
    symbols: List[str],
    kite_service: Optional[KiteConnectService],
    indicators_service: Optional[TechnicalIndicatorsService],
    fundamental_service: Optional[FundamentalService],
    analysis_depth: str
) -> Dict[str, Any]:
    """Collect comprehensive market data for analysis."""
    market_data = {}

    for symbol in symbols:
        symbol_data = {
            "symbol": symbol,
            "technical_indicators": None,
            "fundamental_data": None,
            "current_price": None,
            "price_history": None
        }

        # Get current price from Kite Connect
        if kite_service:
            try:
                quotes = await kite_service.get_quotes([symbol])
                if symbol in quotes:
                    quote = quotes[symbol]
                    symbol_data["current_price"] = quote.last_price
                    symbol_data["price_history"] = {
                        "open": quote.ohlc.get("open"),
                        "high": quote.ohlc.get("high"),
                        "low": quote.ohlc.get("low"),
                        "close": quote.ohlc.get("close"),
                        "volume": quote.volume,
                        "change_percent": quote.change_percent
                    }
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")

        # Get technical indicators
        if kite_service and indicators_service and analysis_depth in ["standard", "deep"]:
            try:
                from datetime import timedelta
                to_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                from_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime('%Y-%m-%d')
                
                historical_data = await kite_service.get_historical_data(
                    symbol=symbol,
                    from_date=from_date,
                    to_date=to_date,
                    interval="day"
                )
                
                if historical_data and len(historical_data) >= 30:
                    indicators = indicators_service.calculate_all_indicators(historical_data)
                    symbol_data["technical_indicators"] = indicators
            except Exception as e:
                logger.warning(f"Failed to calculate indicators for {symbol}: {e}")

        # Get fundamental data
        if fundamental_service and analysis_depth == "deep":
            try:
                fundamental_data = await fundamental_service.fetch_fundamentals_batch([symbol])
                if symbol in fundamental_data:
                    analysis = fundamental_data[symbol]
                    symbol_data["fundamental_data"] = {
                        "pe_ratio": analysis.pe_ratio,
                        "roe": analysis.roe,
                        "debt_to_equity": analysis.debt_to_equity,
                        "market_cap": analysis.market_cap,
                        "overall_score": analysis.overall_score,
                        "recommendation": analysis.recommendation
                    }
            except Exception as e:
                logger.warning(f"Failed to get fundamental data for {symbol}: {e}")

        market_data[symbol] = symbol_data

    return market_data


async def _generate_strategy(market_analysis: Dict[str, Any], config: Config) -> Dict[str, Any]:
    """Generate trading strategy based on market analysis."""
    # This will be enhanced with Claude Agent SDK integration
    # For now, return structured analysis
    
    recommendations = []
    for symbol, data in market_analysis.items():
        recommendation = {
            "symbol": symbol,
            "action": "HOLD",
            "confidence": 0.5,
            "rationale": "Neutral market conditions"
        }

        # Analyze technical indicators
        if data.get("technical_indicators"):
            indicators = data["technical_indicators"]
            rsi = indicators.get("rsi")
            macd = indicators.get("macd")
            
            if rsi and rsi < 30:
                recommendation["action"] = "BUY"
                recommendation["confidence"] = 0.7
                recommendation["rationale"] = f"RSI {rsi:.1f} indicates oversold condition"
            elif rsi and rsi > 70:
                recommendation["action"] = "SELL"
                recommendation["confidence"] = 0.7
                recommendation["rationale"] = f"RSI {rsi:.1f} indicates overbought condition"

        # Analyze fundamental data
        if data.get("fundamental_data"):
            fundamental = data["fundamental_data"]
            if fundamental.get("overall_score", 0) > 70:
                recommendation["action"] = "BUY"
                recommendation["confidence"] = min(0.9, recommendation["confidence"] + 0.2)
                recommendation["rationale"] += f" | Strong fundamentals (score: {fundamental['overall_score']})"

        recommendations.append(recommendation)

    return {
        "market_conditions": "analyzed",
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


async def _get_open_positions(account_id: str, state_manager: DatabaseStateManager) -> List[Dict[str, Any]]:
    """Get open positions for account."""
    # This would query paper trading store
    # Placeholder for now
    return []


async def _find_market_opportunities(
    kite_service: Optional[KiteConnectService],
    indicators_service: Optional[TechnicalIndicatorsService],
    fundamental_service: Optional[FundamentalService],
    config: Config
) -> List[Dict[str, Any]]:
    """Find market opportunities using available services."""
    opportunities = []
    
    # This would scan market for opportunities
    # Placeholder for now
    return opportunities


async def _create_strategy_plan(
    account_id: str,
    available_capital: float,
    risk_tolerance: str,
    portfolio: Any,
    open_positions: List[Dict[str, Any]],
    market_opportunities: List[Dict[str, Any]],
    config: Config
) -> Dict[str, Any]:
    """Create comprehensive strategy plan."""
    return {
        "account_id": account_id,
        "available_capital": available_capital,
        "risk_tolerance": risk_tolerance,
        "recommended_trades": [],
        "position_sizing": {},
        "stop_loss_levels": {},
        "target_prices": {},
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


async def _get_trade_history(account_id: str, period_days: int, state_manager: DatabaseStateManager) -> List[Dict[str, Any]]:
    """Get trade history for account."""
    # This would query paper trading store
    return []


async def _calculate_performance_metrics(trade_history: List[Dict[str, Any]], state_manager: DatabaseStateManager) -> Dict[str, Any]:
    """Calculate performance metrics."""
    return {
        "total_trades": len(trade_history),
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0
    }


async def _generate_evaluation(performance: Dict[str, Any], trade_history: List[Dict[str, Any]], config: Config) -> Dict[str, Any]:
    """Generate strategy evaluation and recommendations."""
    return {
        "performance_summary": performance,
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
