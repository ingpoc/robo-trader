# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Robo-trader is a sophisticated AI-powered autonomous trading system built with Python/FastAPI backend and React/TypeScript frontend. It uses the **Claude Agent SDK** for intelligent trading operations and features a **coordinator-based monolithic architecture** with event-driven communication.

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

#### 4. Three-Queue Architecture
Specialized queues for different task types:
- **Portfolio Queue**: Portfolio operations and trading
- **Data Fetcher Queue**: Market data fetching and analysis
- **AI Analysis Queue**: Claude-powered analysis and decisions

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
5. Run tests (80%+ domain logic coverage)

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

## Common Issues & Quick Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| "Port 8000 already in use" | Orphaned Python process | `lsof -ti:8000 | xargs kill -9` |
| Code changes don't take effect | Stale Python bytecode in memory | `pkill -9 python && sleep 3 && python -m src.main --command web` |
| Frontend WebSocket fails to connect | Backend not running or health check failed | Check `curl -m 3 http://localhost:8000/api/health` |
| SDK timeout errors (>60s) | Prompt too large or slow AI response | Increase timeout in `src/core/sdk_helpers.py` or optimize prompt |
| Import errors after refactoring | Cached bytecode from old structure | `find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null` |
| Tests fail intermittently | Race conditions in async code | Use condition polling instead of `time.sleep()` |

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

## Philosophy

**Core Formula**: Coordinators + DI + Events = loosely coupled, testable, scalable

**Remember**: "Focused coordinators. Injected dependencies. Event-driven communication. Rich error context. Smart scheduling. Resilient APIs. Strategy learning. Three-queue architecture. Event-driven workflows. SDK client manager. Timeout protection. No duplication. Always."