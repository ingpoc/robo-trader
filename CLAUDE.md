# Robo Trader Project - Claude Development Memory

> **Project Memory**: Automatically loaded by Claude Code. Contains permanent development rules and architectural patterns that remain consistent as code evolves.

**Architecture Reference**: See @documentation/ARCHITECTURE_PATTERNS.md for detailed patterns and implementation guidelines.

---

## Core Architectural Patterns (23 Patterns)

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

**Remember**: "Focused coordinators, injected dependencies, event-driven communication, rich error context. Smart scheduling, resilient APIs, strategy learning. Three-queue architecture, event-driven workflows. No duplication. Always."
