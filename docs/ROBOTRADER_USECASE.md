# Robo Trader - Use Case & Functionality

## Primary Use Case

**Robo Trader** is an AI-powered autonomous paper trading system that uses Claude AI to make trading decisions, manage portfolios, and learn from past trades. It's designed as a learning and testing platform for trading strategies without risking real money.

### Core Value Proposition

Transform trading from manual analysis to **collaborative intelligence** where Claude AI acts as your expert trading partner - analyzing markets, managing risk, executing trades, and continuously learning from outcomes.

---

## Core Functionality

### 1. 🤖 Autonomous AI Trading

**What it does:**
- Claude AI makes trading decisions autonomously based on market analysis
- Natural language interaction: Ask questions like "Should I buy RELIANCE?" or "Analyze my portfolio"
- Multi-agent coordination: Specialized agents handle different aspects of trading
- Paper trading only: Simulates trading with virtual money (₹1,00,000 per account)

**Key Features:**
- Autonomous trade execution via Claude Agent SDK
- Conversational approvals and adjustments
- Real-time decision-making with reasoning
- Strategy optimization based on historical performance

### 2. 🧠 Multi-Agent System

The system uses specialized AI agents that work together:

| Agent | Responsibility |
|-------|---------------|
| **Portfolio Analyzer** | Monitors holdings, P&L, exposure, and risk metrics |
| **Technical Analyst** | Calculates RSI, MACD, Bollinger Bands, EMAs, and generates signals |
| **Fundamental Screener** | Filters stocks by value, quality, and growth metrics |
| **Risk Manager** | Enforces position sizing, stop-losses, and exposure limits |
| **Execution Agent** | Places and manages orders intelligently |
| **Market Monitor** | Tracks real-time alerts and threshold triggers |

**How it works:**
- Claude orchestrates these agents based on the task
- Agents collaborate to provide comprehensive analysis
- Decisions are made with full context from all agents

### 3. 💼 Portfolio Management

**Portfolio Tracking:**
- Real-time portfolio monitoring: Holdings, P&L, exposure, risk metrics
- Portfolio scanning: Analyzes current holdings for opportunities
- Market screening: Identifies new trading opportunities based on criteria
- Performance analytics: Calculates metrics, win rates, strategy effectiveness

**Key Capabilities:**
- View all positions with real-time P&L
- Track portfolio performance over time
- Analyze holdings for risk and opportunities
- Generate performance reports

### 4. 📈 Strategy Learning

**Learning Mechanisms:**
- **Daily Reflections**: Claude reviews daily performance and extracts learnings
- **Strategy Effectiveness Tracking**: Learns which strategies work and which don't
- **Monthly Capital Reset**: Resets to ₹1,00,000 monthly for performance tracking
- **Continuous Improvement**: Adapts strategies based on historical performance

**How Learning Works:**
```
Day 1: Execute trades → Track performance
Day 2: Review yesterday's trades → Extract learnings
Day 3: Apply learnings → Adjust strategies
Week 1: Analyze weekly performance → Optimize approach
Month 1: Monthly reset → Start fresh with accumulated knowledge
```

### 5. 📊 Market Intelligence

**Data Sources:**
- **News Monitoring**: Fetches and analyzes market news affecting portfolio
- **Earnings Tracking**: Monitors earnings calendar and reports
- **Technical Analysis**: Real-time indicators and trading signals
- **Fundamental Analysis**: Value, quality, and growth metrics

**Intelligence Features:**
- Automated news fetching and sentiment analysis
- Earnings calendar integration
- Real-time technical indicator calculations
- Fundamental screening based on multiple criteria

### 6. 🛡️ Safety & Risk Management

**Safety Layers:**
- **Multi-layer Guardrails**: Allowlists, hooks, approvals
- **Environment Modes**: Dry-run, paper, live (with approval)
- **Risk Limits**: Position sizing, exposure limits, stop-losses
- **Audit Trail**: Complete logging of all decisions

**Risk Controls:**
- Maximum position size limits (default: 5% of portfolio)
- Maximum single symbol exposure (default: 15%)
- Stop-loss enforcement (default: 2%)
- Daily trade limits and loss limits
- Emergency stop functionality

### 7. 🎨 Web Dashboard

**Real-Time Interface:**
- **Live Updates**: WebSocket-based real-time data streaming
- **Portfolio Overview**: Holdings, metrics, performance charts
- **AI Transparency**: View Claude's decision reasoning and thought process
- **Paper Trading Interface**: Execute trades, view history, manage accounts
- **System Health Monitoring**: Queue status, agent activity, system resources

