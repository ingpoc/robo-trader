# CLAUDE.md

> **Last Updated**: 2025-11-04 | **Status**: Production Ready | **Tier**: Reference

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Robo-trader is a sophisticated AI-powered autonomous trading system built with Python/FastAPI backend and React/TypeScript frontend. It uses the **Claude Agent SDK** for intelligent trading operations and features a **coordinator-based monolithic architecture** with event-driven communication.

**Key Constraint**: The codebase includes comprehensive layer-specific CLAUDE.md files for different components. Always read the relevant layer guide (`src/CLAUDE.md`, `src/core/CLAUDE.md`, `src/services/CLAUDE.md`, `src/web/CLAUDE.md`, `ui/src/CLAUDE.md`) BEFORE making changes to understand patterns and constraints.

## Quick Start Commands

### Backend Development
- **Start web server with auto-reload**: `python -m src.main --command web`
- **Start CLI interactive mode**: `python -m src.main --command interactive`
- **Run portfolio scan**: `python -m src.main --command scan`
- **Run market screening**: `python -m src.main --command screen`
- **Initialize database**: `python -m src.setup`
- **Run migrations**: `python -m src.migrations`

### Frontend Development
- **Start UI development server**: `cd ui && npm run dev`
- **Build for production**: `cd ui && npm run build`
- **Run linting**: `cd ui && npm run lint`
- **Run tests**: `cd ui && npm run test`

### Docker & Container Management
- **Start all services**: `docker-compose up -d`
- **Stop all services**: `docker-compose down`
- **View logs**: `docker-compose logs -f [service-name]`
- **Rebuild application**: `docker-compose up -d --build robo-trader-app`

### Testing & Quality
- **Run backend tests**: `pytest` or `pytest -v` for verbose output
- **Run specific test**: `pytest tests/test_portfolio.py::test_calculator -v`
- **Run frontend tests**: `cd ui && npm run test`
- **Run specific frontend test**: `npx playwright test tests/e2e/portfolio.spec.ts`

### Health Checks
- **Backend health**: `curl -m 3 http://localhost:8000/api/health`
- **Frontend health**: `curl -m 3 http://localhost:3000/health`
- **Both servers**: `curl -m 3 http://localhost:8000/api/health && curl -m 3 http://localhost:3000/health`

## Architecture Overview

### Core Architecture Pattern: Coordinator-Based Monolith

The system uses a **coordinator-based monolithic architecture** that provides better performance than microservices while maintaining modularity. Key components:

#### 1. Coordinator Layer (`src/core/coordinators/`)
Focused coordinator classes (max 150 lines each) inheriting from `BaseCoordinator`:
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `BroadcastCoordinator` - Real-time UI updates
- `PortfolioCoordinator` - Portfolio operations
- `AgentCoordinator` - Multi-agent coordination
- `MessageCoordinator` - Inter-agent communication
- `QueueCoordinator` - Queue management

#### 2. Dependency Injection Container (`src/core/di.py`)
Centralized dependency management eliminating global state:
- Modular registries for different service types
- Singleton pattern for expensive resources
- Factory pattern for stateful instances

#### 3. Event-Driven Communication (`src/core/event_bus.py`)
Services communicate via typed events using `EventType` enum:
- Rich event structure: ID, type, source, timestamp, correlation ID, data
- EventHandler pattern: Services inherit and handle specific events
- No direct service-to-service calls for cross-cutting concerns

#### 4. Sequential Queue Architecture (CRITICAL)
Specialized queues for task execution via `SequentialQueueManager`:
- **PORTFOLIO_SYNC**: Portfolio operations and trading (queue=`src/services/scheduler/queue_manager.py`)
- **DATA_FETCHER**: Market data fetching and analysis
- **AI_ANALYSIS**: Claude-powered analysis and decisions (MUST use for all Claude requests)

**Architecture Pattern**:
- **3 queues execute in PARALLEL**: PORTFOLIO_SYNC, DATA_FETCHER, and AI_ANALYSIS run simultaneously
- **Tasks WITHIN each queue execute SEQUENTIALLY**: Tasks in each queue run one-at-a-time per queue

**CRITICAL RULE**: All Claude analysis requests must be submitted to the `AI_ANALYSIS` queue as `RECOMMENDATION_GENERATION` tasks. Tasks WITHIN the AI_ANALYSIS queue execute sequentially (one-at-a-time). This prevents turn limit exhaustion when analyzing large stock portfolios (e.g., 81 stocks).

**Why**: Analyzing all 81 stocks in one Claude session hits turn limits (~15 turns before optimization completes). Queue system batches requests automatically - each task analyzes 2-3 stocks in its own session with plenty of turns available.

