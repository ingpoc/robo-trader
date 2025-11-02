# Architecture Violations Report

Generated: 2025-01-27

This document identifies violations of the established architecture patterns documented in `CLAUDE.md` and layer-specific `CLAUDE.md` files.

## Executive Summary

The codebase has **critical architectural violations** that need to be addressed:

1. **CRITICAL**: Direct database access bypassing locked state methods (49+ instances)
2. **HIGH**: Coordinator size violations (3 coordinators exceed 150-line limit)
3. **HIGH**: Direct Claude SDK client creation bypassing client manager (14+ instances)
4. **MEDIUM**: Potential direct service calls instead of event-driven communication
5. **MEDIUM**: Missing timeout helpers in Claude SDK calls

---

## 1. CRITICAL: Direct Database Access Violations

### Rule Violated
**From `CLAUDE.md` line 312**: "Never access database directly via `config_state.db.connection.execute()`. Use locked state methods instead."

### Impact
- Database contention during concurrent operations
- Blocking other operations during long-running processes (e.g., 30+ second Claude analysis)
- Potential race conditions and data corruption

### Violations Found

#### 1.1 ConfigurationState (`src/core/database_state/configuration_state.py`)
**49 instances of direct database access**

**Examples:**
```115:116:src/core/database_state/configuration_state.py
await self.db.connection.executescript(schema)
await self.db.connection.commit()
```

```130:132:src/core/database_state/configuration_state.py
cursor = await self.db.connection.execute(
    "SELECT COUNT(*) as count FROM background_tasks_config"
)
```

**All violations in this file:**
- Lines 115-116: `_create_tables()` - direct executescript
- Lines 130-132: `_initialize_default_config()` - direct execute
- Lines 175, 194, 247, 268, 474, 490, 587, 619, 649, 701, 741, 772, 832, 872, 966, 976, 1006, 1041, 1086, 1097, 1170, 1196, 1231, 1371, 1405: Various methods with direct execute calls

**Recommended Fix:**
All database operations should be wrapped in `async with self._lock:` blocks. ConfigurationState already has a `_lock` attribute, but it's not consistently used for database operations.

#### 1.2 Other State Managers
**Additional violations found in:**
- `src/core/database_state/news_earnings_state.py` - 7 instances
- `src/core/database_state/approval_state.py` - 3 instances  
- `src/core/database_state/portfolio_state.py` - 2 instances
- `src/core/database_state/analysis_state.py` - 6 instances
- `src/core/database_state/intent_state.py` - 2 instances
- `src/services/claude_agent/analysis_logger.py` - 1 instance

**Note**: Some of these files use `async with self.db.connection.execute()` which is a context manager pattern, but they still bypass the state manager's locking mechanism.

---

## 2. HIGH: Coordinator Size Violations

### Rule Violated
**From `src/core/CLAUDE.md` line 114**: "❌ No more than 150 lines per coordinator"

### Impact
- Coordinators violate single responsibility principle
- Harder to maintain and test
- Indicates business logic leakage into coordination layer

### Violations Found

| Coordinator | Lines | Limit | Over by | File |
|------------|-------|-------|---------|------|
| StatusCoordinator | 626 | 150 | 476 | `src/core/coordinators/status_coordinator.py` |
| ClaudeAgentCoordinator | 615 | 150 | 465 | `src/core/coordinators/claude_agent_coordinator.py` |
| QueueCoordinator | 536 | 150 | 386 | `src/core/coordinators/queue_coordinator.py` |
| TaskCoordinator | 367 | 150 | 217 | `src/core/coordinators/task_coordinator.py` |
| MessageCoordinator | 332 | 150 | 182 | `src/core/coordinators/message_coordinator.py` |
| BroadcastCoordinator | 326 | 150 | 176 | `src/core/coordinators/broadcast_coordinator.py` |

### Recommended Fix
Split large coordinators into focused sub-coordinators or extract business logic into service classes.

**Example Split Strategy for StatusCoordinator:**
- `SystemStatusCoordinator` - System health status
- `AIStatusCoordinator` - AI agent status  
- `AgentStatusCoordinator` - Multi-agent status
- `ServiceStatusCoordinator` - Service health status

---

## 3. HIGH: Direct Claude SDK Client Creation

### Rule Violated
**From `CLAUDE.md` line 98**: "Always use client manager: `client_manager = await ClaudeSDKClientManager.get_instance()`"

**From `src/core/CLAUDE.md` line 523**: "**SDK Client Manager**: Use `ClaudeSDKClientManager` - never create direct `ClaudeSDKClient`"

### Impact
- Performance degradation (no singleton reuse)
- Potential session exhaustion
- Missing timeout protection
- Inconsistent client lifecycle management

### Violations Found

#### 3.1 Direct ClaudeSDKClient Creation (14+ instances)

**Files with violations:**

1. **`src/core/orchestrator.py:261`**
```python
return ClaudeSDKClient(options=self.options)
```
**Fix**: Should use `ClaudeSDKClientManager.get_instance().get_client()`

2. **`src/core/conversation_manager.py:185`**
```python
self.client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

3. **`src/core/coordinators/claude_agent_coordinator.py:225`**
```python
self.client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

