# Comprehensive Scheduler Validation Plan

> **Status**: Active
> **Last Updated**: 2025-11-08
> **Testing Methodology**: Backtracking Functional Validation (BFV)
> **Scope**: All 7 Schedulers in System Health Page

---

## Executive Summary

This document outlines a comprehensive testing plan to validate all 7 schedulers in the System Health monitoring page. Using **behavior-driven backtracking validation**, we will:

1. Identify what backend actions would change each scheduler metric
2. Execute those actions programmatically
3. Monitor real-time metric changes via WebSocket
4. Verify data accuracy across all layers (UI → Store → API → Backend → Database)
5. Validate error detection and reporting

---

## Validation Methodology: Backtracking Functional Validation (BFV)

### Core Principle
Start from **UI observation** → Work **backwards** to identify what backend actions would change metrics → **Execute** those actions → **Verify** real-time updates via WebSocket

### Pattern
```
Observation: "I see Data Fetcher Scheduler showing 2 done"
↓
Backward Question: "What backend action creates completed tasks?"
↓
Answer: "Task execution in data_fetcher queue completes tasks"
↓
Trigger Action: "Create NEWS_MONITORING task in data_fetcher queue"
↓
Expected Change: "Pending +1, then Running +1, then Completed +1"
↓
Verify: "Monitor WebSocket messages and UI updates in real-time"
```

---

## Testing Infrastructure

### Test Script Location
```
/Users/gurusharan/Documents/remote-claude/robo-trader/test_scheduler_validation.py
```

### Script Capabilities

```bash
# List all available schedulers and test configurations
python test_scheduler_validation.py --list-schedulers

# List all available queue names
python test_scheduler_validation.py --list-queues

# List all available task types
python test_scheduler_validation.py --list-task-types

# Test specific scheduler with default task
python test_scheduler_validation.py --scheduler portfolio_sync

# Test scheduler with specific task
python test_scheduler_validation.py --scheduler data_fetcher --task news_monitoring

# Test AI Analysis (long-running task)
python test_scheduler_validation.py --scheduler ai_analysis --task recommendation_generation
```

---

## Scheduler Testing Specifications

### 1. Background Scheduler (Event-Driven)

**Type**: Event-driven, not queue-based
**Description**: Responds to domain events and creates tasks in other queues

#### Metrics to Validate
- ✅ Uptime (increments continuously)
- ✅ Processed (count of event handling executions)
- ✅ Failed (count of failed event handling)
- ✅ Success Rate (processed / (processed + failed))
- ✅ Last Run (timestamp of last execution)
- ✅ Active Jobs (always 0, event-driven)

#### Trigger Actions

**Action 1: Portfolio Update Event**
```
Trigger: Publish PORTFOLIO_POSITION_CHANGE event
Expected:
  - Tasks processed +1
  - Creates tasks in PORTFOLIO_SYNC queue
  - Last run updates
Method: Via event bus (internal trigger)
```

**Action 2: Market News Event**
```
Trigger: Publish MARKET_NEWS event
Expected:
  - Tasks processed +1
  - Creates task in AI_ANALYSIS queue
Method: Via event bus (internal trigger)
```

#### Verification Steps
1. Baseline: Capture "Processed" count (currently 0)
2. Trigger: Publish portfolio_updated event
3. Observe: execution_history array increases
4. Verify: Tasks created in PORTFOLIO_SYNC queue
5. Confirm: Last run timestamp updates

#### Expected Behavior
- Event handling completes quickly (< 1 second)
- Execution history populated with event details
- Tasks created in dependent queues visible

---

### 2. Portfolio Sync Scheduler

**Type**: Queue-based (Sequential execution)
**Queue**: `portfolio_sync`
**Description**: Syncs account balances, updates positions, validates portfolio risks

#### Task Types Available
```
TaskType.SYNC_ACCOUNT_BALANCES      # Priority 10
TaskType.UPDATE_POSITIONS           # Priority 9
TaskType.CALCULATE_OVERNIGHT_PNL    # Priority 8
TaskType.VALIDATE_PORTFOLIO_RISKS   # Priority 8
```

