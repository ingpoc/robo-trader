# Scheduler Validation Testing Guide

> **Document Type**: System Health Testing Methodology - Schedulers Tab
> **Last Updated**: 2025-11-07 | **Testing Approach**: Backtracking Functional Validation
> **Purpose**: Dynamic validation of all 7 schedulers through action triggers and real-time metric observation

## Overview

This document provides comprehensive validation testing for the **Schedulers** tab in the System Health page. Unlike static testing, this methodology emphasizes **triggering actual scheduler actions** and **observing real-time metric changes** to validate that the UI accurately reflects backend state.

**Core Testing Principle**: "Every number you see, trigger an action to make it change" - then verify the UI updates correctly.

---

## System Health Schedulers Architecture

### 7 Schedulers Overview

The system manages 7 distinct schedulers executing background tasks:

| # | Scheduler Name | Type | Queue | Purpose | Duration | Real-Time? |
|---|---|---|---|---|---|---|
| 1 | **Background Scheduler** | Event-Driven | N/A | Reacts to system events | Varies | Yes |
| 2 | **Portfolio Sync Scheduler** | Queue-Based | PORTFOLIO_SYNC | Syncs holdings from broker | 2-5 sec | Yes |
| 3 | **Data Fetcher Scheduler** | Queue-Based | DATA_FETCHER | Fetches market data (OHLC, etc.) | 5-15 sec | Yes |
| 4 | **AI Analysis Scheduler** | Queue-Based | AI_ANALYSIS | Runs Claude analysis on stocks | 30-60 sec | Yes |
| 5 | **Portfolio Analysis Scheduler** | Queue-Based | PORTFOLIO_ANALYSIS | Analyzes portfolio risk metrics | 10-20 sec | Yes |
| 6 | **Paper Trading Research Scheduler** | Queue-Based | PAPER_TRADING_RESEARCH | Pre-analysis for paper trades | 15-30 sec | Yes |
| 7 | **Paper Trading Execution Scheduler** | Queue-Based | PAPER_TRADING_EXECUTION | Executes paper trades (simulated) | 5-10 sec | Yes |

---

## 1. Background Scheduler Tests

**Scheduler Type**: Event-Driven (reacts to system events)
**Metrics to Monitor**: Event count, completion rate, event types
**Critical Bug Found**: None specific to this scheduler

### 1.1 Basic Metrics Display Test
- **Field to Test**: Scheduler summary card showing "Background Scheduler" count
- **Expected Display**: Name, status (running/stopped), uptime
- **How to Trigger**: Observe initial load (no action needed)
- **Expected Change**: Metrics displayed on page load
- **Verification**: Visual inspection of summary card
- **Pass Criteria**: Scheduler listed in summary with accurate status

### 1.2 Event Type Tracking Test
- **Field to Test**: Event types processed (shown in expanded view)
- **Expected Display**: Event type names and counts
- **How to Trigger**:
  1. Observe initial state
  2. Generate system event (portfolio change, configuration update, etc.)
  3. Verify event is tracked
- **Expected Change**: Event count increments when events occur
- **Verification**: Event count in scheduler detail increases
- **Pass Criteria**: Event counts match actual events fired

### 1.3 Completion Rate Test
- **Field to Test**: "jobs_processed" counter
- **Expected Display**: Number of events successfully handled
- **How to Trigger**: Generate multiple system events
- **Expected Change**: Counter increments per event
- **Verification**: Check `/api/monitoring/scheduler` endpoint
- **Pass Criteria**: Counter accurately reflects events processed

### 1.4 Event-Driven Responsiveness Test
- **Field to Test**: Real-time update on WebSocket
- **Expected Display**: Immediate update when event fired
- **How to Trigger**:
  1. Watch Schedulers tab in System Health
  2. Trigger any configuration change
  3. Observe metrics update in real-time
- **Expected Change**: WebSocket delivers update within 1 second
- **Verification**: UI updates without page refresh
- **Pass Criteria**: Real-time update visible without delay

### 1.5 Uptime Tracking Test
- **Field to Test**: "uptime_seconds" counter
- **Expected Display**: Seconds since scheduler started
- **How to Trigger**:
  1. Note uptime value at time T1
  2. Wait 10 seconds
  3. Refresh page at time T2
- **Expected Change**: uptime_seconds increases by ~10
- **Verification**: Simple math: uptime_T2 ≈ uptime_T1 + 10 (±1 second)
- **Pass Criteria**: Uptime increments with elapsed time

### 1.6 Failed Events Tracking Test (CRITICAL BUG AREA)
- **Field to Test**: "jobs_failed" counter
- **Expected Display**: Count of failed event handlers
- **How to Trigger**:
  1. Trigger event that causes error (invalid config, API timeout, etc.)
  2. Observe jobs_failed counter
