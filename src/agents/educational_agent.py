"""
Educational Agent

Provides explanations for trading concepts, decisions, and market analysis.
Helps users understand why the system makes specific recommendations.
"""

import json
from typing import Dict, List, Any
from datetime import datetime, timezone

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import PortfolioState, Signal, RiskDecision


def create_educational_tools(config: Config, state_manager: DatabaseStateManager) -> List:
    """Create educational tools with dependencies via closure."""
    
    @tool("explain_concept", "Explain a trading concept or indicator", {
        "concept": str,
        "context": str,
        "detail_level": str
    })
    async def explain_concept_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Explain trading concepts in simple, educational terms."""
        try:
            concept = args.get("concept", "").lower()
            context = args.get("context", "")
            detail_level = args.get("detail_level", "intermediate")

            explanation = await _generate_concept_explanation(concept, context, detail_level)

            return {
                "content": [
                    {"type": "text", "text": explanation}
                ]
            }

        except Exception as e:
            logger.error(f"Concept explanation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error explaining concept: {str(e)}"}],
                "is_error": True
            }

    @tool("explain_decision", "Explain why a specific trading decision was made", {
        "intent_id": str,
        "decision_type": str
    })
    async def explain_decision_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Explain the reasoning behind specific trading decisions."""
        try:
            intent_id = args.get("intent_id", "")
            decision_type = args.get("decision_type", "risk_assessment")

            intent = await state_manager.get_intent(intent_id)

            if not intent:
                return {
                    "content": [{"type": "text", "text": f"Intent {intent_id} not found"}],
                    "is_error": True
                }

            explanation = await _generate_decision_explanation(intent, decision_type)

            return {
                "content": [
                    {"type": "text", "text": explanation}
                ]
            }

        except Exception as e:
            logger.error(f"Decision explanation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error explaining decision: {str(e)}"}],
                "is_error": True
            }

    @tool("explain_portfolio", "Explain portfolio composition and strategy", {
        "focus_area": str,
        "user_experience": str
    })
    async def explain_portfolio_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Explain portfolio composition and underlying strategy."""
        try:
            focus_area = args.get("focus_area", "overview")
            user_experience = args.get("user_experience", "intermediate")

            portfolio = await state_manager.get_portfolio()

            explanation = await _generate_portfolio_explanation(portfolio, focus_area, user_experience)

            return {
                "content": [
                    {"type": "text", "text": explanation}
                ]
            }

        except Exception as e:
            logger.error(f"Portfolio explanation failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error explaining portfolio: {str(e)}"}],
                "is_error": True
            }
    
    return [explain_concept_tool, explain_decision_tool, explain_portfolio_tool]


async def _generate_concept_explanation(concept: str, context: str, detail_level: str) -> str:
    """Generate educational explanation for trading concepts."""

    explanations = {
        "rsi": {
            "basic": "RSI (Relative Strength Index) measures how fast a stock's price is changing. It ranges from 0-100 and helps identify if a stock is overbought (above 70) or oversold (below 30).",
            "intermediate": "RSI compares the average gains and losses over a specific period (usually 14 days). When RSI is above 70, the stock might be overbought and could fall soon. When below 30, it might be oversold and could rise. RSI divergence (when price and RSI move in opposite directions) often signals trend reversals.",
            "advanced": "RSI uses the formula: RSI = 100 - (100 / (1 + RS)), where RS is the average of upward price changes divided by average downward price changes. The indicator works best in ranging markets and loses effectiveness in strong trends. Look for RSI divergences, failure swings, and centerline crossovers for trading signals."
        },
        "macd": {
            "basic": "MACD (Moving Average Convergence Divergence) shows the relationship between two moving averages of a stock's price. It helps identify trend changes and momentum.",
            "intermediate": "MACD consists of the MACD line (difference between fast and slow EMAs) and signal line (EMA of MACD line). When MACD crosses above the signal line, it's a bullish signal. When it crosses below, it's bearish. The histogram shows the difference between MACD and signal line.",
            "advanced": "MACD uses exponential moving averages (typically 12 and 26 periods) to identify trend momentum. Zero line crossovers indicate trend changes, while signal line crossovers show entry/exit points. Divergences between MACD and price action provide strong reversal signals."
        },
        "bollinger_bands": {
            "basic": "Bollinger Bands create a channel around the stock price based on volatility. The bands widen when volatility increases and narrow when it decreases.",
            "intermediate": "Bollinger Bands consist of a middle line (20-day SMA) and upper/lower bands (2 standard deviations away). Prices touching the upper band suggest overbought conditions, while touching the lower band suggests oversold conditions. Band squeeze often precedes significant price moves.",
            "advanced": "Bollinger Bands measure volatility using standard deviation. The %B indicator shows where price is within the bands (above 1 = above upper band, below 0 = below lower band). Band width indicates volatility - narrow bands often precede breakouts."
        },
        "stop_loss": {
            "basic": "A stop loss is an order to sell a stock when it reaches a certain price, limiting your potential losses on a trade.",
            "intermediate": "Stop losses protect your capital by automatically closing positions at predetermined levels. Common stop loss strategies include percentage-based (e.g., 5% below entry), volatility-based (using ATR), and support-based (just below technical support levels).",
            "advanced": "Advanced stop loss techniques include trailing stops (move up as price rises), time-based stops (exit after certain period), and volatility-adjusted stops (wider stops for volatile stocks). The key is balancing risk management with avoiding premature exits from winning trades."
        },
        "position_sizing": {
            "basic": "Position sizing determines how much money to invest in each trade, helping manage risk across your portfolio.",
            "intermediate": "Position sizing considers your total capital, risk tolerance per trade, and stop loss distance. A common rule is to risk no more than 1-2% of your portfolio on any single trade. Kelly Criterion provides mathematically optimal position sizes based on win rate and average win/loss ratio.",
            "advanced": "Optimal position sizing balances risk and reward using probabilistic models. The Kelly formula calculates: f = (bp - q) / b, where b=odds, p=win probability, q=loss probability. Risk-adjusted sizing considers correlation between positions and portfolio volatility."
        }
    }

    # Get explanation based on detail level
    concept_explanations = explanations.get(concept, {
        "basic": f"{concept.upper()} is a technical indicator used in stock analysis.",
        "intermediate": f"{concept.upper()} helps traders make informed decisions about buying and selling stocks.",
        "advanced": f"{concept.upper()} is an advanced technical analysis tool requiring careful interpretation."
    })

    base_explanation = concept_explanations.get(detail_level, concept_explanations.get("intermediate", ""))

    # Add context-specific information
    if context:
        base_explanation += f"\n\nIn this context: {context}"

    # Add practical trading tip
    trading_tips = {
        "rsi": "\n\n💡 Tip: Don't buy just because RSI is low, or sell just because it's high. Look for confirmation from price action and other indicators.",
        "macd": "\n\n💡 Tip: MACD works best in trending markets. In sideways markets, it may give false signals.",
        "bollinger_bands": "\n\n💡 Tip: When bands are narrow (squeeze), watch for breakout opportunities. When wide, consider mean reversion trades.",
        "stop_loss": "\n\n💡 Tip: Place stop losses at logical technical levels (support/resistance) rather than arbitrary percentages.",
        "position_sizing": "\n\n💡 Tip: Smaller positions for volatile stocks, larger positions for stable blue-chip companies."
    }

    base_explanation += trading_tips.get(concept, "")

    return base_explanation


async def _generate_decision_explanation(intent, decision_type: str) -> str:
    """Generate explanation for why a specific decision was made."""

    if not intent:
        return "No intent provided for explanation."

    symbol = intent.symbol

    if decision_type == "risk_assessment" and intent.risk_decision:
        decision = intent.risk_decision

        explanation = f"""## Risk Assessment Explanation for {symbol}

