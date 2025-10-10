# Robo Trader - Claude-Powered Autonomous Trading System

A sophisticated multi-agent trading platform built with **Claude Agent SDK** that brings the full power of AI to retail trading.

## 🎯 Vision

Transform trading from manual analysis to **collaborative intelligence** where Claude AI acts as your expert trading partner - analyzing markets, managing risk, executing trades, and continuously learning from outcomes.

## ✨ Features

### 🤖 Multi-Agent Architecture
- **Portfolio Analyzer**: Real-time P&L, exposure, and risk monitoring
- **Technical Analyst**: RSI, MACD, Bollinger Bands, EMA calculations
- **Fundamental Screener**: Value, quality, and growth filtering
- **Risk Manager**: Position sizing, stop-loss, exposure limits
- **Execution Agent**: Intelligent order placement and management
- **Market Monitor**: Real-time alerts and threshold tracking

### 🧠 Claude-Powered Intelligence
- Natural language interaction with your portfolio
- AI-driven risk assessments with reasoning
- Educational explanations for every decision
- Strategy suggestions and optimization
- Conversational approvals
- Self-improving through analysis of past trades

### 🛡️ Safety First
- Multi-layer guardrails (allowlists, hooks, approvals)
- Environment modes: dry-run, paper, live
- PreToolUse hooks for policy enforcement
- Idempotent order placement
- Audit trail for all decisions
- Kill-switch for emergencies

### 🎨 Modern Web UI
- Swiss minimalist design
- Real-time WebSocket updates
- GSAP animations for smooth UX
- Responsive layout
- Dark mode support

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.10+
python --version

# Install Claude Agent SDK
pip install claude-agent-sdk anthropic

# Install dependencies
pip install -r requirements.txt
```

### Setup

1. **Clone and configure**:
```bash
git clone <your-repo>
cd robo-trader
cp .env.example .env
```

2. **Set your Claude API key** (REQUIRED):
```bash
# Edit .env file
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

Get your key from: https://console.anthropic.com/

3. **Optional: Add Zerodha credentials** (for live trading):
```bash
ZERODHA_API_KEY=your_key
ZERODHA_API_SECRET=your_secret
```

4. **Start the system**:
```bash
# Web UI (recommended)
python -m src.main --command web

# OR CLI mode
python -m src.main --command interactive
```

5. **Access dashboard**: http://localhost:8000

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| [`.docs/README.md`](.docs/README.md) | Documentation index and quick start |
| [`.docs/IMPLEMENTATION.md`](.docs/IMPLEMENTATION.md) | Current implementation status |
| [`.docs/CLAUDE_SDK_GUIDE.md`](.docs/CLAUDE_SDK_GUIDE.md) | **How to maximize Claude SDK power** ⭐ |
| [`.docs/ROADMAP.md`](.docs/ROADMAP.md) | Development roadmap |
| [`.docs/API.md`](.docs/API.md) | API reference |
| [`.docs/ANALYSIS.md`](.docs/ANALYSIS.md) | Gap analysis |

## 🎓 How It Works

### 1. Claude Orchestrates Everything
```
User Query → Claude Orchestrator → Appropriate Agents → Claude Decision → Action
```

### 2. Natural Language Trading
```
You: "Should I buy RELIANCE right now?"

Claude: "Let me analyze RELIANCE for you...
         [uses technical_analysis tool]
         [uses fundamental_screening tool]
         [uses risk_assessment tool]
         
         Based on analysis:
         - RSI: 68.2 (approaching overbought)
         - MACD showing bullish cross
         - Good value metrics
         
         Recommendation: Wait for pullback to ₹2,450
         or buy small position now with tight stop at ₹2,520"
```

### 3. Collaborative Decision Making
```
System: "I found a good opportunity in TCS:
         - Strong technicals (RSI: 45, MACD bullish)
         - Entry: ₹3,850
         - Stop: ₹3,800
         - Target: ₹4,000
         - Size: 50 shares (₹1,92,500)
         
         This matches your conservative profile.
         Approve this trade?"

You: "Yes, but reduce size by 30%"

Claude: "Adjusted to 35 shares (₹1,34,750).
         Executing now..."
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Claude AI (Intelligence Layer)         │
│  - Decision Making                      │
│  - Risk Assessment                      │
│  - Natural Language Understanding       │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│  Orchestrator (Coordination)            │
│  - Agent Routing                        │
│  - Tool Permissions                     │
│  - Safety Hooks                         │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
┌───────▼──────┐ ┌─────▼────────┐
│  Agents MCP  │ │  Broker MCP  │
│  - Analysis  │ │  - Orders    │
│  - Screening │ │  - Portfolio │
│  - Risk      │ │  - Quotes    │
└──────────────┘ └──────────────┘
```

