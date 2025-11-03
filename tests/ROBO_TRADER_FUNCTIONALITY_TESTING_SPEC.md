# ROBO TRADER - COMPREHENSIVE FUNCTIONALITY TESTING SPECIFICATION

**Document Type**: End-to-End Testing & Functionality Verification  
**Created**: 2025-11-03  
**Status**: Active Testing Phase  
**Scope**: Verify actual functionality (DB → API → UI) not just UI rendering

---

## EXECUTIVE SUMMARY

Testing revealed that **Robo Trader UI renders correctly but data is NOT persisting to the database**. Core functionality appears to be **cosmetic/placeholder only**.

### Critical Findings
1. ❌ **AI Analysis**: `analysis_history` table is EMPTY (0 records)
2. ❌ **Recommendations**: `recommendations` table is EMPTY (0 records)  
3. ❌ **Paper Trades**: `paper_trades` table is EMPTY (0 records)
4. ⚠️ **Queue Tasks**: 10 tasks in "pending" state - NOT EXECUTING
5. ⚠️ **Database Writes**: No evidence of persistence layer working

### Hypothesis
The application is a **UI prototype** with mock/simulated features. Backend business logic (analysis, trading, queueing) either:
- Never executes
- Executes silently without error handling
- Doesn't persist results to database
- Has disabled or broken data storage layer

---

## PART 1: FUNCTIONALITY SPECIFICATION

### 1.1 AI Transparency - Analysis Tab

**Feature**: Display AI portfolio analysis with confidence scores and data quality metrics

**Expected Behavior**:
- User navigates to: **AI Transparency → Analysis tab**
- Tab displays: List of portfolio analyses with:
  - Symbol (which stock was analyzed)
  - Analysis timestamp
  - Confidence score (0-100%)
  - Data quality metrics
  - Technical indicators (RSI, MACD, etc.)
  - Fundamental analysis (P/E ratio, growth metrics)
  - Sentiment analysis (if news fetched)

**Data Source**: `analysis_history` table
```sql
CREATE TABLE analysis_history (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    analysis TEXT NOT NULL,  -- JSON with all analysis data
    created_at TEXT NOT NULL
);
```

**Database Action Flow**:
```
User Action: Trigger analysis
    ↓
Backend: PortfolioIntelligenceAnalyzer.analyze_portfolio_intelligence()
    ↓
Persist: ConfigurationState.store_analysis_history(symbol, timestamp, analysis_json)
    ↓
Insert: INSERT INTO analysis_history VALUES (...)
```

**Verification Points**:
1. **Database Check**: `SELECT COUNT(*) FROM analysis_history;` should increase
2. **Record Content**: 
   ```sql
   SELECT symbol, timestamp, 
          json_extract(analysis, '$.confidence_score') as confidence,
          json_extract(analysis, '$.data_quality') as quality
   FROM analysis_history 
   ORDER BY created_at DESC LIMIT 1;
   ```
3. **API Response**: `GET /api/claude/transparency/analysis` should return analysis array
4. **UI Display**: Analysis tab should show the data (not "No data" message)

**Current Status**: ❌ BROKEN
- Database table is empty (0 records)
- UI shows placeholder message
- No analysis being generated/persisted

---

### 1.2 AI Transparency - Recommendations Tab

**Feature**: Display AI trading recommendations with BUY/SELL/HOLD decisions

**Expected Behavior**:
- User navigates to: **AI Transparency → Recommendations tab**
- Tab displays: List of recommendations with:
  - Symbol (recommended stock)
  - Recommendation type (BUY / SELL / HOLD)
  - Confidence score (0-100%)
  - Target price and stop loss
  - Reasoning (why this recommendation)
  - Time horizon (short/medium/long-term)
  - Risk level (low/medium/high)

**Data Source**: `recommendations` table
```sql
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    recommendation_type TEXT NOT NULL,  -- BUY/SELL/HOLD
    confidence_score REAL,
    target_price REAL,
    stop_loss REAL,
    quantity INTEGER,
    reasoning TEXT,
    analysis_type TEXT,
    time_horizon TEXT,
    risk_level TEXT,
    created_at TEXT NOT NULL,
    executed_at TEXT,  -- When trade was executed
    outcome TEXT,      -- Final result
    actual_return REAL -- Actual return %
);
```

**Database Action Flow**:
```
User Action: Trigger analysis (or automatic during analysis)
    ↓
Backend: PortfolioIntelligenceAnalyzer creates recommendations
    ↓
Persist: ConfigurationState.store_recommendation(symbol, rec_type, score, reasoning, analysis_type)
    ↓
Insert: INSERT INTO recommendations VALUES (...)
```