#### Metrics to Validate
- ✅ Uptime (increments continuously)
- ✅ Processed (count of completed tasks today)
- ✅ Failed (count of failed tasks)
- ✅ Success Rate ((processed / (processed + failed)) * 100)
- ✅ Last Run (timestamp of last task completion)
- ✅ Active Jobs (1 during execution, 0 when idle)

#### Test Case 1: SYNC_ACCOUNT_BALANCES

**Setup**
```bash
python test_scheduler_validation.py --scheduler portfolio_sync --task sync_balances
```

**Execution Timeline**
```
T+0s:   Task created (Pending +1)
        WebSocket: queue_status_update {pending: 1}
        UI updates: "Portfolio Sync Scheduler ... 0 done"

T+1-5s: Task starts executing (Running +1, Pending -1)
        WebSocket: queue_status_update {running: 1, pending: 0}
        UI updates: Expand scheduler to see active job

T+5-10s: Task completes (Completed +1, Running -1)
        WebSocket: queue_status_update {completed: 1, running: 0}
        UI updates: "Portfolio Sync Scheduler ... 1 done" (if successful)

T+10s:  Final state
        Metrics: Processed=1, Failed=0, Success Rate=100%
```

**Expected Outcome**
- ✅ Pending count increases then decreases
- ✅ Active Jobs shows 1 during execution
- ✅ Completed count increases after task finishes
- ✅ Success rate recalculates
- ✅ Last run timestamp updates
- ✅ WebSocket messages received for each state change

#### Test Case 2: UPDATE_POSITIONS

```bash
python test_scheduler_validation.py --scheduler portfolio_sync --task update_positions
```

Same validation as Test Case 1, with position data instead of balance sync.

#### Baseline Metrics
```
Current State (Baseline):
  Uptime: ~X minutes
  Processed: 0
  Failed: 0
  Success Rate: N/A
  Last Run: Never
  Active Jobs: 0
```

#### Verification Checklist
- [ ] Task created successfully
- [ ] Pending count shows 1
- [ ] Active Jobs increases to 1
- [ ] Task completes within expected time (5-10s)
- [ ] Processed count increments
- [ ] Success rate updates correctly
- [ ] Last Run timestamp is current
- [ ] WebSocket messages logged in browser console
- [ ] No error messages in Errors tab

---

### 3. Data Fetcher Scheduler

**Type**: Queue-based (Sequential execution)
**Queue**: `data_fetcher`
**Description**: Fetches market data, news, earnings, fundamentals

#### Current State
```
Baseline: Processed=2, Failed=0, Success Rate=100%
```

#### Task Types Available
```
TaskType.NEWS_MONITORING            # Priority 8-9
TaskType.EARNINGS_CHECK             # Priority 7
TaskType.EARNINGS_SCHEDULER         # Priority 7
TaskType.FUNDAMENTALS_UPDATE        # Priority 7
```

#### Test Case 1: NEWS_MONITORING

**Setup**
```bash
python test_scheduler_validation.py --scheduler data_fetcher --task news_monitoring
```

**Expected Changes**
```
Before:  Processed=2, Failed=0, Success Rate=100%

After:   Processed=3, Failed=0, Success Rate=100%
         Last Run: <current timestamp>
         Active Jobs: 0 (completed)
```

**Execution Flow**
1. Create NEWS_MONITORING task with symbols: ["SBIN", "TCS", "INFY"]
2. Monitor pending count (should be 1)
3. Wait for active_jobs = 1
4. Task processes news for specified stocks
5. Task completes: processed=3
6. Verify execution history populated

**Duration**: ~5-10 seconds per task

#### Test Case 2: EARNINGS_CHECK

```bash
python test_scheduler_validation.py --scheduler data_fetcher --task earnings_check
```

