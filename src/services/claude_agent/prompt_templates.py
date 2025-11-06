"""Prompt templates for Claude Agent sessions."""


class SystemPrompts:
    """System prompts for different trading scenarios."""

    SWING_TRADER_SYSTEM = """You are RoboTrader-Swing, an expert swing trader managing a paper trading account.

EXPERTISE:
- Technical analysis (RSI, MACD, Bollinger Bands, support/resistance)
- Fundamental screening (P/E, growth rates, sector trends)
- Position management (risk/reward ratios, stop-loss placement)
- Behavioral discipline (strict rules, emotion control)

RESPONSIBILITIES:
1. Analyze price action and volume
2. Identify swing trade setups (2-5 day holds)
3. Execute trades autonomously with strict risk management
4. Monitor and close positions based on targets/stops
5. Learn from daily P&L and adjust strategy

CONSTRAINTS:
- Max position size: 5% of portfolio per trade
- Min stop-loss: 2% below entry
- Max daily trades: 10
- Hold period: 2-5 days typically

DECISION FRAMEWORK:
1. Is there a clear setup based on technicals + fundamentals?
2. Is risk/reward favorable (at least 1:2)?
3. Is buying power sufficient?
4. Are there better opportunities?

Execute trades decisively. Manage positions disciplined. Learn continuously."""

    OPTIONS_TRADER_SYSTEM = """You are RoboTrader-Options, trading options like PR Sundar (hedging expert).

EXPERTISE:
- Options Greeks (delta, theta, gamma, vega)
- Spread strategies (call spreads, put spreads, iron condors)
- Hedging and protective strategies
- Volatility analysis and IV optimization
- Expiry management (avoid STT penalties)

RESPONSIBILITIES:
1. Create hedging positions for equity exposure
2. Sell premium through spreads
3. Manage Greeks to remain market-neutral when needed
4. Monitor positions daily for adjustments
5. Close positions before expiry when optimal

CONSTRAINTS:
- Max hedge cost: 2% monthly premium
- Hedge effectiveness: minimum 80%
- Max loss per position: 1% portfolio
- Avoid holding through earnings if unhedged

DECISION FRAMEWORK:
1. What's the market outlook (bullish/neutral/bearish)?
2. Is hedging needed for core equity positions?
3. Can we sell premium profitably?
4. What's the optimal entry/exit timing?
5. Are Greeks within targets?

Execute hedges strategically. Capture theta decay. Protect downside."""

    @staticmethod
    def get_system_prompt(account_type: str) -> str:
        """Get system prompt for account type."""
        if account_type == "options":
            return SystemPrompts.OPTIONS_TRADER_SYSTEM
        else:
            return SystemPrompts.SWING_TRADER_SYSTEM


class MorningPrompts:
    """Morning session prompts."""

    MORNING_TEMPLATE = """MORNING TRADING SESSION - {timestamp}

ACCOUNT STATUS:
- Type: {account_type}
- Balance: ₹{balance:,.2f}
- Buying Power: ₹{buying_power:,.2f}

OPEN POSITIONS ({position_count}):
{positions_formatted}

MARKET CONTEXT:
{market_context}

EARNINGS TODAY:
{earnings_today}

YOUR TASKS (in priority order):
1. Review each open position:
   - Should we close it (target hit / stop loss / reassess)?
   - Or hold and let it run?
   - Any risk management adjustments?

2. Scan for new opportunities:
   - Technical setups that match your strategy
   - Stocks showing relative strength/weakness
   - Sector rotation opportunities

3. Execute your trading plan:
   - Use execute_trade tool for new entries
   - Use close_position tool for exits
   - Include clear rationale for each trade

DECISION RULES:
- Only trade if risk/reward is favorable (1:2 minimum)
- Honor stop losses religiously
- Take profits at targets
- Never average down
- Max {max_daily_trades} trades today

Remember: Your decisions will be analyzed tonight. Trade with conviction."""

    @staticmethod
    def build_morning_prompt(
        account_type: str,
        balance: float,
        buying_power: float,
        positions: str,
        market_context: str,
        earnings: str = "None scheduled",
        max_trades: int = 10,
    ) -> str:
        """Build morning prompt with context."""
        from datetime import datetime

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        position_count = len([p for p in positions.split("\n") if p.strip()])

        return MorningPrompts.MORNING_TEMPLATE.format(
            timestamp=timestamp,
            account_type=account_type,
            balance=balance,
            buying_power=buying_power,
            position_count=max(position_count - 1, 0),  # Adjust for header
            positions_formatted=positions,
            market_context=market_context,
            earnings_today=earnings,
            max_daily_trades=max_trades,
        )


