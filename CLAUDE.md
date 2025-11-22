# CLAUDE.md - Robo Trader Project Guide

**Last Updated**: 2025-11-22 | **Status**: Production Ready

## Quick Commands

**Backend**: `python -m src.main --command web` | **Frontend**: `cd ui && npm run dev` | **Health**: `curl -m 3 http://localhost:8000/api/health`

## Architecture Summary

- **Pattern**: Coordinator-based monolith (better perf than microservices)
- **AI**: Claude Agent SDK ONLY (no direct API calls)
- **Communication**: Event-driven via EventBus
- **Queues**: 3 parallel (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS), sequential tasks within each
- **DI**: Centralized container in `src/core/di.py`

## Critical Rules

| Rule | Reason |
|------|--------|
| **Queue AI analysis** | Prevents turn limit exhaustion on large portfolios |
| **Use locked state methods** | Prevents "database is locked" errors |
| **Max 150 lines per coordinator** | Maintainability, single responsibility |
| **Event-driven comms** | Loose coupling, no direct service calls |
| **Async/await throughout** | Non-blocking, proper concurrency |

## Task Payloads (Portfolio Analysis Coordinator)

When queuing analysis tasks, MUST include symbol:
```python
await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"agent_name": "scan", "symbols": ["AAPL"]}  # Symbol REQUIRED
)
```

## Layer-Specific Guides

Read BEFORE modifying code in each layer:
- **Backend Architecture**: `src/CLAUDE.md`
- **Core Infrastructure**: `src/core/CLAUDE.md`
- **Services**: `src/services/CLAUDE.md`
- **Web Layer**: `src/web/CLAUDE.md`
- **Database Locking**: `src/core/CLAUDE.md` (CRITICAL section)

## Development Workflow

1. **Identify layer** → Read relevant CLAUDE.md
2. **Check patterns** → Find similar code in codebase
3. **Verify constraints** → Check modularization, async, error handling
4. **Test end-to-end** → Browser test for UI changes
5. **Check logs** → Verify no errors in backend/frontend logs

## Common Issues & Fixes

| Error | Fix |
|-------|-----|
| "database is locked" | Use `config_state.store_*()` locked methods, never direct connection |
| "Queue execution already in progress" | Remove "limit" parameter from `get_pending_tasks()` |
| "Missing symbol in analysis task" | Include "symbols" key in task payload |
| "Task execution timeout" | Increase timeout from 300s to 900s for AI_ANALYSIS queue |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |

## File Locations

| Component | Path | Purpose |
|-----------|------|---------|
| API routes | `src/web/routes/` | FastAPI endpoints |
| Coordinators | `src/core/coordinators/` | Service orchestration |
| Services | `src/services/` | Domain business logic |
| State management | `src/core/database_state/` | Database access with locking |
| Queue system | `src/services/scheduler/` | Task processing |
| Frontend features | `ui/src/features/` | Feature-based UI components |

## Database Backup & Recovery

- **Automatic backups**: Startup, shutdown, every 24h
- **List backups**: `curl http://localhost:8000/api/backups/list?hours=168`
- **Restore**: `curl -X POST http://localhost:8000/api/backups/restore/{filename}`

## Pre-Deployment Checklist

- [ ] Backend health: `curl -m 3 http://localhost:8000/api/health` → 200
- [ ] Frontend health: `curl -m 3 http://localhost:3000/health` → 200
- [ ] Tests pass: `pytest` (backend) + `npm run test` (frontend)
- [ ] No type errors: `npx tsc --noEmit` (if using TypeScript)
- [ ] Logs clean: No ERROR or unhandled exceptions in logs