### AI Integration: Claude Agent SDK

**CRITICAL**: All AI functionality uses Claude Agent SDK only. NO direct Anthropic API calls.

**Authentication**: Claude Code CLI only (no API keys)

**Key Components**:
- `ClaudeSDKClientManager` - Singleton client manager for performance
- `sdk_helpers.py` - Timeout protection and error handling
- Multi-agent framework with specialized trading agents

**Usage Patterns**:
```python
# Always use client manager
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)

# Always use timeout helpers
response = await query_with_timeout(client, prompt, timeout=60)
```

**Claude Agent Turn Limits (CRITICAL)**:
- Each session has a turn limit (configurable, default ~50 in config.py)
- Each Claude interaction (analysis, optimization, data refetch) consumes 1 turn
- Analyzing 81 stocks in one session requires ~100+ turns (read, analyze, optimize earnings, optimize news, recheck)
- **Solution**: Use AI_ANALYSIS queue to process stocks in batches of 2-3 per session
- Example: 81 stocks = ~40 tasks × 2-3 stocks each = 40 queue tasks executed sequentially

**SDK Timeout Management**:
- Always wrap Claude calls with timeout protection: `await query_with_timeout(client, prompt, timeout=60.0)`
- Analysis operations may take 30-60+ seconds per batch depending on data volume
- Long-running operations use `receive_response_with_timeout()` to handle streaming responses
- Timeout values are in `src/core/sdk_helpers.py` - increase if batch analysis times out
- **Note**: Timeout protection prevents hanging threads; it doesn't extend Claude turn limits

### Database & State Management

- **Async SQLite**: All database operations are async
- **Atomic writes**: Temp file → `os.replace()` pattern
- **Connection pooling**: Managed database connections
- **Locking pattern**: Each state class uses `asyncio.Lock()` for concurrent ops
- **Per-stock state tracking**: Smart scheduling eliminates redundant API calls

### Frontend Architecture

#### Feature-Based Organization (`ui/src/features/`)
Modular features with self-contained components:
- `dashboard/` - Portfolio overview, metrics, AI insights
- `ai-transparency/` - Claude trading transparency interface
- `system-health/` - Infrastructure monitoring
- `paper-trading/` - Account management
- `news-earnings/` - News feed and analysis

#### Component Structure
- **Features**: Self-contained modules with main component + internal components
- **Shared Components**: `ui/` (primitives), `Dashboard/`, `Sidebar/`
- **State Management**: Local component state + WebSocket integration
- **Styling**: TailwindCSS + Radix UI components

#### WebSocket Integration
- **Differential updates**: Only send changed data (not full state)
- **Real-time broadcasting**: System health, portfolio updates, market data
- **Connection management**: Automatic reconnection and error handling

## Key File Locations

| Purpose | Path | Notes |
|---------|------|-------|
| Backend entry point | `src/main.py` | CLI commands: web, interactive, scan, screen |
| FastAPI application | `src/web/app.py` | Uvicorn serves this on port 8000 |
| Frontend entry point | `ui/src/main.tsx` | Vite dev server on port 5173 |
| API route handlers | `src/web/routes/` | All endpoint definitions |
| SDK client manager | `src/core/claude_sdk_client_manager.py` | CRITICAL: Singleton pattern |
| Coordinators | `src/core/coordinators/` | Service orchestration layer |
| Configuration | `src/config.py` | Loaded from `config/config.json` + env vars |
| Background scheduler | `src/core/background_scheduler/` | Task processing and monitoring |
| Services | `src/services/` | Domain services (trading, analysis, etc.) |
| Frontend features | `ui/src/features/` | Feature-based component organization |
| Docker configuration | `docker-compose.yml` | Container orchestration |
| Dependencies | `requirements.txt` | Python dependencies |

## Development Workflow