## 🔧 Configuration

Edit [`config/config.json`](config/config.json):

```json
{
  "environment": "dry-run",  // Start here for safety
  
  "risk": {
    "max_position_size_percent": 5.0,
    "max_single_symbol_exposure_percent": 15.0,
    "stop_loss_percent": 2.0
  },
  
  "execution": {
    "auto_approve_paper": true,
    "require_manual_approval_live": true
  }
}
```

**Environments**:
- `dry-run`: Simulate everything (safe for testing)
- `paper`: Paper trading (requires paper account)
- `live`: Real money (requires approval for each trade)

## 🎮 Usage Examples

### Web UI
```bash
# Start web server
python -m src.main --command web

# Access at http://localhost:8000
# - View portfolio
# - Run scans
# - Execute trades
# - Monitor agents
```

### CLI
```bash
# Portfolio scan
python -m src.main --command scan

# Market screening
python -m src.main --command screen

# Interactive mode
python -m src.main --command interactive
>>> scan
>>> screen
>>> help me find a good stock to buy
```

### Programmatic
```python
from src.config import load_config
from src.core.orchestrator import initialize_orchestrator

config = load_config()
orchestrator = await initialize_orchestrator(config)
await orchestrator.start_session()

# Natural language query
responses = await orchestrator.process_query(
    "Analyze my portfolio and suggest 3 high-conviction trades"
)

# Claude will:
# 1. Call analyze_portfolio tool
# 2. Call fundamental_screening tool
# 3. Call technical_analysis for each candidate
# 4. Call risk_assessment for sizing
# 5. Provide recommendations with reasoning
```

## 🎯 What Makes This "Truly Claude-Powered"

Unlike basic LLM integrations, this system:

1. **Claude Orchestrates Agents** - Not hard-coded workflows
2. **Natural Language Everything** - Configure, trade, analyze via chat
3. **AI-Driven Risk** - Claude assesses risk, not just rule checks
4. **Continuous Learning** - Claude analyzes past trades to improve
5. **Transparent Decisions** - Every action explained by Claude
6. **Collaborative Trading** - Human + AI partnership

See [`.docs/CLAUDE_SDK_GUIDE.md`](.docs/CLAUDE_SDK_GUIDE.md) for advanced patterns.

## 📊 Current Status

✅ **Implemented** (60% Complete):
- Multi-agent architecture
- Claude Agent SDK integration
- MCP servers (broker + agents)
- Safety hooks and guardrails
- Web UI with real-time updates
- State management
- Risk validation
- Portfolio analytics

⏳ **In Progress**:
- Enhanced streaming with Claude
- Approval workflow UI
- Full ticker WebSocket

🔜 **Planned**:
- Web UI authentication
- Enhanced checkpointing
- Chat interface
- Strategy learning loop
- Advanced error handling

See [`ROADMAP.md`](.docs/ROADMAP.md) for details.

## 🔒 Security

- ✅ API keys in environment variables (not in code)
- ✅ Tool allowlists prevent unauthorized actions  
- ✅ PreToolUse hooks validate all operations
- ✅ Environment modes control execution permissions
- ⏳ Web UI authentication (planned)
- ⏳ User role management (planned)

## 🧪 Testing

```bash
# Run in dry-run mode (safe)
python -m src.main --command scan --dry-run

# Test portfolio scan
python -m src.main --command scan

# Test market screening
python -m src.main --command screen
```

Unit tests coming soon - see [`ROADMAP.md`](.docs/ROADMAP.md).

## 🤝 Contributing

This is an autonomous trading system. Please:
1. Always test in `dry-run` mode first
2. Add comprehensive tests for new features
3. Follow the safety-first approach
4. Document all changes

## ⚠️ Disclaimer

**This is experimental trading software. Use at your own risk.**

- Start with `dry-run` mode
- Test thoroughly in `paper` mode before live
- Never risk more than you can afford to lose
- Understand all risks before live trading
- Comply with all applicable regulations

## 📝 License

See LICENSE file.

## 🙏 Acknowledgments

Built with:
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) by Anthropic
- [Zerodha Kite Connect](https://kite.trade/docs/connect/) for broker integration
- FastAPI, GSAP, and other open-source libraries

---

**Ready to trade with AI?** Start with the [Quick Start](#-quick-start) guide above!