# Robo Trader - Quick Guide

**Backend**: `python -m src.main --command web` | **Frontend**: `cd ui && npm run dev` | **Health**: `curl -m 3 http://localhost:8000/api/health`

## Architecture
- Coordinator-based monolith (async/await throughout)
- Claude Agent SDK only (no direct API calls)
- Event-driven via EventBus
- 3 queues: PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS (parallel, sequential tasks within)

## Critical Rules
| Rule | Reason |
|------|--------|
| Queue AI tasks | Prevent token exhaustion on large portfolios |
| Use locked state methods | Prevent "database is locked" |
| Max 150 lines/coordinator | Maintainability, single responsibility |
| Event-driven comms | No direct service calls, loose coupling |
| Always async/await | Non-blocking, proper concurrency |

## Task Payload Example
Include symbols in AI_ANALYSIS tasks:
```
payload={"agent_name": "scan", "symbols": ["AAPL"]}
```

## Layer-Specific Guides
Read before modifying: `src/CLAUDE.md`, `src/core/CLAUDE.md`, `src/services/CLAUDE.md`, `src/web/CLAUDE.md`

## Common Issues & Fixes
| Error | Fix |
|-------|-----|
| database is locked | Use `config_state.store_*()`, not direct connection |
| Queue execution in progress | Remove "limit" from `get_pending_tasks()` |
| Missing symbol in task | Add "symbols" key to payload |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |

## File Locations
| Component | Path |
|-----------|------|
| API routes | `src/web/routes/` |
| Coordinators | `src/core/coordinators/` |
| Services | `src/services/` |
| State mgmt | `src/core/database_state/` |
| Queue system | `src/services/scheduler/` |

## Pre-Deploy
- Backend: `curl -m 3 http://localhost:8000/api/health` → 200
- Frontend: `curl -m 3 http://localhost:3000/health` → 200
- Tests: `pytest` + `npm run test`
- Logs: No ERROR or exceptions