### Before Coding
1. Identify architectural pattern (coordinator, service, processor, etc.)
2. Check if similar code exists (consolidate don't duplicate)
3. Plan error scenarios (custom exceptions)
4. List event dependencies (emit/subscribe what?)

### After Coding
1. Self-review modularization limits (<350 lines, <10 methods)
2. Verify error handling completeness
3. Check async/file operation rules
4. Ensure backward compatibility
5. **CRITICAL: Verify work actually works** - Do NOT claim "work is complete" or "issue is resolved" until:
   - For backend changes: Test API endpoints, check logs, verify functionality works
   - For frontend changes: Test in browser UI, check console, verify interactions work
   - For API routes: Test authentication, error handling, endpoint responses
   - For database changes: Test migrations, verify data integrity
   - Always: Test end-to-end flow, confirm no errors in logs/console
   - If not tested: Say "I've made the changes. Please test in [UI/backend] to verify it works."
6. Run tests (80%+ domain logic coverage)

### Background Process Management (CRITICAL)

**CRITICAL RULE**: When starting servers, ALWAYS kill existing processes first.

**Clean Start Workflow**:
```bash
# Kill all background processes
pkill -9 python && pkill -9 uvicorn && pkill -9 node
sleep 3

# Clear Python bytecode cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Start fresh server
python -m src.main --command web
```

### Server Commands
- **Kill both servers**: `lsof -ti:8000 -ti:3000 | xargs kill -9`
- **Start backend**: `uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload`
- **Start frontend**: `cd ui && npm run dev`

### Live Development Rules
- Always use `--reload` (backend) + hot reload (frontend)
- After auto-restart, check server logs for errors
- Any backend endpoint change requires frontend update + test
- Test all relevant features in browser after code changes

## Code Quality Standards

### Modularization (ENFORCED)
- **Max 350 lines per file**
- **Max 10 methods per class**
- **Single responsibility per file**
- No monolithic files or god objects

### Async-First Design (MANDATORY)
- **All I/O is non-blocking**: Use `async/await`
- **Use `aiofiles` for file operations**
- **Atomic writes**: temp file → `os.replace()`
- **Timeout protection**: All async operations have cancellation handling

### Database Persistence & Backup System

**CRITICAL**: Database backups happen automatically to prevent data loss.

**Backup Features**:
- **Automatic startup backup**: Database backed up when server starts
- **Automatic shutdown backup**: Database backed up when server stops
- **Periodic backups**: Configurable interval (default 24 hours)
- **Automatic rotation**: Keeps latest 7 backups, deletes old ones automatically
- **Manual backups**: Can create on-demand via API
- **Restore capability**: Can restore to any previous backup state

**Backup API Endpoints**:
- `GET /api/backups/status` - View backup statistics & database info
- `GET /api/backups/list?hours=24` - List recent backups
- `GET /api/backups/latest` - Get latest backup info
- `POST /api/backups/create?label=manual` - Create manual backup
- `POST /api/backups/restore/{filename}` - Restore from backup file

**Configuration** (`src/config.py`):
```python
database:
  backup_enabled: true              # Enable/disable backups
  backup_interval_hours: 24         # Backup every 24 hours
  max_backup_files: 7               # Keep last 7 backups
```

**Backup Location**: `state/backups/` directory with naming pattern `robo_trader_{label}_{timestamp}.db`

**What Gets Backed Up**:
- ✅ Analysis history (all Claude analysis with recommendations)
- ✅ Trade data (execution history, decisions, outcomes)
- ✅ Portfolio state (holdings, cash, risk metrics)
- ✅ Recommendation logs (all trading recommendations)
- ✅ Fundamental analysis data
- ✅ News and earnings data

### Error Handling (MANDATORY)
- **Custom exception types**: Inherit from `TradingError`
- **Rich error context**: category, severity, code, metadata
- **Catch at entry points**: Log with structured information
- **Never expose stack traces to UI**

### Background Tasks & Timeouts (CRITICAL)
- **Wrap cancellation**: `await asyncio.wait_for(task, timeout=5.0)`
- **Error handlers on all tasks**
- **Rate limit handling with exponential backoff**
- **Emit completion/failure events**

## Testing Requirements

### Backend Tests
- **Framework**: pytest
- **Coverage target**: 80%+ on domain logic (services, coordinators)
- **Mocking strategy**: Mock external APIs (Claude SDK, market data)
- **Pattern**: One test file per service/coordinator

### Frontend Tests
- **Tool**: Playwright (`@playwright/test`)
- **Coverage**: Critical user flows (login, portfolio view, trades)
- **Location**: `ui/tests/` or inline with components

### Integration Tests
- **Scope**: End-to-end coordinator workflows
- **Approach**: Test full flow with mocked externals
- **Verification**: Event emissions, state transitions, error handling

## Configuration Management

### Environment Configuration
- **Config file**: `config/config.json`
- **Environment variables**: Override config values
- **Database**: SQLite for development, PostgreSQL for production
- **API Keys**: Environment variables only (never hardcoded)

### Environment Modes
- **`dry-run`**: Simulate everything (safe for testing)
- **`paper`**: Paper trading (requires paper account)
- **`live`**: Real money (requires approval for each trade)

### Feature Management
- **Dynamic feature flags**: Runtime system behavior control
- **Dependency validation**: Check dependencies before activation
- **Event-driven changes**: Broadcast feature status via events

## Database & State Management Patterns

### Safe Database Access with Locking

**Rule**: Never access database directly via `config_state.db.connection.execute()`. Use locked state methods instead.

**Why**: Direct connection access bypasses locking, causing database contention and blocking other operations during long-running processes (e.g., 30+ second Claude analysis).

✅ **DO**:

```python
# Use safe locked methods from ConfigurationState
success = await config_state.store_analysis_history(symbol, timestamp, json.dumps(analysis))
success = await config_state.store_recommendation(symbol, rec_type, score, reasoning, analysis_type)
```

❌ **DON'T**:

```python
# Never direct access - causes contention
await config_state.db.connection.execute(...)
await config_state.db.connection.commit()
```

### Portfolio Analysis Scheduling

**Rule**: Analyze stocks with no prior analysis first, then oldest analysis, then skip.

**Why**: Smart scheduling prevents redundant analyses and focuses computational effort on unknowns.

Implement in `_get_stocks_with_updates()`:

```python
# Priority: unanalyzed > oldest analysis > skip
for stock in portfolio:
    if not has_analysis(stock):
        return stock  # Highest priority
    elif analysis_age(stock) > threshold:
        return stock  # Medium priority
```

### AI Transparency Data Flow

**Rule**: Analysis results must flow through AnalysisLogger + database for proper UI display.

**Flow**:

1. `PortfolioIntelligenceAnalyzer` generates analysis
2. Calls `config_state.store_analysis_history()` with locked access
3. `AnalysisLogger` reads from database via API endpoint
4. `/api/claude/transparency/analysis` retrieves and formats data
5. UI tabs display in correct categories

**Key**: Don't skip database persistence thinking logging is optional - UI depends on it.

### Queue-Based Claude Analysis Pattern (BEST PRACTICE)

**Rule**: All Claude analysis requests must go through the AI_ANALYSIS queue, NOT direct service calls.

**Why This Pattern**:
- Prevents turn limit exhaustion (81 stocks in one session = failure)
- Ensures sequential execution (only one analysis at a time)
- Fair resource allocation (FIFO queue fairness)
- Graceful error handling (task retries via queue)

**Implementation**:
```python
# WRONG - Direct call exhausts turns
result = await analyzer.analyze_portfolio_intelligence(agent_name="scan", symbols=None)

# CORRECT - Queue the analysis as a task
await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"agent_name": "scan", "symbols": None},
    priority=7
)
# Task handler executes analysis and logs results to transparency
```

**Task Handler Registration**:
```python
# In task service initialization
task_service.register_handler(
    TaskType.RECOMMENDATION_GENERATION,
    async def handle_recommendation_generation(task: SchedulerTask):
        analyzer = await container.get("portfolio_intelligence_analyzer")
        await analyzer.analyze_portfolio_intelligence(
            agent_name=task.payload["agent_name"],
            symbols=task.payload.get("symbols")
        )
```

**Result**: Even 81 stocks = ~40 tasks × 2-3 stocks each, executed sequentially with full Claude session turns for optimization and refetching.

## Common Issues & Quick Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| "Port 8000 already in use" | Orphaned Python process | `lsof -ti:8000 \| xargs kill -9` |
| Code changes don't take effect | Stale Python bytecode in memory | `pkill -9 python && sleep 3 && python -m src.main --command web` |
| Frontend WebSocket fails to connect | Backend not running or health check failed | Check `curl -m 3 http://localhost:8000/api/health` |
| SDK timeout errors (>60s) | Prompt too large or slow AI response | Increase timeout in `src/core/sdk_helpers.py` or optimize prompt |
| Import errors after refactoring | Cached bytecode from old structure | `find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null` |
| Tests fail intermittently | Race conditions in async code | Use condition polling instead of `time.sleep()` |
| Pages freeze during analysis | Database lock contention from direct access | Use `config_state.store_*()` locked methods only |
| Analysis not showing in AI Transparency tabs | Analysis not persisted to database | Verify analysis is saved via `store_analysis_history()` and logged to `analysis_history` table |
| Database lost after restart | Backups disabled or corrupted | Check `/state/backups/` for latest backup, restore via `POST /api/backups/restore/{filename}` |
| Backups not being created | Backup scheduler not started | Check `backup_enabled: true` in config, restart backend server |
| Need to restore from backup | Previous backup available | Retrieve list via `GET /api/backups/list?hours=8760`, restore via API |
| Claude analysis hits `error_max_turns` | Analyzing too many stocks in one session (e.g., 81 stocks = ~100+ turns needed) | Submit analysis to AI_ANALYSIS queue instead of calling directly. Each queue task analyzes 2-3 stocks in separate session |
| All analysis requests block each other | Analysis called directly instead of queued | Use `SequentialQueueManager`: queue as `RECOMMENDATION_GENERATION` tasks to `AI_ANALYSIS` queue |

### Backend Health Check Pattern

**Rule**: When backend appears unresponsive, check health endpoint first (5 second timeout).

```bash
# Quick health check
curl -m 3 http://localhost:8000/api/health

# If no response, kill and restart
lsof -ti:8000 | xargs kill -9
sleep 2
python -m src.main --command web
```

### Background Process Limits

**Rule**: Maximum 2 background processes. Before starting new process, verify existing ones are necessary.

```bash
# Check running processes
ps aux | grep -E "python|node|uvicorn"

# Kill unnecessary processes
pkill -9 python  # Kill all Python processes
pkill -9 node    # Kill all Node processes
```

**Why**: Multiple orphaned processes = port conflicts, memory leaks, hard-to-debug state issues.

## Container Networking (CRITICAL)

**Rule**: All inter-service communication uses container names. NEVER `.orb.local` DNS names.

**Format**: `http://robo-trader-<service-name>:<port>` (e.g., `http://robo-trader-postgres:5432`)

**Why**: `.orb.local` only works in OrbStack. Container names work everywhere (Docker, Compose, OrbStack).

## API Contract Sync (MANDATORY)

**Rule**: Any backend endpoint/response change requires frontend update + test.

**Why**: Prevents "works in backend tests, but API returns field UI doesn't expect."

## End-to-End Browser Testing (MANDATORY)

After any backend or frontend code change:

1. Restart relevant server(s)
2. Test all relevant features in browser
3. Only mark complete after browser test passes

## Debugging Sequence (FOLLOW THIS)

**Order**: Browser → Frontend Logs → Backend Logs → Health Check → Fix → Restart → Retest

**Browser Problem** → Check:

1. Browser DevTools (console errors, network failures)
2. Backend logs (tail for errors/warnings)
3. Health endpoint: `curl -m 3 http://localhost:8000/api/health`

## When in Doubt

1. Read architecture documentation in CLAUDE.md files
2. Find similar pattern in codebase
3. Check: Single responsibility? Split if multiple
4. Modularization > monolithic code
5. Async-first. Error-handling mandatory. Testing important
6. Pattern emerges? Update relevant CLAUDE.md

## Database Backup & Recovery

### Automatic Backup Management

The system automatically manages database backups to ensure critical data (analysis, trades, recommendations) is never lost.

**Backup Timeline**:
- **On startup**: Full backup with `startup` label
- **On shutdown**: Full backup with `shutdown` label
- **Every 24 hours**: Periodic backup with `periodic` label
- **Manual**: On-demand backups via API with custom labels

**Backup Rotation**:
- Latest 7 backups kept automatically
- Older backups deleted to conserve disk space
- Each backup ~0.7-1.5 MB depending on data volume

### Manual Backup Operations

**Create backup before major operations**:
```bash
curl -X POST 'http://localhost:8000/api/backups/create?label=before_deploy'
```

**List all recent backups**:
```bash
curl 'http://localhost:8000/api/backups/list?hours=168'  # Last 7 days
```

**Get backup statistics**:
```bash
curl 'http://localhost:8000/api/backups/status'
```

**Restore from backup**:
```bash
# First, list available backups
curl 'http://localhost:8000/api/backups/list?hours=8760'

# Then restore (server restart required afterward)
curl -X POST 'http://localhost:8000/api/backups/restore/robo_trader_startup_20251101_191015.db'
```

### Backup Storage

**Location**: `state/backups/` directory in project root

**File format**: `robo_trader_{label}_{YYYYMMDD_HHMMSS}.db`

**Examples**:
- `robo_trader_startup_20251101_191015.db`
- `robo_trader_shutdown_20251102_023045.db`
- `robo_trader_before_deploy_20251102_150230.db`

## Philosophy

**Core Formula**: Coordinators + DI + Events = loosely coupled, testable, scalable

**Remember**: "Focused coordinators. Injected dependencies. Event-driven communication. Rich error context. Smart scheduling. Resilient APIs. Strategy learning. Three-queue architecture. Event-driven workflows. SDK client manager. Timeout protection. No duplication. Always."

**Data Safety**: "Automatic backups on startup/shutdown. Periodic backups every 24 hours. Automatic rotation keeps latest 7 backups. Manual backups anytime via API. All critical data persisted and recoverable."