**Dashboard Features:**
- Portfolio metrics with rolling number animations
- Performance charts (30-day history)
- Asset allocation visualization
- AI insights panel with current tasks
- Real-time connection status indicator

---

## Typical Workflow

### Morning Trading Prep (9:15 AM IST)

```
1. Market opens → System detects MARKET_OPEN event
2. Claude reviews open positions from yesterday
3. Checks earnings calendar for today
4. Analyzes market opportunities
5. Executes autonomous trades based on strategy
6. Dashboard updates in real-time via WebSocket
```

### Throughout the Day

```
- Monitors news affecting portfolio stocks
- Generates trade recommendations based on analysis
- Updates portfolio metrics in real-time
- Responds to market alerts and triggers
- Tracks position performance continuously
```

### Evening Strategy Review (4:30 PM IST)

```
1. Market closes → System detects MARKET_CLOSE event
2. Calculates daily P&L for all positions
3. Analyzes strategy effectiveness (what worked, what didn't)
4. Extracts learnings for tomorrow
5. Plans next day's strategy
6. Generates reflection report
```

### Monthly Capital Reset (1st of Month at 00:01 IST)

```
1. System checks date → Detects month change
2. Saves current performance to monthly history
3. Resets capital to ₹1,00,000
4. Generates monthly performance report
5. Claude logs monthly reflection
6. Dashboard shows monthly performance chart
```

---

## User Scenarios

### Scenario 1: Beginner Trader Learning

**User**: "I want to learn trading without losing real money"

**How Robo Trader helps:**
- Provides paper trading environment with ₹1,00,000 virtual capital
- Claude explains every decision in educational terms
- AI assistant teaches trading concepts naturally
- Monthly reset allows practice without consequences
- Tracks performance to see improvement over time

### Scenario 2: Strategy Testing

**User**: "I have a trading strategy. Can I test it?"

**How Robo Trader helps:**
- Backtest strategies using historical data
- Run strategy in paper trading mode
- Track effectiveness metrics (win rate, average P&L)
- Compare multiple strategies side-by-side
- Learn what works and what doesn't

### Scenario 3: Portfolio Analysis

**User**: "I have a portfolio. Can Claude analyze it?"

**How Robo Trader helps:**
- Natural language queries: "Analyze my portfolio"
- Technical analysis of all holdings
- Fundamental screening for opportunities
- Risk assessment with recommendations
- Generate actionable insights

### Scenario 4: Autonomous Trading

**User**: "I want Claude to trade autonomously"

**How Robo Trader helps:**
- Configure Claude to make autonomous decisions
- Set risk parameters and limits
- Monitor trades in real-time
- Review daily performance and learnings
- Adjust strategy based on results

---

## Key Differentiators

### 1. AI-First Architecture
- **Claude Orchestrates Agents**: Not hard-coded workflows, but intelligent agent coordination
- **Natural Language Everything**: Configure, trade, analyze via chat interface
- **Self-Improving**: Learns from past trades to improve strategies

### 2. Transparent Decision Making
- **Every Decision Explained**: Claude provides reasoning for every trade
- **AI Transparency Dashboard**: View Claude's thought process
- **Audit Trail**: Complete logging of all decisions and actions

### 3. Safety First
- **Multi-Layer Guardrails**: Allowlists, hooks, approvals, risk limits
- **Paper Trading First**: Test extensively before live trading
- **Emergency Controls**: Kill-switch and emergency stop functionality

### 4. Learning & Improvement
- **Daily Reflections**: Claude reviews performance daily
- **Strategy Optimization**: Adapts based on what works
- **Monthly Resets**: Fresh start with accumulated knowledge

### 5. Comprehensive Monitoring
- **Real-Time Updates**: WebSocket-based live data
- **System Health**: Monitor queues, agents, resources
- **Performance Tracking**: Detailed metrics and analytics

---

## Technology Stack

### Backend
- **Python 3.10+**: Core language
- **FastAPI**: Web framework and API
- **Claude Agent SDK**: AI integration (exclusively used)
- **SQLite**: State management and persistence
- **Event-Driven Architecture**: Internal event bus

### Frontend
- **React 18 + TypeScript**: Modern UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **WebSocket**: Real-time updates
- **React Query**: Data fetching and caching

### Infrastructure
- **Coordinator Pattern**: Service orchestration
- **Dependency Injection**: Centralized service management
- **Event Bus**: Loose coupling between services
- **Background Scheduler**: Periodic task processing

---

## Target Users