class EveningPrompts:
    """Evening review session prompts."""

    EVENING_TEMPLATE = """EVENING STRATEGY REVIEW - {timestamp}

TODAY'S PERFORMANCE:
- Trades Executed: {trade_count}
- Daily P&L: ₹{daily_pnl:,.2f}
- Win Rate: {win_rate:.1f}%
- Avg Hold Time: {avg_hold_hours:.1f}h

TODAY'S TRADES:
{trades_summary}

REFLECTION QUESTIONS:
1. WHAT WORKED TODAY?
   - Which strategy patterns were profitable?
   - When did your entries/exits work?
   - What market conditions favored your trades?
   → List specific observations

2. WHAT DIDN'T WORK?
   - Which setups failed or underperformed?
   - Were any losses due to poor discipline?
   - Did market conditions change unexpectedly?
   → List specific observations

3. STRATEGY ADJUSTMENTS FOR TOMORROW:
   - Will you emphasize profitable strategies?
   - Will you avoid failed patterns?
   - Should you adjust stop-loss/target levels?
   → Be specific about changes

4. RESEARCH TOPICS FOR TOMORROW:
   - Any specific sectors/stocks to research?
   - Any technical patterns to study?
   - Any fundamental changes affecting holdings?
   → List topics to investigate

RESPONSE FORMAT (JSON):
{{
  "what_worked": ["observation 1", "observation 2"],
  "what_failed": ["observation 1"],
  "strategy_changes": ["change 1", "change 2"],
  "research_topics": ["topic 1", "topic 2"],
  "confidence_level": 0.75
}}

Remember: This reflection helps you evolve your strategy. Be honest about what works and what doesn't."""

    @staticmethod
    def build_evening_prompt(
        account_type: str,
        trade_count: int,
        daily_pnl: float,
        win_rate: float,
        trades_summary: str,
        avg_hold_hours: float = 0.0,
    ) -> str:
        """Build evening prompt with context."""
        from datetime import datetime

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        return EveningPrompts.EVENING_TEMPLATE.format(
            timestamp=timestamp,
            trade_count=trade_count,
            daily_pnl=daily_pnl,
            win_rate=win_rate,
            avg_hold_hours=avg_hold_hours,
            trades_summary=trades_summary,
        )


class AnalysisPrompts:
    """Analysis prompts for stock recommendations."""

    ANALYSIS_TEMPLATE = """INVESTMENT ANALYSIS - {symbol}

LATEST NEWS (past 7 days):
{news_summary}

EARNINGS INFORMATION:
{earnings_info}

FUNDAMENTAL METRICS:
{fundamentals}

ANALYSIS TASK:
Analyze whether to KEEP or SELL this stock.

Consider:
1. News sentiment - positive/negative/neutral?
2. Earnings surprise and guidance
3. Fundamental health and growth
4. Technical price action
5. Risk/reward in current market

RESPONSE (JSON):
{{
  "recommendation": "buy|sell|hold",
  "confidence": 0.75,
  "fair_value": 3200.50,
  "reasoning": "Clear explanation",
  "risk_factors": ["risk 1", "risk 2"],
  "catalysts": ["catalyst 1"]
}}"""

    @staticmethod
    def build_analysis_prompt(
        symbol: str, news_summary: str, earnings_info: str, fundamentals: str
    ) -> str:
        """Build analysis prompt."""
        return AnalysisPrompts.ANALYSIS_TEMPLATE.format(
            symbol=symbol,
            news_summary=news_summary,
            earnings_info=earnings_info,
            fundamentals=fundamentals,
        )


class PromptBuilder:
    """Main prompt builder interface."""

    def __init__(self):
        """Initialize builder."""
        self.system_prompts = SystemPrompts()
        self.morning_prompts = MorningPrompts()
        self.evening_prompts = EveningPrompts()
        self.analysis_prompts = AnalysisPrompts()

    def build_system_prompt(self, account_type: str) -> str:
        """Get system prompt."""
        return SystemPrompts.get_system_prompt(account_type)

    def build_morning_prompt(
        self,
        account_type: str,
        balance: float,
        buying_power: float,
        positions: str,
        market_context: str,
        earnings: str = "None scheduled",
        max_trades: int = 10,
    ) -> str:
        """Build morning prompt."""
        return MorningPrompts.build_morning_prompt(
            account_type,
            balance,
            buying_power,
            positions,
            market_context,
            earnings,
            max_trades,
        )

    def build_evening_prompt(
        self,
        account_type: str,
        trade_count: int,
        daily_pnl: float,
        win_rate: float,
        trades_summary: str,
        avg_hold_hours: float = 0.0,
    ) -> str:
        """Build evening prompt."""
        return EveningPrompts.build_evening_prompt(
            account_type,
            trade_count,
            daily_pnl,
            win_rate,
            trades_summary,
            avg_hold_hours,
        )

    def build_analysis_prompt(
        self, symbol: str, news_summary: str, earnings_info: str, fundamentals: str
    ) -> str:
        """Build analysis prompt."""
        return AnalysisPrompts.build_analysis_prompt(
            symbol, news_summary, earnings_info, fundamentals
        )
