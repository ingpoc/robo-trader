# Robo Trader Project - Claude Development Memory

> **Project Memory**: Loaded by Claude Code. Permanent rules & patterns that stay consistent.

> **Last Updated**: 2025-10-31 | **Status**: Production Ready

**Architecture Details**: @documentation/ARCHITECTURE_PATTERNS.md

## Contents

- [Development Operations (CRITICAL)](#development-operations-critical)
- [Core Architectural Patterns](#core-architectural-patterns) (25 patterns)
- [Code Quality Standards](#code-quality-standards)
- [Development Workflow](#development-workflow)
- [Quick Reference](#quick-reference---what-to-do)
- [Pre-Commit Checklist](#pre-commit-checklist)
- [Maintaining CLAUDE.md Files](#maintaining-claudemd-files)
- [When in Doubt](#when-in-doubt)

---

## Core Architectural Patterns (25 Patterns)

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

### 11. Feature Management Pattern (Responsibility: Dynamic Configuration)

Dynamic feature flags with runtime system behavior control.

**Rule**: Use feature flags for new functionality, validate dependencies, broadcast changes via events.

### 12. Three-Queue Architecture (Responsibility: Task Processing)

Specialized queues: Portfolio Queue, Data Fetcher Queue, AI Analysis Queue with event-driven triggering.

**Rule**: Use right queue for task type, implement event-driven triggers, monitor queue health.

### 13. Multi-Agent Framework (Responsibility: AI Coordination)

Register agents with clear capabilities, use structured messaging, implement consensus.

**Rule**: Use `MultiAgentFramework`, implement agent lifecycle, enable inter-agent communication.

### 14. Service Integration Pattern (Responsibility: Service Communication)

Services inherit from `EventHandler`, react to domain events.

**Rule**: Use events only for cross-service communication. Never direct service calls.

### 15. Container Networking Pattern (Responsibility: Deployment)

Use container names: `robo-trader-<service-name>:<port>`. Never use `.orb.local` DNS names.

**Why**: `.orb.local` only works in OrbStack. Container names work everywhere (Docker, Compose, OrbStack).

### 16. Real-Time WebSocket Updates (Responsibility: Efficient UI)

Send only changed data. Client applies diffs. Format: `{type, data: {...changes}}`.

**Rule**: Differential updates only. Include correlation IDs. Client-side patch application.

### 17. Strategy Evolution Engine (Responsibility: AI Improvement)

AI-driven strategy optimization based on performance feedback. Use genetic algorithms + A/B testing.

**Rule**: Track performance statistically. Use significance testing. Implement rollback.

### 18. Atomic Write Pattern (Responsibility: Data Consistency)

Write to temp file first. Use `os.replace()` for atomic operation. Validate before commit.

**Rule**: Always atomic writes for persistence. Validate. Cleanup temp files on failure.

### 19. Monthly Reset Monitor (Responsibility: Paper Trading Capital Management)

Reset account capital on 1st of month. Preserve trade history & strategy learnings.

**Process**:
1. Daily check if today is 1st
2. Calculate monthly performance (P&L, trades, win rate, drawdown)
3. Save to `monthly_performance_history.json` (atomic write)
4. Reset balance to initial amount
5. Emit `ACCOUNT_RESET` event
6. UI updates with monthly summary

### 20. Real-Time System Health Monitoring (Responsibility: Live Infrastructure Status)

WebSocket-based system health monitoring. `StatusCoordinator` aggregates metrics. `BroadcastCoordinator` sends updates.

**Rule**: All health data via WebSocket diffs. No polling. Component-level refresh only for detailed data.

### 21. Integrated System Logs (Responsibility: Contextual Log Monitoring)

Logs within health monitoring interface. Filtered for system health relevance. No standalone Logs page.

**Rule**: View within System Health only. Focus on errors, warnings, system-component events.

### 22. 🔴 CRITICAL: SDK Architecture (Responsibility: AI Operations)

**All AI functionality uses Claude Agent SDK only. NO direct Anthropic API calls.**

**Authentication**: Claude Code CLI only (no API keys)

**✅ Use**:
```python
from claude_agent_sdk import ClaudeAgentOptions, tool
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

# Always use client manager singleton (NOT direct ClaudeSDKClient)
client_manager = await ClaudeSDKClientManager.get_instance()
options = ClaudeAgentOptions(mcp_servers={"trading": mcp_server})
client = await client_manager.get_client("trading", options)

# Always use timeout helpers (NEVER direct client.query())
await query_with_timeout(client, prompt, timeout=60.0)
async for response in receive_response_with_timeout(client, timeout=120.0):
    process(response)
```

**❌ NEVER**:
```python
from anthropic import AsyncAnthropic  # FORBIDDEN
client = AsyncAnthropic(api_key="...")  # FORBIDDEN
```

**Client Types**: `"trading"` (with tools), `"query"` (no tools), `"conversation"` (multi-turn)

**Performance**: 1 shared client = 12s. 7+ clients = 84s wasted. Use manager to save 70 seconds.

**Error Types** (handled by helpers): `CLINotFoundError`, `CLIConnectionError`, `ProcessError`, `CLIJSONDecodeError`, `ClaudeSDKError`

**Timeout Values**:
- Query: 60s (default), 90s (trading)
- Response: 120s (default), 180s (multi-turn)
- Init: 30s | Health: 5s

**System Prompt**: Validate before init. Keep under 8000 tokens (safe under 10k limit).

**Validation**:
```python
from src.core.sdk_helpers import validate_system_prompt_size

is_valid, token_count = validate_system_prompt_size(prompt, max_tokens=8000)
if not is_valid:
    logger.warning(f"Prompt {token_count} tokens - may timeout")
```

### 23. Database-Backed AI Prompt Management (Responsibility: Dynamic Prompt Configuration)

Store prompts in `ai_prompts_config` table. Never hardcode in frontend.

**Why**: Hardcoded prompts = Claude can't see/modify them. Database = full access for AI-driven optimization.

**Table**: `ai_prompts_config` (id, prompt_name, prompt_content, description, created_at, updated_at)

**APIs**:
- `GET /api/configuration/prompts` (all)
- `GET /api/configuration/prompts/{name}` (specific)
- `PUT /api/configuration/prompts/{name}` (update)

**Rule**: Database first. Fetch via API. Never hardcode.

---

## Code Quality Standards

### 🔴 Modularization (ENFORCED)

**✅ DO**: Max 350 lines/file. Max 10 methods/class. One responsibility per file.

**❌ DON'T**: Monolithic files. God objects. Multiple responsibilities.

### 🔴 Async/File Operations (MANDATORY)

**✅ DO**: `aiofiles` for all async I/O. Lazy load: `_data = None`, load on first access. Atomic writes: temp file → `os.replace()`.

**❌ DON'T**: `open()`, `json.load()` in async. Blocking I/O in `__init__()`. Sync ops in async context.

### 🔴 Error Handling (MANDATORY)

**✅ DO**: Specific exception types. Inherit from `TradingError`. Catch at entry points. Log with category/severity/code. Include recoverable flag.

**❌ DON'T**: Bare `except Exception:`. Silent suppression `except: pass`. Expose stack traces to UI.

### 🔴 Background Tasks & Timeouts (CRITICAL)

**✅ DO**: Wrap cancellation: `await asyncio.wait_for(task, timeout=5.0)`. Error handlers on all tasks. Rate limit handling. Exponential backoff. Emit completion/failure events.

**❌ DON'T**: `await task` after `.cancel()` without `wait_for()`. Unmonitored background tasks. Ignore TimeoutError/CancelledError.

### Testing Requirements

**✅ DO**: 80%+ coverage on domain logic. Mock externals. Integration tests for coordinators. Test error scenarios.

**❌ DON'T**: Test simple getters. Integration tests without mocks.

### Documentation Standards

**✅ DO**: Module docstring (purpose + API). Class docstring (responsibility + usage). Method docstring (args, returns, raises). Type hints on all functions.

**❌ DON'T**: Skip type hints. Use `Any` without reason.

---

## Testing & Debugging Patterns

### 🔴 Systematic Debugging (4-Phase Process)

When debugging: Follow this. Always.

**Phase 1**: Read error completely. Reproduce consistently. Check recent changes. Gather evidence from multiple places. Trace backward.

**Phase 2**: Find working examples. Compare against references. Identify ALL differences (small = big). Understand dependencies.

**Phase 3**: Form ONE clear hypothesis. Test with SMALLEST change. One variable at a time. Verify.

**Phase 4**: Create failing test first. Fix root cause (not symptoms). One change at a time. Verify works.

**STOP RULE**: If 3+ fixes fail → question architecture (not symptoms).

---

## Critical Permanent Rules

### 1. No Code Duplication

Consolidate into shared utilities. Example: 8 Perplexity API calls → 1 unified `PerplexityClient`.

### 2. Single Responsibility Per File

One domain per module. Clear public interface.

### 3. 🔴 Async-First Design

ALL I/O = non-blocking. Use `async/await`. Never block event loop. Always protect timeouts with cancellation.

### 4. 🔴 Error Handling is Non-Optional

Every async op handles failures. Background tasks have retry logic. Timeouts have cancellation. External APIs handle rate limits.

### 5. Summary Documents - User-Initiated Only

NEVER auto-generate summaries. WAIT for explicit request. When created: place ONLY in `@documentation/`.

### 6. Backward Compatibility

Never break public APIs. When refactoring: maintain import paths (use wrapper). Test before deploy.

### 7. 🔴 Feature Management (CRITICAL)

Use feature flags for all new functionality with dependency management.

**Why**: Safe rollout. Emergency disable. A/B testing. Gradual deployment.

**Use**: `FeatureManagementService` for dynamic control. Validate dependencies before activation.

### 8. 🔴 Container Networking (CRITICAL)

**Rule**: All inter-service communication uses container names. NEVER `.orb.local` DNS names.

**Format**: `http://robo-trader-<service-name>:<port>` (e.g., `http://robo-trader-postgres:5432`)

**Why**: `.orb.local` only works in OrbStack. Container names work everywhere (Docker, Compose, OrbStack).

**Update**: docker-compose.yml, prometheus.yml, grafana datasources, ENV variables.

**Restart Scripts**: `./restart_server.sh`, `./scripts/restart-safe.sh [service]`, `./scripts/rebuild-all.sh`

**Detailed Guide**: @documentation/CONTAINER_NETWORKING.md

---

## Quick Reference - What to Do

**Core Infrastructure** (#1-8)
| Situation | Solution |
|-----------|----------|
| Service orchestration | `BaseCoordinator` subclass |
| Share instances | `DependencyContainer` singleton |
| Service communication | `EventBus` + `EventType` enum |
| Handle errors | Custom exception + inherit `TradingError` |
| Background tasks | `background_scheduler/` max 350 lines |
| Major refactor | New structure + wrapper re-exports |

**Frontend & UI** (#7, 16, 20-21)
| Situation | Solution |
|-----------|----------|
| React component | Feature folder + one component/file |
| Real-time updates | WebSocket differential updates |
| System health UI | `StatusCoordinator` + `BroadcastCoordinator` |
| System logs UI | Within System Health. No standalone page |

**State & Configuration** (#9-10, 23)
| Situation | Solution |
|-----------|----------|
| Distributed state | `StateCoordinator` + change events |
| Configuration | Single `Config` class via DI |
| AI prompts | Database `ai_prompts_config` table. Fetch via API. No hardcode |

**API & Data** (#11-12, 14-19)
| Situation | Solution |
|-----------|----------|
| API resilience | Exponential backoff + retry logic |
| Feature flags | `FeatureManagementService` + dependency validation |
| Three-queue scheduler | Portfolio, DataFetcher, AIAnalysis queues |
| Container networking | `robo-trader-<service-name>:<port>` format |
| Strategy logging | `StrategyLogStore` for daily learnings |
| Trading metrics | `PerformanceCalculator` for P&L |

**AI & SDK** (#22)
| Situation | Solution |
|-----------|----------|
| AI functionality | Claude Agent SDK only (NO direct Anthropic API) |
| SDK client | `ClaudeSDKClientManager.get_instance()` |
| SDK query/response | `query_with_timeout()` + `receive_response_with_timeout()` |
| System prompt | Validate size before init (keep <8000 tokens) |

---

## Pre-Commit Checklist

**Core** ✓
- [ ] Architecture: coordinator/DI/event pattern
- [ ] Modularization: <350 lines, <10 methods, single responsibility
- [ ] Async: `aiofiles`, atomic writes, timeout+cancellation
- [ ] Errors: specific types, inherit `TradingError`, proper logging
- [ ] No duplication: checked & consolidated

**Quality** ✓
- [ ] Testing: 80%+ coverage domain logic, mocks for externals
- [ ] Docs: module/class/method docstrings, type hints (no `Any`)
- [ ] Backward compat: old imports work, no breaking changes
- [ ] Input validation: Pydantic models with constraints

**Pydantic v2** ✓
- [ ] Uses `pattern=` (NOT `regex=`)
- [ ] Proper constraints (`gt=0`, `le=`, etc.)
- [ ] Negative inputs blocked (`gt=0` for quantities)

**API & Data** ✓
- [ ] Single client per API, key rotation, exponential backoff
- [ ] Multi-layer fallback for data parsing
- [ ] Smart scheduling: check state before API calls
- [ ] Atomic writes: temp file → `os.replace()`

**Services** ✓
- [ ] Inherit `EventHandler` if receiving events
- [ ] Event-driven communication, no direct calls
- [ ] Proper cleanup on shutdown
- [ ] Error handlers on all background tasks

**Web Layer** ✓
- [ ] Error middleware + rate limiting
- [ ] Input validation on all endpoints
- [ ] Container networking: `robo-trader-<name>` (no `.orb.local`)

**Trading/Strategy** ✓
- [ ] `PerformanceCalculator` for all P&L
- [ ] Log daily reflections in `StrategyLogStore`
- [ ] Feature flags for new functionality

**AI/SDK** 🔴 **CRITICAL** ✓
- [ ] NO direct Anthropic API calls (SDK only)
- [ ] `ClaudeSDKClientManager.get_instance()` (not direct client)
- [ ] `query_with_timeout()` + `receive_response_with_timeout()` (never direct)
- [ ] Validate system prompt size before init (<8000 tokens)
- [ ] Handle all SDK error types explicitly

**System** ✓
- [ ] WebSocket diffs for real-time updates (no polling)
- [ ] System Health UI with logs (no standalone Logs page)
- [ ] Database locking: `asyncio.Lock()` for concurrent ops
- [ ] Monthly reset monitor (preserve history)

---

## Development Operations (CRITICAL)

### Background Process Management (MANDATORY WORKFLOW)

**CRITICAL RULE**: When starting servers or background processes, ALWAYS kill existing processes first. Orphaned processes cause stale code execution and impossible debugging.

**Problem**: Multiple background processes from previous attempts cause:
- **Stale code execution** (old versions of files running in memory)
- **Port conflicts** ("Address already in use" errors)
- **Cache inconsistency** (Python bytecode cached in memory, not on disk)
- **Impossible verification** (code changes don't take effect even after file modifications)

**Root Cause**: Python's module import caching + FastAPI's route decoration at import time = OLD FUNCTION DEFINITIONS remain in running process even after source file is modified. Process memory caches the old handler, not the new file on disk.

**Clean Start Workflow** (ALWAYS DO THIS BEFORE RESTARTING SERVERS):
```bash
# Step 1: Kill ALL background processes (not just individual ones)
pkill -9 python      # Kill ALL Python processes
pkill -9 uvicorn     # Kill ALL uvicorn instances
pkill -9 node        # Kill ALL Node.js instances
sleep 3              # Wait for OS to release resources

# Step 2: Clear Python bytecode cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Step 3: Clear Python import caches
export PYTHONDONTWRITEBYTECODE=1  # Prevent new .pyc files

# Step 4: Start fresh server
python -m src.main --command web

# Step 5: VERIFY old processes are gone
ps aux | grep -E "python|uvicorn|node" | grep -v grep
# Should output NOTHING if successful
```

**When to Use**:
- ✅ **ALWAYS** before restarting servers
- ✅ After modifying route files or handlers (configuration.py, etc.)
- ✅ When code changes don't take effect after file edits
- ✅ When debugging "code not executing" issues
- ✅ When "Address already in use" port errors occur
- ✅ When log output shows old function behavior

**DO NOT DO**:
- ❌ `lsof -ti:8000 | xargs kill` only (leaves other processes running)
- ❌ Assume hot-reload works for FastAPI routes (it doesn't for decorated endpoints)
- ❌ Clear cache without killing processes (cache still in memory)
- ❌ Start new process without waiting 3 seconds (OS hasn't released ports/resources)

**Why This Matters**:
When FastAPI imports the routes module at startup, it decorates endpoints with @router.post(). These decorated function objects are stored in the FastAPI app's route table. If you modify the source file later, the original decorated function remains in memory in the running process. Simply clearing `.pyc` files doesn't affect the already-loaded function object in process memory. Only killing the process forces a fresh import and new decoration.

---

## Development Workflow

**Before Coding**:
1. Identify architectural pattern (coordinator, service, processor, etc.)
2. Check if similar code exists (consolidate!)
3. Plan error scenarios (which custom exceptions?)
4. List event dependencies (emit/subscribe what?)

**After Coding**:
1. Self-review modularization limits (<350 lines, <10 methods)
2. Verify error handling completeness
3. Check async/file operation rules
4. Ensure backward compatibility
5. Run tests (80%+ domain logic)

**When Refactoring**:
1. Create new modular structure first
2. Update old imports to use wrapper pattern
3. Test existing code works unchanged
4. Update documentation
5. Verify all tests pass

---

## Key Files Reference

**Core Infrastructure**:
- `src/core/orchestrator.py` - Main facade
- `src/core/coordinators/` - Service coordinators
- `src/core/di.py` - Dependency injection container
- `src/core/event_bus.py` - Event infrastructure
- `src/core/errors.py` - Error hierarchy

**SDK & AI** 🔴:
- `src/core/claude_sdk_client_manager.py` - Singleton SDK client (CRITICAL)
- `src/core/sdk_helpers.py` - Timeout + error handling + validation

**Background Scheduler**:
- `src/core/background_scheduler/clients/` - API clients (perplexity, retry handler)
- `src/core/background_scheduler/stores/` - Stock state, strategy logs
- `src/core/background_scheduler/processors/` - Domain logic (earnings, parsing)

**Services & Web**:
- `src/services/` - Domain services with EventHandler
- `src/services/paper_trading/performance_calculator.py` - Trading metrics
- `src/web/app.py` - FastAPI with error middleware + rate limiting
- `config/config.json` - Configuration

**Frontend**:
- `ui/src/pages/` - Top-level pages
- `ui/src/features/` - Feature components
- `ui/src/components/ui/` - Shared primitives

---

## Maintaining CLAUDE.md Files

### 🔴 Multi-File CLAUDE.md Strategy (MANDATORY)

**Project CLAUDE.md Hierarchy**:

```
Root CLAUDE.md (THIS FILE)
├─ Project-wide patterns (23 core patterns)
├─ Code quality standards (all layers)
├─ Development operations (servers, testing, debugging)
├─ Quick reference table (by domain)
└─ Pre-commit checklist (comprehensive)

src/CLAUDE.md (Backend Guidelines)
├─ Backend-specific patterns
├─ Service architecture
├─ Async/File operations rules
└─ Database patterns

src/core/CLAUDE.md (Core Infrastructure)
├─ Orchestrator patterns
├─ Coordinator implementation
├─ DI container rules
├─ Event bus patterns
└─ Error handling

ui/src/CLAUDE.md (Frontend Guidelines)
├─ Component architecture
├─ Feature organization
├─ WebSocket patterns
└─ State management
```

**Rule**: Each CLAUDE.md is specialty-focused. Root = project-wide. Subfolder = domain-specific.

### Update Decision Tree

**Is it a pattern** → Add to root CLAUDE.md
**Is it domain-specific** → Add to domain CLAUDE.md (src/, ui/)
**Is it architecture** → Add to both root + detailed in @documentation/ARCHITECTURE_PATTERNS.md
**Is it a one-time fix** → Don't add (it's not permanent)
**Is it a best practice** → Add to root + link in relevant domain CLAUDE.md

### 🔴 When to Update CLAUDE.md (ALL LAYERS) (MANDATORY)

Update immediately when:

- New architecture pattern emerges (rare, architectural decisions)
- Existing pattern implementation changes (code evolves)
- New best practice discovered (repeatedly effective approach)
- Anti-pattern identified in code (prevent future mistakes)
- Critical rule needs documentation (stops bugs before they happen)

Don't update for:

- One-time decisions or workarounds (temp fixes)
- Specific implementation details (use @documentation/ARCHITECTURE_PATTERNS.md)
- Temporary code changes (not permanent)
- Session-specific notes (only for this session)

### Format for New Pattern

```markdown
### N. Pattern Name (Responsibility: What it does)

**Rule**: Core rule in 1-2 lines

**✅ DO**: Correct approach

**❌ DON'T**: Anti-pattern
```

### 🔴 Update ALL Affected CLAUDE.md Files (MANDATORY)

When adding pattern to root CLAUDE.md:

1. **Root CLAUDE.md**:
   - Add to Core Architectural Patterns (sequential #)
   - Add to Quick Reference table
   - Add to Pre-Commit Checklist (if checkable)
   - Add to Key Files Reference (if new file)

2. **Domain CLAUDE.md** (if applicable):
   - Add domain-specific details (src/, ui/, etc.)
   - Reference root pattern by number
   - Don't duplicate root content (link instead)
   - Add domain-specific examples

3. **@documentation/ARCHITECTURE_PATTERNS.md**:
   - Add detailed implementation guide
   - Include code examples
   - Document gotchas + edge cases
   - Root CLAUDE.md links here

**Example Update**:
```markdown
Root CLAUDE.md: "### 24. My Pattern (brief, checkable)"

src/core/CLAUDE.md: "See root CLAUDE.md #24. Domain-specific: X, Y, Z"

@documentation/ARCHITECTURE_PATTERNS.md: "### My Pattern - Detailed Implementation Guide"
```

### 🔴 Cross-File Consistency Rules (MANDATORY)

**Rule 1**: No duplicate content across CLAUDE.md files. Root = source of truth.

**Rule 2**: Domain files link to root. Example: `See root CLAUDE.md #5 for core pattern`.

**Rule 3**: Implementation details in @documentation/ only. CLAUDE.md = decisions only.

**Rule 4**: All patterns follow same format (Rule + ✅ DO + ❌ DON'T).

**Rule 5**: Pre-Commit Checklist organized by category (Core, Quality, Pydantic, API, etc).

**Rule 6**: Quick Reference table grouped by domain (#patterns, not flat list).

### Best Practices for CLAUDE.md Maintenance ✓

**Permanent + Architectural**: Only rules that stay true as code evolves
**WHY + WHAT**: Not HOW (HOW goes in @documentation/ARCHITECTURE_PATTERNS.md)
**Include DO's + DON'Ts**: Anti-patterns prevent mistakes
**Keep Concise**: Max 1-2 sentences per rule (sacrifice grammar if needed)
**Link, Don't Duplicate**: Cross-file references prevent sync issues
**Update When Code Changes**: If pattern emerges in code, document it
**Version Tracking**: Update date in root CLAUDE.md header after changes

### Synchronization Checklist

After adding/updating any pattern:

- [ ] Root CLAUDE.md updated (pattern + ref table + checklist)
- [ ] Domain CLAUDE.md updated (if applicable, with link to root)
- [ ] @documentation/ARCHITECTURE_PATTERNS.md updated (if detailed impl needed)
- [ ] All file headers have same format + style
- [ ] No duplicate content across files (use links)
- [ ] Root CLAUDE.md date updated to today
- [ ] Test: grep pattern name across all CLAUDE.md files (should have 1 root + N domain refs)

---

## When in Doubt

1. Read `@documentation/ARCHITECTURE_PATTERNS.md` (detailed implementation)
2. Find similar pattern in codebase
3. Check: Single responsibility? Split if multiple.
4. Modularization > monolithic code
5. Async-first. Error-handling mandatory. Testing important.
6. Pattern emerges? Update relevant CLAUDE.md.

---

**Philosophy**: Patterns maintain code quality + prevent debugging overhead.

**Core Formula**: Coordinators + DI + Events = loosely coupled, testable, scalable.

**Remember**: "Focused coordinators. Injected dependencies. Event-driven communication. Rich error context. Smart scheduling. Resilient APIs. Strategy learning. Three-queue architecture. Event-driven workflows. SDK client manager. Timeout protection. No duplication. Always."

---

## Development Operations

### Server Commands

**Kill both servers** (if stuck):
```bash
lsof -ti:8000 -ti:3000 | xargs kill -9
```

**Start backend** (with auto-reload):
```bash
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
```

**Start frontend** (with hot reload):
```bash
cd ui && npm run dev
```

### 🔴 Live Reload Automation (MANDATORY)

**Rule**: Always use `--reload` (backend) + hot reload (frontend). Auto-restart picks up code changes.

**Critical**: After auto-restart, always re-check server logs for errors. Don't assume reload was successful.

### 🔴 Strict API Contract Sync (MANDATORY)

**Rule**: Any backend endpoint/response change requires frontend update + test (and vice versa).

**Why**: Prevents "works in backend tests, but API returns field UI doesn't expect."

### 🔴 End-to-End Browser Testing (MANDATORY)

After any backend or frontend code change:
1. Restart relevant server(s)
2. Test all relevant features in browser
3. Only mark complete after browser test passes

### 🔴 Debugging Sequence (FOLLOW THIS)

**Order**: Browser → Frontend Logs → Backend Logs → Health Check → Fix → Restart → Retest

**Logs**:
- Frontend: `logs/frontend.log`
- Backend: `logs/*.log`

**Browser Problem** → Check:
1. Browser DevTools (console errors, network failures)
2. Backend logs (tail for errors/warnings)
3. Health endpoint: `curl -m 3 http://localhost:8000/api/health`

**Server Unresponsive** → Fix → Restart → Verify logs clean → Retest

### 🔴 Server Health Checks (MANDATORY)

Always use timeout on health checks. Never rely on default.

```bash
curl -m 3 http://localhost:8000/api/health
curl -m 3 http://localhost:3000/health
```

**Only mark operational if**:
- Endpoint returns quickly (<3s)
- Response matches expected format
- Server logs show clean startup (no fatal errors)