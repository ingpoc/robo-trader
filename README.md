# Robo Trader

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ingpoc/robo-trader)

Robo Trader is a paper-trading-first swing-trading operator console. It uses Claude Code / Claude Agent SDK for research and decision support, and native backend services for execution truth, positions, P&L, and capability state.

## Mission

Robo Trader exists to turn a retail trading workflow into an AI-assisted operating system that is:

- safer than ad hoc manual execution
- more observable than a black-box bot
- paper-trading-first until execution, risk, and monitoring behavior are trustworthy

## Active Product Surface

The routed product is intentionally narrow:

- `Overview`
- `Paper Trading`
- `System Health`
- `Configuration`

`News & Earnings` and `AI Transparency` now live inside `Paper Trading` as workflow tabs, not as separate products.

## Product Rules

- Paper trading is the only active execution claim.
- Claude handles cognition, not portfolio truth.
- The app should fail loud when required dependencies are missing.
- Mission-critical paths must not silently substitute CSV, mock success, or synthetic healthy states.
- Dark theme is intentionally unsupported.

## In Scope

- paper-trading accounts, positions, and P&L
- paper trade execution and review
- candidate discovery from news/earnings and related research inputs
- Claude-assisted research, decision support, and review traces
- system health, readiness, and operator-visible blockers
- Zerodha-backed market data where the real dependency path is available

## Not An Active Claim

- production-ready live trading
- generic multi-agent platform behavior outside the paper-trading loop
- broker execution that silently falls back to mocks
- route-level product surfaces outside the 4-screen operator console

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Claude Code CLI authenticated with your subscription account

### Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
claude auth login
```

Set your default Claude model in `~/.claude/settings.json`:

```json
{
  "model": "haiku"
}
```

### Frontend setup

```bash
cd ui
npm install
```

### Local development

Backend:

```bash
python -m src.main --command web --host 127.0.0.1 --port 8010
```

Frontend:

```bash
cd ui
VITE_PROXY_TARGET=http://127.0.0.1:8010 \
VITE_WS_TARGET=ws://127.0.0.1:8010 \
npm run dev -- --host 127.0.0.1 --port 3001
```

Then open `http://127.0.0.1:3001`.

## Verification

Focused backend verification:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin \
  tests/test_dashboard_operator_view.py \
  tests/test_evening_performance_review.py \
  tests/test_paper_trading_store_authority.py \
  tests/test_status_truthfulness.py \
  tests/test_claude_transparency_truthfulness.py \
  tests/test_claude_paper_trading_coordinator.py -q
```

## Key Docs

- [Mission](docs/reference/MISSION.md)
- [Repo Scope](docs/reference/REPO-SCOPE.md)
- [Roadmap](ROADMAP.md)
- [Mission-Cut ADR](docs/adrs/0001-mission-cut-paper-trading-core.md)
- [Browser Testing Control Plane](docs/workflow/browser-testing-control-plane.md)
- [Zerodha Broker Control Plane](docs/workflow/zerodha-broker-control-plane.md)
- [Codex Runtime Control Plane](docs/workflow/codex-runtime-control-plane.md)
- [Repo Governance](docs/workflow/repo-governance.md)
- [Linear Issue Control Plane](docs/workflow/linear-issue-control-plane.md)
- [Notion Memory Control Plane](docs/workflow/notion-memory-control-plane.md)
- [MCP/Auth Bootstrap](docs/workflow/mcp-auth-bootstrap.md)

## Current Reality

- The active operator path is centered on paper-trading truth.
- Claude readiness and Zerodha readiness are surfaced as explicit capabilities.
- Live trading remains out of scope until the paper-trading and reconciliation path is trustworthy.
