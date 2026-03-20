# Robo Trader Roadmap

This roadmap is repo-local. It tracks implementation direction for this codebase only.

## Mission

Build a trustworthy AI-assisted trading platform with:

- paper-trading-first execution
- transparent AI reasoning and operational visibility
- strong guardrails before any live-trading expansion

## Current State

- Backend: coordinator-based FastAPI monolith with event bus, queues, persistent state, and MCP surfaces.
- Frontend: React/Vite operator console for dashboard, paper trading, AI transparency, configuration, and system health.
- Maturity: paper trading and observability are stronger than live trading; several live integrations still rely on mocks, fallbacks, or partial wiring.

## Near-Term Priorities

1. Stabilize paper-trading workflows end to end.
2. Reduce mock and fallback paths in critical analysis and execution flows.
3. Make queue, scheduler, and AI transparency surfaces consistent and testable.
4. Tighten repo governance so docs, issues, and durable memory stop drifting.

## Delivery Streams

### Trading Reliability

- Harden paper trade execution, positions, and performance accounting.
- Close gaps between API responses, stored state, and UI displays.
- Improve safety gates around autonomous or scheduled trading actions.

### AI Operations

- Make Claude-agent sessions, recommendations, and transparency logs easier to inspect.
- Standardize prompt and decision logging.
- Separate aspirational live-autonomy features from production-ready paper-trading flows.

### Platform Health

- Simplify queue and scheduler operations.
- Improve health reporting for backend, frontend, auth, and integrations.
- Keep MCP and auth dependencies explicit and reproducible.

### Product Clarity

- Keep the repo narrative honest: paper trading is the default operating path.
- Document what is real, what is simulated, and what is still being hardened.
- Keep repo-local docs aligned with the actual routed UI and backend surfaces.

## Exit Signals For The Next Governance Cycle

- Every material feature has a Linear issue with acceptance criteria.
- Durable decisions are linked from Notion and, when architecture-shaping, captured locally under `docs/adrs/`.
- Workflow docs remain the single repo-local source for issue, memory, and MCP/auth handling.
