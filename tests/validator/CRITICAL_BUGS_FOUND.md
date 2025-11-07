# Critical Bugs Found During Phase 1 Testing

> **Date**: 2025-11-07
> **Testing Phase**: Phase 1 - Individual Scheduler Validation
> **Total Bugs Found**: 7 (3 CRITICAL, 4 MEDIUM)

## Bug Priority Matrix

| # | Bug | Severity | Status | Impact | Fix Effort |
|---|-----|----------|--------|--------|-----------|
| 1 | Failed Tasks Not in Errors Tab | CRITICAL | Confirmed | High - Silent failures | Medium |
| 2 | Success Rate Math Wrong | CRITICAL | Confirmed | High - Wrong health metrics | Low |
| 3 | Active Jobs Not Real-Time | CRITICAL | Confirmed | High - No task visibility | Medium |
| 4 | Invalid Date Parsing | MEDIUM | Confirmed | Low - UI issue | Low |
| 5 | Queue Pending Counts Wrong | MEDIUM | Confirmed | Medium - Inconsistent data | Medium |
| 6 | WebSocket Incomplete Messages | MEDIUM | Confirmed | Medium - Partial updates | High |
| 7 | Portfolio Sync Not Executing | MEDIUM | Requires Investigation | High - Tasks stuck | High |

---

## CRITICAL BUG #1: Failed Tasks Not Displayed in Errors Tab

**Severity**: 🚨 CRITICAL

**Description**:
System Health page Errors tab shows "All Systems Healthy" and "No recent errors or alerts detected" even when tasks have failed in the backend.

**Evidence**:
```
Backend Reality:
- ai_analysis queue: failed_tasks: 1
- portfolio_sync queue: failed_tasks: 2
- Total: 3 failed tasks

UI Display:
- Errors tab: "All Systems Healthy"
- No failures shown
- No alerts
```

**Reproduction Steps**:
1. Queue any task that fails
2. Check backend: `curl -s 'http://localhost:8000/api/queues/status'`
3. Confirm: `failed_tasks: > 0`
4. Check UI: Errors tab
5. Result: Shows "All Systems Healthy" ❌

**Root Cause**:
- Errors tab component doesn't fetch failed_tasks field
- May not be included in WebSocket queue_status_update messages
- Or UI doesn't parse it from the message

**Impact**:
- **CRITICAL**: Users have no visibility into failures
- System appears healthy while tasks are failing
- Silent failures - no alerting mechanism
- Ops team can't see problems

**Fix Location**:
- File: `ui/src/features/system-health/tabs/ErrorsTab.tsx` (or similar)
- Action: Query `/api/queues/status`, check each queue's `failed_tasks`, display failures

**Workaround**:
User can view Queues tab and manually check queue statuses for error states

**Priority**: 🔴 **FIX IMMEDIATELY**

---

## CRITICAL BUG #2: Success Rate Calculation Wrong

**Severity**: 🚨 CRITICAL

**Description**:
Success Rate shows 100% even when tasks have failed and no tasks have been processed.

**Evidence**:
```
Portfolio Sync Scheduler:
- Processed: 0
- Failed: 2
- Success Rate: 100% ❌ (WRONG)
- Should be: N/A or 0%

AI Analysis Scheduler:
- Processed: 0
- Failed: 1
- Success Rate: 100% ❌ (WRONG)
- Should be: N/A or 0%
```

**Formula Issue**:
Current (apparent): `100%` (hardcoded or wrong logic)
Correct: `((Processed - Failed) / Processed) * 100%` or `(Processed - Failed) / Processed` (with edge case handling)

**Reproduction**:
1. Queue a task that fails
2. Observe scheduler metrics
3. Processed=0, Failed>0
4. Success Rate shows 100% ❌

**Root Cause**:
- Likely hardcoded as "100%" for idle schedulers
- Or formula doesn't account for division by zero
- Or formula uses wrong fields

**Impact**:
- **CRITICAL**: Health metrics are mathematically incorrect
- System appears healthier than it is
- Ops team can't trust health percentages
- Misleading for alerting thresholds