4. **`src/core/coordinators/session_coordinator.py:100`**
```python
self.client = ClaudeSDKClient(options=self.options)
```
**Fix**: Should use client manager

5. **`src/services/recommendation_service.py:748`**
```python
self.claude_client = ClaudeSDKClient(options=self.claude_options)
```
**Fix**: Should use client manager

6. **`src/services/paper_trading_execution_service.py:501`**
```python
self._client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

7. **`src/core/strategy_evolution_engine.py:614`**
```python
self.client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

8. **`src/core/multi_agent_framework.py:250`**
```python
self.client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

9. **`src/core/learning_engine.py:817`**
```python
self.client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

10. **`src/core/ai_planner.py:767`**
```python
self.client = ClaudeSDKClient(options=options)
```
**Fix**: Should use client manager

#### 3.2 Missing Timeout Helpers

**Rule Violated**: **From `CLAUDE.md` line 102**: "Always use timeout helpers: `response = await query_with_timeout(client, prompt, timeout=60)`"

**Violations:**
- `src/services/recommendation_service.py:760` - Direct `client.query()` without timeout wrapper
- `src/services/recommendation_service.py:764` - Direct `client.receive_response()` without timeout wrapper

---

## 4. MEDIUM: Event-Driven Communication Violations

### Rule Violated
**From `CLAUDE.md` line 72**: "No direct service-to-service calls for cross-cutting concerns"

**From `src/services/CLAUDE.md` line 192**: "❌ NEVER directly call other services (emit events instead)"

### Potential Violations

#### 4.1 Direct Service Call in Task Handler
**File**: `src/core/di_registry_core.py:151`

```python
return await analyzer.analyze_portfolio_intelligence(
    agent_name=task.payload["agent_name"],
    symbols=symbols_to_analyze,
    batch_info={...}
)
```

**Analysis**: This is within a task handler, which may be acceptable as it's part of the task execution flow. However, it should be reviewed to ensure it follows event-driven patterns where appropriate.

#### 4.2 Direct Database Connection Access
**File**: `src/web/routes/configuration.py:399`

```python
fundamental_executor = FundamentalExecutor(
    perplexity_client,
    state_manager.db.connection,  # Direct connection access
    event_bus,
    execution_tracker
)
```

**Analysis**: This violates the rule of not accessing database connections directly. Should use state manager methods instead.

---

## 5. MEDIUM: Missing Error Handling Patterns

### Rule Violated
**From `CLAUDE.md` line 263**: "Catch at entry points: Log with structured information"

### Potential Issues

Some service methods may not have proper error handling with `TradingError` inheritance, though this requires deeper code review.

---

## Priority Fix Recommendations

### Phase 1: CRITICAL (Immediate)
1. **Fix ConfigurationState database access** (49 violations)
   - Wrap all `db.connection.execute()` calls in `async with self._lock:`
   - Create locked wrapper methods for common operations
   - Estimated effort: 2-3 days

### Phase 2: HIGH (This Sprint)
2. **Fix direct Claude SDK client creation** (14+ violations)
   - Replace all `ClaudeSDKClient()` with `ClaudeSDKClientManager.get_instance().get_client()`
   - Add timeout helpers to all SDK calls
   - Estimated effort: 1-2 days

3. **Fix coordinator size violations** (6 coordinators)
   - Split `StatusCoordinator` (626 lines) into 3-4 focused coordinators
   - Split `ClaudeAgentCoordinator` (615 lines) into focused components
   - Split `QueueCoordinator` (536 lines) if needed
   - Estimated effort: 3-5 days

### Phase 3: MEDIUM (Next Sprint)
4. **Fix remaining state manager database access**
   - Ensure all state managers use locking consistently
   - Remove direct connection access in web routes
   - Estimated effort: 1-2 days

---

## Verification Checklist

After fixes, verify:
- [ ] No direct `db.connection.execute()` calls outside of locked methods
- [ ] All coordinators under 150 lines
- [ ] All Claude SDK clients created via `ClaudeSDKClientManager`
- [ ] All SDK calls use timeout helpers (`query_with_timeout`, `receive_response_with_timeout`)
- [ ] All service-to-service communication uses EventBus
- [ ] All database operations in state managers use locks

---

## Additional Notes

### Acceptable Patterns
- Task handlers calling services directly (if part of task execution flow)
- Database operations within locked state manager methods
- Coordinators delegating to services (this is correct pattern)

### Architecture Patterns Correctly Followed
- ✅ Dependency Injection container pattern
- ✅ Event-driven communication (in most places)
- ✅ Error hierarchy with TradingError
- ✅ Async-first design (most code uses async/await)
- ✅ Coordinator pattern (structure is correct, just size violations)

---

## Conclusion

The codebase follows most architectural patterns correctly, but has **critical violations** in:
1. Database access patterns (bypassing locks)
2. Coordinator size limits (business logic leakage)
3. Claude SDK client management (missing singleton pattern)

These should be addressed to prevent:
- Database contention issues
- Performance degradation
- Maintainability problems
- Session/turn limit exhaustion