**Expected Changes**
```
Processed: 2 → 3 (after completion)
Failed: 0 (no failures expected)
```

#### Smart Scheduling Validation

**Verify**: Data fetcher only processes stocks with oldest timestamps
- Check: `StockStateStore` consulted before API calls
- Confirm: Only 5 stocks processed per task max
- Validate: No redundant API calls for recently updated stocks

#### Verification Checklist
- [ ] Task created successfully
- [ ] Pending count shows 1
- [ ] Task executes within 10 seconds
- [ ] Processed count increments by 1
- [ ] Failed count remains 0
- [ ] Success rate stays 100%
- [ ] Last Run updates
- [ ] Execution history shows processor name (news_processor)
- [ ] WebSocket updates received

---

### 4. AI Analysis Scheduler

**Type**: Queue-based (Sequential execution - CRITICAL)
**Queue**: `ai_analysis`
**Description**: Claude-powered analysis and recommendations (CRITICAL: Sequential to prevent turn limit exhaustion)

#### ⚠️ CRITICAL ARCHITECTURE NOTE

**Why Sequential?**
- Analyzing 81 stocks in one Claude session = ~100+ turns needed
- Each task analyzes 2-3 stocks in isolated session = Full turn limit available
- Sequential execution prevents turn limit exhaustion

**Timeout**: 900 seconds (15 minutes) per task

#### Current State
```
Baseline: Processed=0, Failed=6, Success Rate=0%
```

#### Task Types Available
```
TaskType.RECOMMENDATION_GENERATION       # Priority 7
TaskType.CLAUDE_MORNING_PREP             # Priority varies
TaskType.CLAUDE_EVENING_REVIEW           # Priority varies
TaskType.CLAUDE_NEWS_ANALYSIS            # Priority 8
TaskType.CLAUDE_EARNINGS_REVIEW          # Priority 8
TaskType.CLAUDE_FUNDAMENTAL_ANALYSIS     # Priority 8
```

#### Test Case 1: RECOMMENDATION_GENERATION (CRITICAL - 5-10 MINUTES)

**Setup**
```bash
python test_scheduler_validation.py --scheduler ai_analysis --task recommendation_generation
```

**Expected Changes**
```
Before:  Processed=0, Failed=6, Success Rate=0%

After:   Processed=1, Failed=6, Success Rate=14% (1/(1+6))
         Last Run: <current timestamp>
         Active Jobs: 0 (completed after 5-10 min)
```

**Execution Timeline**
```
T+0s:    Task created
         WebSocket: queue_status_update {pending: 1}
         Pending count: 1

T+1-5s:  Task starts
         Active Jobs: 1
         WebSocket: queue_status_update {running: 1}

T+5-600s: Claude analysis in progress
         Monitor: Backend logs show Claude API calls
         Task: Analyzes 2-3 stocks with full session context

T+600s:  Task completes (or times out)
         WebSocket: queue_status_update {completed: 1}
         Processed: 0 → 1
         Success Rate: 0% → 14%
         Last Run: Updates to completion time
```

**Expected Behavior**
- Active Jobs shows 1 during entire execution (5-10+ minutes)
- No other AI tasks execute (sequential queue)
- Backend logs show Claude API interactions
- Task completion timestamp logged
- Analysis results stored in database

#### Test Case 2: CLAUDE_NEWS_ANALYSIS

```bash
python test_scheduler_validation.py --scheduler ai_analysis --task news_analysis
```

Similar to Test Case 1, but analyzes news impact on portfolio.

#### Monitoring During Execution

**Watch For**:
```
✅ Active Jobs = 1 (for entire duration)
✅ Running count = 1 (sequential)
✅ No other tasks in queue executing (sequential queue behavior)
✅ Backend logs show Claude API calls
✅ Browser console shows WebSocket queue_status_update messages
✅ Timeout not exceeded (max 900 seconds)
```