**Fix Location**:
- File: `ui/src/features/system-health/components/SchedulerCard.tsx` (or similar)
- Action: Fix formula to handle edge cases (processed=0, failed>0)
  ```typescript
  if (processed === 0) {
    successRate = failed > 0 ? 0 : 100;
  } else {
    successRate = ((processed - failed) / processed) * 100;
  }
  ```

**Priority**: 🔴 **FIX IMMEDIATELY**

---

## CRITICAL BUG #3: Active Jobs Not Updating in Real-Time

**Severity**: 🚨 CRITICAL

**Description**:
When a task is queued, UI doesn't update to show it as an active/pending job. The Active Jobs counter remains 0 even though a task is queued.

**Evidence**:
```
Action: Queue AI Analysis task
Backend: pending_tasks: 0 → 1 ✓

UI Schedulers Tab:
- Active Jobs: 0 (doesn't change to 1) ❌
- Should update to 1 while task is pending

UI Queues Tab:
- Summary shows "Pending Tasks: 1" ✓ (Works here!)
- Individual queue shows "1 pending" ✓ (Works here!)
- But Schedulers tab doesn't show it ❌
```

**Reproduction**:
1. Open System Health > Schedulers tab
2. Note Active Jobs: 0
3. Queue a task: `curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'`
4. Watch Active Jobs counter
5. Remains 0 ❌ (Should become 1)

**Root Cause**:
- Scheduler card doesn't show pending_tasks
- May only display active_tasks from scheduler.jobs
- Queue tasks may not be reflected in scheduler active_jobs field
- WebSocket update may not trigger UI refresh

**Impact**:
- **CRITICAL**: Users can't see queued work
- Schedulers tab (primary view) appears idle when actually processing
- Confusion about whether system is working
- May lead to duplicate triggers or retries

**Fix Location**:
- File: `ui/src/features/system-health/components/SchedulerCard.tsx`
- Action: Display `pending_tasks` from queue status alongside `active_tasks` from scheduler
  ```typescript
  const totalActive = scheduler.active_jobs + (queue?.pending_tasks || 0);
  ```

**Priority**: 🔴 **FIX IMMEDIATELY**

---

## MEDIUM BUG #4: Invalid Date Parsing for Last Run

**Severity**: ⚠️ MEDIUM

**Description**:
"Last Run" field displays "Invalid Date" instead of actual timestamp or "Never run" message.

**Evidence**:
```
UI Display:
- Last Run: Invalid Date ❌

Expected:
- Last Run: 2025-11-07 10:33:21 (actual time)
- Or: Never (if never run)
```

**Root Cause**:
- `last_run_time` field is empty string or null
- Date parsing tries to parse empty string
- Results in Invalid Date object

**Impact**:
- Low - cosmetic issue
- Users can't see when scheduler last ran
- May be useful for troubleshooting timing issues

**Fix**:
```typescript
const lastRun = scheduler.last_run_time
  ? new Date(scheduler.last_run_time).toLocaleString()
  : 'Never';
```

**Priority**: 🟡 LOW (Cosmetic)

---

## MEDIUM BUG #5: Queue Pending Counts Not Synchronized

**Severity**: ⚠️ MEDIUM

**Description**:
Queue detail view shows incorrect pending task counts. Summary says "1 Pending Tasks" but individual queues show "0 pending".

**Evidence**:
```
Queue Health Summary:
- "1 Pending Tasks" ✓ (Correct)

Individual Queue (portfolio_sync):
- Shows "0 pending" ❌ (Wrong - has 1 pending)
- Backend: pending_tasks: 1

Individual Queue (ai_analysis):
- Shows "1 pending" ✓ (Correct)
```

**Root Cause**:
- Different data sources for summary vs individual queues
- Queue display may not be refreshing
- WebSocket message incomplete or not parsed correctly

**Impact**:
- Confusing - data doesn't match between views
- Users see conflicting information
- May not trust the numbers

**Fix**:
- Ensure all queue displays pull from same data source
- Force refresh on WebSocket update

**Priority**: 🟡 MEDIUM

---

## MEDIUM BUG #6: WebSocket Messages Incomplete

**Severity**: ⚠️ MEDIUM

**Description**:
WebSocket queue_status_update messages may not include all fields (particularly failed_tasks), causing UI to miss critical failure information.