**Decision:** {decision.decision.upper()}

### Why this decision was made:

"""

        if decision.reasons:
            for i, reason in enumerate(decision.reasons, 1):
                explanation += f"{i}. **{reason}**\n"

        if decision.constraints:
            explanation += "\n### Risk Constraints Applied:\n"
            for constraint in decision.constraints:
                explanation += f"• {constraint}\n"

        if decision.size_qty:
            explanation += f"""
### Position Sizing:
- **Recommended Size:** {decision.size_qty} shares
- **Risk Amount:** ₹{decision.max_risk_inr or 'N/A'}
- **Stop Loss:** {decision.stop.price if decision.stop else 'N/A'}

### Educational Context:
This decision balances potential returns with risk management. The position size ensures that even if this trade goes wrong, it won't significantly impact your overall portfolio. The stop loss protects your capital while giving the trade room to work."""

        return explanation

    elif decision_type == "technical_signal" and intent.signal:
        signal = intent.signal

        explanation = f"""## Technical Analysis Explanation for {symbol}

### Signal Details:
- **Timeframe:** {signal.timeframe}
- **Confidence:** {signal.confidence * 100:.1f}%
- **Rationale:** {signal.rationale}

### Indicator Analysis:
"""

        if signal.indicators:
            for indicator, value in signal.indicators.items():
                explanation += f"• **{indicator.upper()}:** {value}\n"

        explanation += f"""

### Trading Plan:
- **Entry:** {signal.entry.type.title() if signal.entry else 'Market'} at {signal.entry.price if signal.entry else 'N/A'}
- **Stop Loss:** {signal.stop.value}% {signal.stop.type} at {signal.stop.price if signal.stop else 'N/A'}
- **Targets:** {len(signal.targets) if signal.targets else 0} target levels identified

### Educational Context:
Technical analysis uses historical price patterns and mathematical indicators to predict future price movements. This signal combines multiple indicators to increase reliability and reduce false signals."""

        return explanation

    else:
        return f"""## Trading Decision Explanation for {symbol}

**Status:** {intent.status.title()}

This trade intent was created on {intent.created_at[:19]} and has gone through several stages of analysis:

1. **Technical Analysis:** Indicators and price patterns were evaluated
2. **Risk Assessment:** Position size and risk parameters were calculated
3. **Execution Planning:** Optimal order parameters were determined

For detailed explanations of each stage, use:
- `explain_decision` with `decision_type: "technical_signal"`
- `explain_decision` with `decision_type: "risk_assessment"`"""


