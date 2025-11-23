# Robo-Trader Specific Patterns Reference

> **Purpose**: Comprehensive reference of robo-trader architectural patterns for detection and analysis
> **Last Updated**: 2025-11-09

## Queue Handler Patterns

### Detection Targets
- Files: `src/services/scheduler/handlers/*.py`
- Pattern: Classes with `@task_handler()` decorator or inheriting from `TaskHandler`
- Evidence: Import from `src.services.scheduler.task_handler` or `src.services.scheduler.queue_manager`

### Known Queue Names
- `PORTFOLIO_SYNC` - Portfolio operations and trading
- `DATA_FETCHER` - Market data fetching and analysis
- `AI_ANALYSIS` - Claude-powered analysis and decisions (CRITICAL)
- `FORECAST_ANALYSIS` - Stock forecast predictions
- `SENTIMENT_ANALYSIS` - News sentiment analysis
- `SIGNAL_DETECTION` - Trading signal detection
- `RISK_ASSESSMENT` - Risk calculation and monitoring

### Known Task Types
- `RECOMMENDATION_GENERATION` - AI analysis task
- `PORTFOLIO_SYNC` - Portfolio update task
- `DATA_FETCH` - Market data task
- `EARNINGS_FETCH` - Earnings data task
- `NEWS_FETCH` - News data task
- `SIGNAL_CALCULATION` - Signal generation task
- `FORECAST_CALCULATION` - Forecast generation task

### Documentation Reference
- Location: `src/CLAUDE.md` or `src/core/CLAUDE.md`
- Section: "Sequential Queue Architecture (CRITICAL)"
- Critical Rule: All Claude analysis must use AI_ANALYSIS queue

## Coordinator Patterns

### Detection Targets
- Files: `src/core/coordinators/*.py`
- Pattern: Classes inheriting from `BaseCoordinator`
- Structure: Max 150 lines per coordinator, single responsibility

### Known Coordinators
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `BroadcastCoordinator` - Real-time UI updates
- `PortfolioCoordinator` - Portfolio operations
- `AgentCoordinator` - Multi-agent coordination
- `MessageCoordinator` - Inter-agent communication
- `QueueCoordinator` - Queue management

### Documentation Reference
- Location: `src/core/CLAUDE.md`
- Section: "Coordinator Layer"
- Critical Rule: Max 150 lines, single responsibility, inherit from BaseCoordinator

## Database Access Patterns

### Locked Access (✅ CORRECT)
```python
# Use ConfigurationState locked methods
config_state = await container.get("configuration_state")
success = await config_state.store_analysis_history(...)
success = await config_state.store_recommendation(...)
```

### Direct Access (❌ WRONG - Causes Locks)
```python
# NEVER do this - bypasses locking
database = await container.get("database")
await database.connection.execute(...)
```

### Detection Rules
- VIOLATION: Direct calls to `db.connection.execute()` in any file
- VIOLATION: Direct calls to `database.connection.commit()`
- CORRECT: Calls to `config_state.store_*()` methods
- CORRECT: Calls to `config_state.get_*()` methods

### Documentation Reference
- Location: `CLAUDE.md` → "Database & State Management" section
- Critical Rule: "Never access database directly via `config_state.db.connection.execute()`. Use locked state methods instead."

## SDK Usage Patterns

### Correct Usage (✅)
```python
# Always use ClaudeSDKClientManager
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)
response = await query_with_timeout(client, prompt, timeout=60)
```

### Critical Constraint
- Timeout protection required: `await query_with_timeout(client, prompt, timeout=60.0)`
- Session turn limits: ~50 turns per session
- Batch analysis: 81 stocks = ~40 tasks × 2-3 stocks each

### Detection Rules
- VIOLATION: Direct Anthropic API calls (should use SDK only)
- VIOLATION: SDK calls without timeout protection
- VIOLATION: Analyzing large portfolios in single session (turn limit exhaustion)
- CORRECT: All Claude calls via ClaudeSDKClientManager singleton

### Documentation Reference
- Location: `CLAUDE.md` → "AI Integration: Claude Agent SDK"
- Critical Rule: "All AI functionality uses Claude Agent SDK only. NO direct Anthropic API calls."

## Event-Driven Patterns

### Detection Targets
- Pattern: Classes implementing event publishing/subscribing
- Files: Services that emit `EventBus` events

### Correct Event Emission
```python
await self.event_bus.publish(Event(
    type=EventType.PORTFOLIO_POSITION_CHANGE,
    data={"symbol": symbol, "quantity": quantity}
))
```

### Detection Rules
- PATTERN: Service emitting events for state changes
- VIOLATION: Direct service-to-service calls for cross-cutting concerns
- CORRECT: All inter-service communication via EventBus

### Documentation Reference
- Location: `src/services/CLAUDE.md`
- Section: "Event-Driven Communication"
- Critical Rule: "Services MUST emit events for state changes"

