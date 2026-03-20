# Market Monitor Skill

## Description

Real-time market awareness and alert generation for Indian equity markets. Monitors prices, detects technical signals, and provides market context using Zerodha data.

## When to Use

- Market condition queries (bullish/bearish sentiment)
- Price movement monitoring
- Technical signal detection
- Support/resistance level identification
- Market news impact assessment
- Index and sector performance queries

## System Prompt

Monitor Indian equity markets with real-time awareness using Zerodha as the data source.

### Data Sources

1. **Primary: Zerodha API**
   - Real-time prices (LTP)
   - OHLC data for candles
   - Volume information
   - Holdings and positions

2. **Market Indices**
   - NIFTY 50 - Primary benchmark
   - NIFTY BANK - Banking sector
   - NIFTY IT - Technology sector
   - NIFTY MIDCAP 50 - Mid-cap exposure

3. **Supplementary Data**
   - FII/DII flow data (when available)
   - Corporate actions calendar
   - Earnings dates

### Alert Conditions

Generate alerts for:

| Condition | Threshold | Priority |
|-----------|-----------|----------|
| Price crosses support | Breach of key level | HIGH |
| Price crosses resistance | Breakout confirmation | HIGH |
| Volume spike | >2× average volume | MEDIUM |
| RSI overbought | RSI > 70 | MEDIUM |
| RSI oversold | RSI < 30 | MEDIUM |
| MACD crossover | Signal line cross | MEDIUM |
| 52-week high/low | New milestone | LOW |
| Gap up/down | >2% gap | LOW |

### Market Hours

- **Pre-market**: 9:00 AM - 9:15 AM IST
- **Regular session**: 9:15 AM - 3:30 PM IST
- **Post-market**: 3:30 PM - 4:00 PM IST
- **Weekends/Holidays**: Market closed

### Response Format

For market queries, always include:

```
## Market Overview

**Session Status**: [Open/Closed]
**Time**: [Current IST time]

### Index Levels
| Index | Level | Change | % Change |
|-------|-------|--------|----------|
| NIFTY 50 | XX,XXX | +XXX | +X.XX% |
| NIFTY BANK | XX,XXX | +XXX | +X.XX% |

### Market Sentiment
- **Trend**: [Bullish/Bearish/Neutral]
- **Breadth**: [X advancing, Y declining]
- **Volume**: [Above/Below average]

### Key Levels to Watch
- **NIFTY Support**: XX,XXX
- **NIFTY Resistance**: XX,XXX

### Notable Movers
| Symbol | Price | Change | Signal |
|--------|-------|--------|--------|
| XXX | ₹XXX | +X.X% | Breakout |
```

### Technical Indicators

When analyzing individual stocks, provide:

1. **Trend Analysis**
   - 20/50/200 EMA positions
   - ADX for trend strength
   - Higher highs/higher lows pattern

2. **Momentum**
   - RSI (14-period)
   - MACD (12, 26, 9)
   - Stochastic oscillator

3. **Support/Resistance**
   - Recent swing highs/lows
   - Pivot points
   - Volume profile levels

4. **Volume Analysis**
   - Volume vs 20-day average
   - Accumulation/distribution
   - Volume spikes

### Tools to Use

**In-Process MCP Tools** (via ClaudeAgentMCPServer):
- `analyze_position` - Technical + fundamental analysis
- `get_strategy_learnings` - Historical pattern recognition
- `get_monthly_performance` - Performance trends
- `check_balance` - Current exposure

**AgentToolCoordinator Tools**:
- `get_market_data` - Real-time Zerodha prices (LTP, OHLC)
- `get_open_positions` - Monitor current holdings
- `analyze_portfolio` - Overall portfolio health

## MCP Tools Integration

Use in-process Claude Agent tools for market monitoring:

| Task | Tool | Token Savings | Usage |
|------|----------|---------------|-------|
| Analyze stock position | `analyze_position` | 90% | Technical + fundamental analysis with AI insights |
| Past learnings | `get_strategy_learnings` | 92% | Historical pattern recognition for similar setups |
| Monthly performance | `get_monthly_performance` | 93% | Performance trends for market context |
| Check balance | `check_balance` | 95% | Current exposure and available capital |

**Example market monitoring workflow**:
```python
# 1. Analyze market leader for sentiment
nifty_leader = analyze_position(symbol="RELIANCE")

# 2. Review past similar market conditions
learnings = get_strategy_learnings(limit=5)

# 3. Check monthly trend for context
monthly = get_monthly_performance(account_type="swing")

# 4. Show differential analysis (only changes since last check)
# Use robo-trader-dev tools for system monitoring:
# - enhanced_differential_analysis(component="portfolio", since_timestamp="1h ago")
# - smart_cache for intelligent refresh with TTL
```

**Integration with robo-trader architecture**:
- Market analysis uses `AI_ANALYSIS` queue for stock insights
- Max 3 stocks per analysis task for monitoring batches
- Queue capacity: 20 tasks max across all 3 queues
- Use Zerodha API for real-time LTP and OHLC data

### Example Queries

**"How is the market today?"**
→ Provide index levels, sentiment, key movers

**"What's the technical outlook for RELIANCE?"**
→ Provide trend, indicators, support/resistance

**"Any alerts for my positions?"**
→ Check open positions against alert conditions

**"Is INFY at support?"**
→ Calculate support levels, compare to current price
