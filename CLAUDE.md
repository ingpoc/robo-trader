# Robo Trader - Quick Guide

**Backend**: `python -m src.main --command web` | **Frontend**: `cd ui && npm run dev` | **Health**: `curl -m 3 http://localhost:8000/api/health`

## Architecture
- Coordinator-based monolith (async/await throughout)
- Claude Agent SDK only (no direct API calls)
- Event-driven via EventBus
- 3 queues: PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS (parallel, sequential tasks within)

## Component Locations (.claude/ Shared by Claude Code + Agent SDK)

The `.claude/` folder is shared by both Claude Code and the Agent SDK bot:

| Component | Location | Discovered By |
|-----------|----------|---------------|
| Skills | `.claude/skills/SKILL_NAME/SKILL.md` | Both Claude Code + Agent SDK bot |
| Agents | `.claude/agents/AGENT_NAME.md` | Agent SDK bot |
| Hooks | `.claude/settings.json` + `.claude/hooks/` | Both (validation) |
| MCP Servers | `.mcp.json` at root | Both (different servers) |
| Internal code | `src/core/`, `src/services/` | Not auto-discovered |
| Dev debugging | `shared/robotrader_mcp/` | Claude Code only |

## Critical Rules
| Rule | Reason |
|------|--------|
| Queue AI tasks | Prevent token exhaustion on large portfolios |
| Use locked state methods | Prevent "database is locked" |
| Max 150 lines/coordinator | Maintainability, single responsibility |
| Event-driven comms | No direct service calls, loose coupling |
| Always async/await | Non-blocking, proper concurrency |

## Task Payload Example
Updated for STOCK_ANALYSIS with batch processing (max 3 stocks):
```
payload={"agent_name": "scan", "symbols": ["AAPL", "GOOGL", "MSFT"]}
```

## Layer-Specific Guides
Read before modifying: `src/CLAUDE.md`, `src/core/CLAUDE.md`, `src/services/CLAUDE.md`, `src/web/CLAUDE.md`
MCP integration: `.claude/INTEGRATION_GUIDE.md` for workflow mappings

## Common Issues & Fixes
| Error | Fix |
|-------|-----|
| database is locked | Use `config_state.store_*()`, not direct connection |
| Queue execution in progress | Remove "limit" from `get_pending_tasks()` |
| Missing symbol in task | Add "symbols" key to payload (max 3 stocks) |
| Task timeout (>180s) | Check AI analysis complexity, consider single stock per task |
| Queue capacity (20) exceeded | Wait for tasks to complete before adding more |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |

## File Locations
`src/web/routes/` (API) | `src/core/coordinators/` | `src/services/` | `src/core/database_state/` (state)

## Pre-Deploy
- Health: Backend (8000) + Frontend (3000) → 200
- Tests: `pytest` + `npm run test` pass
- Logs: No ERROR/exceptions
- Always restart backend after code changes