## Error Handling Patterns

### Correct Pattern
```python
# Use custom exception types inheriting from TradingError
raise TradingError(
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.HIGH,
    code="INVALID_SYMBOL",
    metadata={"symbol": symbol}
)
```

### Detection Rules
- VIOLATION: Generic `Exception` raises without context
- VIOLATION: Stack traces exposed to UI
- CORRECT: Custom TradingError with rich context
- CORRECT: Structured error logging

### Documentation Reference
- Location: `src/CLAUDE.md` → "Error Handling"
- Critical Rule: "Custom exception types inherit from TradingError"

## Async/Await Patterns

### Correct Pattern
```python
# Use asyncio.wait_for for timeout protection
try:
    result = await asyncio.wait_for(async_operation(), timeout=5.0)
except asyncio.TimeoutError:
    logger.error("Operation timed out")
```

### Anti-Pattern Detection (❌ WRONG)
```python
# NEVER use time.sleep() in async code
time.sleep(1)  # Blocks all async operations!

# Use condition polling instead
while not condition:
    await asyncio.sleep(0.1)
```

### Detection Rules
- ANTI-PATTERN: `time.sleep()` in async functions (3+ occurrences)
- VIOLATION: Blocking I/O in async context
- CORRECT: `await asyncio.sleep()` for delays
- CORRECT: Timeout protection on all async operations

### Documentation Reference
- Location: `CLAUDE.md` → "Async-First Design"
- Critical Rule: "All I/O is non-blocking: Use `async/await`"

## Modularization Patterns

### Detection Rules
- VIOLATION: Files exceeding 350 lines
- VIOLATION: Classes with >10 methods
- VIOLATION: Functions with >50 lines without single responsibility
- CORRECT: Single responsibility per file
- CORRECT: Max 350 lines per file
- CORRECT: Max 10 methods per class

### Documentation Reference
- Location: `CLAUDE.md` → "Code Quality Standards"
- Section: "Modularization (ENFORCED)"

## Frontend Component Patterns

### Correct Organization
- Location: `ui/src/features/[feature-name]/`
- Structure: Self-contained modules with main component + internal components
- Naming: `DashboardPage.tsx`, `DashboardMetrics.tsx` (kebab-case files)

### State Management
- Use Zustand stores, not prop drilling
- Custom hooks for API interactions
- Local component state for UI state only

### Detection Rules
- PATTERN: Feature-based organization in `ui/src/features/`
- VIOLATION: Components >350 lines
- VIOLATION: Prop drilling more than 2 levels
- CORRECT: Zustand for shared state
- CORRECT: Custom hooks for API calls

### Documentation Reference
- Location: `ui/src/CLAUDE.md` → "Feature-Based Organization"
- Critical Rule: "Use TypeScript, not JavaScript"

## Anti-Patterns (Common Mistakes)

### Database Lock Contention
- **What**: Direct database access during long-running operations (30+ seconds)
- **Why**: Bypasses ConfigurationState's asyncio.Lock()
- **Fix**: Use `config_state.store_*()` locked methods
- **Detection**: Direct `db.connection.execute()` calls

### Turn Limit Exhaustion
- **What**: Analyzing 81 stocks in single Claude session (~100+ turns needed)
- **Why**: Each interaction consumes 1 turn, limited turns per session
- **Fix**: Queue analysis to AI_ANALYSIS queue (2-3 stocks per task)
- **Detection**: Direct analyzer calls with large stock portfolios

### Blocking Async Operations
- **What**: Using `time.sleep()` in async context
- **Why**: Blocks all async operations, no other tasks can run
- **Fix**: Use `await asyncio.sleep()` or condition polling
- **Detection**: `time.sleep()` in async functions

### Missing Error Context
- **What**: Generic exceptions without structured metadata
- **Why**: Difficult to debug, no rich error information
- **Fix**: Use TradingError with category/severity/code/metadata
- **Detection**: Bare `Exception()` raises

### Portfolio Analysis Inefficiency
- **What**: Analyzing all stocks regardless of age
- **Why**: Redundant API calls, wasted computational effort
- **Fix**: Prioritize unanalyzed > oldest > skip
- **Detection**: No smart scheduling logic in `_get_stocks_with_updates()`

## Learning Rules

### High-Confidence Patterns (80-100%)
- Exact code matches (same pattern in 5+ files)
- Critical violations (documented constraints)
- Documented anti-patterns appearing 4+ times

### Medium-Confidence Patterns (60-80%)
- Similar patterns in 3-4 files
- Edge case violations
- Anti-patterns appearing 2-3 times

### Low-Confidence Patterns (40-60%)
- New patterns appearing only 2-3 times
- Potential violations (ambiguous code)
- Single anti-pattern occurrence

### Feedback Adjustments
- Accepted recommendation: +5% confidence for similar patterns
- Rejected recommendation: -10% confidence (may be false positive)
- No feedback: Keep baseline confidence
