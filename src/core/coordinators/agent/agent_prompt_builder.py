"""
Agent Prompt Builder

Focused utility for building Claude agent prompts.
Extracted from ClaudeAgentCoordinator for reusability.
"""

import json
from datetime import datetime
from typing import Dict, Any

from src.config import Config


class AgentPromptBuilder:
    """
    Builds prompts for Claude agent sessions.
    
    Responsibilities:
    - Build system prompts
    - Build morning prep prompts
    - Build evening review prompts
    """

    def __init__(self, config: Config):
        self.config = config

    def build_system_prompt(self, account_type: str) -> str:
        """Build system prompt for Claude."""
        return f"""You are RoboTrader, an autonomous trading agent managing a {account_type} trading account.

Your responsibilities:
1. Analyze market conditions and trade setups
2. Execute trades autonomously using available tools
3. Monitor positions and close trades when appropriate
4. Manage risk according to portfolio constraints
5. Learn from previous trading decisions

You have access to trading tools. Use them wisely to execute your trading strategy.

Risk Management Rules:
- Max position size: 5% of portfolio
- Max portfolio risk: 10%
- Stop loss minimum: 2% below entry
- All trades must have clear rationale

Remember: Your decisions will be logged and analyzed. Trade responsibly."""

    def build_morning_prompt(self, account_type: str, context: Dict[str, Any]) -> str:
        """Build token-optimized morning prompt with learning loop."""
        historical_learnings = context.get('historical_learnings', [])
        learnings_text = ""
        if historical_learnings:
            learnings_text = "\n\nRECENT LEARNINGS FROM PAST SESSIONS:\n" + "\n".join(f"- {learning}" for learning in historical_learnings[:3])

        return f"""Morning Trading Session - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}

CURRENT STATE:
- Account: {account_type}
- Balance: ₹{context.get('acct', {}).get('bal', 100000)}
- Buying Power: ₹{context.get('acct', {}).get('bp', 100000)}
- Open Positions: {len(context.get('pos', []))}

OPEN POSITIONS:
{json.dumps(context.get('pos', [])[:5], indent=2)}

MARKET CONTEXT:
{context.get('mkt', 'No market data available')}

{learnings_text}

YOUR TASK:
1. Analyze open positions - should any be closed based on current conditions?
2. Review market opportunities considering past performance
3. Execute new trades if opportunities exist and align with successful strategies
4. Use tools to execute your decisions
5. Apply learnings from previous sessions to improve decision-making

Think strategically, learn from the past, and execute your trades."""

    def build_evening_prompt(self, account_type: str, context: Dict[str, Any]) -> str:
        """Build evening review prompt with strategy analysis."""
        strategy_analysis = ""
        if context.get('strat'):
            strat = context['strat']
            if strat.get('worked'):
                strategy_analysis += f"\n\nWHAT WORKED WELL:\n" + "\n".join(f"- {item}" for item in strat['worked'][:2])
            if strat.get('failed'):
                strategy_analysis += f"\n\nWHAT FAILED:\n" + "\n".join(f"- {item}" for item in strat['failed'][:2])

        return f"""Evening Strategy Review - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}

TODAY'S PERFORMANCE:
- Account: {context.get('acct', account_type)}
- Trades Executed: {context.get('n_trades', 0)}
- Daily P&L: ₹{context.get('pnl', 0)}

TRADES TODAY:
{json.dumps(context.get('trades', [])[:10], indent=2)}

{strategy_analysis}

REFLECTION TASKS:
1. What strategies worked well today? What evidence supports this?
2. What failed and why? What patterns do you see?
3. What will you adjust for tomorrow based on today's results?
4. What do you want to research to improve future performance?
5. How can you apply today's learnings to avoid past mistakes?

Provide detailed, actionable insights for continuous improvement. Focus on specific, measurable changes you can implement."""

