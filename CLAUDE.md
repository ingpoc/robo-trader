# Robo Trader Project - Claude Development Memory

> **Project Memory**: Automatically loaded by Claude Code. Contains permanent development rules and architectural patterns that remain consistent as code evolves.

> **Last Updated**: 2025-10-31 | **Status**: Production Ready - Configuration management enhanced with database-backed prompts

**Architecture Reference**: See @documentation/ARCHITECTURE_PATTERNS.md for detailed patterns and implementation guidelines.

## Contents

- [Claude Agent SDK Architecture](#claude-agent-sdk-architecture-critical)
- [Core Architectural Patterns](#core-architectural-patterns-29-patterns)
- [Code Quality Standards](#code-quality-standards)
- [Development Workflow](#development-workflow)
- [Quick Reference](#quick-reference---what-to-do)
- [Pre-Commit Checklist](#pre-commit-checklist)
- [When in Doubt](#when-in-doubt)

## Claude Agent SDK Architecture (CRITICAL)

### SDK-Only Architecture (MANDATORY)

**CRITICAL RULE**: This application uses **ONLY** Claude Agent SDK for all AI functionality. No direct Anthropic API calls are permitted.

**Authentication**: Claude Code CLI authentication only (no API keys)
**Implementation**: All AI features use `ClaudeSDKClient` and MCP server pattern
**Tools**: Registered via `@tool` decorators in MCP servers
**Sessions**: Managed through SDK client lifecycle

**✅ CORRECT - SDK Implementation with Client Manager:**
```python
from claude_agent_sdk import ClaudeAgentOptions, tool
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

# MCP server with tools
@tool("analyze_portfolio")
async def analyze_portfolio_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    # Tool implementation
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

# Use client manager (singleton pattern) - CRITICAL for performance
client_manager = await ClaudeSDKClientManager.get_instance()
options = ClaudeAgentOptions(mcp_servers={"trading": mcp_server})
client = await client_manager.get_client("trading", options)

# Use timeout helpers for all SDK operations
await query_with_timeout(client, prompt, timeout=60.0)
async for response in receive_response_with_timeout(client, timeout=120.0):
    # Process response
```

**❌ VIOLATION - Direct API Usage:**
```python
# NEVER DO THIS
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key="sk-ant-...")
response = await client.messages.create(...)
```

**Why SDK-Only?**
- Consistent authentication via Claude CLI
- Proper tool execution patterns
- Built-in session management
- MCP server standardization
- No API key management complexity
- Official Claude integration patterns

**Verification**: All AI code must import from `claude_agent_sdk` only. Direct `anthropic` imports are forbidden.

### SDK Client Management (CRITICAL PERFORMANCE)

**CRITICAL RULE**: Always use `ClaudeSDKClientManager` singleton for client reuse. Each client instance has ~12s startup overhead.

**Before (Bad)**:
```python
# Each service creates its own client - wastes 84s startup time
self.client = ClaudeSDKClient(options=options)
await self.client.__aenter__()
```

**After (Good)**:
```python
# Use singleton client manager - saves ~70 seconds startup time
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)
```

**Client Types**:
- `"trading"` - For trading operations with MCP tools
- `"query"` - For general queries without tools
- `"conversation"` - For conversational interactions

**Performance Impact**: 7+ clients × 12s = 84s wasted → 2-3 shared clients × 12s = 24-36s startup time

### SDK Timeout Handling (MANDATORY)

**CRITICAL RULE**: All SDK operations must use timeout wrappers. Never call `client.query()` or `client.receive_response()` directly.

**✅ CORRECT**:
```python
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

await query_with_timeout(client, prompt, timeout=60.0)
async for response in receive_response_with_timeout(client, timeout=120.0):
    # Process response
```

**❌ VIOLATION**:
```python
# NEVER do this - can hang indefinitely
await client.query(prompt)
async for response in client.receive_response():
    # Process response
```

**Timeout Values**:
- Query timeout: 60 seconds (default)
- Response timeout: 120 seconds (for multi-turn conversations)
- Trading sessions: 90s query, 180s response (longer for complex operations)

### SDK Error Handling (MANDATORY)

**CRITICAL RULE**: Handle all SDK error types explicitly. Use `sdk_helpers` wrappers which handle all error types automatically.

**Error Types Handled**:
- `CLINotFoundError` - CLI not installed (non-recoverable)
- `CLIConnectionError` - Connection issues (retry with backoff)
- `ProcessError` - Process failures (check exit code)
- `CLIJSONDecodeError` - JSON parsing errors (retry)
- `ClaudeSDKError` - Generic SDK errors (retry if recoverable)

**✅ CORRECT**:
```python
from src.core.sdk_helpers import query_with_timeout

try:
    await query_with_timeout(client, prompt, timeout=60.0)
except TradingError as e:
    if not e.recoverable:
        # Non-recoverable - log and fail
        raise
    # Recoverable - retry logic handled by helper
```

### SDK System Prompt Validation (RECOMMENDED)

**CRITICAL RULE**: Validate system prompt size before initialization. Prompts > 10k tokens can cause initialization failures.

**✅ CORRECT**:
```python
from src.core.sdk_helpers import validate_system_prompt_size

system_prompt = self._build_system_prompt()
is_valid, token_count = validate_system_prompt_size(system_prompt, max_tokens=8000)
if not is_valid:
    logger.warning(f"System prompt is {token_count} tokens, may cause issues")
```

**Recommendation**: Keep system prompts under 8000 tokens (safe limit under 10k SDK limit)

### SDK Health Monitoring (RECOMMENDED)

**CRITICAL RULE**: Monitor client health and auto-recover unhealthy clients.

**Implementation**: `ClaudeSDKClientManager` includes built-in health monitoring:
```python
# Check health
is_healthy = await client_manager.check_health("trading")

# Auto-recovery
recovered = await client_manager.recover_client("trading")

# Performance metrics
metrics = client_manager.get_performance_metrics()
```

---

## Core Architectural Patterns (28 Patterns)

### 1. Coordinator Pattern (Responsibility: Service Orchestration)

Use focused coordinator classes inheriting from `BaseCoordinator` for each major responsibility.

**Current Coordinators**:
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `LifecycleCoordinator` - Emergency operations
- `BroadcastCoordinator` - UI state broadcasting
- `ClaudeAgentCoordinator` - AI agent session management
- `AgentCoordinator` - Multi-agent coordination and lifecycle
- `MessageCoordinator` - Inter-agent communication routing
- `QueueCoordinator` - Queue management and orchestration

**Rule**: Each coordinator has single responsibility, async `initialize()`/`cleanup()`, delegates to services. Thin `RoboTraderOrchestrator` facade only coordinates coordinators.

### 11. Per-Stock State Tracking (Responsibility: Smart Scheduling)

Track last fetch dates per stock to eliminate redundant API calls and enable intelligent scheduling.

**Implementation**: `StockStateStore` persists state to `data/stock_scheduler_state.json` with methods for checking fetch needs.

**Rule**: Always check `needs_news_fetch()` or `needs_fundamentals_check()` before making API calls. Update state immediately after successful fetches.

### 12. Exponential Backoff & Retry (Responsibility: API Resilience)

Implement exponential backoff with jitter for rate-limited external APIs, plus automatic key rotation.

**Implementation**: `RetryHandler` with configurable backoff strategy, `PerplexityClient` with key rotation.

**Rule**: All external API calls must use retry logic with exponential backoff. Never make HTTP requests without retry protection.

### 13. Strategy Learning & Logging (Responsibility: AI Improvement)

Persist daily trading strategy reflections to create feedback loop for Claude's learning.

**Implementation**: `StrategyLogStore` tracks what worked/didn't work, enables performance insights.

**Rule**: Log strategies after each trading session. Use insights for tomorrow's focus areas.

### 14. Performance Metrics Calculation (Responsibility: Trading Analytics)

Comprehensive P&L, win rate, drawdown calculations for both individual trades and account-level metrics.

**Implementation**: `PerformanceCalculator` provides standardized metrics across the system.

**Rule**: Always use calculator for metrics, never calculate P&L inline. Include drawdown protection.

### 2. Dependency Injection Container (Responsibility: Service Lifecycle)

All services resolved through `DependencyContainer` - no global state, no direct instantiation.

**Rule**: Pass container to services, resolve dependencies at initialization time. Singletons for expensive resources (database, APIs, event bus), factories for stateful instances.

### 3. Event-Driven Communication (Responsibility: Decoupled Communication)

Services emit events via `EventBus`, handlers subscribe without direct coupling.

**Rule**: Use `EventType` enum for all events. Emit with source, timestamp, correlation ID. Subscribe with proper cleanup. No direct service-to-service calls for cross-cutting concerns.

### 4. Rich Error Context (Responsibility: Debugging & Recovery)

All errors inherit from `TradingError` with category, severity, code, metadata.

**Error Categories**: TRADING, MARKET_DATA, API, VALIDATION, RESOURCE, CONFIGURATION, SYSTEM
**Error Severities**: CRITICAL, HIGH, MEDIUM, LOW

**Rule**: Always use custom exception types, include recoverable flag, provide retry guidance. Never expose internal stack traces to UI.

### 5. Modularized Background Scheduler (Responsibility: Task Processing)

Scheduler organized by domain into 8 focused modules (max 350 lines each).

**Structure**:
- `models.py` - Task definitions
- `stores/` - Async persistence
- `clients/` - Unified API clients
- `processors/` - Domain logic (earnings, news, fundamentals)
- `monitors/` - Monitoring (market, risk, health)
- `config/` - Configuration management
- `events/` - Event routing
- `background_scheduler.py` - Facade

**Rule**: No monolithic files. Consolidate duplicate logic. Max 10 methods per class.

### 6. Backward Compatibility Layer (Responsibility: Zero Migration Overhead)

Refactored modules use wrapper pattern to maintain original import paths.

**Rule**: When refactoring, create new modular structure, update original file to re-export from new location. Existing code works unchanged.

### 7. Frontend Feature-Based Organization (Responsibility: Scalable UI)

React components organized by feature, not by type (pages, features, components/ui).

**Rule**: One component per file. Feature folders contain related components. Shared primitives in `components/ui/`. No deeply nested hierarchies.

### 8. WebSocket Differential Updates (Responsibility: Real-Time Efficiency)

Backend sends only changed data, client applies diffs.

**Rule**: Reduce bandwidth, lower latency. Send `{type, data: {...changes}}` not full state.

### 9. State Management via StateCoordinator (Responsibility: Distributed State)

Focused state stores per domain, centralized through coordinator.

**Rule**: Use `StateCoordinator` (not legacy `StateManager`). Async-first, event-driven updates, persistent storage when needed.

### 10. Centralized Configuration (Responsibility: Runtime Settings)

Single `Config` class loaded once at startup, passed to all services via DI.

**Rule**: Load from `config/config.json` and environment variables. Initialize once. Pass to container, never modify after.

### 13. Strategy Learning & Logging (Responsibility: AI Improvement)

Persist daily trading strategy reflections to create feedback loop for Claude's learning.

**Implementation**: `StrategyLogStore` tracks what worked/didn't work, enables performance insights.

**Rule**: Log strategies after each trading session. Use insights for tomorrow's focus areas.

### 14. Performance Metrics Calculation (Responsibility: Trading Analytics)

Comprehensive P&L, win rate, drawdown calculations for both individual trades and account-level metrics.

**Implementation**: `PerformanceCalculator` provides standardized metrics across the system.

**Rule**: Always use calculator for metrics, never calculate P&L inline. Include drawdown protection.

### 15. Feature Management Pattern (Responsibility: Dynamic Configuration)

Dynamic feature flags and dependency management for runtime system behavior control.

**Implementation**: `FeatureManagementService` provides feature CRUD operations, dependency resolution, and real-time updates.

**Rule**: Use feature flags for new functionality, implement dependency validation, broadcast changes via events.

### 16. Three-Queue Architecture (Responsibility: Task Processing)

Specialized queues for different task types with event-driven triggering between queues.

**Implementation**: Portfolio Queue, Data Fetcher Queue, and AI Analysis Queue with orchestrated workflows.

**Rule**: Use appropriate queue for task type, implement event-driven triggers, monitor queue health.

### 17. Multi-Agent Framework (Responsibility: AI Coordination)

Framework for coordinating multiple specialized AI agents with Claude SDK integration.

**Implementation**: `MultiAgentFramework` with specialized coordinators for agent lifecycle, task management, and communication.

**Rule**: Register agents with clear capabilities, use structured message protocols, implement consensus building.

### 18. Service Integration Pattern (Responsibility: Service Communication)

Event-driven service integration with handlers reacting to domain events.

**Implementation**: Services inherit from `EventHandler`, implement `handle_event()`, subscribe to relevant events.

**Rule**: Use events for cross-service communication, implement proper cleanup, never make direct service calls.

### 19. Container Networking Pattern (Responsibility: Deployment)

Reliable container-to-container communication using container names instead of DNS names.

**Implementation**: Use `robo-trader-<service-name>` format for all service URLs and environment variables.

**Rule**: Always use container names, never use `.orb.local` DNS names, document networking configuration.

### 20. WebSocket Differential Updates (Responsibility: Real-time UI)

Efficient real-time updates by sending only changed data to clients.

**Implementation**: Calculate diffs between current and previous state, send `{type, data: {...changes}}` format.

**Rule**: Send differential updates only, include correlation IDs, implement client-side patch application.

### 21. Strategy Evolution Engine (Responsibility: AI Improvement)

AI-driven strategy optimization and parameter evolution based on performance feedback.

**Implementation**: Genetic algorithms, A/B testing framework, performance-based parameter tuning.

**Rule**: Track strategy performance, use statistical significance testing, implement rollback mechanisms.

### 22. Atomic Write Pattern (Responsibility: Data Consistency)

Ensure data consistency during concurrent writes using atomic file operations.

**Implementation**: Write to temporary file first, use `os.replace()` for atomic operation, validate before commit.

**Rule**: Always use atomic writes for persistence, implement validation, cleanup temporary files on failure.

### 23. Monthly Reset Monitor (Responsibility: Paper Trading Capital Management)

Automatically reset paper trading account capital on the 1st of each month while preserving performance history.

**Implementation**: `MonthlyResetMonitor` runs daily, checks if it's the 1st, captures monthly metrics, resets balance.

**Rule**: Reset happens on 1st of month only. Preserve closed trades and strategy learnings. Track monthly P&L in history file. Emit reset event for UI broadcast.

**Process**:
1. Daily check if today is the 1st of month
2. If yes: Calculate monthly performance (P&L, trades, win rate, max drawdown)
3. Save metrics to `monthly_performance_history.json` (atomic write)
4. Reset account balance to initial amount (₹1,00,000)
5. Emit `ACCOUNT_RESET` event with monthly summary
6. UI updates show monthly results and capital reset confirmation

### 24. Real-Time System Health Monitoring (Responsibility: Live Infrastructure Status)

Comprehensive WebSocket-based system health monitoring with real-time updates for schedulers, queues, database, and logs.

**Implementation**: `StatusCoordinator` aggregates system metrics, `BroadcastCoordinator` sends WebSocket updates, frontend stores manage real-time state.

**Rule**: All system health data updates via WebSocket differential updates. No polling for health status. Component-level refresh only for detailed data.

**Components**:
- **Backend**: `StatusCoordinator`, `BroadcastCoordinator`, enhanced monitoring APIs
- **Frontend**: `SystemHealthFeature` with tabs for schedulers, queues, database, logs, errors
- **WebSocket**: Real-time updates for connection status, queue health, scheduler status
- **APIs**: `/api/monitoring/scheduler`, `/api/queues/status`, `/api/system/status`

### 25. Integrated System Logs (Responsibility: Contextual Log Monitoring)

System logs integrated within health monitoring interface, filtered for system health relevance.

**Implementation**: `SystemHealthLogs` component fetches from `/api/logs`, filters for system-relevant events, shows error/warning counts.

**Rule**: No standalone Logs page. All log viewing within System Health context. Focus on errors, warnings, and system-component events.

**Features**:
- Real-time log filtering (error, warning, info levels)
- System-health relevant filtering (excludes unrelated application logs)
- Component attribution (RiskManager, NewsMonitor, etc.)
- Refresh functionality with 30-second polling
- Error/warning summary counts in header

### 26. SDK Client Manager Pattern (Responsibility: SDK Performance Optimization)

Singleton client manager for efficient SDK client reuse to reduce startup overhead and memory usage.

**Implementation**: `ClaudeSDKClientManager` provides shared clients by type (`trading`, `query`, `conversation`) with health monitoring, auto-recovery, and performance metrics.

**Rule**: Always use `ClaudeSDKClientManager.get_instance()` instead of creating direct `ClaudeSDKClient` instances. Use appropriate client type for operation. Client manager handles cleanup automatically.

**Performance Impact**:
- Before: 7+ clients × 12s = 84s startup time
- After: 2-3 shared clients × 12s = 24-36s startup time
- **Savings: ~70 seconds faster startup**

**Usage**:
```python
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager

client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)
```

### 27. SDK Timeout & Error Handling Pattern (Responsibility: SDK Reliability)

Comprehensive timeout protection and error handling for all SDK operations to prevent hanging and ensure graceful failure recovery.

**Implementation**: `sdk_helpers` module provides `query_with_timeout()`, `receive_response_with_timeout()`, and `sdk_operation_with_retry()` with exponential backoff.

**Rule**: Never call `client.query()` or `client.receive_response()` directly. Always use timeout helpers from `sdk_helpers`. Handle all SDK error types explicitly (`CLINotFoundError`, `CLIConnectionError`, `ProcessError`, `CLIJSONDecodeError`, `ClaudeSDKError`).

**Timeout Values**:
- Query: 60s (default), 90s (trading sessions)
- Response: 120s (default), 180s (multi-turn conversations)
- Init: 30s
- Health check: 5s

**Usage**:
```python
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

await query_with_timeout(client, prompt, timeout=60.0)
async for response in receive_response_with_timeout(client, timeout=120.0):
    # Process response
```

### 28. SDK System Prompt Validation Pattern (Responsibility: SDK Initialization Safety)

Validate system prompt token counts before SDK client initialization to prevent timeout failures.

**Implementation**: `validate_system_prompt_size()` in `sdk_helpers` estimates tokens and warns if over limit.

**Rule**: Always validate system prompt size before creating `ClaudeAgentOptions`. Keep prompts under 8000 tokens (safe limit under 10k SDK limit). Monitor prompt sizes for services with large JSON contexts.

**Usage**:
```python
from src.core.sdk_helpers import validate_system_prompt_size

system_prompt = self._build_system_prompt()
is_valid, token_count = validate_system_prompt_size(system_prompt, max_tokens=8000)
if not is_valid:
    logger.warning(f"System prompt is {token_count} tokens, may cause issues")
```

### 29. Database-Backed AI Prompt Management Pattern (Responsibility: Dynamic Prompt Configuration)

Store AI prompts in database instead of hardcoding them in code, enabling Claude to view and modify prompts dynamically.

**Problem Solved**: Initially prompts were hardcoded in React components, preventing Claude from accessing or modifying them. Now prompts are stored in database and fetched via API.

**Implementation**: `ai_prompts_config` table stores prompts with content, description, and metadata.

**Database Schema**:
```sql
CREATE TABLE ai_prompts_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_name TEXT NOT NULL UNIQUE,
    prompt_content TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**API Endpoints**:
- `GET /api/configuration/prompts` - Fetch all prompts
- `GET /api/configuration/prompts/{name}` - Fetch specific prompt
- `PUT /api/configuration/prompts/{name}` - Update prompt

**Frontend Integration**:
```typescript
// Fetch prompts from database instead of hardcoded values
const getSchedulerPrompt = (taskName: string) => {
  return prompts[taskName]?.content || `No prompt available for ${taskName}`
}
```

**Rule**: Never hardcode AI prompts in frontend code. Always store in database and fetch via API. This allows Claude to view current prompts and modify them for strategy optimization.

**Lesson Learned**: Initial configuration UI had hardcoded prompts in JavaScript. Claude couldn't see or modify prompts, limiting AI-driven prompt optimization. Database-backed approach enables full AI access to prompt management.

---

## Code Quality Standards

### Modularization (ENFORCED)

- ✅ Max 350 lines per file (tight focus)
- ✅ Max 10 methods per class (cohesion)
- ✅ One responsibility per class/module (SRP)
- ✅ Clear, minimal public interfaces
- ❌ NEVER monolithic files over 350 lines
- ❌ NEVER god objects with 10+ methods

### Async/File Operations - MANDATORY

- ✅ Use `aiofiles` for ALL file I/O in async methods
- ✅ Lazy loading: Init with `_data = None`, load on first access
- ✅ Atomic writes: Write to temp file, then `os.replace()`
- ✅ Proper async context manager usage
- ❌ NEVER `open()`, `json.load()`, `json.dump()` in async code
- ❌ NEVER block I/O in `__init__()` methods
- ❌ NEVER sync operations in async context

### Error Handling - MANDATORY

- ✅ Use specific exception types (not generic `Exception`)
- ✅ Inherit from `TradingError` for domain errors
- ✅ Catch at entry points, handle gracefully
- ✅ Log with category, severity, code
- ✅ Include recoverable flag and retry guidance
- ❌ NEVER bare `except Exception:` without specific handling
- ❌ NEVER silent error suppression `except: pass`
- ❌ NEVER expose stack traces to UI/clients

### Background Tasks & Timeouts - CRITICAL

- ✅ Wrap task cancellation: `await asyncio.wait_for(task, timeout=5.0)`
- ✅ All background tasks must have error handlers
- ✅ All external API calls must handle rate limits
- ✅ Use exponential backoff for retries
- ✅ Emit events on task completion/failure
- ❌ NEVER `await task` after `.cancel()` without `wait_for()` wrapper
- ❌ NEVER start background tasks without monitoring
- ❌ NEVER ignore TimeoutError or CancelledError

### Testing Requirements

- ✅ Aim for 80%+ coverage on domain logic
- ✅ Mock all external dependencies (APIs, databases)
- ✅ Integration tests for coordinator interactions
- ✅ Test error scenarios and edge cases
- ❌ DON'T test simple getters/property access
- ❌ DON'T write integration tests without mocking

### Documentation Standards

- ✅ Module docstring: Purpose and public API
- ✅ Class docstring: Responsibility and usage
- ✅ Method docstring: Args, returns, raises
- ✅ Type hints on ALL functions (no `Any`)
- ✅ Examples in docstrings for complex logic
- ❌ NEVER skip type hints
- ❌ NEVER use `Any` without explicit reason

---

## Testing & Debugging Patterns

### Testing Methodology: Systematic Debugging (4-Phase Process)

When issues are discovered, follow this mandatory 4-phase debugging approach:

**Phase 1: Root Cause Investigation**
- Read error messages completely
- Reproduce issue consistently
- Check recent code changes
- Gather evidence from multiple components
- Trace data flow backward to source

**Phase 2: Pattern Analysis**
- Find working examples in codebase
- Compare against reference implementations
- Identify all differences (no matter how small)
- Understand dependencies and assumptions

**Phase 3: Hypothesis and Testing**
- Form single clear hypothesis
- Test with SMALLEST possible change
- One variable at a time
- Verify before continuing

**Phase 4: Implementation**
- Create failing test case first
- Fix root cause (not symptoms)
- One change at a time
- Verify fix works

**Critical Rule**: If 3+ fixes fail → STOP and question architecture (don't continue fixing symptoms)

### Input Validation Pattern Discovery

**Root Cause**: Negative quantities were accepted
**Investigation**: TradeRequest had no validators
**Solution**: Added Pydantic Field constraints
**Documentation**: Updated src/web/CLAUDE.md with comprehensive validation patterns

### Pydantic v2 Compatibility Discovery

**Root Cause**: Server wouldn't start after adding validation
**Investigation**: Used `regex=` parameter (deprecated in Pydantic v2)
**Solution**: Changed to `pattern=` parameter
**Documentation**: Added Pydantic v2 syntax examples and common mistakes

---

## Critical Permanent Rules

### 1. No Code Duplication

Consolidate repeated patterns into shared utilities. Example: 8 Perplexity API calls → 1 unified `PerplexityClient`.

### 2. Single Responsibility Per File

One domain per module. Clear public interface. Split if multiple responsibilities needed.

### 3. Async-First Design

ALL I/O must be non-blocking. Use `async/await` throughout. Never block event loop. Always protect timeouts with cancellation.

### 4. Error Handling is Non-Optional

Every async operation must handle failures. Background tasks must have retry logic. Timeouts must have cancellation. External APIs must handle rate limits.

### 5. Summary Documents - User-Initiated Only

NEVER auto-generate summary documents after work completes. WAIT for explicit user request. When created, place ONLY in `@documentation/` directory.

### 6. Backward Compatibility

Never break existing public APIs. When refactoring, maintain import paths (use wrapper if needed). Test with existing code before deployment.

### 7. Feature Management (CRITICAL)

**Rule**: Use feature flags for all new functionality with proper dependency management.

**Implementation**: Use `FeatureManagementService` for dynamic feature control, validate dependencies before activation.

**Why**:
- Enables safe rollout of new features
- Provides emergency disable capability
- Supports A/B testing and gradual deployment
- Allows feature experimentation without code deployment

### 8. Container Networking (CRITICAL)

**Rule**: All inter-service communication MUST use container names, NOT `.orb.local` DNS names.

**Format**: `http://robo-trader-<service-name>:<port>` (e.g., `http://robo-trader-postgres:5432`)

**Why**:
- `.orb.local` only works in OrbStack, fails in standard Docker
- Container names work reliably across Docker, Docker Compose, OrbStack
- Avoids DNS resolution failures and service communication timeouts

**Where to Update**:
- `docker-compose.yml` - service environment variables (DATABASE_URL, RABBITMQ_URL, SERVICE_URLs)
- `monitoring/prometheus.yml` - scrape targets
- `monitoring/grafana/provisioning/datasources/prometheus.yml` - datasource URLs
- Service code (if hardcoding URLs) - use ENV variables instead

**Naming Convention**: `robo-trader-<service-name>` (always use this exact format for new services)

**See**: @documentation/CONTAINER_NETWORKING.md for troubleshooting and detailed guide.

**Restart Scripts Available**:
- `./restart_server.sh` - Complete restart with automatic cache prevention
- `./scripts/restart-safe.sh [service] [--rebuild]` - Safe restart with optional rebuild
- `./scripts/safe-build.sh [service] [force]` - Build single service safely
- `./scripts/rebuild-all.sh` - Nuclear option: remove all and rebuild from scratch
- `./scripts/verify-cache.sh [service]` - Verify no stale code in containers

---

## Quick Reference - What to Do

| Situation | Pattern | Reference |
|-----------|---------|-----------|
| Need service orchestration | Create coordinator inheriting from `BaseCoordinator` | Coordinator Pattern |
| Need to share instance | Register in `DependencyContainer` as singleton | DI Container |
| Services need to communicate | Emit via `EventBus` using `EventType` enum | Event-Driven |
| Error can fail | Create custom exception, inherit from `TradingError` | Rich Error Context |
| Implementing task processing | Add to `background_scheduler/` with max 350 lines | Modularized Scheduler |
| Refactoring major module | Create new structure, wrapper re-exports old imports | Backward Compat |
| Building UI component | Feature folder with one component per file | Frontend Organization |
| Need real-time updates | Send changed data only via `differential_update` | WebSocket Diffs |
| Managing distributed state | Use `StateCoordinator`, emit change events | State Management |
| Centralizing configuration | Single `Config` class, load once, pass via DI | Centralized Configuration |
| Consolidating API calls | One client per API, key rotation, retry logic | API Client Pattern (src/core) |
| Parsing external data | 3-layer fallback: structured → regex → basic | Fallback Parsing (src/core) |
| Services receiving events | Inherit `EventHandler`, implement handler, cleanup | Event Handler Pattern (src/services) |
| HTTP endpoints & WebSockets | Middleware error handling, rate limiting | Web Layer (src/web) |
| Smart scheduling needed | Check `StockStateStore.needs_news_fetch()` before API calls | Per-Stock State Tracking |
| API resilience needed | Use `retry_on_rate_limit()` with exponential backoff | Exponential Backoff & Retry |
| Strategy learning needed | Log daily reflections in `StrategyLogStore` | Strategy Learning & Logging |
| Performance metrics needed | Use `PerformanceCalculator` for all P&L calculations | Performance Metrics Calculation |
| Three-queue scheduler needed | Implement PortfolioQueue, DataFetcherQueue, AIAnalysisQueue | Three Separate Scheduler Queues |
| Event-driven triggering needed | NEWS_FETCHED → AI analysis, EARNINGS_FETCHED → fundamentals update | Event-Driven Triggering |
| Monthly capital reset needed | Run MonthlyResetMonitor daily, reset on 1st, save performance history | Monthly Reset Monitor |
| AI functionality needed | Use Claude Agent SDK only - NO direct Anthropic API calls | SDK-Only Architecture |
| System health monitoring needed | Use StatusCoordinator + BroadcastCoordinator + WebSocket real-time updates | Real-Time System Health Monitoring |
| System logs viewing needed | Use SystemHealthLogs component within System Health, no standalone Logs page | Integrated System Logs |
| SDK client needed | Use ClaudeSDKClientManager.get_instance() - NEVER create direct ClaudeSDKClient | SDK Client Manager Pattern |
| SDK query/response needed | Use query_with_timeout() and receive_response_with_timeout() - NEVER call directly | SDK Timeout & Error Handling |
| System prompt validation needed | Validate prompt size with validate_system_prompt_size() before initialization | SDK System Prompt Validation |
| Database locking needed | Add `self._lock = asyncio.Lock()` and `async with self._lock:` for all database operations | Database Locking Pattern |
| AI prompts need to be configurable | Store prompts in `ai_prompts_config` table, fetch via API, never hardcode in frontend | Database-Backed AI Prompt Management |

---

## Pre-Commit Checklist

Every code submission MUST pass:

- [ ] **Architecture**: Follows coordinator/DI/event pattern appropriately
- [ ] **Modularization**: < 350 lines, < 10 methods/class, single responsibility
- [ ] **Async Rules**: Only `aiofiles`, atomic writes, timeout protection with cancellation
- [ ] **Error Handling**: Specific exceptions, proper logging, user-facing errors safe
- [ ] **No Duplication**: Checked for similar code, consolidated if needed
- [ ] **Testing**: Testable design, mocks for externals, 80%+ coverage for domain logic
- [ ] **Documentation**: Module/class/method docstrings, type hints
- [ ] **Backward Compat**: Old imports still work, no breaking changes
- [ ] **Input Validation**: Pydantic models with Field constraints on all requests
- [ ] **Pydantic v2**: Uses `pattern=` (NOT `regex=`), proper constraints (`gt=`, `le=`, etc.)
- [ ] **Negative Input Handling**: Numeric fields have `gt=0` or appropriate lower bound
- [ ] **API Clients**: Single client per API, key rotation, exponential backoff (src/core)
- [ ] **Parsing**: Multi-layer fallback if parsing external data (src/core)
- [ ] **Services**: Inherit EventHandler if reacting to events, proper cleanup (src)
- [ ] **Web Layer**: Error middleware + rate limiting + input validation (src/web)
- [ ] **Container Networking**: All URLs use container names, not .orb.local
- [ ] **Smart Scheduling**: Check stock state before API calls, update after fetches
- [ ] **API Resilience**: All external calls use retry with exponential backoff
- [ ] **Strategy Learning**: Log daily reflections, use insights for improvement
- [ ] **Performance Metrics**: Use PerformanceCalculator for all trading metrics
- [ ] **Three-Queue Architecture**: Implement separate Portfolio, Data Fetcher, and AI Analysis queues
- [ ] **Event-Driven Workflows**: Automatic triggering between scheduler queues
- [ ] **Feature Management**: Use feature flags for new functionality with dependency validation
- [ ] **Multi-Agent Coordination**: Register agents with capabilities, use structured communication
- [ ] **Service Integration**: Inherit EventHandler for services reacting to events
- [ ] **Atomic Writes**: Use temp files and os.replace() for data consistency
- [ ] **Systematic Debugging**: Use 4-phase process when fixing issues (root cause first)
- [ ] **SDK-Only Architecture**: NO direct Anthropic API calls - use Claude Agent SDK only
- [ ] **SDK Client Manager**: Use ClaudeSDKClientManager.get_instance() - NEVER create direct ClaudeSDKClient instances
- [ ] **SDK Timeout Handling**: Use query_with_timeout() and receive_response_with_timeout() - NEVER call client.query() directly
- [ ] **SDK Error Handling**: Handle all SDK error types (CLINotFoundError, CLIConnectionError, ProcessError, etc.)
- [ ] **SDK Prompt Validation**: Validate system prompt size before initialization (keep under 8000 tokens)
- [ ] **Database Locking**: All database state classes use `asyncio.Lock()` for concurrent operations
- [ ] **Database-Backed Prompts**: Never hardcode AI prompts in frontend - store in database and fetch via API
- [ ] **Real-Time System Health**: Use WebSocket differential updates, no polling for health status
- [ ] **Integrated System Logs**: SystemHealthLogs component within System Health, no standalone Logs page

---

## Development Workflow

### Before Writing Code

1. Identify which architectural layer/pattern applies (coordinator, service, processor, etc.)
2. Check if similar code exists - consolidate, don't duplicate
3. Plan error scenarios - what custom exceptions are needed?
4. List event dependencies - what events will this emit/subscribe to?

### After Implementation

1. Self-review against modularization limits
2. Verify error handling completeness
3. Check for async/file operation violations
4. Ensure backward compatibility maintained
5. Run tests, aim for 80%+ domain logic coverage

### For Refactoring

1. Create new modular structure first
2. Update original imports to use wrapper pattern
3. Test existing code works unchanged
4. Update documentation of new patterns
5. Verify all tests pass

---

## Key Files Reference

- `src/core/orchestrator.py` - Main facade (thin, delegates to coordinators)
- `src/core/coordinators/` - Focused service coordinators
- `src/core/di.py` - Dependency injection container (511 lines)
- `src/core/event_bus.py` - Event infrastructure (343 lines)
- `src/core/errors.py` - Error hierarchy with context (219 lines)
- `src/core/claude_sdk_client_manager.py` - Singleton SDK client manager (CRITICAL for performance)
- `src/core/sdk_helpers.py` - SDK operation helpers (timeout, error handling, validation)
- `src/core/background_scheduler/` - Modularized scheduler (8 focused domains)
   - `clients/perplexity_client.py` - Unified API client with key rotation
   - `clients/retry_handler.py` - Exponential backoff & retry logic
   - `stores/stock_state_store.py` - Per-stock state tracking
   - `stores/strategy_log_store.py` - Daily strategy learning logs
   - `processors/earnings_processor.py` - Fallback parsing strategy
- `src/services/` - Domain services with EventHandler pattern
- `src/services/paper_trading/performance_calculator.py` - Trading metrics calculation
- `src/web/app.py` - FastAPI with middleware error handling & rate limiting
- `config/config.json` - Runtime configuration
- `ui/src/pages/` - Top-level pages
- `ui/src/features/` - Feature-specific components
- `ui/src/components/ui/` - Reusable primitives

---

## Maintaining CLAUDE.md Files

### When to Update CLAUDE.md

**Update if**:
- New architecture pattern emerges (add to 10 patterns)
- Existing pattern changes implementation
- New best practice discovered
- Anti-pattern identified in code
- Domain-specific rule needed

**Don't update if**:
- One-time decision or workaround
- Specific implementation detail (use ARCHITECTURE_PATTERNS.md instead)
- Temporary code change
- Session-specific note

### How to Update CLAUDE.md

**Format for New Pattern**:
```markdown
### N. Pattern Name (Responsibility: What it does)

**Rule**: Core rule in 1-2 lines

**Implementation**:
✅ DO:
- Correct approach

❌ DON'T:
- Anti-pattern
```

**Locations to Update**:
1. Add pattern to main section (10 Patterns, Quality Standards, Rules)
2. Add to "Quick Reference - What to Do" table
3. Add to "Pre-Commit Checklist" if verification needed
4. Update folder-level CLAUDE.md if domain-specific

### Best Practices

- ✅ Keep patterns permanent and architectural
- ✅ Focus on WHY and WHAT, not HOW (HOW goes in ARCHITECTURE_PATTERNS.md)
- ✅ Include DO's and DON'Ts for each pattern
- ✅ Link to detailed implementation in ARCHITECTURE_PATTERNS.md
- ✅ Update when code patterns change
- ❌ Don't include one-time decisions
- ❌ Don't add implementation code (add to ARCHITECTURE_PATTERNS.md)
- ❌ Don't duplicate across CLAUDE.md files

### CLAUDE.md Hierarchy

```
.claude/CLAUDE.md (Agent Preferences)
├─ No auto-summaries
├─ Test files in @tests/
└─ Update patterns when they change

Root CLAUDE.md (Project Patterns)
├─ 10 architectural patterns
├─ Code quality standards
├─ Quick reference table
└─ Pre-commit checklist

src/CLAUDE.md (Backend Guidelines)
├─ Backend architecture layers
├─ Service patterns
└─ Async/File operations

src/core/CLAUDE.md (Core Infrastructure)
├─ Orchestrator, Coordinators, DI
├─ Event Bus, Error handling
└─ Background Scheduler patterns

ui/src/CLAUDE.md (Frontend Guidelines)
├─ Component architecture
├─ Feature organization
└─ WebSocket patterns
```

---

## When in Doubt

1. Read `@documentation/ARCHITECTURE_PATTERNS.md` for detailed implementation
2. Check existing pattern in codebase for similar functionality
3. Verify single responsibility - if multiple, split into multiple files
4. Prefer modularization over monolithic code
5. Async-first, error-handling mandatory, testing important
6. If pattern emerges, update relevant CLAUDE.md file

---

**Key Philosophy**: Patterns exist to maintain code quality and prevent debugging overhead. Coordinators + DI + Events = loosely coupled, highly testable, scalable architecture.

**Remember**: "Focused coordinators, injected dependencies, event-driven communication, rich error context. Smart scheduling, resilient APIs, strategy learning. Three-queue architecture, event-driven workflows. SDK client manager for performance, timeout protection for reliability. No duplication. Always."
