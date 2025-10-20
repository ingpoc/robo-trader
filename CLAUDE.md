# Robo Trader Project - Claude Development Memory

> **Project Memory**: Automatically loaded by Claude Code. Contains permanent development rules and architectural patterns that remain consistent as code evolves.

**Architecture Reference**: See @documentation/ARCHITECTURE_PATTERNS.md for detailed patterns and implementation guidelines.

---

## <� Core Architectural Patterns

### 1. Coordinator Pattern (Responsibility: Service Orchestration)

Use focused coordinator classes inheriting from `BaseCoordinator` for each major responsibility.

**Current Coordinators**:
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `LifecycleCoordinator` - Emergency operations
- `BroadcastCoordinator` - UI state broadcasting

**Rule**: Each coordinator has single responsibility, async `initialize()`/`cleanup()`, delegates to services. Thin `RoboTraderOrchestrator` facade only coordinates coordinators.

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

---

## =� Code Quality Standards

### Modularization (ENFORCED)

-  Max 350 lines per file (was 400, tightened for clarity)
-  Max 10 methods per class
-  One responsibility per class/module
-  Clear public interfaces

### Async/File Operations - MANDATORY

-  Use `aiofiles` for ALL file I/O in async methods
-  Lazy loading: Init with `_data = None`, load on first access
-  Atomic writes: Write to temp file, then `os.replace()`
- L NEVER use `open()`, `json.load()`, `json.dump()` in async methods
- L NEVER block I/O in `__init__()`

### Error Handling - MANDATORY

-  Use specific exception types (not generic `Exception`)
-  Catch errors at entry points, handle gracefully
-  Log with context (category, severity, code)
- L NEVER bare `except Exception:` without specific handling
- L NEVER silent error suppression

### Background Tasks & Timeouts - CRITICAL

-  Wrap timeouts with cancellation: `await asyncio.wait_for(task, timeout=5.0)` when cancelling
-  All tasks have error handlers
-  All external API calls handle rate limits
- L NEVER `await task` after `.cancel()` without `wait_for()` wrapper
- L NEVER start background tasks without error monitoring

### Testing Requirements

-  Aim for 80%+ coverage on domain logic
-  Mock all external dependencies (APIs, database)
-  Integration tests for coordinator interactions
-  No tests needed for simple getters/property access

### Documentation Standards

-  Module docstring explaining responsibility
-  Class docstrings with purpose
-  Method docstrings with args, returns, raises
-  Type hints on all functions

---

## = Critical Permanent Rules

### 1. No Code Duplication

Consolidate repeated patterns into shared utilities. Example: 8 Perplexity API calls � 1 unified `PerplexityClient`.

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

---

## =� Quick Reference - What to Do

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
| **Centralizing configuration** | **Single `Config` class, load once, pass via DI** | **Centralized Configuration** |
| **Consolidating API calls** | **One client per API, key rotation, retry logic** | **API Client Pattern** (src/core) |
| **Parsing external data** | **3-layer fallback: structured → regex → basic** | **Fallback Parsing** (src/core) |
| **Services receiving events** | **Inherit `EventHandler`, implement handler, cleanup** | **Event Handler Pattern** (src/services) |
| **HTTP endpoints & WebSockets** | **Middleware error handling, rate limiting** | **Web Layer** (src/web) |

---

## � Pre-Commit Checklist

Every code submission MUST pass:

- [ ] **Architecture**: Follows coordinator/DI/event pattern appropriately
- [ ] **Modularization**: < 350 lines, < 10 methods/class, single responsibility
- [ ] **Async Rules**: Only `aiofiles`, atomic writes, timeout protection with cancellation
- [ ] **Error Handling**: Specific exceptions, proper logging, user-facing errors safe
- [ ] **No Duplication**: Checked for similar code, consolidated if needed
- [ ] **Testing**: Testable design, mocks for externals, 80%+ coverage for domain logic
- [ ] **Documentation**: Module/class/method docstrings, type hints
- [ ] **Backward Compat**: Old imports still work, no breaking changes
- [ ] **API Clients**: Single client per API, key rotation, exponential backoff (src/core)
- [ ] **Parsing**: Multi-layer fallback if parsing external data (src/core)
- [ ] **Services**: Inherit EventHandler if reacting to events, proper cleanup (src)
- [ ] **Web Layer**: Error middleware + rate limiting for endpoints (src/web)

---

## <� Development Workflow

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

## =� Key Files Reference

- `src/core/orchestrator.py` - Main facade (thin, delegates to coordinators)
- `src/core/coordinators/` - Focused service coordinators
- `src/core/di.py` - Dependency injection container (511 lines)
- `src/core/event_bus.py` - Event infrastructure (343 lines)
- `src/core/errors.py` - Error hierarchy with context (219 lines)
- `src/core/background_scheduler/` - Modularized scheduler (8 focused domains)
  - `clients/perplexity_client.py` - Unified API client pattern
  - `processors/earnings_processor.py` - Fallback parsing strategy
- `src/services/` - Domain services with EventHandler pattern
- `src/web/app.py` - FastAPI with middleware error handling & rate limiting
- `config/config.json` - Runtime configuration
- `ui/src/pages/` - Top-level pages
- `ui/src/features/` - Feature-specific components
- `ui/src/components/ui/` - Reusable primitives

---

## 📝 Maintaining CLAUDE.md Files

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

## =� When in Doubt

1. Read `@documentation/ARCHITECTURE_PATTERNS.md` for detailed implementation
2. Check existing pattern in codebase for similar functionality
3. Verify single responsibility - if multiple, split into multiple files
4. Prefer modularization over monolithic code
5. Async-first, error-handling mandatory, testing important
6. If pattern emerges, update relevant CLAUDE.md file

---

**Key Philosophy**: Patterns exist to maintain code quality and prevent debugging overhead. Coordinators + DI + Events = loosely coupled, highly testable, scalable architecture.

**Remember**: "Focused coordinators, injected dependencies, event-driven communication, rich error context. No duplication. Always."