#### Verification Checklist
- [ ] Task created successfully
- [ ] Pending count shows 1
- [ ] Active Jobs shows 1 immediately
- [ ] Task executes for 5-10+ minutes
- [ ] No timeout errors (watch for 900s limit)
- [ ] Task completes successfully
- [ ] Processed count increments to 1
- [ ] Failed count stays at 6 (previous failures unresolved)
- [ ] Success rate updates to 14%
- [ ] Last Run timestamp is current
- [ ] Execution history shows analysis details
- [ ] Analysis results in database/transparency logs
- [ ] No other queue tasks execute simultaneously (sequential proof)

#### Important Notes
- **⏱️ Duration**: 5-10+ minutes (have patience!)
- **🔍 Monitoring**: Keep System Health page open to watch progress
- **📊 Real-Time**: WebSocket updates will show running progress
- **💾 Results**: Check `/api/claude/transparency/analysis` for results
- **🚨 Errors**: If timeout occurs, increase 900s limit in queue_manager.py

---

### 5. Portfolio Analysis Scheduler

**Type**: Queue-based (Sequential execution)
**Queue**: `portfolio_analysis`
**Description**: Comprehensive portfolio analysis and recommendations

#### Current State
```
Baseline: Processed=0, Failed=0, Success Rate=N/A
```

#### Task Types Available
```
TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS        # Priority 7
TaskType.PORTFOLIO_RECOMMENDATION_UPDATE        # Priority 6
TaskType.PORTFOLIO_DATA_OPTIMIZATION            # Priority 6
TaskType.PROMPT_TEMPLATE_OPTIMIZATION           # Priority 5
```

#### Test Case 1: PORTFOLIO_INTELLIGENCE_ANALYSIS

**Setup**
```bash
python test_scheduler_validation.py --scheduler portfolio_analysis --task portfolio_intelligence
```

**Expected Changes**
```
Before:  Processed=0, Failed=0, Success Rate=N/A

After:   Processed=1, Failed=0, Success Rate=100%
         Last Run: <current timestamp>
         Active Jobs: 0 (completed)
```

**Execution Timeline**
```
T+0s:   Task created (Pending +1)
T+1-5s: Task starts (Active Jobs = 1)
T+5-30s: Analysis in progress
T+30s:  Task completes (Processed +1)
```

**Expected Behavior**
- Similar to data fetcher (completes within 30 seconds)
- Portfolio analyzed holistically
- Results stored in portfolio_analysis table
- Success rate calculates correctly

#### Verification Checklist
- [ ] Task created successfully
- [ ] Pending count shows 1
- [ ] Active Jobs shows 1 during execution
- [ ] Task completes within 30 seconds
- [ ] Processed count increments to 1
- [ ] Success rate updates to 100%
- [ ] Last Run timestamp is current
- [ ] Execution history populated
- [ ] Analysis data stored in database

---

### 6. Paper Trading Research Scheduler

**Type**: Queue-based (Sequential execution)
**Queue**: `paper_trading_research`
**Description**: Market research and trading strategy development

#### Current State
```
Baseline: Processed=0, Failed=0, Success Rate=N/A
```

#### Task Types Available
```
TaskType.MARKET_RESEARCH_PERPLEXITY             # Priority 7
TaskType.STOCK_SCREENING_ANALYSIS              # Priority 6
TaskType.TRADING_STRATEGY_DEVELOPMENT          # Priority 6
TaskType.RESEARCH_DATA_SYNTHESIS               # Priority 5
```

#### Test Case 1: MARKET_RESEARCH_PERPLEXITY

**Setup**
```bash
python test_scheduler_validation.py --scheduler paper_trading_research --task market_research
```

**Expected Changes**
```
Before:  Processed=0, Failed=0, Success Rate=N/A

After:   Processed=1, Failed=0, Success Rate=100%
         Last Run: <current timestamp>
```

**Execution Flow**
1. Create MARKET_RESEARCH_PERPLEXITY task
2. Task calls Perplexity API for research
3. Research synthesized and stored
4. Task completes successfully

