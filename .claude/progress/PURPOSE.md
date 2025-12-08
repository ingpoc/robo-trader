# Robo Trader - System Purpose

## 🎯 Core Mission

**Build an autonomous AI trading system to evaluate if Claude can be trusted with real money through paper trading while providing intelligent portfolio analysis.**

---

## Two Independent Systems

### 1. Portfolio Analysis System (Your Real Money)
- **Purpose**: Help you make better decisions about your existing portfolio
- **Frequency**: Monthly analysis (not daily trading advice)
- **Process**:
  - Claude analyzes each stock in your portfolio
  - Uses Perplexity API for fundamentals, earnings, news sentiment
  - Provides recommendation: **KEEP** or **SELL**
  - You decide whether to act on recommendations
- **Goal**: Improve your real investment returns

### 2. Paper Trading System (Virtual Money)
- **Purpose**: Test if Claude can be a profitable trader
- **Capital**: ₹1,00,000 virtual money (never real)
- **Process**:
  - Claude acts as independent trader
  - Daily morning/evening trading sessions
  - Uses Kite Connect API for real prices
  - Research via Perplexity API
  - Evolves strategies over time
- **Goal**: Achieve consistent returns to prove trading capability

---

## 🔒 Key Principles

### Fully Autonomous
- No manual override features
- No emergency stops (circuit breakers handle risk)
- Claude makes all trading decisions
- Human only observes monthly performance

### Paper Trading Only
- **NEVER** real money involved
- Virtual portfolio completely separate from your real portfolio
- Claude can trade any stocks, not just your holdings
- Real market prices, virtual money

### Separate Goals
- **Portfolio Analysis**: Help you with existing investments
- **Paper Trading**: Test Claude's trading skill
- No confusion between the two systems

---

## 📊 Success Criteria

### For Paper Trading (Can Claude be Trusted?)
1. **Performance**: Consistent monthly returns
2. **Risk Management**: Sharpe ratio > 1.0
3. **Drawdown Control**: Maximum loss < 15%
4. **Strategy Evolution**: Improves over time
5. **Consistency**: Positive returns 6+ consecutive months
6. **Final Score**: > 85/100 overall rating

### For Portfolio Analysis
1. **Accuracy**: Correct keep/sell recommendations
2. **Timeliness**: Early warning on deteriorating stocks
3. **Clarity**: Clear reasoning for each recommendation
4. **Actionability**: Specific insights you can use

---

## 🚫 What This System is NOT

- **NOT** a day trading bot for your real money
- **NOT** a copy trading service
- **NOT** financial advice platform
- **NOT** a social trading network
- **NOT** a portfolio tracker with alerts

---

## 🎪 The Ultimate Question

**After 6+ months of consistent profitable paper trading, can Claude be trusted with real money?**

This system provides the data to answer that question objectively.

---

*This purpose document guides all feature development. Any feature must serve either portfolio analysis, paper trading, or both. Features that enable manual intervention or real money trading are explicitly excluded as they violate the core mission.*