async def _generate_portfolio_explanation(portfolio: PortfolioState, focus_area: str, user_experience: str) -> str:
    """Generate educational explanation of portfolio composition."""

    if not portfolio:
        return """## Portfolio Education

You don't have a portfolio loaded yet. Here's how to get started:

### First Steps:
1. **Load Portfolio Data:** Use the Portfolio Scan button to load your current holdings
2. **Review Risk Metrics:** Check your concentration risk and sector exposure
3. **Set Risk Parameters:** Configure your risk tolerance and position sizing rules

### Key Concepts:
- **Diversification:** Don't put all your eggs in one basket
- **Risk Management:** Always use stop losses and proper position sizing
- **Asset Allocation:** Balance between different types of investments"""

    explanation = f"""## Portfolio Analysis & Education

**Portfolio Value:** ₹{portfolio.exposure_total + portfolio.cash.free:.2f}
**Last Updated:** {portfolio.as_of[:19]}

"""

    if focus_area == "risk":
        explanation += """### Risk Analysis:
"""
        if portfolio.risk_aggregates.portfolio:
            risk = portfolio.risk_aggregates.portfolio
            explanation += f"""
- **Concentration Risk:** {risk.concentration_risk:.1f}%
- **Total P&L:** ₹{risk.total_pnl:.2f}
- **Sector Distribution:** {len(risk.sector_exposure)} sectors represented

### Risk Education:
Concentration risk measures how much of your portfolio is tied up in a single area. High concentration increases volatility and potential losses if that area performs poorly. A well-diversified portfolio typically has concentration risk below 20%.
"""
        else:
            explanation += "Risk metrics will be calculated after running a portfolio scan."

    elif focus_area == "performance":
        explanation += """### Performance Analysis:
"""
        # Calculate basic performance metrics
        total_pnl = 0
        for holding in portfolio.holdings:
            total_pnl += holding.get("pnl_abs", 0)

        explanation += f"""
- **Total Unrealized P&L:** ₹{total_pnl:.2f}
- **Number of Positions:** {len(portfolio.holdings)}
- **Cash Available:** ₹{portfolio.cash.free:.2f}

### Performance Education:
P&L (Profit and Loss) shows how your investments are performing. Positive P&L means your investments have gained value, while negative P&L indicates losses. Focus on both individual stock performance and overall portfolio health."""

    elif focus_area == "allocation":
        explanation += """### Asset Allocation:
"""
        if portfolio.risk_aggregates.portfolio and portfolio.risk_aggregates.portfolio.sector_exposure:
            sectors = portfolio.risk_aggregates.portfolio.sector_exposure
            for sector, exposure in sectors.items():
                percentage = (exposure / portfolio.exposure_total) * 100
                explanation += f"- **{sector.title()}:** {percentage:.1f}% (₹{exposure:.0f})\n"

            explanation += """
### Allocation Education:
Asset allocation determines your portfolio's risk and return characteristics. Different sectors perform differently in various market conditions. A balanced allocation reduces risk while maintaining growth potential."""
        else:
            explanation += "Sector allocation will be analyzed after running a portfolio scan."

    else:  # overview
        explanation += """### Portfolio Overview:

**Composition:**
- **Equity Holdings:** {len(portfolio.holdings)}
- **Cash Position:** ₹{portfolio.cash.free:.2f}
- **Total Portfolio Value:** ₹{portfolio.exposure_total + portfolio.cash.free:.2f}

### Portfolio Education:
A well-structured portfolio balances risk and reward while aligning with your investment goals and time horizon. Regular monitoring and rebalancing help maintain optimal performance."""

    # Add general educational tips based on user experience level
    if user_experience == "beginner":
        explanation += """

### Beginner Tips:
• Start with blue-chip stocks in different sectors
• Use stop losses to protect your capital
• Don't invest more than you can afford to lose
• Learn one indicator at a time before using complex strategies"""
    elif user_experience == "advanced":
        explanation += """

### Advanced Considerations:
• Monitor correlations between holdings
• Consider options for hedging
• Implement systematic rebalancing
• Track transaction costs and tax implications"""

    return explanation