**Verification Points**:
1. **Database Check**: `SELECT COUNT(*) FROM recommendations;` should increase
2. **Record Content**:
   ```sql
   SELECT symbol, recommendation_type, confidence_score, target_price, stop_loss
   FROM recommendations 
   WHERE confidence_score > 60
   ORDER BY created_at DESC LIMIT 5;
   ```
3. **API Response**: `GET /api/claude/transparency/recommendations` should return recommendations
4. **UI Display**: Recommendations tab should show BUY/SELL/HOLD with scores

**Current Status**: ❌ BROKEN
- Database table is empty (0 records)
- UI shows placeholder message
- No recommendations being generated/persisted

---

### 1.3 AI Transparency - Sessions Tab

**Feature**: Display Claude Agent SDK session logs with token usage

**Expected Behavior**:
- User navigates to: **AI Transparency → Sessions tab**
- Tab displays: List of Claude sessions with:
  - Session ID
  - Strategy type (e.g., swing trading)
  - Total tokens used
  - Cost (USD)
  - Execution timestamp
  - Success/failure status

**Data Source**: `strategy_logs` table
```sql
CREATE TABLE strategy_logs (
    id INTEGER PRIMARY KEY,
    strategy_type TEXT NOT NULL,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    decisions_made INTEGER,
    token_usage INTEGER,
    cost_usd REAL,
    status TEXT  -- success/failed
);
```

**Verification Points**:
1. **Database Check**: `SELECT COUNT(*) FROM strategy_logs;`
2. **Recent Sessions**:
   ```sql
   SELECT strategy_type, session_id, timestamp, token_usage, cost_usd
   FROM strategy_logs 
   ORDER BY timestamp DESC LIMIT 10;
   ```
3. **UI Display**: Sessions tab should show session history

**Current Status**: ⚠️ Unknown
- Need to check if strategy_logs has data
- Sessions tab structure exists in UI

---

### 1.4 AI Transparency - Data Quality Tab

**Feature**: Display data quality metrics for analysis inputs