**Expected Duration**: ~10-20 seconds

#### Verification Checklist
- [ ] Task created successfully
- [ ] Pending count shows 1
- [ ] Active Jobs shows 1
- [ ] Task completes within 30 seconds
- [ ] Processed count increments
- [ ] Success rate updates to 100%
- [ ] Last Run timestamp updates
- [ ] Research results stored in database
- [ ] Execution history populated

---

### 7. Paper Trading Execution Scheduler

**Type**: Queue-based (Sequential execution)
**Queue**: `paper_trading_execution`
**Description**: Paper trading execution and performance tracking

#### Current State
```
Baseline: Processed=0, Failed=0, Success Rate=N/A
```

#### Task Types Available
```
TaskType.PAPER_TRADE_EXECUTION                 # Priority 7
TaskType.STRATEGY_BACKTESTING                  # Priority 6
TaskType.TRADE_RISK_VALIDATION                 # Priority 7
TaskType.PAPER_PERFORMANCE_TRACKING            # Priority 6
```

#### Test Case 1: PAPER_TRADE_EXECUTION

**Setup**
```bash
python test_scheduler_validation.py --scheduler paper_trading_execution --task paper_trade_execution
```

**Expected Changes**
```
Before:  Processed=0, Failed=0, Success Rate=N/A

After:   Processed=1, Failed=0, Success Rate=100%
         Last Run: <current timestamp>
```

**Execution Flow**
1. Create PAPER_TRADE_EXECUTION task
2. Task validates trade risk
3. Task executes paper trade
4. Trade result stored
5. P&L tracked

**Expected Duration**: ~5-10 seconds

#### Verification Checklist
- [ ] Task created successfully
- [ ] Pending count shows 1
- [ ] Active Jobs shows 1
- [ ] Task completes within 15 seconds
- [ ] Processed count increments
- [ ] Success rate updates to 100%
- [ ] Last Run timestamp updates
- [ ] Trade result stored in database
- [ ] P&L calculated and tracked
- [ ] Execution history populated

---

## Real-Time Monitoring Setup

### Browser Console Monitoring

**Open DevTools Console** and watch for WebSocket messages:

```javascript
// Log all WebSocket messages
window.addEventListener('message', (e) => {
  if (e.data.type?.includes('update')) {
    console.log('📊 WebSocket Update:', e.data)
  }
})
```

**Expected Messages During Testing**:
```
queue_status_update {
  queues: {
    portfolio_sync: {
      pending_tasks: 1,
      active_tasks: 0,
      completed_tasks: 0,
      failed_tasks: 0
    }
  }
}

system_health_update {
  schedulers: [...],
  timestamp: "2025-11-08T13:23:44.112Z"
}
```

### API Monitoring

**During Task Execution**, monitor queue status:

```bash
# Watch queue metrics in real-time (every 2 seconds)
watch -n 2 'curl -s http://localhost:8000/api/monitoring/scheduler | python3 -m json.tool | grep -A 10 "portfolio_sync"'
```

### Execution History Tracking

**Expand Scheduler** in UI to view:
```
Active Jobs: Shows currently executing task
Execution History: Lists completed/failed tasks with details
  - Task ID
  - Start time
  - Duration
  - Status (completed/failed)
  - Error message (if failed)
```

---

## Failure Testing

### Test Case: Task Failure

**Objective**: Verify failed task tracking

**Setup**
```bash
# Create task with invalid payload (will fail)
python test_scheduler_validation.py --scheduler portfolio_sync --task sync_balances
# Modify payload to cause failure before execution
```

**Expected Behavior**
```
Before:  Failed=0
After:   Failed=1

Metrics Updated:
  - Failed count: 0 → 1
  - Success rate: 100% → 0%
  - Execution history shows error message
  - Error details logged in database
```

**Verification Steps**
1. Create task that will fail
2. Monitor failed count
3. Verify error logged in execution_history
4. Check error message in UI
5. Confirm success rate recalculated