- **Expected Change**: Counter increments when error occurs
- **Verification**: Check `/api/monitoring/scheduler` response
- **Known Issue**: **UI may not display failed_tasks** - this is a bug!
- **Pass Criteria**: Backend tracks failures (even if UI doesn't show)

### 1.7 Active Jobs Monitoring Test
- **Field to Test**: "active_jobs" counter
- **Expected Display**: Number of events currently being processed
- **How to Trigger**:
  1. Trigger long-running event handler
  2. Quickly check active_jobs counter
- **Expected Change**: Counter increases during processing
- **Verification**: active_jobs > 0 during processing, = 0 when idle
- **Pass Criteria**: Counter reflects actual processing state

---

## 2. Portfolio Sync Scheduler Tests

**Scheduler Type**: Queue-Based (PORTFOLIO_SYNC queue)
**Metrics to Monitor**: Sync count, holdings updated, sync duration
**Typical Duration**: 2-5 seconds per sync

### 2.1 Basic Metrics Display Test
- **Field to Test**: "Portfolio Sync Scheduler" in summary
- **Expected Display**: Name, status (running/waiting), queue name
- **How to Trigger**: Observe initial load
- **Expected Change**: Visible in Schedulers tab
- **Verification**: Summary card shows scheduler
- **Pass Criteria**: Displayed with correct queue name

### 2.2 Trigger Portfolio Sync Test
- **Field to Test**: Pending/Active task counters
- **Expected Display**: Number of pending sync tasks
- **How to Trigger**:
  ```bash
  curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_sync_scheduler/execute'
  ```
- **Expected Change**:
  - Before: pending_tasks = 0, active_tasks = 0, completed_tasks = N
  - After trigger: pending_tasks = 1 (briefly), then active_tasks = 1
  - After completion: pending_tasks = 0, active_tasks = 0, completed_tasks = N+1
- **Verification**: Check Queues tab PORTFOLIO_SYNC queue status
- **Pass Criteria**: Task flows from pending → active → completed

### 2.3 Sync Duration Measurement Test
- **Field to Test**: Task execution duration
- **Expected Display**: Completion time in UI
- **How to Trigger**: Trigger sync and monitor
- **Expected Change**: Duration 2-5 seconds typical
- **Verification**: Monitor task execution time
- **Pass Criteria**: Execution completes in expected timeframe

### 2.4 Holdings Count Update Test
- **Field to Test**: Portfolio holdings count
- **Expected Display**: Number of holdings after sync
- **How to Trigger**:
  1. Trigger portfolio sync
  2. Observe holdings count change
- **Expected Change**: Count updates after sync completion
- **Verification**: Cross-check with `/api/portfolio/holdings` endpoint
- **Pass Criteria**: Holdings count reflects actual broker data

### 2.5 Last Sync Timestamp Test
- **Field to Test**: "last_updated" timestamp
- **Expected Display**: ISO 8601 timestamp
- **How to Trigger**: Trigger sync, note timestamp
- **Expected Change**: Timestamp updates to sync completion time
- **Verification**: Check configuration_state database
- **Pass Criteria**: Timestamp matches sync completion

### 2.6 Sync Failure Handling Test
- **Field to Test**: "jobs_failed" counter
- **Expected Display**: Failed sync attempts
- **How to Trigger**:
  1. Disconnect broker API
  2. Trigger sync
  3. Observe failure
- **Expected Change**: jobs_failed increments
- **Verification**: Check scheduler metrics and logs
- **Known Issue**: **UI may show "All Systems Healthy" despite failure**
- **Pass Criteria**: Backend tracks failure (bug: UI doesn't display)

### 2.7 Concurrent Sync Prevention Test
- **Field to Test**: active_tasks counter (max 1)
- **Expected Display**: Only one sync can run at a time
- **How to Trigger**:
  1. Trigger sync 1
  2. Before completion, trigger sync 2
  3. Observe both are queued, only 1 active
- **Expected Change**: active_tasks stays at 1, pending_tasks = 1
- **Verification**: Only one task executes at a time
- **Pass Criteria**: Queue prevents concurrent execution

---

## 3. Data Fetcher Scheduler Tests

**Scheduler Type**: Queue-Based (DATA_FETCHER queue)
**Metrics to Monitor**: Data fetch count, API calls, rate limit handling
**Typical Duration**: 5-15 seconds per batch
**Known Issues**: Rate limit failures, API timeouts

### 3.1 Basic Metrics Display Test
- **Field to Test**: "Data Fetcher Scheduler" in summary
- **Expected Display**: Name, queue (DATA_FETCHER), status
- **How to Trigger**: Observe initial load
- **Expected Change**: Visible in Schedulers tab
- **Verification**: Summary card shows scheduler
- **Pass Criteria**: Displayed with correct details

### 3.2 Trigger Data Fetch Test
- **Field to Test**: Pending/Active counters
- **Expected Display**: Number of data fetch tasks
- **How to Trigger**:
  ```bash
  curl -X POST 'http://localhost:8000/api/configuration/schedulers/data_fetcher_scheduler/execute'
  ```
- **Expected Change**: pending_tasks = 1 → active_tasks = 1 → completed_tasks++
- **Verification**: Check DATA_FETCHER queue status
- **Pass Criteria**: Task executes and completes

### 3.3 Market Data Update Test
- **Field to Test**: OHLC data freshness
- **Expected Display**: Latest price, volume, timestamp
- **How to Trigger**: Trigger data fetch, wait for completion
- **Expected Change**: Data timestamp updates to fetch time
- **Verification**: Compare timestamps before/after
- **Pass Criteria**: Data reflects recent market activity

### 3.4 Rate Limit Handling Test (CRITICAL)
- **Field to Test**: jobs_failed counter during rate limit
- **Expected Display**: Failed fetch attempts
- **How to Trigger**:
  1. Trigger data fetch multiple times rapidly (3-5 times)
  2. Observe for rate limit errors
  3. Check jobs_failed counter
- **Expected Change**: Some tasks may fail with rate limit error
- **Verification**: Check backend logs for rate limit messages
- **Known Issue**: **Failures not displayed in UI Errors tab**
- **Pass Criteria**: Backend handles gracefully, retries with backoff

### 3.5 API Timeout Handling Test
- **Field to Test**: Task timeout behavior
- **Expected Display**: Completion or timeout after N seconds
- **How to Trigger**:
  1. Simulate slow API (use network throttling or API mock)
  2. Trigger data fetch
  3. Monitor execution
- **Expected Change**: Task completes or fails after timeout
- **Verification**: Check logs for timeout messages
- **Pass Criteria**: Timeout prevents indefinite hanging

### 3.6 Retry Logic Test
- **Field to Test**: Task retry attempts
- **Expected Display**: Retry count in logs or metrics
- **How to Trigger**:
  1. Trigger fetch to failed API
  2. Monitor retry behavior
  3. Check retry count
- **Expected Change**: Task retries with exponential backoff
- **Verification**: Check scheduler logs for "retry" messages
- **Pass Criteria**: Retries follow exponential backoff pattern

### 3.7 Batch Processing Test
- **Field to Test**: Data points fetched per task
- **Expected Display**: Number of stocks/symbols processed
- **How to Trigger**: Trigger fetch with multiple symbols
- **Expected Change**: Metrics show batch size processed
- **Verification**: Compare input symbols to output data
- **Pass Criteria**: All requested symbols fetched in one task

---

## 4. AI Analysis Scheduler Tests

**Scheduler Type**: Queue-Based (AI_ANALYSIS queue)
**Metrics to Monitor**: Analysis count, Claude API calls, turn limits
**Typical Duration**: 30-60 seconds per analysis
**CRITICAL ISSUE**: Task failures not displayed in UI

### 4.1 Basic Metrics Display Test
- **Field to Test**: "AI Analysis Scheduler" in summary
- **Expected Display**: Name, queue (AI_ANALYSIS), status
- **How to Trigger**: Observe initial load
- **Expected Change**: Visible in Schedulers tab
- **Verification**: Summary card shows scheduler
- **Pass Criteria**: Displayed with correct details

### 4.2 Trigger AI Analysis Test
- **Field to Test**: Pending/Active counters
- **Expected Display**: Number of analysis tasks
- **How to Trigger**:
  ```bash
  curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'
  ```
- **Expected Change**: pending_tasks = 1 → active_tasks = 1 → completed_tasks++
- **Verification**: Check AI_ANALYSIS queue status
- **Pass Criteria**: Task queued and executes

### 4.3 Analysis Duration Measurement Test
- **Field to Test**: Task execution time
- **Expected Display**: Analysis duration (30-60+ seconds typical)
- **How to Trigger**: Trigger analysis and monitor
- **Expected Change**: Duration reflects Claude API response time
- **Verification**: Monitor task execution duration
- **Pass Criteria**: Task completes within expected timeframe

### 4.4 Claude Turn Limit Test (CRITICAL)
- **Field to Test**: Turn usage per analysis
- **Expected Display**: Turns consumed per task
- **How to Trigger**:
  1. Trigger analysis on large portfolio
  2. Monitor Claude session turns
  3. Check if turn limit exceeded
- **Expected Change**: Turns increment per Claude interaction
- **Known Issue**: Large portfolios (81 stocks) in single session can exceed turn limits
- **Verification**: Check Claude SDK logs for turn limit errors
- **Pass Criteria**: Queue prevents turn limit exhaustion (batches analysis)

### 4.5 Analysis Results Storage Test
- **Field to Test**: Analysis stored to database
- **Expected Display**: Analysis accessible via `/api/claude/transparency/analysis`
- **How to Trigger**:
  1. Trigger analysis
  2. Wait for completion
  3. Call `/api/claude/transparency/analysis` endpoint
- **Expected Change**: Analysis results appear in transparency API
- **Verification**: Check configuration_state analysis_history table
- **Pass Criteria**: Results persisted and retrievable

### 4.6 Failed Analysis Detection Test (CRITICAL BUG)
- **Field to Test**: failed_tasks counter in AI_ANALYSIS queue
- **Expected Display**: Failed analysis count in UI (BUG: NOT DISPLAYED)
- **How to Trigger**:
  1. Note failed_tasks = 0 in backend
  2. Trigger analysis with invalid prompt
  3. Observe task failure
  4. Check `/api/queues/status` → ai_analysis queue
- **Expected Change**: failed_tasks increments
- **Verification**:
  ```bash
  curl -s 'http://localhost:8000/api/queues/status' | jq '.[] | select(.name=="ai_analysis")'
  # Returns: {"name":"ai_analysis","failed_tasks":1,...}
  ```
- **Known Issue**: **CRITICAL BUG - UI shows "All Systems Healthy" despite failed_tasks: 1**
- **UI Bug Location**: Errors tab doesn't parse or display failed_tasks from WebSocket
- **Pass Criteria**: Backend correctly tracks failures (UI bug confirmed)

### 4.7 Queue vs Direct Call Test
- **Field to Test**: Task execution behavior
- **Expected Display**: Analysis completes successfully via queue
- **How to Trigger**:
  1. Compare direct API call vs queue submission
  2. Direct call: May hit turn limits on large portfolio
  3. Queue call: Batches analysis to prevent turn limit exhaustion
- **Expected Change**: Queue approach completes, direct approach may fail
- **Verification**: Monitor queue task count vs API call response
- **Pass Criteria**: Queue prevents turn limit failures

---

## 5. Portfolio Analysis Scheduler Tests

**Scheduler Type**: Queue-Based (PORTFOLIO_ANALYSIS queue)
**Metrics to Monitor**: Analysis count, risk metrics, correlation analysis
**Typical Duration**: 10-20 seconds per analysis

### 5.1 Basic Metrics Display Test
- **Field to Test**: "Portfolio Analysis Scheduler" in summary
- **Expected Display**: Name, queue (PORTFOLIO_ANALYSIS), status
- **How to Trigger**: Observe initial load
- **Expected Change**: Visible in Schedulers tab
- **Verification**: Summary card shows scheduler
- **Pass Criteria**: Displayed with correct details

### 5.2 Trigger Portfolio Analysis Test
- **Field to Test**: Pending/Active counters
- **Expected Display**: Number of analysis tasks
- **How to Trigger**:
  ```bash
  curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_analysis_scheduler/execute'
  ```
- **Expected Change**: pending_tasks = 1 → active_tasks = 1 → completed_tasks++
- **Verification**: Check PORTFOLIO_ANALYSIS queue status
- **Pass Criteria**: Task executes to completion

### 5.3 Risk Metrics Calculation Test
- **Field to Test**: Risk metrics (Sharpe ratio, Sortino, VaR, etc.)
- **Expected Display**: Updated risk scores after analysis
- **How to Trigger**: Trigger analysis, wait for completion
- **Expected Change**: Risk metrics reflect current portfolio composition
- **Verification**: Compare metrics before/after analysis
- **Pass Criteria**: Metrics calculated accurately

### 5.4 Correlation Matrix Update Test
- **Field to Test**: Stock correlation data
- **Expected Display**: Correlation matrix updated
- **How to Trigger**: Trigger portfolio analysis
- **Expected Change**: Correlation data refreshed
- **Verification**: Check analytics database for updated correlations
- **Pass Criteria**: Correlations reflect recent price movements

### 5.5 Analysis Caching Test
- **Field to Test**: Cache hit rate for analyses
- **Expected Display**: Analysis reuse from cache
- **How to Trigger**:
  1. Trigger analysis 1 (cache miss)
  2. Immediately trigger analysis 2 (cache hit possible)
  3. Monitor timing
- **Expected Change**: Second analysis may complete faster
- **Verification**: Check cache hit metrics
- **Pass Criteria**: Caching improves repeated analysis performance

### 5.6 Stale Analysis Detection Test
- **Field to Test**: Analysis age threshold
- **Expected Display**: Analysis marked stale if > N hours old
- **How to Trigger**:
  1. Trigger analysis
  2. Wait for configured staleness timeout
  3. Trigger new analysis
- **Expected Change**: Old analysis marked stale, new analysis created
- **Verification**: Check analysis_history table timestamps
- **Pass Criteria**: Stale detection prevents using outdated risk metrics

### 5.7 Multi-Asset Class Analysis Test
- **Field to Test**: Cross-asset risk analysis
- **Expected Display**: Risk metrics account for all asset types
- **How to Trigger**: Add multiple asset types, trigger analysis
- **Expected Change**: Risk metrics reflect diversification
- **Verification**: Check risk calculations for accuracy
- **Pass Criteria**: Multi-asset risk properly calculated

---

## 6. Paper Trading Research Scheduler Tests

**Scheduler Type**: Queue-Based (PAPER_TRADING_RESEARCH queue)
**Metrics to Monitor**: Research count, recommendation generation, analysis depth
**Typical Duration**: 15-30 seconds per research task

### 6.1 Basic Metrics Display Test
- **Field to Test**: "Paper Trading Research Scheduler" in summary
- **Expected Display**: Name, queue (PAPER_TRADING_RESEARCH), status
- **How to Trigger**: Observe initial load
- **Expected Change**: Visible in Schedulers tab
- **Verification**: Summary card shows scheduler
- **Pass Criteria**: Displayed with correct details

### 6.2 Trigger Paper Trading Research Test
- **Field to Test**: Pending/Active counters
- **Expected Display**: Number of research tasks
- **How to Trigger**:
  ```bash
  curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_research_scheduler/execute'
  ```
- **Expected Change**: pending_tasks = 1 → active_tasks = 1 → completed_tasks++
- **Verification**: Check PAPER_TRADING_RESEARCH queue status
- **Pass Criteria**: Task queues and executes

### 6.3 Research Data Collection Test
- **Field to Test**: Fundamental and technical data gathered
- **Expected Display**: Data points collected during research
- **How to Trigger**: Trigger research, monitor data gathering
- **Expected Change**: Research analysis shows data sources used
- **Verification**: Check research logs for data collection
- **Pass Criteria**: All required data sources queried

### 6.4 Recommendation Generation Test
- **Field to Test**: Trading recommendation generated
- **Expected Display**: Buy/Sell/Hold recommendation with confidence
- **How to Trigger**: Trigger research and wait for completion
- **Expected Change**: Recommendation appears in research results
- **Verification**: Check `/api/claude/transparency/research` endpoint
- **Pass Criteria**: Recommendation generated and stored

### 6.5 Recommendation Justification Test
- **Field to Test**: Analysis reasoning for recommendation
- **Expected Display**: Detailed justification of recommendation
- **How to Trigger**: Trigger research, examine recommendation detail
- **Expected Change**: Justification includes factors analyzed
- **Verification**: Check transparency API response
- **Pass Criteria**: Justification is comprehensive and traceable

### 6.6 Risk Assessment Test
- **Field to Test**: Risk factors identified in research
- **Expected Display**: Risk summary in recommendation
- **How to Trigger**: Trigger research on volatile stock
- **Expected Change**: Risk factors reflected in recommendation
- **Verification**: Check recommendation risk level
- **Pass Criteria**: Risk assessment impacts confidence score

### 6.7 Multiple Symbol Research Test
- **Field to Test**: Batch research processing
- **Expected Display**: Multiple stocks researched in one task
- **How to Trigger**: Trigger research with portfolio of stocks
- **Expected Change**: All symbols processed in single task
- **Verification**: Check research results for all symbols
- **Pass Criteria**: Batch processing completes efficiently

---

## 7. Paper Trading Execution Scheduler Tests

**Scheduler Type**: Queue-Based (PAPER_TRADING_EXECUTION queue)
**Metrics to Monitor**: Trade count, execution success rate, order fills
**Typical Duration**: 5-10 seconds per execution
**Critical**: Executes simulated paper trades (no real money)

### 7.1 Basic Metrics Display Test
- **Field to Test**: "Paper Trading Execution Scheduler" in summary
- **Expected Display**: Name, queue (PAPER_TRADING_EXECUTION), status
- **How to Trigger**: Observe initial load
- **Expected Change**: Visible in Schedulers tab
- **Verification**: Summary card shows scheduler
- **Pass Criteria**: Displayed with correct details

### 7.2 Trigger Paper Trade Execution Test
- **Field to Test**: Pending/Active counters
- **Expected Display**: Number of execution tasks
- **How to Trigger**:
  ```bash
  curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_execution_scheduler/execute'
  ```
- **Expected Change**: pending_tasks = 1 → active_tasks = 1 → completed_tasks++
- **Verification**: Check PAPER_TRADING_EXECUTION queue status
- **Pass Criteria**: Task executes to completion

### 7.3 Order Placement Test
- **Field to Test**: Paper trade orders created
- **Expected Display**: Order ID, symbol, quantity, price
- **How to Trigger**: Trigger execution, check paper trading account
- **Expected Change**: New order appears in paper account
- **Verification**: Check `/api/paper-trading/orders` endpoint
- **Pass Criteria**: Order successfully placed in paper account

### 7.4 Order Fill Simulation Test
- **Field to Test**: Order fill status
- **Expected Display**: Order transitions from PENDING → FILLED
- **How to Trigger**:
  1. Trigger execution (creates order)
  2. Monitor order status
  3. Observe simulated fill
- **Expected Change**: Order status updates to FILLED with fill price
- **Verification**: Check order status in paper trading API
- **Pass Criteria**: Fill simulated at reasonable price

### 7.5 Position Update Test
- **Field to Test**: Paper trading positions updated
- **Expected Display**: New holdings in paper account
- **How to Trigger**: Trigger trade execution, monitor positions
- **Expected Change**: Paper account holdings reflect executed trades
- **Verification**: Check `/api/paper-trading/positions` endpoint
- **Pass Criteria**: Positions accurate after trade

### 7.6 Cash Balance Update Test
- **Field to Test**: Paper account cash balance
- **Expected Display**: Cash reduced by trade cost
- **How to Trigger**: Trigger BUY trade execution
- **Expected Change**: Cash balance decreases by (qty × fill_price)
- **Verification**: Cash balance math: balance_new = balance_old - cost
- **Pass Criteria**: Cash balance correctly updated

### 7.7 Trade History Recording Test
- **Field to Test**: Executed trades logged
- **Expected Display**: Trade appears in history with timestamp
- **How to Trigger**: Trigger execution, wait for completion
- **Expected Change**: Trade logged with full details
- **Verification**: Check `/api/paper-trading/trades` endpoint
- **Pass Criteria**: Trade recorded with accurate details

### 7.8 Slippage Simulation Test
- **Field to Test**: Price slippage on large orders
- **Expected Display**: Fill price different from expected
- **How to Trigger**: Trigger large trade execution
- **Expected Change**: Fill price includes slippage adjustment
- **Verification**: Compare expected vs actual fill price
- **Pass Criteria**: Slippage realistically simulated

### 7.9 Execution Failure Handling Test
- **Field to Test**: Failed execution handling
- **Expected Display**: Failed trades logged with reason
- **How to Trigger**:
  1. Attempt trade exceeding account balance
  2. Observe execution failure
  3. Check failed_tasks counter
- **Expected Change**: failed_tasks increments, order rejected
- **Verification**: Check scheduler logs for failure reason
- **Known Issue**: **UI may not display failure in Errors tab**
- **Pass Criteria**: Backend handles gracefully, logs reason

---

## Cross-Scheduler Validation Tests

### Test C1: Scheduler Summary Accuracy
- **Test**: Sum of all scheduler counts equals total scheduler count
- **How to Trigger**: Count individual schedulers, compare to summary
- **Expected**: Sum(individual counts) = Summary total
- **Verification**: Manual count vs summary display
- **Pass Criteria**: Numbers match exactly

### Test C2: Queue-Based Scheduler Correlation
- **Test**: Scheduler queue name matches PORTFOLIO_SYNC/DATA_FETCHER/etc.
- **How to Trigger**: Check each scheduler's queue assignment
- **Expected**: Scheduler → Queue mapping matches architecture
- **Verification**: Compare `/api/configuration/schedulers` to `/api/queues/status`
- **Pass Criteria**: Correct queue names assigned to each scheduler

### Test C3: Real-Time Update Consistency
- **Test**: WebSocket updates consistent across all schedulers
- **How to Trigger**: Trigger multiple schedulers, monitor updates
- **Expected**: All scheduler updates arrive via WebSocket
- **Verification**: Check browser network tab for WebSocket messages
- **Pass Criteria**: Updates arrive within 1 second of change

### Test C4: Task Execution Ordering
- **Test**: Tasks within same queue execute sequentially
- **How to Trigger**:
  1. Queue 3 tasks to same queue
  2. Monitor active_tasks counter
  3. Verify only 1 active at a time
- **Expected**: active_tasks never exceeds 1 per queue
- **Verification**: Check queue status continuously
- **Pass Criteria**: Sequential execution enforced

### Test C5: Scheduler Uptime Tracking
- **Test**: Each scheduler tracks uptime independently
- **How to Trigger**: Note uptime for each scheduler, wait 10 seconds
- **Expected**: Each scheduler uptime increases by ~10 seconds
- **Verification**: Compare uptime_T2 - uptime_T1 ≈ 10 for each
- **Pass Criteria**: All schedulers maintain accurate uptime

---

## Critical Issues & Known Bugs

### BUG #1: Failed Tasks Not Displayed in UI (CRITICAL)

**Description**: Task failures are tracked in backend queue state but not displayed in UI.

**Evidence**:
```bash
# Backend shows failure
curl -s 'http://localhost:8000/api/queues/status' | jq '.[] | select(.name=="ai_analysis")'
# Output: {"name":"ai_analysis","failed_tasks":1,"pending_tasks":0,"active_tasks":0,...}

# But UI shows
# "All Systems Healthy" in Errors tab - WRONG!
```

**Root Cause**:
- Backend endpoint correctly returns `failed_tasks` field
- Frontend UI doesn't parse `failed_tasks` from WebSocket `queue_status_update` messages
- Errors tab has no logic to detect failures

**Impact**:
- System appears healthy when tasks are failing
- Failures completely invisible to end users
- No alerting on critical failures

**Fix Required**:
1. Backend: Ensure `failed_tasks` included in WebSocket messages
2. Frontend: Parse and display `failed_tasks` in queue metrics
3. Errors tab: Show failures in red alert

**Test to Verify Bug**:
```bash
# Before fix:
1. Trigger AI analysis on invalid input → fails
2. Check UI Errors tab → Shows "All Systems Healthy" ❌ (WRONG)
3. Check `/api/queues/status` → Shows failed_tasks: 1 ✓ (CORRECT)

# After fix:
1. Trigger AI analysis on invalid input → fails
2. Check UI Errors tab → Shows failure alert ✓ (CORRECT)
3. Check `/api/queues/status` → Shows failed_tasks: 1 ✓ (CORRECT)
```

### BUG #2: AI Analysis Turn Limit Exhaustion (ARCHITECTURAL)

**Description**: Analyzing large portfolios (81+ stocks) in single Claude session exhausts turn limits.

**Evidence**:
- Single session turn limit: ~50 turns (configurable)
- Analyzing 81 stocks requires ~100+ turns (read, analyze, optimize, refetch)
- Result: Analysis fails partway through

**Root Cause**:
- Analysis submitted directly to Claude instead of through queue
- Queue system meant to batch analysis into 2-3 stocks per task
- Bypassing queue causes all stocks analyzed in one session

**Impact**:
- Large portfolio analysis fails with `error_max_turns`
- No graceful degradation
- User sees failure without understanding root cause

**Fix Applied**:
- All Claude analysis must go through AI_ANALYSIS queue
- Queue batches analysis automatically (2-3 stocks per task)
- Each task gets fresh Claude session with full turn budget

**Test to Verify Pattern**:
```bash
# WRONG - Direct call, will fail on 81 stocks:
curl -X POST 'http://localhost:8000/api/portfolio-scan' \
  -H "Content-Type: application/json" \
  -d '{"analyze": true}'
# Result: May fail with turn limit error

# CORRECT - Queue submission:
curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'
# Result: Batches analysis, completes successfully
```

### BUG #3: WebSocket Message Incompleteness (INFORMATIONAL)

**Description**: WebSocket `queue_status_update` messages may not include all fields.

**Evidence**:
- Some fields missing from WebSocket (e.g., `failed_tasks`)
- Frontend can't display metrics not in WebSocket message
- Must fall back to polling `/api/queues/status`

**Root Cause**:
- Differential update pattern excludes unchanged fields
- `failed_tasks` may not be included if unchanged

**Impact**:
- UI requires polling fallback for complete data
- Real-time updates incomplete for some metrics

**Fix Required**:
- Always include queue status fields in WebSocket messages
- Or implement smart include logic for critical fields

---

## Test Execution Workflow

### Phase 1: Individual Scheduler Validation (No Dependencies)
Execute tests for each scheduler independently:
- Run in any order
- Each test is self-contained
- No prerequisite tests required

**Command Sequence**:
```bash
# Test Background Scheduler
echo "Testing Background Scheduler..."
# Run tests 1.1-1.7

# Test Portfolio Sync Scheduler
echo "Testing Portfolio Sync Scheduler..."
curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_sync_scheduler/execute'
# Monitor and verify

# Test Data Fetcher Scheduler
echo "Testing Data Fetcher Scheduler..."
curl -X POST 'http://localhost:8000/api/configuration/schedulers/data_fetcher_scheduler/execute'
# Monitor and verify

# Test AI Analysis Scheduler
echo "Testing AI Analysis Scheduler..."
curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'
# Monitor and verify (expect long duration)

# Test Portfolio Analysis Scheduler
echo "Testing Portfolio Analysis Scheduler..."
curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_analysis_scheduler/execute'
# Monitor and verify

# Test Paper Trading Research Scheduler
echo "Testing Paper Trading Research Scheduler..."
curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_research_scheduler/execute'
# Monitor and verify

# Test Paper Trading Execution Scheduler
echo "Testing Paper Trading Execution Scheduler..."
curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_execution_scheduler/execute'
# Monitor and verify
```

### Phase 2: Parallel Execution Testing
Test multiple schedulers running simultaneously:
```bash
# Trigger all queue-based schedulers in parallel
for scheduler in portfolio_sync_scheduler data_fetcher_scheduler portfolio_analysis_scheduler; do
  curl -X POST "http://localhost:8000/api/configuration/schedulers/$scheduler/execute" &
done
wait

# Monitor queue statuses in parallel
# Verify all tasks are queued and executing in their respective queues
```

### Phase 3: Failure Scenario Testing
Intentionally trigger failures and verify handling:
```bash
# Trigger analysis that will fail (invalid input)
curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute' \
  -H "Content-Type: application/json" \
  -d '{"invalid": "payload"}'

# Verify failure tracked in queue
curl -s 'http://localhost:8000/api/queues/status' | jq '.[] | select(.name=="ai_analysis")'

# Check UI Errors tab (SHOULD show failure, but may not due to bug)
```

### Phase 4: Real-Time Update Verification
Verify WebSocket updates without page refresh:
```bash
# Open browser to System Health > Schedulers
# Keep page open while triggering scheduler tasks
# Observe metrics update in real-time (should not require page refresh)
# All task metrics should update within 1 second of change
```

---

## Test Execution Matrix

| Scheduler | Test Count | Estimated Duration | Critical Tests | Known Issues |
|-----------|----------|--------|---------|----------|
| Background Scheduler | 7 | 5 min | 1.3, 1.6 | None specific |
| Portfolio Sync | 7 | 10 min | 2.2, 2.6 | Failure visibility |
| Data Fetcher | 7 | 15 min | 3.2, 3.4, 3.5 | Rate limit handling |
| **AI Analysis** | 7 | **60+ min** | **4.2, 4.4, 4.6** | **3 critical bugs** |
| Portfolio Analysis | 7 | 15 min | 5.2, 5.5 | Caching accuracy |
| Paper Trading Research | 7 | 30 min | 6.2, 6.5 | Recommendation quality |
| Paper Trading Execution | 9 | 20 min | 7.2, 7.5, 7.9 | Slippage accuracy |
| **Cross-Scheduler** | 5 | 30 min | C3, C4 | Real-time sync |
| **TOTAL** | **60 tests** | **~3.5 hours** | **Multiple** | **See bugs section** |

---

## Validation Checklist

### Pre-Testing
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] System Health page accessible
- [ ] Schedulers tab visible
- [ ] Browser DevTools console open (check for errors)
- [ ] Network tab monitoring WebSocket messages

### Per-Scheduler Testing
- [ ] Summary metric displays correctly
- [ ] Trigger endpoint works (receives 200 OK)
- [ ] Task queues to correct queue
- [ ] Metrics update in real-time
- [ ] Task completes or fails predictably
- [ ] Duration matches expected range
- [ ] Failure handling graceful (if applicable)

### Post-Testing
- [ ] All 7 schedulers tested
- [ ] All critical tests passed
- [ ] Known bugs documented with evidence
- [ ] UI/UX issues noted
- [ ] Performance metrics recorded
- [ ] Test execution log created

---

## Quick Reference: Trigger Endpoints

```bash
# Portfolio Sync Scheduler
curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_sync_scheduler/execute'

# Data Fetcher Scheduler
curl -X POST 'http://localhost:8000/api/configuration/schedulers/data_fetcher_scheduler/execute'

# AI Analysis Scheduler (LONG DURATION - 30-60+ sec)
curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'

# Portfolio Analysis Scheduler
curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_analysis_scheduler/execute'

# Paper Trading Research Scheduler
curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_research_scheduler/execute'

# Paper Trading Execution Scheduler
curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_execution_scheduler/execute'

# Check Queue Status
curl -s 'http://localhost:8000/api/queues/status'

# Check All Schedulers
curl -s 'http://localhost:8000/api/monitoring/scheduler'

# Check System Health
curl -s 'http://localhost:8000/api/health'
```

---

## Next Steps After Validation

1. **Fix BUG #1** (Critical): Display failed_tasks in UI Errors tab
2. **Verify BUG #2**: Confirm queue-based analysis prevents turn limit exhaustion
3. **Implement BUG #3 Fix**: Ensure complete WebSocket messages
4. **Document Scheduler Configuration**: Create scheduler-specific config guide
5. **Create Automated Tests**: Convert manual tests to pytest + Playwright automation
6. **Performance Baseline**: Record typical execution times for each scheduler
7. **Monitoring Rules**: Set up alerts for queue failures and scheduler hangs

---

**Document Version**: 1.0
**Testing Methodology**: Backtracking Functional Validation
**Created**: 2025-11-07
**Last Verified**: Testing framework documented, ready for execution