**Expected Behavior**:
- User navigates to: **AI Transparency → Data Quality tab**
- Tab displays: Quality metrics per data source:
  - Earnings data quality (% available, recency)
  - News data quality (# articles, sentiment distribution)
  - Technical data quality (# price points, indicator completeness)
  - Fundamental data quality (# metrics, freshness)

**Data Source**: Extracted from `analysis_history.analysis` JSON field
```json
{
  "data_quality": {
    "earnings": {
      "available": 45,
      "stale": 5,
      "fresh_percentage": 90
    },
    "news": {
      "articles": 120,
      "sentiment_distribution": {...}
    },
    "technical": {
      "indicators_complete": true
    },
    "fundamental": {
      "metrics_available": 23
    }
  }
}
```

**Verification Points**:
1. **Database Check**: Query `analysis_history.analysis` for data_quality JSON
   ```sql
   SELECT symbol, 
          json_extract(analysis, '$.data_quality') as quality_data
   FROM analysis_history 
   LIMIT 1;
   ```
2. **UI Display**: Data Quality tab should show metrics

---

### 1.5 Paper Trading - Execute Trade

**Feature**: Execute BUY/SELL trades in paper trading account

**Expected Behavior**:
- User navigates to: **Paper Trading → Execute Trade tab**
- User fills form:
  - Trade Type: BUY or SELL
  - Symbol: e.g., RELIANCE
  - Quantity: e.g., 10 shares
  - Price: Current market price or limit price
  - Stop Loss: Risk management price
  - Target Price: Profit taking price
  - Strategy Rationale: Why making this trade
- User clicks: "Execute BUY" or "Execute SELL"
- System:
  1. Validates inputs (quantity ≤ available capital, position size limits)
  2. Fetches current market price
  3. Creates trade record in database with status='open'
  4. Reduces account buying power
  5. Returns trade confirmation with trade ID

**Data Source**: `paper_trades` table
```sql
CREATE TABLE paper_trades (
    trade_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    trade_type TEXT NOT NULL,  -- BUY or SELL
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_timestamp TEXT NOT NULL,
    strategy_rationale TEXT NOT NULL,
    claude_session_id TEXT,
    exit_price REAL,
    exit_timestamp TEXT,
    realized_pnl REAL,
    unrealized_pnl REAL,
    status TEXT NOT NULL DEFAULT 'open',  -- open/closed
    stop_loss REAL,
    target_price REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**API Endpoint**: `POST /api/paper-trading/accounts/{account_id}/trades/buy` or `/trades/sell`

**Database Action Flow**:
```
User Action: Fill form + Click "Execute BUY"
    ↓
Backend: PaperTradingExecutionService.execute_buy_trade()
    ↓
Validate: Check quantity, capital, position limits
    ↓
Fetch: Get current LTP from Zerodha Kite API
    ↓
Insert: INSERT INTO paper_trades (trade_id, account_id, symbol, quantity, entry_price, status='open')
    ↓
Update: UPDATE paper_trading_accounts SET buying_power = buying_power - (quantity * entry_price)
    ↓
Response: Return {success: true, order_id: "trade_xxx", ...}
```

**Verification Points**:
1. **Pre-Execution DB State**:
   ```sql
   SELECT account_id, current_balance, buying_power 
   FROM paper_trading_accounts 
   WHERE account_id = 'paper_swing_main';
   ```
2. **Execute Trade**: Use API or UI form
3. **Post-Execution DB Check**:
   ```sql
   -- Check new trade created
   SELECT trade_id, symbol, quantity, entry_price, status 
   FROM paper_trades 
   WHERE account_id = 'paper_swing_main' 
   ORDER BY created_at DESC LIMIT 1;
   
   -- Check account balance updated
   SELECT account_id, current_balance, buying_power 
   FROM paper_trading_accounts 
   WHERE account_id = 'paper_swing_main';
   ```
4. **API Response**: Returns trade_id and confirmation
5. **UI Update**: Positions tab shows new open position

**Expected Results**:
- ✅ New row in `paper_trades` with status='open'
- ✅ Account buying_power reduced by (quantity × entry_price)
- ✅ Positions tab shows new position
- ✅ P&L calculated with live prices

**Current Status**: ❌ BROKEN
- Database table is empty (0 records)
- No trades persisting
- Account balance not updating

---

### 1.6 Paper Trading - Positions Tab

**Feature**: Display all open paper trading positions with real-time P&L

**Expected Behavior**:
- User navigates to: **Paper Trading → Positions tab**
- Tab displays: Table of open positions with:
  - Trade ID
  - Symbol
  - Quantity
  - Entry Price
  - Current LTP (live from Zerodha)
  - Unrealized P&L (Current - Entry)
  - P&L % ((Current - Entry) / Entry × 100)
  - Days Held
  - Actions (Close, Edit Stop Loss, etc.)

**Data Source**: `paper_trades` table WHERE status='open'
```sql
SELECT trade_id, symbol, quantity, entry_price, status
FROM paper_trades
WHERE account_id = ? AND status = 'open'
ORDER BY entry_timestamp DESC;
```

**Real-time Data**: Current LTP fetched from Zerodha Kite API
- Must be LIVE prices, not cached
- Updates on every page refresh or via WebSocket

**Verification Points**:
1. **Database Check**:
   ```sql
   SELECT COUNT(*) FROM paper_trades WHERE status='open';
   ```
2. **Record Details**:
   ```sql
   SELECT trade_id, symbol, quantity, entry_price, stop_loss, target_price
   FROM paper_trades 
   WHERE account_id='paper_swing_main' AND status='open';
   ```
3. **UI Display**:
   - Shows exact number of open positions (must match DB count)
   - P&L values must match calculation: (LTP - entry_price) × quantity
   - LTP must be current (not yesterday's price)

**Current Status**: ❌ BROKEN
- No open positions in database
- Positions tab shows empty

---

### 1.7 Paper Trading - Trade Closure

**Feature**: Close open positions and calculate realized P&L

**Expected Behavior**:
- User navigates to: **Paper Trading → Positions tab**
- User clicks: "Close" button on open position
- System:
  1. Fetches current LTP
  2. Calculates realized P&L: (exit_price - entry_price) × quantity
  3. Updates trade record: status='closed', exit_price, exit_timestamp, realized_pnl
  4. Returns account balance to buying_power
  5. Updates account balance with realized gains/losses
  6. Moves trade from Positions to History

**Database Action Flow**:
```
User Action: Click "Close" on position
    ↓
Backend: PaperTradingExecutionService.close_trade()
    ↓
Fetch: Get current LTP
    ↓
Calculate: realized_pnl = (exit_price - entry_price) × quantity
    ↓
Update: UPDATE paper_trades SET status='closed', exit_price, realized_pnl, exit_timestamp WHERE trade_id=?
    ↓
Update: UPDATE paper_trading_accounts SET current_balance = current_balance + realized_pnl, buying_power = buying_power + (entry_price × quantity)
```

**Verification Points**:
1. **Trade Status Update**:
   ```sql
   SELECT trade_id, status, exit_price, realized_pnl 
   FROM paper_trades 
   WHERE trade_id = 'trade_xxx';
   ```
   Expected: status='closed', exit_price populated, realized_pnl calculated
2. **Account Balance Update**:
   ```sql
   SELECT account_id, current_balance 
   FROM paper_trading_accounts;
   ```
   Expected: Balance increased/decreased by realized_pnl
3. **UI Update**: Trade moved from Positions to History tab

**Current Status**: ❌ BROKEN
- No trades to close
- Cannot test closure logic

---

### 1.8 Paper Trading - Trade History

**Feature**: Display all closed trades with realized P&L and performance metrics

**Expected Behavior**:
- User navigates to: **Paper Trading → History tab**
- Tab displays: Table of closed trades with:
  - Trade ID
  - Symbol
  - Entry price, quantity, entry date
  - Exit price, exit date
  - Realized P&L (₹ and %)
  - Days Held
  - Status (Win/Loss)

**Data Source**: `paper_trades` table WHERE status='closed'
```sql
SELECT trade_id, symbol, quantity, entry_price, exit_price, 
       realized_pnl, entry_timestamp, exit_timestamp
FROM paper_trades
WHERE account_id = ? AND status = 'closed'
ORDER BY exit_timestamp DESC
LIMIT 50;
```

**Verification Points**:
1. **Database Query**:
   ```sql
   SELECT COUNT(*) as closed_trades FROM paper_trades WHERE status='closed';
   ```
2. **History Accuracy**:
   ```sql
   SELECT symbol, entry_price, exit_price, realized_pnl,
          CAST((exit_price - entry_price) * quantity AS FLOAT) as calculated_pnl
   FROM paper_trades 
   WHERE status='closed' 
   LIMIT 5;
   ```
   Expected: realized_pnl == calculated_pnl
3. **Performance Stats**:
   ```sql
   SELECT 
       COUNT(*) as total_trades,
       SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
       CAST(SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as win_rate,
       SUM(realized_pnl) as total_pnl
   FROM paper_trades 
   WHERE account_id='paper_swing_main' AND status='closed';
   ```

**Current Status**: ❌ BROKEN
- No closed trades in database
- History tab shows empty

---

## PART 2: QUEUE SYSTEM & BACKGROUND EXECUTION

### 2.1 Queue Tasks (SequentialQueueManager)

**Feature**: Queue-based task execution for background processing

**Architecture**:
```
3 Sequential Queues (execute in PARALLEL, tasks WITHIN queue execute SEQUENTIALLY):
├── PORTFOLIO_SYNC   → Portfolio operations (buy/sell, rebalancing)
├── DATA_FETCHER     → Market data fetching (news, earnings, technical)
└── AI_ANALYSIS      → Claude AI analysis (batch analysis with turn limit protection)
```

**Expected Behavior**:
- Tasks submitted to queue with status='pending'
- SequentialQueueManager picks up task
- Task execution starts (status='running')
- Task completes and results persisted (status='completed')
- Execution logged to `execution_history`

**Data Source**: `queue_tasks` table
```sql
CREATE TABLE queue_tasks (
    task_id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,  -- PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS
    task_type TEXT NOT NULL,   -- RECOMMENDATION_GENERATION, FETCH_NEWS, etc.
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    priority INTEGER DEFAULT 5,
    payload TEXT,  -- JSON with task parameters
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT
);
```

**Verification Points**:
1. **Queue Status**:
   ```sql
   SELECT queue_name, status, COUNT(*) as count 
   FROM queue_tasks 
   GROUP BY queue_name, status;
   ```
2. **Task Execution**:
   ```sql
   SELECT task_id, status FROM queue_tasks ORDER BY created_at DESC LIMIT 5;
   ```
   Expected: Status progression pending → running → completed
3. **Execution Logged**:
   ```sql
   SELECT task_name, status, timestamp FROM execution_history 
   ORDER BY timestamp DESC LIMIT 10;
   ```

**Current Status**: ⚠️ CRITICAL ISSUE
- 10 tasks in 'pending' state
- No 'running' or 'completed' tasks
- Schedulers NOT picking up tasks
- Queue system appears broken

---

### 2.2 Configuration → AI Analysis Trigger

**Feature**: Manually trigger analysis from Configuration → AI Agents panel

**Expected Behavior**:
```
User Action: Configuration → AI Agents → Enable "portfolio_analyzer" → Click "Trigger Analysis"
    ↓
Backend: TaskService.create_task(queue_name=AI_ANALYSIS, task_type=RECOMMENDATION_GENERATION)
    ↓
Database: Task added to queue_tasks with status='pending'
    ↓
Scheduler: SequentialQueueManager picks up task from AI_ANALYSIS queue
    ↓
Execute: PortfolioIntelligenceAnalyzer.analyze_portfolio_intelligence()
    ↓
Persist: Results stored in analysis_history and recommendations tables
    ↓
Logging: Execution logged to execution_history
    ↓
UI Update: AI Transparency tabs updated with new data
```

**Verification Points**:
1. **Queue Check Before**:
   ```sql
   SELECT COUNT(*) FROM queue_tasks WHERE queue_name='ai_analysis' AND status='pending';
   ```
2. **Trigger Analysis**: Use UI or API
3. **Queue Check After**:
   ```sql
   SELECT task_id, queue_name, status, created_at 
   FROM queue_tasks 
   WHERE queue_name='ai_analysis' 
   ORDER BY created_at DESC LIMIT 1;
   ```
4. **Execution Progress**:
   - Monitor status: pending → running → completed
   - Check logs for execution start/end
5. **Results Check**:
   ```sql
   SELECT COUNT(*) FROM analysis_history 
   WHERE created_at > datetime('now', '-1 minute');
   ```
6. **UI Display**: AI Transparency tabs show new analysis

**Current Status**: ❌ BROKEN
- Queue system not executing tasks
- Analysis not being generated
- Database tables remain empty

---

## PART 3: SYSTEM HEALTH MONITORING

### 3.1 Scheduler Status Verification

**Feature**: Monitor background scheduler execution

**Expected Behavior**:
- UI: System Health → Schedulers
- Shows: List of running schedulers with:
  - Scheduler name (Background Scheduler, Portfolio Sync, Data Fetcher, AI Analysis)
  - Status (running/idle)
  - Jobs processed count (should match DB)
  - Jobs failed count
  - Active jobs currently running

**Data Source**: `execution_history` table
```sql
SELECT task_name, status, COUNT(*) as count 
FROM execution_history 
GROUP BY task_name, status;
```

**UI Display Mapping**:
```
System Health → Schedulers shows "25 done" for Background Scheduler
Should equal: SELECT COUNT(*) FROM execution_history WHERE task_name='background_scheduler';
```

**Verification Points**:
1. **Database Count**:
   ```sql
   SELECT COUNT(*) FROM execution_history;  -- Should match "X done" in UI
   ```
2. **By Task**:
   ```sql
   SELECT task_name, COUNT(*) as execution_count 
   FROM execution_history 
   GROUP BY task_name;
   ```
3. **UI Check**: Verify numbers match exactly
4. **Pass Criteria**:
   - [ ] "25 done" in UI == 25+ records in database (or actual count)
   - [ ] NOT hardcoded (real data)
   - [ ] Counts update as tasks execute

**Current Status**: ✅ PARTIAL
- Execution history table has data (44 records)
- But UI numbers need verification

---

### 3.2 Queue Status Verification

**Feature**: Monitor task queue status

**Expected Behavior**:
- UI: System Health → Queues tab
- Shows: Statistics for each queue:
  - Queue name (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS)
  - Status (idle, running)
  - Pending tasks count
  - Running tasks count
  - Completed count
  - Failed count

**Data Source**: `queue_tasks` table
```sql
SELECT queue_name, 
       COUNT(CASE WHEN status='pending' THEN 1 END) as pending,
       COUNT(CASE WHEN status='running' THEN 1 END) as running,
       COUNT(CASE WHEN status='completed' THEN 1 END) as completed,
       COUNT(CASE WHEN status='failed' THEN 1 END) as failed
FROM queue_tasks 
GROUP BY queue_name;
```

**Verification Points**:
1. **Database Query**: Get actual counts
2. **UI Display**: Compare with System Health → Queues
3. **Pass Criteria**:
   - [ ] Pending count == UI pending
   - [ ] Running count == UI running
   - [ ] Completed count == UI completed
   - [ ] Failed count == UI failed
   - [ ] Numbers are REAL data, not placeholders

**Current Status**: ❌ BROKEN
- 10 pending tasks in database
- UI shows "0 active • 0 total tasks"
- UI numbers don't match database
- Possible hardcoding or API not returning real data

---

## PART 4: COMPREHENSIVE TEST SCENARIOS

### Scenario A: End-to-End AI Analysis Flow

**Objective**: Verify analysis triggers, executes, persists, and displays

**Prerequisites**:
- Backend running: `python -m src.main --command web`
- Frontend running: `cd ui && npm run dev`
- Database accessible: `state/robo_trader.db`
- Playwright MCP: Connected

**Steps**:

```
STEP 1: Get DB baseline
├─ sqlite3 state/robo_trader.db "SELECT COUNT(*) FROM analysis_history;"
└─ Expected: 0 or known count

STEP 2: Trigger Analysis
├─ Navigate to Configuration → AI Agents
├─ Enable "portfolio_analyzer"
├─ Click "Trigger Analysis"
└─ Monitor backend logs for execution start

STEP 3: Monitor Queue Execution
├─ sqlite3 state/robo_trader.db "SELECT status FROM queue_tasks WHERE queue_name='ai_analysis' ORDER BY created_at DESC LIMIT 1;"
├─ Expected progression: pending → running → completed
└─ Time to complete: 30-120 seconds (depends on portfolio size)

STEP 4: Verify Analysis Persisted
├─ sqlite3 state/robo_trader.db "SELECT COUNT(*) FROM analysis_history WHERE created_at > datetime('now', '-1 minute');"
├─ Expected: > 0
├─ Get analysis details:
│  SELECT symbol, json_extract(analysis, '$.confidence_score') as confidence
│  FROM analysis_history 
│  ORDER BY created_at DESC LIMIT 1;
└─ Expected: Real confidence scores, not NULL

STEP 5: Verify Recommendations Persisted
├─ sqlite3 state/robo_trader.db "SELECT COUNT(*) FROM recommendations WHERE created_at > datetime('now', '-1 minute');"
├─ Expected: > 0
└─ Get recommendation details:
   SELECT symbol, recommendation_type, confidence_score 
   FROM recommendations 
   ORDER BY created_at DESC LIMIT 3;

STEP 6: Check UI Display
├─ Browser: AI Transparency → Analysis tab
├─ Expected: Shows new analysis records (not "No data" message)
├─ Browser: AI Transparency → Recommendations tab
├─ Expected: Shows new recommendations with BUY/SELL/HOLD
└─ Verify field values match database

STEP 7: Confirm Data Consistency
├─ Pick one analysis from UI
├─ Verify in database:
│  SELECT * FROM analysis_history 
│  WHERE symbol = 'RELIANCE'  -- or symbol from UI
│  ORDER BY created_at DESC LIMIT 1;
└─ Expected: All fields match exactly between UI and DB
```

**Pass Criteria**:
- [ ] Queue task created with status='pending'
- [ ] Task status progresses: pending → running → completed
- [ ] New records in `analysis_history` table
- [ ] New records in `recommendations` table
- [ ] UI Analysis tab shows data (not placeholder)
- [ ] UI Recommendations tab shows data (not placeholder)
- [ ] Field values match: DB == API == UI
- [ ] No database errors in logs

**Failure Indicators**:
- [ ] Analysis count doesn't increase
- [ ] Recommendations count doesn't increase
- [ ] Task stuck in "pending" state
- [ ] UI shows "No data available yet"
- [ ] Backend logs show exceptions

---

### Scenario B: End-to-End Paper Trading Flow

**Objective**: Execute trade, verify persistence, check positions, close, verify history

**Prerequisites**: Same as above

**Steps**:

```
STEP 1: Get DB baseline
├─ SELECT current_balance, buying_power FROM paper_trading_accounts WHERE account_id='paper_swing_main';
├─ SELECT COUNT(*) FROM paper_trades WHERE status='open';
└─ Expected: Balance=100000, No open trades

STEP 2: Execute Trade
├─ Navigate to Paper Trading → Execute Form
├─ Fill form:
│  ├─ Trade Type: BUY
│  ├─ Symbol: RELIANCE
│  ├─ Quantity: 10
│  └─ Strategy: "Technical analysis bullish"
├─ Click "Execute BUY"
└─ Note returned trade_id from response

STEP 3: Verify Trade Persisted
├─ sqlite3 state/robo_trader.db "SELECT * FROM paper_trades WHERE symbol='RELIANCE' ORDER BY created_at DESC LIMIT 1;"
├─ Expected: 
│  └─ trade_id, account_id, symbol='RELIANCE', quantity=10, entry_price=XXXX, status='open'
└─ Verify entry_price is current market price (not old cache)

STEP 4: Verify Account Balance Updated
├─ SELECT current_balance, buying_power FROM paper_trading_accounts WHERE account_id='paper_swing_main';
├─ Expected: 
│  └─ buying_power reduced by (10 × entry_price)
│  └─ current_balance may be same (depends on implementation)
└─ Example: If RELIANCE=2500, buying_power should be 100000-25000=75000

STEP 5: Verify Positions Tab Shows Trade
├─ Browser: Paper Trading → Positions
├─ Expected:
│  ├─ Shows RELIANCE position
│  ├─ Quantity: 10
│  ├─ Entry Price: XXXX
│  ├─ Current LTP: YYYY (must be LIVE, not old price)
│  └─ Unrealized P&L: Calculated correctly
└─ Formula: (LTP - entry_price) × quantity

STEP 6: Close Trade
├─ Browser: Paper Trading → Positions
├─ Click "Close" button on RELIANCE position
├─ System fetches current LTP and closes position
└─ Expected: Trade moves to History tab

STEP 7: Verify Trade Closed in DB
├─ sqlite3 state/robo_trader.db "SELECT * FROM paper_trades WHERE trade_id='trade_xxx';"
├─ Expected:
│  ├─ status = 'closed'
│  ├─ exit_price = current LTP when closed
│  ├─ exit_timestamp = close time
│  └─ realized_pnl = (exit_price - entry_price) × 10
└─ Example: If exit @ 2600, realized_pnl = (2600-2500) × 10 = 1000

STEP 8: Verify Account Balance Updated
├─ SELECT current_balance, buying_power FROM paper_trading_accounts WHERE account_id='paper_swing_main';
├─ Expected:
│  └─ current_balance increased by realized_pnl (1000 in example)
│  └─ buying_power restored (75000 + 25000 = 100000 again)
└─ New balance: 100000 + realized_pnl = 101000

STEP 9: Verify History Tab Shows Trade
├─ Browser: Paper Trading → History
├─ Expected:
│  ├─ Shows closed RELIANCE trade
│  ├─ Entry price, exit price
│  ├─ Realized P&L: +1000 (or actual)
│  └─ Realized P&L %: +1.0%
└─ Formula: (realized_pnl / (entry_price × quantity)) × 100

STEP 10: Confirm Data Consistency
├─ Verify all numbers match: DB == API == UI
└─ No discrepancies in amounts, counts, or calculations
```

**Pass Criteria**:
- [ ] Trade record created in `paper_trades` table
- [ ] Trade has status='open' and current entry_price
- [ ] Account buying_power reduced by trade cost
- [ ] Positions tab shows open trade
- [ ] LTP displayed is current (live price)
- [ ] Unrealized P&L calculates correctly
- [ ] Trade closure updates status to 'closed'
- [ ] Realized P&L calculated: (exit-entry)×qty
- [ ] Account balance updated with realized P&L
- [ ] History tab shows closed trade
- [ ] All values consistent: DB == UI

**Failure Indicators**:
- [ ] No trade in database after execution
- [ ] Account balance unchanged
- [ ] Positions tab empty (despite DB having open trade)
- [ ] LTP is cached/old price (not current)
- [ ] UI numbers don't match database
- [ ] Closed trade not in history
- [ ] Realized P&L calculation incorrect

---

## PART 5: TESTING CHECKLIST & VERIFICATION

### Pre-Testing Verification
- [ ] Backend running: `curl -m 3 http://localhost:8000/api/health`
- [ ] Frontend running: `curl -m 3 http://localhost:3000/health`
- [ ] Database exists: `ls state/robo_trader.db`
- [ ] Playwright MCP connected
- [ ] User has permissions to write to state/robo_trader.db

### AI Transparency - Complete Checklist

#### Analysis Tab
- [ ] **Baseline**: `SELECT COUNT(*) FROM analysis_history;` = 0
- [ ] **Action**: Configuration → AI Agents → Trigger Analysis
- [ ] **Queue**: Task appears in `queue_tasks` with status='pending'
- [ ] **Execution**: Status transitions pending → running → completed
- [ ] **Persistence**: `SELECT COUNT(*) FROM analysis_history;` > 0
- [ ] **Content**: New record has symbol, timestamp, analysis JSON
- [ ] **UI**: Analysis tab shows new record (not "No data")
- [ ] **Values**: DB values == UI displayed values
- [ ] **Pass**: All checkboxes above checked

#### Recommendations Tab
- [ ] **Baseline**: `SELECT COUNT(*) FROM recommendations;` = 0
- [ ] **Action**: Same as analysis (recommendations created during analysis)
- [ ] **Persistence**: `SELECT COUNT(*) FROM recommendations;` > 0
- [ ] **Content**: New records have symbol, recommendation_type, confidence_score
- [ ] **UI**: Recommendations tab shows BUY/SELL/HOLD with scores
- [ ] **Values**: DB values == UI values
- [ ] **Pass**: All checkboxes above checked

#### Sessions Tab (if applicable)
- [ ] **Check**: `SELECT COUNT(*) FROM strategy_logs;`
- [ ] **UI**: Sessions tab displays session records
- [ ] **Values**: Token usage, cost, timestamp all populated
- [ ] **Pass**: All data present and correct

#### Data Quality Tab
- [ ] **Source**: Extracted from analysis_history.analysis JSON
- [ ] **UI**: Data Quality tab shows quality metrics
- [ ] **Values**: Earnings %, News count, Technical completeness all displayed
- [ ] **Pass**: Data quality metrics visible and meaningful

### Paper Trading - Complete Checklist

#### Before Trade Execution
- [ ] **Account**: `SELECT current_balance, buying_power FROM paper_trading_accounts WHERE account_id='paper_swing_main';`
- [ ] **Balance**: ₹100,000
- [ ] **Buying Power**: ₹100,000
- [ ] **Open Trades**: `SELECT COUNT(*) FROM paper_trades WHERE status='open';` = 0
- [ ] **Status**: Account ready for trading

#### Trade Execution
- [ ] **Form Fill**: Symbol=RELIANCE, Qty=10, Type=BUY
- [ ] **Execution**: Click "Execute BUY"
- [ ] **Response**: API returns trade_id
- [ ] **Note Trade ID**: Save for verification

#### After Trade Creation
- [ ] **DB Check**: `SELECT * FROM paper_trades WHERE symbol='RELIANCE' ORDER BY created_at DESC LIMIT 1;`
- [ ] **Trade ID**: Matches API response
- [ ] **Status**: 'open'
- [ ] **Symbol**: 'RELIANCE'
- [ ] **Quantity**: 10
- [ ] **Entry Price**: Real market price (not 0 or old)
- [ ] **Timestamp**: Current time

#### Account Update
- [ ] **Balance Check**: `SELECT buying_power FROM paper_trading_accounts WHERE account_id='paper_swing_main';`
- [ ] **Calculation**: buying_power == 100000 - (10 × entry_price)
- [ ] **Example**: If RELIANCE=2500, buying_power should be 75000
- [ ] **Verification**: Math is correct

#### Positions Tab
- [ ] **Navigation**: Paper Trading → Positions
- [ ] **Count**: Shows 1 position
- [ ] **Symbol**: RELIANCE
- [ ] **Quantity**: 10
- [ ] **Entry Price**: Matches database
- [ ] **Current LTP**: Live price (not cached)
- [ ] **Unrealized P&L**: (LTP - entry_price) × 10
- [ ] **Verification**: Calculation correct

#### Trade Closure
- [ ] **Action**: Click "Close" on RELIANCE position
- [ ] **Fetch**: System gets current LTP
- [ ] **Close**: Trade status changes to 'closed'
- [ ] **Calculate**: realized_pnl = (exit_price - entry_price) × 10

#### After Trade Closure
- [ ] **DB Check**: `SELECT * FROM paper_trades WHERE trade_id='trade_xxx';`
- [ ] **Status**: 'closed'
- [ ] **Exit Price**: Current LTP value
- [ ] **Realized P&L**: (exit - entry) × qty
- [ ] **Account Update**: current_balance increased by realized_pnl

#### History Tab
- [ ] **Navigation**: Paper Trading → History
- [ ] **Count**: Shows 1 trade
- [ ] **Symbol**: RELIANCE
- [ ] **Entry/Exit**: Both prices shown
- [ ] **Realized P&L**: Actual amount and percentage
- [ ] **Verification**: All values match database

### System Health - Complete Checklist

#### Schedulers
- [ ] **Query**: `SELECT COUNT(*) FROM execution_history;`
- [ ] **UI**: System Health → Schedulers → "X done"
- [ ] **Verify**: Count in UI == count in database
- [ ] **Accuracy**: Not hardcoded (changes if execute new tasks)
- [ ] **Status**: All schedulers show "running"

#### Queues
- [ ] **Query**: `SELECT queue_name, status, COUNT(*) FROM queue_tasks GROUP BY queue_name, status;`
- [ ] **UI**: System Health → Queues → statistics
- [ ] **Verify**: Pending count matches UI
- [ ] **Verify**: Running count matches UI
- [ ] **Verify**: Completed count matches UI (not just "0")
- [ ] **Pass**: All counts are REAL data, not placeholders

#### Database
- [ ] **Check**: Displays "Connected"
- [ ] **Loaded**: Shows "Portfolio loaded"
- [ ] **Status**: Both indicators visible and accurate

---

## PART 6: EXPECTED OUTCOMES & FAILURE MODES

### Success Path
**All of the above tests pass** →
- ✅ Functionality is WORKING end-to-end
- ✅ Data persists to database
- ✅ API returns real data
- ✅ UI displays matching data
- ✅ System is production-ready

### Failure Path
**One or more tests fail** → Possible root causes:
1. **Analysis not persisting**
   - `PortfolioIntelligenceAnalyzer` not called
   - `ConfigurationState.store_analysis_history()` failing silently
   - Database write permissions issue
   - Exception in analysis code (check logs)

2. **Paper trades not persisting**
   - Trade execution API not implemented
   - Database insert failing
   - Account balance not updating
   - Database locking issue

3. **Queue tasks not executing**
   - SequentialQueueManager not initialized
   - Task polling not happening
   - Task handlers not registered
   - Scheduler disabled

4. **UI showing placeholders**
   - API endpoint returns hardcoded data
   - API not calling database
   - Frontend not receiving data
   - Data transformation error

---

## CONCLUSION

This comprehensive testing specification provides:
1. **Feature-by-feature functionality definitions**
2. **Expected data flow (DB → API → UI)**
3. **Verification SQL queries**
4. **Step-by-step test scenarios**
5. **Pass/fail criteria for each feature**
6. **Complete testing checklist**

**Next step**: Execute tests and document results against this specification.