### Test Case: Task Retry

**Objective**: Verify retry mechanism (if implemented)

**Setup**
1. Create failing task
2. Verify failed_count increments
3. Wait for automatic retry (if configured)
4. Monitor retry_count in execution_history

---

## Validation Checklist Template

For each scheduler tested, use this checklist:

```markdown
## [SCHEDULER_NAME] Testing Checklist

### Pre-Test
- [ ] Backend running and healthy
- [ ] Frontend connected
- [ ] System Health page open
- [ ] Baseline metrics captured

### Task Creation
- [ ] Test script executed successfully
- [ ] Task ID returned
- [ ] No error messages in logs

### Real-Time Monitoring
- [ ] WebSocket messages logged
- [ ] Pending count increased
- [ ] Active Jobs shows 1 during execution
- [ ] No WebSocket disconnections

### Task Completion
- [ ] Task completed successfully
- [ ] Processed count incremented
- [ ] Active Jobs returned to 0
- [ ] Last Run timestamp updated

### Metrics Validation
- [ ] Uptime incrementing
- [ ] Processed count accurate
- [ ] Failed count accurate
- [ ] Success rate calculated correctly
- [ ] Execution history populated

### Database Verification
- [ ] Task stored in queue_tasks table
- [ ] Status tracked (pending→running→completed)
- [ ] Results stored appropriately

### UI Verification
- [ ] Metrics visible in Schedulers tab
- [ ] Execution history displayed when expanded
- [ ] No error messages in Errors tab
- [ ] WebSocket updates shown in console
```

---

## Known Issues & Workarounds

### Issue 1: Backend Restart Loses Temporary State
**Solution**: Database persists all metrics. No workaround needed.

### Issue 2: AI Analysis Timeout (>900 seconds)
**Symptom**: Task doesn't complete after 15 minutes
**Cause**: Complex analysis or slow Claude API
**Workaround**: Increase timeout in `src/services/scheduler/queue_manager.py:139`

### Issue 3: WebSocket Messages Not Appearing
**Symptom**: Metrics don't update in real-time
**Cause**: WebSocket connection lost
**Solution**: Refresh page to reconnect

### Issue 4: Failed Tasks Not Clearing
**Symptom**: Failed count high after fixes
**Cause**: Previous execution failures still in database
**Solution**: Database retains history (expected). New successful tasks improve success rate.

---

## Test Execution Order

**Recommended Sequence** (shortest to longest):

1. **Portfolio Sync Scheduler** (5-10 seconds)
2. **Data Fetcher Scheduler** (5-10 seconds)
3. **Portfolio Analysis Scheduler** (5-30 seconds)
4. **Paper Trading Research Scheduler** (10-20 seconds)
5. **Paper Trading Execution Scheduler** (5-15 seconds)
6. **AI Analysis Scheduler** ⏱️ (5-10 MINUTES - do last!)
7. **Background Scheduler** (event-based, test throughout)

---

## Success Criteria

All schedulers are **fully operational** when:

✅ All 7 schedulers show "running" status
✅ Metrics update in real-time via WebSocket
✅ Task creation → execution → completion flows smoothly
✅ Uptime increments continuously
✅ Processed/Failed counts accurate
✅ Success rates calculate correctly
✅ Last Run timestamps update
✅ Active Jobs show/hide during execution
✅ Execution history populated with details
✅ No database lock contention errors
✅ No WebSocket disconnection issues

---

## References

- **Test Script**: `/Users/gurusharan/Documents/remote-claude/robo-trader/test_scheduler_validation.py`
- **Queue Management**: `src/services/scheduler/queue_manager.py`
- **Scheduler Models**: `src/models/scheduler.py`
- **Task Storage**: `src/stores/scheduler_task_store.py`
- **Coordinator**: `src/core/coordinators/queue/queue_coordinator.py`
- **Monitoring API**: `src/web/routes/monitoring.py`

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-08 | 1.0 | Initial comprehensive plan created |

