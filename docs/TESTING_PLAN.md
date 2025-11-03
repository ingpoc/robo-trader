Comprehensive Robo Trader Functionality Testing Plan

     Objective

     Verify that Robo Trader functionality is actually working end-to-end with real data flowing from database → API → UI, not 
     just rendering placeholder UIs.

     Testing Approach

     Phase 1: Database State Verification (Read-Only)

     1. Connect to SQLite database: state/robo_trader.db
     2. Query all relevant tables to understand current state:
       - analysis_history - AI analysis records
       - recommendations - Trading recommendations  
       - paper_trades - Open/closed trades
       - paper_trading_accounts - Account balances
       - queue_tasks - Task queue status
       - execution_history - Scheduler execution logs
     3. Document baseline state (counts, recent records)

     Phase 2: AI Transparency Tab Testing

     Test AI Analysis Flow:
     1. Check DB baseline: Count records in analysis_history and recommendations
     2. Trigger analysis: Configuration → AI Agents → Trigger Analysis
     3. Monitor queue: Query queue_tasks for pending → running → completed
     4. Verify DB persistence: Check new records in analysis_history
     5. Verify UI display: AI Transparency tabs show matching data
     6. Confirm field matching: DB values == API response == UI display

     Verify each tab:
     - Analysis tab: Database query vs UI display
     - Recommendations tab: Check if API endpoint exists and returns real data
     - Sessions tab: Verify strategy_logs has data
     - Data Quality tab: Check JSON fields contain quality metrics

     Phase 3: Paper Trading Flow Testing

     Test Complete Trade Execution:
     1. Check DB baseline: Account balance, open positions count
     2. Execute trade: Paper Trading → Execute Form → BUY RELIANCE 10 shares
     3. Verify DB write: New row in paper_trades with status='open'
     4. Verify balance update: Account balance reduced by trade cost
     5. Verify Positions tab: Shows new position with real-time LTP
     6. Close trade: Verify status changes to 'closed', P&L calculated
     7. Verify History tab: Shows closed trade with realized P&L

     Check all endpoints:
     - POST /api/paper-trading/accounts/{id}/trades/buy - Creates trade
     - GET /api/paper-trading/accounts/{id}/positions - Returns open trades
     - GET /api/paper-trading/accounts/{id}/trades - Returns history
     - POST /api/paper-trading/accounts/{id}/positions/{trade_id}/close - Closes trade

     Phase 4: System Health Verification

     Verify Real Data:
     1. Check execution_history table for actual execution logs
     2. Verify "25 done" count matches DB records (not hardcoded)
     3. Check queue_tasks table for queue statistics
     4. Confirm queue counts match DB queries
     5. Verify scheduler status reflects actual system state

     Phase 5: Configuration → Analysis Integration

     Test End-to-End Flow:
     1. Trigger: Configuration → AI Agents → Enable → Trigger Analysis
     2. Verify queuing: Task appears in queue_tasks with status='pending'
     3. Monitor execution: Status progresses pending → running → completed
     4. Verify results: Analysis written to analysis_history
     5. Verify UI update: AI Transparency tabs show new data
     6. Confirm: All data matches across DB → API → UI

     Deliverables

     1. Test execution document with pass/fail for each scenario
     2. Screenshots showing UI state for each test
     3. SQL query results proving data exists in database
     4. API responses confirming data flow
     5. Discrepancy report listing any placeholder/non-functional features

     Tools Used

     - Playwright MCP server for browser testing
     - SQLite CLI/queries for database verification
     - Backend logs monitoring for execution tracking
     - API endpoint testing via browser network tab

     Success Criteria

     ✅ All database tables have real data (not empty)
     ✅ API endpoints return data from database (not hardcoded)
     ✅ UI displays match database content exactly
     ✅ Actions trigger database writes that persist
     ✅ Real-time updates reflect actual data changes
     ✅ No placeholder text where real data should exist