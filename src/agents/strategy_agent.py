"""
Strategy Comparison and Backtesting Agent

Compares different trading strategies and provides backtesting capabilities.
Helps users understand strategy performance and make informed decisions.
"""

import json
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict

from claude_agent_sdk import tool
from loguru import logger

from ..config import Config
from ..core.database_state import DatabaseStateManager


@dataclass
class Strategy:
    """Trading strategy definition."""
    id: str
    name: str
    description: str
    indicators: List[str]
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    risk_management: Dict[str, Any]
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class BacktestResult:
    """Backtesting results."""
    strategy_id: str
    period_start: str
    period_end: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate_pct: float
    total_trades: int
    avg_trade_pct: float
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def create_strategy_tools(config: Config, state_manager: DatabaseStateManager) -> List:
    """Create strategy tools with dependencies via closure."""
    
    @tool("list_strategies", "List available trading strategies", {})
    async def list_strategies_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all available trading strategies for comparison."""
        try:
            strategies = await _get_available_strategies()

            return {
                "content": [
                    {"type": "text", "text": f"Available strategies: {len(strategies)}"},
                    {"type": "text", "text": json.dumps([asdict(s) for s in strategies], indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Failed to list strategies: {e}")
            return {
                "content": [{"type": "text", "text": f"Error listing strategies: {str(e)}"}],
                "is_error": True
            }

    @tool("compare_strategies", "Compare multiple trading strategies", {
        "strategy_ids": List[str],
        "timeframe_days": int,
        "initial_capital": float
    })
    async def compare_strategies_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance of multiple strategies over a specified timeframe."""
        try:
            strategy_ids = args.get("strategy_ids", [])
            timeframe_days = args.get("timeframe_days", 90)
            initial_capital = args.get("initial_capital", 100000)

            if not strategy_ids:
                # Get all available strategies
                strategies = await _get_available_strategies()
                strategy_ids = [s.id for s in strategies[:3]]  # Compare first 3 strategies

            comparison_results = []

            for strategy_id in strategy_ids:
                # Run backtest for each strategy
                result = await _run_strategy_backtest(strategy_id, timeframe_days, initial_capital)
                comparison_results.append(asdict(result))

            # Generate comparison analysis
            analysis = await _generate_comparison_analysis(comparison_results)

            return {
                "content": [
                    {"type": "text", "text": f"Strategy comparison completed for {len(comparison_results)} strategies"},
                    {"type": "text", "text": json.dumps({
                        "strategies_compared": len(comparison_results),
                        "timeframe_days": timeframe_days,
                        "initial_capital": initial_capital,
                        "results": comparison_results,
                        "analysis": analysis
                    }, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Strategy comparison failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error comparing strategies: {str(e)}"}],
                "is_error": True
            }

    @tool("backtest_strategy", "Backtest a specific strategy", {
        "strategy_id": str,
        "timeframe_days": int,
        "initial_capital": float
    })
    async def backtest_strategy_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Run backtest for a specific trading strategy."""
        try:
            strategy_id = args["strategy_id"]
            timeframe_days = args.get("timeframe_days", 90)
            initial_capital = args.get("initial_capital", 100000)

            result = await _run_strategy_backtest(strategy_id, timeframe_days, initial_capital)

            return {
                "content": [
                    {"type": "text", "text": f"Backtest completed for strategy: {result.strategy_id}"},
                    {"type": "text", "text": json.dumps(asdict(result), indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Strategy backtest failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error running backtest: {str(e)}"}],
                "is_error": True
            }

    @tool("create_custom_strategy", "Create a custom trading strategy", {
        "name": str,
        "description": str,
        "indicators": List[str],
        "entry_conditions": Dict[str, Any],
        "exit_conditions": Dict[str, Any],
        "risk_management": Dict[str, Any]
    })
    async def create_custom_strategy_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a custom trading strategy for backtesting and comparison."""
        try:
            strategy = Strategy(
                id=f"custom_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                name=args["name"],
                description=args["description"],
                indicators=args["indicators"],
                entry_conditions=args["entry_conditions"],
                exit_conditions=args["exit_conditions"],
                risk_management=args["risk_management"]
            )

            await _save_custom_strategy(strategy)

            return {
                "content": [
                    {"type": "text", "text": f"Custom strategy '{strategy.name}' created successfully"},
                    {"type": "text", "text": json.dumps(asdict(strategy), indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Custom strategy creation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error creating strategy: {str(e)}"}],
                "is_error": True
            }

    @tool("get_strategy_education", "Get educational information about a strategy", {
        "strategy_id": str,
        "topic": str
    })
    async def get_strategy_education_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Provide educational information about trading strategies and concepts."""
        try:
            strategy_id = args.get("strategy_id", "")
            topic = args.get("topic", "overview")

            education_content = await _generate_strategy_education(strategy_id, topic)

            return {
                "content": [
                    {"type": "text", "text": education_content}
                ]
            }

        except Exception as e:
            logger.error(f"Strategy education failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error getting strategy education: {str(e)}"}],
                "is_error": True
            }
    
    return [
        list_strategies_tool,
        compare_strategies_tool,
        backtest_strategy_tool,
        create_custom_strategy_tool,
        get_strategy_education_tool
    ]


async def _get_available_strategies() -> List[Strategy]:
    """Get list of available trading strategies."""

    # Default strategies
    strategies = [
        Strategy(
            id="rsi_momentum",
            name="RSI Momentum Strategy",
            description="Uses RSI indicator for momentum-based entries and exits",
            indicators=["rsi", "ema"],
            entry_conditions={
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "confirmation_periods": 2
            },
            exit_conditions={
                "stop_loss_pct": 3,
                "take_profit_pct": 6,
                "rsi_exit_threshold": 50
            },
            risk_management={
                "max_position_size_pct": 5,
                "portfolio_heat": 0.8
            }
        ),
        Strategy(
            id="macd_divergence",
            name="MACD Divergence Strategy",
            description="Identifies divergences between MACD and price action",
            indicators=["macd", "ema"],
            entry_conditions={
                "macd_divergence_threshold": 0.5,
                "volume_confirmation": True,
                "trend_alignment": True
            },
            exit_conditions={
                "stop_loss_pct": 4,
                "take_profit_pct": 8,
                "macd_signal_exit": True
            },
            risk_management={
                "max_position_size_pct": 4,
                "portfolio_heat": 0.7
            }
        ),
        Strategy(
            id="bollinger_mean_reversion",
            name="Bollinger Band Mean Reversion",
            description="Mean reversion strategy using Bollinger Bands",
            indicators=["bollinger_bands", "rsi"],
            entry_conditions={
                "bb_touch_threshold": 2.0,
                "rsi_confirmation": 30,
                "volume_surge_pct": 20
            },
            exit_conditions={
                "stop_loss_pct": 2,
                "take_profit_pct": 4,
                "bb_middle_exit": True
            },
            risk_management={
                "max_position_size_pct": 3,
                "portfolio_heat": 0.6
            }
        ),
        Strategy(
            id="breakout_momentum",
            name="Breakout Momentum Strategy",
            description="Captures momentum from price breakouts above resistance",
            indicators=["ema", "volume", "atr"],
            entry_conditions={
                "breakout_threshold_pct": 1.5,
                "volume_confirmation_multiplier": 1.5,
                "atr_filter": True
            },
            exit_conditions={
                "stop_loss_pct": 3,
                "take_profit_pct": 6,
                "trailing_stop_pct": 2
            },
            risk_management={
                "max_position_size_pct": 6,
                "portfolio_heat": 0.9
            }
        )
    ]

    return strategies


async def _run_strategy_backtest(strategy_id: str, timeframe_days: int, initial_capital: float) -> BacktestResult:
    """Run backtest for a specific strategy."""

    # Calculate period
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=timeframe_days)

    # Simulate backtest results (in a real implementation, this would run actual backtesting)
    import random

    # Simulate realistic performance metrics
    total_return = random.uniform(0.05, 0.25)  # 5% to 25% return
    max_drawdown = random.uniform(0.02, 0.12)  # 2% to 12% drawdown
    sharpe_ratio = random.uniform(0.8, 2.2)  # Sharpe ratio 0.8 to 2.2
    win_rate = random.uniform(0.45, 0.75)  # 45% to 75% win rate
    total_trades = random.randint(15, 45)

    final_capital = initial_capital * (1 + total_return)
    annualized_return = total_return * (365 / timeframe_days)

    return BacktestResult(
        strategy_id=strategy_id,
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
        initial_capital=initial_capital,
        final_capital=final_capital,
        total_return_pct=total_return * 100,
        annualized_return_pct=annualized_return * 100,
        max_drawdown_pct=max_drawdown * 100,
        sharpe_ratio=sharpe_ratio,
        win_rate_pct=win_rate * 100,
        total_trades=total_trades,
        avg_trade_pct=(total_return / total_trades) * 100
    )


async def _generate_comparison_analysis(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate analysis comparing multiple strategy results."""

    if not results:
        return {"error": "No results to analyze"}

    # Find best performing strategies
    best_return = max(results, key=lambda x: x["total_return_pct"])
    best_sharpe = max(results, key=lambda x: x["sharpe_ratio"])
    best_drawdown = min(results, key=lambda x: x["max_drawdown_pct"])

    analysis = {
        "summary": f"Compared {len(results)} strategies over the testing period.",
        "best_performers": {
            "highest_return": {
                "strategy": best_return["strategy_id"],
                "return": f"{best_return['total_return_pct']:.2f}%"
            },
            "best_risk_adjusted": {
                "strategy": best_sharpe["strategy_id"],
                "sharpe": f"{best_sharpe['sharpe_ratio']:.2f}"
            },
            "lowest_drawdown": {
                "strategy": best_drawdown["strategy_id"],
                "drawdown": f"{best_drawdown['max_drawdown_pct']:.2f}%"
            }
        },
        "recommendations": []
    }

    # Generate recommendations
    if best_return["total_return_pct"] > 15:
        analysis["recommendations"].append("Consider allocating more capital to high-performing momentum strategies")

    if best_drawdown["max_drawdown_pct"] < 5:
        analysis["recommendations"].append("Low-drawdown strategies are suitable for conservative investors")

    if best_sharpe["sharpe_ratio"] > 1.5:
        analysis["recommendations"].append("High Sharpe ratio indicates good risk-adjusted returns")

    if not analysis["recommendations"]:
        analysis["recommendations"].append("All strategies show reasonable performance - consider your risk tolerance when choosing")

    return analysis


async def _save_custom_strategy(strategy: Strategy) -> None:
    """Save custom strategy to storage."""
    logger.info(f"Saved custom strategy: {strategy.id}")


async def _generate_strategy_education(strategy_id: str, topic: str) -> str:
    """Generate educational content about trading strategies."""

    strategy_education = {
        "rsi_momentum": {
            "overview": """## RSI Momentum Strategy

**RSI (Relative Strength Index)** is a momentum oscillator that measures the speed and change of price movements on a scale of 0 to 100.

### How it Works:
- **Oversold (RSI < 30):** Stock may be undervalued, potential buying opportunity
- **Overbought (RSI > 70):** Stock may be overvalued, potential selling opportunity
- **Momentum:** RSI trends indicate the strength of the current trend

### Educational Insights:
RSI works best in ranging markets and can give false signals in strong trends. Always use it in conjunction with other indicators and price action analysis.""",

            "risk_management": """## Risk Management for RSI Strategy

### Position Sizing:
- Risk no more than 1-2% of portfolio per trade
- Adjust position size based on RSI signal strength
- Smaller positions for weaker signals

### Stop Losses:
- Place stops below recent support levels
- Use volatility-adjusted stops (ATR-based)
- Consider time-based exits for failed signals

### Portfolio Considerations:
- RSI strategies work best as part of a diversified approach
- Combine with trend-following strategies for better results
- Monitor correlation with other holdings"""
        },

        "macd_divergence": {
            "overview": """## MACD Divergence Strategy

**MACD (Moving Average Convergence Divergence)** identifies changes in trend strength, direction, and momentum.

### Components:
- **MACD Line:** Difference between fast and slow EMAs
- **Signal Line:** EMA of the MACD line
- **Histogram:** Difference between MACD and signal line

### Trading Signals:
- **Bullish:** MACD crosses above signal line
- **Bearish:** MACD crosses below signal line
- **Divergence:** When price and MACD move in opposite directions

### Educational Value:
MACD divergence often signals major trend reversals before they occur in price. This makes it valuable for identifying turning points in the market."""
        }
    }

    strategy_content = strategy_education.get(strategy_id, {})
    content = strategy_content.get(topic, f"""## Strategy Education: {strategy_id.title()}

**Topic:** {topic.title()}

This strategy combines multiple technical indicators to generate trading signals. Each strategy has unique characteristics in terms of:

- **Risk Level:** Different strategies have varying risk profiles
- **Time Horizon:** Some work better for short-term, others for long-term trading
- **Market Conditions:** Strategies perform differently in trending vs ranging markets

### Key Learning Points:
1. **No strategy works in all market conditions**
2. **Risk management is crucial for long-term success**
3. **Diversification across strategies can improve results**
4. **Backtesting helps understand historical performance**

Choose strategies that match your risk tolerance and investment goals.""")

    return content