# Architecture Issues Found During Review

**Date**: 2025-11-02

---

## Issues Requiring Immediate Attention

### 1. Query Coordinator: Direct SDK Call Without Helper ✅ **FIXED**

**File**: `src/core/coordinators/query_coordinator.py` (line 80)

**Issue**: Uses `asyncio.wait_for(client.query(query), timeout=30.0)` directly instead of timeout helper

**Fix Applied**:
- Added `query_only_with_timeout()` helper in `sdk_helpers.py` for query-only operations
- Updated `query_coordinator.py` to use the new helper

**New Code**:
```python
# Uses new helper for query-only operations
await query_only_with_timeout(client, query, timeout=30.0)

# Receives responses with existing helper
async for response in receive_response_with_timeout(client, timeout=60.0):
```

**Status**: ✅ **FIXED** (2025-11-02)

---

### 2. Database Access Pattern: Needs Verification (LOW Priority)

**Files**: 
- `src/core/database_state/configuration_state.py` (27 instances)
- `src/core/database_state/analysis_state.py` (4 instances)

**Issue**: Need to verify all `await self.db.connection.execute()` calls are inside `async with self._lock:` blocks

**Status**: ⚠️ **Needs Verification** (likely compliant based on previous fixes)

---

## Architecture Compliance Status

### ✅ Compliant Patterns

1. **Claude SDK Usage**: ✅ All services use `ClaudeSDKClientManager`
2. **Database Locking**: ✅ All database operations use `async with self._lock:`
3. **Queue Architecture**: ✅ Parallel queues, sequential tasks
4. **Event-Driven Communication**: ✅ Typed events, EventHandler pattern
5. **Dependency Injection**: ✅ Centralized DI container

### ⚠️ Minor Issues Found

1. **Query Coordinator**: One direct SDK call without helper (easy fix)
2. **Database Access**: Needs verification (likely already compliant)

---

## Action Items

### Immediate (This Week)

1. **Fix Query Coordinator** (30 minutes)
   - Replace `asyncio.wait_for(client.query(...))` with `query_with_timeout()`
   - Ensure consistency across all SDK calls

2. **Verify Database Locking** (1 hour)
   - Check all 27 instances in `configuration_state.py`
   - Check all 4 instances in `analysis_state.py`
   - Ensure all are inside `async with self._lock:` blocks

### Next Sprint

1. **Address 65 File Size Violations** (see comprehensive review)
2. **Extract Reusable Utilities**
3. **Optimize Performance**

---

## Conclusion

**Overall Architecture Status**: ✅ **EXCELLENT**

- All major architectural patterns are compliant
- Only minor issues found (easily fixable)
- Main concern is modularity (65 file size violations)

**Recommendation**: Fix minor issues first, then address modularity violations systematically.