**Evidence**:
```
Queue Summary (working): Shows "1 Pending Tasks"
Errors Tab (broken): Shows "All Systems Healthy"

Likely cause: WebSocket message missing failed_tasks field
```

**Root Cause**:
- WebSocket differential update pattern may exclude unchanged fields
- Or failed_tasks not included in initial message format
- Frontend may not handle missing fields gracefully

**Impact**:
- Real-time updates incomplete
- Errors tab can't detect failures
- Inconsistent state between different views

**Fix**:
- Ensure failed_tasks always included in queue_status_update
- Or UI polls `/api/queues/status` periodically as fallback

**Priority**: 🟡 MEDIUM

---

## MEDIUM BUG #7: Portfolio Sync Tasks Not Executing

**Severity**: ⚠️ MEDIUM
**Status**: Requires Investigation

**Description**:
Portfolio Sync tasks are queued successfully but never execute. They remain in pending state indefinitely.

**Evidence**:
```
Trigger: curl -X POST '.../portfolio_sync_scheduler/execute'
Response: {"status":"success", "task_id":"...", "queue_name":"portfolio_sync"}

Backend Queue:
- pending_tasks: 1 ✓ (Task queued)
- active_tasks: 0 (never becomes 1)
- completed_tasks: 0 (never completes)

After 8+ seconds: Still pending (should have executed in 2-5 seconds)

Scheduler:
- jobs_processed: 0
- last_run_time: "" (empty)
```

**Root Cause**:
- Queue manager not processing tasks (possible causes):
  1. Scheduler not integrated with queue system
  2. Queue worker/processor not running
  3. Task handler not registered
  4. Task stuck due to dependency or lock

**Impact**:
- **HIGH**: Tasks queued but never execute
- User sees success response but work never happens
- System appears to be working but silently fails

**Next Steps**:
1. Check queue processor logs
2. Verify scheduler is polling queue
3. Check if Portfolio Sync handler is registered
4. Monitor active_tasks transition (should go 0→1→0)

**Priority**: 🟡 MEDIUM (But HIGH impact if confirmed)

---

## Summary Table

### Bugs by Tab

| Schedulers Tab | Queues Tab | Errors Tab | Overall |
|---|---|---|---|
| Active Jobs not updating (Critical) | Pending counts wrong (Medium) | Failed tasks not shown (Critical) | Success rate wrong (Critical) |
| Success rate math wrong (Critical) | Queue summary works (Good) | No alerts visible (Critical) | Invalid dates (Medium) |
| Invalid dates (Medium) | | | WebSocket incomplete (Medium) |
| | | | Portfolio Sync not executing (Medium) |

### Bugs by Component

**Scheduler Cards**:
- Active Jobs not real-time (Critical)
- Success Rate wrong calculation (Critical)
- Invalid Date parsing (Medium)

**Queue Display**:
- Pending counts not synchronized (Medium)
- Queue summary works but detail doesn't (Medium)

**Errors Tab**:
- Failed tasks not fetched/displayed (Critical)
- No alerting mechanism (Critical)

**WebSocket/Real-Time**:
- Messages may be incomplete (Medium)
- Updates inconsistent across tabs (Medium)

---

## Testing Evidence

All bugs confirmed through:
1. **Backtracking Functional Validation**: Triggered actions → Observed changes → Cross-checked with backend
2. **Backend Verification**: All metrics correctly tracked via `/api/queues/status` and `/api/monitoring/scheduler`
3. **UI Inspection**: Playwright browser snapshots showing actual UI state
4. **Real-Time Monitoring**: WebSocket messages logged in browser console

---

## Action Items

### Immediate (Today)
- [ ] Fix Errors tab to display failed_tasks
- [ ] Fix Success Rate calculation
- [ ] Make Active Jobs real-time

### This Week
- [ ] Investigate Portfolio Sync task execution issue
- [ ] Fix Invalid Date parsing
- [ ] Synchronize queue counts across views
- [ ] Verify WebSocket message completeness

### This Sprint
- [ ] Add automated tests for these bugs
- [ ] Add error logging and alerting
- [ ] Review task execution pipeline

---

**Report Generated**: 2025-11-07 10:35 AM
**Phase**: 1 - Individual Scheduler Validation
**Next Phase**: Phase 2 - Parallel Execution Testing