### 1. Learning Traders
- Want to learn trading without risking real money
- Need educational explanations of trading concepts
- Want to practice trading strategies safely

### 2. Strategy Developers
- Need to test trading strategies
- Want to compare multiple strategies
- Require performance tracking and analytics

### 3. Portfolio Managers
- Need portfolio analysis and insights
- Want risk assessment and recommendations
- Require automated monitoring and alerts

### 4. AI Enthusiasts
- Interested in AI-powered trading systems
- Want to experiment with Claude AI
- Explore autonomous trading capabilities

---

## Current Capabilities

### ✅ Implemented Features

- **Paper Trading Execution**: Buy/sell/close positions
- **Portfolio Analysis**: Real-time portfolio tracking and analysis
- **Market Screening**: Identify trading opportunities
- **Strategy Learning**: Daily reflections and effectiveness tracking
- **Web Dashboard**: Real-time updates and monitoring
- **Natural Language Interface**: Chat with Claude about trading
- **Multi-Agent Coordination**: Specialized agents working together
- **Risk Management**: Position sizing, stop-losses, exposure limits
- **Performance Analytics**: Metrics, charts, and reports

### 🔄 In Progress

- Advanced order types (LIMIT, STOP, STOP-LOSS)
- Options trading execution
- Historical analytics and reporting
- Advanced risk management features

### 🔜 Future Enhancements

- Multi-asset support (forex, commodities, crypto)
- Enterprise features (multi-user, compliance, audit trails)
- Advanced ML models and predictive analytics
- Mobile application and API marketplace

---

## Usage Modes

### 1. Dry-Run Mode (Safest)
- Simulates all operations
- No actual trades executed
- Perfect for testing and learning
- Safe for experimentation

### 2. Paper Trading Mode (Recommended)
- Real trading simulation with virtual money
- Tracks performance accurately
- Monthly capital reset (₹1,00,000)
- Learn from real trading scenarios

### 3. Live Trading Mode (Advanced)
- Real money trading (requires approval)
- Manual approval for each trade
- Full audit trail
- Production-ready safety mechanisms

---

## Integration Points

### Zerodha Integration
- OAuth authentication for broker access
- Real portfolio data fetching
- Live market data integration
- Order execution (in live mode)

### Claude Agent SDK
- Exclusive AI integration (no direct Anthropic API)
- Natural language processing
- Multi-agent coordination
- Strategy learning and optimization

### Market Data Sources
- News monitoring (Perplexity API)
- Earnings calendar
- Technical indicators
- Fundamental data

---

## Success Metrics

### Performance Metrics
- **Win Rate**: Percentage of profitable trades
- **Average P&L**: Average profit/loss per trade
- **Portfolio Returns**: Overall portfolio performance
- **Strategy Effectiveness**: Which strategies work best

### System Metrics
- **Decision Latency**: Time for Claude to make decisions
- **API Usage**: Token consumption and efficiency
- **System Health**: Queue status, agent activity
- **Error Rate**: System reliability and stability

### Learning Metrics
- **Strategy Evolution**: Improvement over time
- **Learning Effectiveness**: How well system adapts
- **Monthly Performance**: Trends and patterns

---

## Getting Started

### Quick Start

1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Claude API**:
   ```bash
   # Set ANTHROPIC_API_KEY in .env
   ```

3. **Start Backend**:
   ```bash
   python -m src.main --command web
   ```

4. **Start Frontend**:
   ```bash
   cd ui && npm run dev
   ```

5. **Access Dashboard**: http://localhost:3000

### First Steps

1. **Create Paper Trading Account**: Start with ₹1,00,000 virtual capital
2. **Ask Claude a Question**: "Analyze my portfolio" or "Find good stocks to buy"
3. **Monitor Dashboard**: Watch real-time updates and AI insights
4. **Review Daily Performance**: Check evening reflections and learnings
5. **Iterate and Improve**: Adjust strategies based on performance

---

## Summary

**Robo Trader** is a sophisticated AI-powered trading platform that combines:
- **Autonomous AI Decision Making** via Claude Agent SDK
- **Multi-Agent Coordination** for comprehensive analysis
- **Strategy Learning** from historical performance
- **Safety-First Design** with multiple guardrails
- **Real-Time Monitoring** via modern web dashboard
- **Natural Language Interface** for intuitive interaction

The system is designed to be an intelligent trading partner that learns and improves over time, making it perfect for traders who want to learn, test strategies, or automate their trading workflow - all while maintaining safety through paper trading first.

---

**Last Updated**: January 2025  
**Status**: Production Ready (90% Complete)  
**Version**: 2.0.0

