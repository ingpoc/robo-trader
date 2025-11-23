# Robo-Trader Integration Gaps Implementation Plan

**Created**: 2025-11-23
**Status**: Planning Phase
**Total Gaps Identified**: 21
**Estimated Effort**: 4 Phases

---

## Architecture Context

> **Important**: This application is powered by the **Claude Agent SDK** (not direct Claude API calls). **Zerodha is integrated for data** (portfolio, stock prices), but **execution is paper trading only** (no real trades).

| Aspect | Implementation |
|--------|----------------|
| AI Engine | Claude Agent SDK with specialized agents |
| Data Source | Zerodha API (portfolio data, stock prices) |
| Trading Mode | Paper trading only (simulated execution) |
| Communication | Event-driven via EventBus |
| Queue System | 3 parallel queues (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS) |
| Pattern | Coordinator-based monolith |

---

## Executive Summary

This document provides a comprehensive implementation plan for addressing all integration gaps and incomplete functionality identified in the robo-trader application. The plan is organized into 4 phases based on priority, dependencies, and impact.

### Gap Distribution by Severity

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 5 | Blocking core functionality |
| HIGH | 5 | Major feature gaps |
| MEDIUM | 8 | Important enhancements |
| LOW | 3 | Minor improvements |

---

## Phase 1: Critical Infrastructure Fixes

**Priority**: CRITICAL
**Dependencies**: None
**Impact**: Enables core functionality

### 1.1 Event Router Database Persistence

**File**: `src/services/event_router_service.py`
**Lines**: 370-398
**Issue**: Event triggers lost on restart - `_persist_trigger()`, `_update_trigger()`, `_delete_trigger()` are stubs

#### Implementation Steps

1. **Create EventTriggerState Manager**
   ```
   File: src/core/database_state/event_trigger_state.py
   ```

   - Create new state manager following existing patterns (`portfolio_state.py`)
   - Implement methods:
     - `store_event_trigger(trigger: dict) -> bool`
     - `update_event_trigger(trigger_id: str, updates: dict) -> bool`
     - `delete_event_trigger(trigger_id: str) -> bool`
     - `get_all_triggers() -> List[dict]`
     - `get_trigger_by_id(trigger_id: str) -> Optional[dict]`

2. **Add Database Schema**
   ```sql
   CREATE TABLE IF NOT EXISTS event_triggers (
       trigger_id TEXT PRIMARY KEY,
       source_queue TEXT NOT NULL,
       target_queue TEXT NOT NULL,
       event_type TEXT NOT NULL,
       condition JSON,
       enabled INTEGER DEFAULT 1,
       created_at TEXT NOT NULL,
       updated_at TEXT NOT NULL
   );
   ```

3. **Update DatabaseStateManager Facade**
   ```
   File: src/core/database_state/database_state.py
   ```
   - Add `EventTriggerStateManager` import
   - Initialize in constructor
   - Delegate trigger methods

4. **Wire EventRouterService**
   ```
   File: src/services/event_router_service.py
   ```
   - Replace `pass` statements with actual database calls
   - Update `_load_triggers_from_db()` to query database
   - Add migration for existing in-memory triggers

#### Acceptance Criteria
- [ ] Triggers persist across application restarts
- [ ] CRUD operations work via API
- [ ] Backward compatible with existing trigger registration

---

### 1.2 Fix DI Container Syntax Error

**File**: `src/core/di.py`
**Lines**: 142-144
**Issue**: Malformed `get_queue_coordinator()` method - orphaned docstring/return

#### Implementation Steps

1. **Fix Method Syntax**
   ```python
   # Before (broken):
   # async def get_queue_coordinator(self) -> QueueCoordinator:  # Not implemented
       """Get the queue coordinator instance."""
       return await self.get("queue_coordinator")

   # After (fixed):
   async def get_queue_coordinator(self) -> "QueueCoordinator":
       """Get the queue coordinator instance."""
       return await self.get("queue_coordinator")
   ```

2. **Add Type Import** (if not present)
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from src.core.coordinators import QueueCoordinator
   ```

#### Acceptance Criteria
- [ ] Method callable without syntax errors
- [ ] IDE autocomplete works
- [ ] Type hints resolve correctly

---

### 1.3 Implement MCP Trade Execution Handlers

**File**: `ui/src/App.tsx`
**Lines**: 39-62
**Issue**: 5 trade handlers are empty console.log stubs

#### Implementation Steps

1. **Create API Service Module**
   ```
   File: ui/src/services/paperTradingApi.ts
   ```
   ```typescript
   export const paperTradingApi = {
     executeBuy: async (accountId: string, request: BuyRequest) => {
       const response = await fetch(`/api/paper-trading/accounts/${accountId}/trades/buy`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify(request)
       });
       return response.json();
     },

     executeSell: async (accountId: string, request: SellRequest) => {
       // Similar implementation
     },

     closePosition: async (accountId: string, tradeId: string) => {
       // Similar implementation
     },

     modifyPosition: async (accountId: string, tradeId: string, updates: PositionUpdate) => {
       // Similar implementation
     },

     refreshData: async (accountId: string) => {
       // Fetch overview, positions, trades
     }
   };
   ```

2. **Update App.tsx Handlers**
   ```typescript
   const handleExecuteBuy = async (request: any) => {
     try {
       const result = await paperTradingApi.executeBuy(currentAccountId, request);
       if (result.success) {
         toast.success(`Buy order executed for ${request.symbol}`);
         await handleRefresh();
       } else {
         toast.error(result.error || 'Buy order failed');
       }
     } catch (error) {
       toast.error('Failed to execute buy order');
       console.error('Execute buy error:', error);
     }
   };
   ```

3. **Add Account Context Integration**
   - Get `currentAccountId` from `AccountContext`
   - Handle loading states
   - Add error boundaries

#### Acceptance Criteria
- [ ] Buy orders execute via API
- [ ] Sell orders execute via API
- [ ] Position close works
- [ ] UI refreshes after operations
- [ ] Error messages display to user

---

### 1.4 Implement Position Modification Backend API

**File**: `ui/src/pages/PaperTrading.tsx` (Line 1034 - blocked with alert)
**Backend**: Missing endpoint

#### Implementation Steps

1. **Add Backend Endpoint**
   ```
   File: src/web/routes/paper_trading.py
   ```
   ```python
   @router.patch("/paper-trading/accounts/{account_id}/trades/{trade_id}")
   @limiter.limit(paper_trading_limit)
   async def modify_trade(
       request: Request,
       account_id: str,
       trade_id: str,
       body: ModifyTradeRequest,
       container: DependencyContainer = Depends(get_container)
   ) -> Dict[str, Any]:
       """Modify stop loss and/or target for an open position."""
       try:
           account_manager = await container.get("paper_trading_account_manager")
           result = await account_manager.modify_position(
               account_id=account_id,
               trade_id=trade_id,
               stop_loss=body.stop_loss,
               target=body.target
           )
           return {"success": True, "trade": result}
       except TradingError as e:
           return await handle_trading_error(e)
   ```

2. **Add Request Model**
   ```python
   class ModifyTradeRequest(BaseModel):
       stop_loss: Optional[float] = None
       target: Optional[float] = None
   ```

3. **Implement AccountManager Method**
   ```
   File: src/services/paper_trading/account_manager.py
   ```
   ```python
   async def modify_position(
       self, account_id: str, trade_id: str,
       stop_loss: Optional[float] = None,
       target: Optional[float] = None
   ) -> dict:
       """Update stop loss and/or target for open position."""
       # Validate position exists and is open
       # Update database record
       # Return updated position
   ```

4. **Update Frontend**
   ```
   File: ui/src/pages/PaperTrading.tsx
   ```
   - Replace `alert()` with API call
   - Add loading state during update
   - Refresh position data after success

#### Acceptance Criteria
- [ ] PATCH endpoint accepts stop_loss and target
- [ ] Validation prevents invalid values
- [ ] Frontend calls API instead of showing alert
- [ ] Position updates reflected in UI

---

### 1.5 Add Authentication to Prompt Optimization Routes

**File**: `src/web/routes/prompt_optimization.py`
**Lines**: 66, 130, 165, 232, 256, 312, 360, 405
**Issue**: All 8 endpoints have `get_current_user` commented out

#### Implementation Steps

1. **Implement Authentication Dependency**
   ```
   File: src/web/dependencies/auth.py
   ```
   ```python
   from fastapi import Depends, HTTPException, status
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

   security = HTTPBearer(auto_error=False)

   async def get_current_user(
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> dict:
       """Extract and validate current user from request."""
       if credentials is None:
           # For now, return default user (single-user mode)
           return {"user_id": "default", "role": "admin"}

       # TODO: Implement JWT validation when multi-user is needed
       token = credentials.credentials
       # Validate token and return user
       return {"user_id": "default", "role": "admin"}
   ```

2. **Enable in Routes**
   ```python
   from src.web.dependencies.auth import get_current_user

   @router.get("/prompts/active/{data_type}")
   async def get_active_prompt(
       data_type: str,
       current_user: dict = Depends(get_current_user),  # Uncomment
       container: DependencyContainer = Depends(get_container)
   ):
       # Use current_user["user_id"] for user-specific data
   ```

3. **Add User Context to Responses** (optional)
   - Include `user_id` in audit logs
   - Scope prompt templates by user

#### Acceptance Criteria
- [ ] All 8 endpoints have authentication enabled
- [ ] Default user works for single-user mode
- [ ] Foundation ready for multi-user JWT auth

---

## Phase 2: High Priority Feature Completion

**Priority**: HIGH
**Dependencies**: Phase 1 complete
**Impact**: Major feature gaps addressed

### 2.1 Agent Task Tracking System

**File**: `src/web/routes/agents.py`
**Lines**: 62-63, 316, 342, 367, 394, 420, 434
**Issue**: 7 TODO placeholders returning empty/zero data

#### Implementation Steps

1. **Create Agent Tracking Database Schema**
   ```sql
   -- Agent task history
   CREATE TABLE IF NOT EXISTS agent_tasks (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       agent_name TEXT NOT NULL,
       task_type TEXT NOT NULL,
       status TEXT NOT NULL,  -- pending, in_progress, completed, failed
       started_at TEXT,
       completed_at TEXT,
       result JSON,
       error TEXT,
       created_at TEXT NOT NULL
   );

   -- Agent plans
   CREATE TABLE IF NOT EXISTS agent_plans (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       agent_name TEXT NOT NULL,
       plan_type TEXT NOT NULL,  -- focus, task
       content TEXT NOT NULL,
       priority INTEGER DEFAULT 0,
       status TEXT DEFAULT 'active',
       created_at TEXT NOT NULL
   );

   -- Trade execution logs
   CREATE TABLE IF NOT EXISTS agent_trade_logs (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       agent_name TEXT NOT NULL,
       symbol TEXT NOT NULL,
       action TEXT NOT NULL,  -- BUY, SELL, HOLD
       reasoning TEXT,
       confidence REAL,
       executed INTEGER DEFAULT 0,
       trade_id TEXT,
       created_at TEXT NOT NULL
   );

   -- Strategy reflections
   CREATE TABLE IF NOT EXISTS agent_strategy_logs (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       agent_name TEXT NOT NULL,
       reflection_type TEXT NOT NULL,
       content TEXT NOT NULL,
       metrics JSON,
       created_at TEXT NOT NULL
   );
   ```

2. **Create AgentTrackingState Manager**
   ```
   File: src/core/database_state/agent_tracking_state.py
   ```
   - Implement CRUD for all 4 tables
   - Add aggregation methods for metrics

3. **Update Agent Routes**
   ```
   File: src/web/routes/agents.py
   ```
   - Replace hardcoded zeros with database queries
   - Add endpoints for creating/updating records
   - Implement pagination for history

4. **Integrate with Agent Execution**
   - Hook into agent lifecycle events
   - Auto-record task start/completion
   - Capture reasoning and decisions

#### Acceptance Criteria
- [ ] Task history persists and displays in UI
- [ ] Current task shows in agent status
- [ ] Plans and trade logs retrievable
- [ ] Strategy reflections stored

---

### 2.2 Portfolio Sync with Zerodha Integration

**File**: `src/services/portfolio_service.py`
**Lines**: 275-293
**Issue**: Returns hardcoded 100,000 cash instead of actual Zerodha account data

> **Note**: Zerodha is integrated for **data fetching** (portfolio, stock prices). Execution remains **paper trading only**.

#### Implementation Steps

1. **Wire Existing Zerodha Client**
   - Check if Zerodha client is already implemented in codebase
   - Ensure authentication/token handling works
   - Verify API endpoints for account balance and positions

2. **Update Portfolio Service to Use Zerodha**
   ```python
   async def sync_account_balances(self) -> dict:
       """Sync portfolio with Zerodha account data."""
       try:
           zerodha_client = await self._get_zerodha_client()

           # Fetch real balance from Zerodha
           margins = await zerodha_client.get_margins()

           return {
               "status": "completed",
               "cash_balance": margins.get("equity", {}).get("available", {}).get("cash", 0),
               "margin_used": margins.get("equity", {}).get("utilised", {}).get("debits", 0),
               "margin_available": margins.get("equity", {}).get("available", {}).get("live_balance", 0),
               "collateral": margins.get("equity", {}).get("available", {}).get("collateral", 0),
               "sync_timestamp": datetime.now(timezone.utc).isoformat(),
               "broker": "zerodha"
           }
       except Exception as e:
           # Fallback to cached/paper data on API failure
           self._log_error(f"Zerodha sync failed: {e}")
           return await self._get_cached_balance()
   ```

3. **Add Zerodha Position Sync**
   ```python
   async def sync_positions(self) -> List[dict]:
       """Fetch holdings from Zerodha."""
       zerodha_client = await self._get_zerodha_client()
       holdings = await zerodha_client.get_holdings()

       # Transform to standard format
       return [
           {
               "symbol": h["tradingsymbol"],
               "quantity": h["quantity"],
               "average_price": h["average_price"],
               "current_price": h["last_price"],
               "pnl": h["pnl"],
               "pnl_percent": (h["pnl"] / (h["average_price"] * h["quantity"])) * 100
           }
           for h in holdings
       ]
   ```

4. **Separate Real Portfolio from Paper Trading**
   - Real portfolio: Zerodha data (read-only, for reference)
   - Paper trading: Simulated positions/trades (full CRUD)
   - UI should clearly distinguish between the two

#### Acceptance Criteria
- [ ] Portfolio balance fetched from Zerodha API
- [ ] Holdings/positions sync from Zerodha
- [ ] Graceful fallback on API failures
- [ ] Clear separation: Zerodha = real data, Paper = simulated trades

---

### 2.3 Account Management Backend Endpoints

**File**: `ui/src/features/paper-trading/context/AccountContext.tsx`
**Lines**: 97-155, 219
**Issue**: Create/delete account endpoints return 404

#### Implementation Steps

1. **Add Create Account Endpoint**
   ```
   File: src/web/routes/paper_trading.py
   ```
   ```python
   @router.post("/paper-trading/accounts/create")
   async def create_paper_account(
       request: Request,
       body: CreateAccountRequest,
       container: DependencyContainer = Depends(get_container)
   ) -> Dict[str, Any]:
       """Create a new paper trading account."""
       account_manager = await container.get("paper_trading_account_manager")
       account = await account_manager.create_account(
           account_id=body.account_id,
           initial_balance=body.initial_balance,
           account_type=body.account_type
       )
       return {"success": True, "account": account}
   ```

2. **Add Delete Account Endpoint**
   ```python
   @router.delete("/paper-trading/accounts/{account_id}")
   async def delete_paper_account(
       request: Request,
       account_id: str,
       container: DependencyContainer = Depends(get_container)
   ) -> Dict[str, Any]:
       """Delete a paper trading account."""
       account_manager = await container.get("paper_trading_account_manager")
       await account_manager.delete_account(account_id)
       return {"success": True, "message": f"Account {account_id} deleted"}
   ```

3. **Add List Accounts Endpoint**
   ```python
   @router.get("/paper-trading/accounts")
   async def list_paper_accounts(
       request: Request,
       container: DependencyContainer = Depends(get_container)
   ) -> Dict[str, Any]:
       """List all paper trading accounts."""
       account_manager = await container.get("paper_trading_account_manager")
       accounts = await account_manager.list_accounts()
       return {"accounts": accounts}
   ```

4. **Implement AccountManager Methods**
   ```
   File: src/services/paper_trading/account_manager.py
   ```
   - `create_account()` - Initialize new account with balance
   - `delete_account()` - Soft delete with position validation
   - `list_accounts()` - Return all accounts for user

5. **Update Frontend Context**
   - Remove hardcoded `'paper_swing_main'`
   - Fetch accounts on mount
   - Handle multi-account selection

#### Acceptance Criteria
- [ ] Can create new paper accounts via UI
- [ ] Can delete accounts (with confirmation)
- [ ] Account list dynamically loaded
- [ ] Default account auto-selected

---

### 2.4 API Field Name Standardization

**File**: `ui/src/features/paper-trading/hooks/usePaperTrading.ts`
**Lines**: 89-105
**Issue**: Manual camelCase to snake_case transformation

#### Implementation Steps

1. **Define Shared Types**
   ```
   File: ui/src/types/paperTrading.ts
   ```
   - Define Position, Trade, Account interfaces
   - Use consistent naming (pick one convention)

2. **Add Response Transformers**
   ```
   File: ui/src/utils/apiTransformers.ts
   ```
   ```typescript
   export function transformPosition(apiPosition: any): Position {
     return {
       tradeId: apiPosition.trade_id,
       symbol: apiPosition.symbol,
       quantity: apiPosition.quantity,
       entryPrice: apiPosition.entry_price,
       currentPrice: apiPosition.current_price || apiPosition.ltp,
       unrealizedPnl: apiPosition.unrealized_pnl || apiPosition.pnl,
       // ... etc
     };
   }
   ```

3. **Update Backend to Use Consistent Names**
   ```
   File: src/web/routes/paper_trading.py
   ```
   - Use Pydantic response models
   - Configure `by_alias=True` for camelCase output
   ```python
   class PositionResponse(BaseModel):
       trade_id: str = Field(alias="tradeId")
       entry_price: float = Field(alias="entryPrice")

       class Config:
           populate_by_name = True
   ```

#### Acceptance Criteria
- [ ] Backend returns consistent field names
- [ ] Frontend doesn't need manual transformation
- [ ] Type safety maintained end-to-end

---

### 2.5 Complete Portfolio Intelligence Analyzer

**File**: `src/services/portfolio_intelligence/comprehensive_analyzer.py`
**Lines**: 122, 161
**Issue**: Placeholder comments for unimplemented analysis

#### Implementation Steps

1. **Integrate with Market Data Service**
   - Fetch real-time prices
   - Calculate actual portfolio metrics
   - Use historical data for trends

2. **Implement Missing Analysis Methods**
   - Sector exposure analysis
   - Concentration risk calculation
   - Correlation matrix
   - Volatility metrics

3. **Connect to News/Earnings Data**
   - Pull from `news_earnings_state`
   - Factor into risk scores
   - Generate alerts for earnings dates

#### Acceptance Criteria
- [ ] Analysis uses real market data
- [ ] All placeholder methods implemented
- [ ] Results match expected format

---

## Phase 3: Medium Priority Enhancements

**Priority**: MEDIUM
**Dependencies**: Phase 2 substantially complete
**Impact**: Important feature polish

### 3.1 Dashboard Token & Trade Tracking

**File**: `src/web/routes/dashboard.py`
**Lines**: 479-480

#### Implementation Steps

1. **Query claude_token_usage Table**
   ```python
   async def get_token_usage_today(state_manager) -> int:
       """Get total tokens used today."""
       today = datetime.now().strftime("%Y-%m-%d")
       result = await state_manager.query(
           "SELECT SUM(tokens_used) FROM claude_token_usage WHERE date(created_at) = ?",
           (today,)
       )
       return result[0][0] or 0
   ```

2. **Query paper_trades Table**
   ```python
   async def get_trades_today(state_manager) -> int:
       """Get count of trades executed today."""
       today = datetime.now().strftime("%Y-%m-%d")
       result = await state_manager.query(
           "SELECT COUNT(*) FROM paper_trades WHERE date(created_at) = ?",
           (today,)
       )
       return result[0][0] or 0
   ```

3. **Update Dashboard Endpoint**
   - Replace hardcoded zeros
   - Add caching for performance

---

### 3.2 Paper Trading Benchmark Metrics

**File**: `src/web/routes/paper_trading.py`
**Lines**: 400-401

#### Implementation Steps

1. **Add Benchmark Data Source**
   - Fetch NIFTY 50 historical data
   - Store in database for comparison
   - Update daily via scheduler

2. **Calculate Alpha**
   ```python
   def calculate_alpha(portfolio_return: float, benchmark_return: float, beta: float = 1.0) -> float:
       """Calculate Jensen's alpha."""
       risk_free_rate = 0.06  # 6% annual, configurable
       return portfolio_return - (risk_free_rate + beta * (benchmark_return - risk_free_rate))
   ```

3. **Update Performance Endpoint**
   - Fetch benchmark return for period
   - Calculate and return alpha

---

### 3.3 Trade Model Field Additions

**File**: `src/services/paper_trading/account_manager.py`
**Lines**: 229, 265, 267

#### Implementation Steps

1. **Update Trade Database Schema**
   ```sql
   ALTER TABLE paper_trades ADD COLUMN ai_suggested INTEGER DEFAULT 0;
   ALTER TABLE paper_trades ADD COLUMN reason_closed TEXT;
   ```

2. **Update Trade Creation**
   - Accept `ai_suggested` parameter
   - Track source of trade recommendation

3. **Update Trade Closing**
   - Accept `reason_closed` parameter
   - Options: manual_exit, stop_loss, target_hit, expired

---

### 3.4 Risk Assessment Backend Endpoint

**File**: `ui/src/components/Dashboard/QuickTradeForm.tsx`
**Line**: 184

#### Implementation Steps

1. **Create Risk Assessment Endpoint**
   ```
   File: src/web/routes/risk.py
   ```
   ```python
   @router.post("/risk/assess-trade")
   async def assess_trade_risk(
       request: Request,
       body: TradeRiskRequest,
       container: DependencyContainer = Depends(get_container)
   ) -> Dict[str, Any]:
       """Assess risk for proposed trade."""
       risk_service = await container.get("risk_service")
       assessment = await risk_service.assess_trade(
           symbol=body.symbol,
           action=body.action,
           quantity=body.quantity,
           price=body.price
       )
       return assessment
   ```

2. **Implement Risk Assessment Logic**
   - Position size vs portfolio
   - Sector concentration impact
   - Volatility-adjusted risk
   - Stop loss recommendation

3. **Update Frontend**
   - Call assessment before execution
   - Display risk warnings
   - Require confirmation for high-risk trades

---

### 3.5 MCP Server Real Implementations

**File**: `src/mcp/enhanced_paper_trading_server.py`
**Lines**: 413, 571

#### Implementation Steps

1. **Replace Mock Strategy Context**
   - Fetch from agent plans database
   - Include active strategies
   - Return current focus areas

2. **Calculate Real Monthly P&L**
   - Query paper_trades for month
   - Aggregate realized + unrealized
   - Include fees if applicable

---

### 3.6 Recommendation Engine Caching

**File**: `src/services/recommendation_engine/engine.py`
**Line**: 138

#### Implementation Steps

1. **Implement Cache Layer**
   ```python
   from functools import lru_cache
   from datetime import datetime, timedelta

   class RecommendationCache:
       def __init__(self, ttl_seconds: int = 300):
           self._cache = {}
           self._ttl = ttl_seconds

       def get(self, key: str) -> Optional[dict]:
           if key in self._cache:
               value, timestamp = self._cache[key]
               if datetime.now() - timestamp < timedelta(seconds=self._ttl):
                   return value
               del self._cache[key]
           return None

       def set(self, key: str, value: dict):
           self._cache[key] = (value, datetime.now())
   ```

2. **Apply to Recommendation Generation**
   - Cache by symbol + timeframe
   - Invalidate on new market data
   - TTL of 5 minutes default

---

### 3.7 Factor Calculator Integrations

**File**: `src/services/recommendation_engine/factor_calculator.py`
**Lines**: 205+

#### Implementation Steps

1. **Market Sentiment Integration**
   - Pull from news analysis
   - Weight by recency
   - Normalize to -1 to +1

2. **Earnings Surprises**
   - Compare actual vs expected
   - Track historical surprise patterns
   - Weight by materiality

3. **Sector Momentum**
   - Calculate sector-level trends
   - Compare stock vs sector
   - Identify relative strength

---

### 3.8 Global Search Implementation

**File**: `ui/src/components/common/Breadcrumb.tsx`
**Line**: 55

#### Implementation Steps

1. **Create Search Index**
   - Index symbols, agents, settings
   - Support fuzzy matching
   - Recent searches history

2. **Implement Search Component**
   ```
   File: ui/src/components/common/GlobalSearch.tsx
   ```
   - Command palette style (Cmd+K)
   - Categorized results
   - Keyboard navigation

3. **Add Search Backend** (optional)
   - Full-text search endpoint
   - Symbol lookup
   - Documentation search

---

## Phase 4: Code Quality & Maintenance

**Priority**: LOW-MEDIUM
**Dependencies**: Core functionality stable
**Impact**: Long-term maintainability

### 4.1 Refactor Oversized Components

| Component | Current | Target | Action |
|-----------|---------|--------|--------|
| `PaperTrading.tsx` | 1,231 | <350 | Split into feature components |
| `NewsEarnings.tsx` | 818 | <350 | Extract news/earnings sections |
| `ClaudeTransparencyDashboard.tsx` | 667 | <350 | Create sub-dashboards |
| `SchedulerStatus.tsx` | 567 | <350 | Extract queue/job components |
| `QueueHealthMonitor.tsx` | 517 | <350 | Extract metrics/charts |

#### Refactoring Strategy

1. **PaperTrading.tsx** → Split into:
   - `PaperTradingDashboard.tsx` - Overview
   - `PositionsPanel.tsx` - Open positions
   - `TradeHistory.tsx` - Closed trades
   - `PerformanceMetrics.tsx` - Charts/stats
   - `TradeExecutionForm.tsx` - Buy/sell forms

2. **NewsEarnings.tsx** → Split into:
   - `NewsPanel.tsx` - News feed
   - `EarningsCalendar.tsx` - Upcoming earnings
   - `StockAnalysis.tsx` - Individual stock view

---

### 4.2 Remove Debug Console Statements

**Files**: 28 files with console.log

#### Implementation Steps

1. **Create Logger Utility**
   ```typescript
   // ui/src/utils/logger.ts
   const isDev = process.env.NODE_ENV === 'development';

   export const logger = {
     debug: (...args: any[]) => isDev && console.log(...args),
     info: (...args: any[]) => console.info(...args),
     warn: (...args: any[]) => console.warn(...args),
     error: (...args: any[]) => console.error(...args),
   };
   ```

2. **Replace console.log Calls**
   - Use `logger.debug()` for dev-only
   - Keep `logger.error()` for errors
   - Remove unnecessary logging

---

### 4.3 Queue Monitoring Enhancements

**File**: `src/web/routes/monitoring.py`
**Lines**: 98, 105

#### Implementation Steps

1. **Track Queue Uptime**
   - Record queue start time
   - Calculate uptime from start
   - Reset on restart

2. **Add Recent Jobs List**
   - Query last N completed tasks
   - Include status and duration
   - Link to task details

---

### 4.4 Analytics Service Improvements

**File**: `src/services/analytics_service.py`
**Lines**: 197, 237

#### Implementation Steps

1. **Real Support/Resistance Detection**
   - Use pivot points algorithm
   - Identify swing highs/lows
   - Volume-weighted levels

2. **Dynamic Risk Scoring**
   - Multi-factor risk model
   - Volatility component
   - Liquidity component
   - News sentiment component

---

### 4.5 Event Type Standardization

**File**: `src/core/background_scheduler/executors/fundamental_executor.py`
**Lines**: 238, 354

#### Implementation Steps

1. **Add MARKET_DATA_UPDATE Event Type**
   ```python
   # In EventType enum
   MARKET_DATA_UPDATE = "market_data_update"
   ```

2. **Update Executor**
   - Use correct event type
   - Add event metadata

---

## Implementation Schedule

### Recommended Order

```
Phase 1 (Critical) - Start Immediately
├── 1.1 Event Router Persistence
├── 1.2 DI Container Fix
├── 1.3 MCP Trade Handlers
├── 1.4 Position Modification API
└── 1.5 Authentication

Phase 2 (High) - After Phase 1
├── 2.1 Agent Task Tracking
├── 2.2 Broker Integration
├── 2.3 Account Management
├── 2.4 Field Standardization
└── 2.5 Portfolio Intelligence

Phase 3 (Medium) - Parallel with Phase 2
├── 3.1 Dashboard Metrics
├── 3.2 Benchmark Metrics
├── 3.3 Trade Model Fields
├── 3.4 Risk Assessment
├── 3.5 MCP Real Implementations
├── 3.6 Recommendation Caching
├── 3.7 Factor Integrations
└── 3.8 Global Search

Phase 4 (Maintenance) - Ongoing
├── 4.1 Component Refactoring
├── 4.2 Debug Statement Cleanup
├── 4.3 Queue Monitoring
├── 4.4 Analytics Improvements
└── 4.5 Event Standardization
```

---

## Testing Requirements

### Unit Tests Required

| Component | Test File | Coverage Target |
|-----------|-----------|-----------------|
| EventTriggerState | `test_event_trigger_state.py` | 90% |
| AgentTrackingState | `test_agent_tracking_state.py` | 90% |
| BrokerClient | `test_broker_client.py` | 85% |
| AccountManager | `test_account_manager.py` | 90% |
| RiskAssessment | `test_risk_assessment.py` | 85% |

### Integration Tests Required

| Flow | Test File |
|------|-----------|
| Trade Execution E2E | `test_trade_flow.py` |
| Account Lifecycle | `test_account_lifecycle.py` |
| Event Trigger Persistence | `test_event_persistence.py` |

### Frontend Tests

| Component | Test File |
|-----------|-----------|
| Trade Handlers | `App.test.tsx` |
| Account Context | `AccountContext.test.tsx` |
| API Transformers | `apiTransformers.test.ts` |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Database migration failures | Create backup before schema changes |
| API breaking changes | Version endpoints, deprecation warnings |
| Frontend/backend mismatch | Shared type definitions, contract tests |
| Performance degradation | Load testing, caching strategies |
| Authentication bypass | Security audit after implementation |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| TODO comments in codebase | 21+ | 0 |
| API endpoints returning placeholders | 15+ | 0 |
| Frontend features blocked | 5 | 0 |
| Component size violations | 8 | 0 |
| Console.log in production | 28 files | 0 |

---

## Appendix: File Reference

### Files to Create

```
src/core/database_state/event_trigger_state.py
src/core/database_state/agent_tracking_state.py
src/web/dependencies/auth.py
src/web/routes/risk.py
ui/src/services/paperTradingApi.ts
ui/src/types/paperTrading.ts
ui/src/utils/apiTransformers.ts
ui/src/utils/logger.ts
ui/src/components/common/GlobalSearch.tsx
```

> **Note**: Zerodha client already exists for data. Paper trading uses existing paper_trading_state.

### Files to Modify

```
src/core/di.py
src/core/database_state/database_state.py
src/core/database_state/__init__.py
src/services/event_router_service.py
src/services/portfolio_service.py
src/services/paper_trading/account_manager.py
src/services/recommendation_engine/engine.py
src/services/recommendation_engine/factor_calculator.py
src/services/analytics_service.py
src/web/routes/agents.py
src/web/routes/dashboard.py
src/web/routes/paper_trading.py
src/web/routes/prompt_optimization.py
src/web/routes/monitoring.py
src/mcp/enhanced_paper_trading_server.py
ui/src/App.tsx
ui/src/pages/PaperTrading.tsx
ui/src/features/paper-trading/context/AccountContext.tsx
ui/src/features/paper-trading/hooks/usePaperTrading.ts
ui/src/components/common/Breadcrumb.tsx
ui/src/components/Dashboard/QuickTradeForm.tsx
```

---

## Claude Agent SDK Integration Notes

Since the app is powered by **Claude Agent SDK**, the following considerations apply:

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Agent SDK                         │
├─────────────────────────────────────────────────────────────┤
│  Specialized Agents:                                        │
│  ├── Technical Analyst Agent                                │
│  ├── Risk Manager Agent                                     │
│  ├── Portfolio Optimizer Agent                              │
│  ├── Scan Agent (market screening)                          │
│  └── Execution Agent (paper trades)                         │
├─────────────────────────────────────────────────────────────┤
│  MCP Tools Available to Agents:                             │
│  ├── paper_trading_buy                                      │
│  ├── paper_trading_sell                                     │
│  ├── get_portfolio_positions                                │
│  ├── get_market_data                                        │
│  ├── analyze_stock                                          │
│  └── get_recommendations                                    │
└─────────────────────────────────────────────────────────────┘
```

### SDK-Specific Implementation Guidelines

1. **Agent Task Tracking** (Gap 2.1)
   - Hook into SDK's conversation lifecycle
   - Track tool calls made by agents
   - Record reasoning/decisions from agent responses

2. **MCP Tool Integration** (Gap 1.3)
   - Frontend handlers should call MCP-exposed tools
   - Not direct REST APIs for agent-triggered actions
   - Use WebSocket for real-time agent updates

3. **Token Usage Tracking** (Gap 3.1)
   - SDK provides token usage callbacks
   - Store in `claude_token_usage` table
   - Aggregate by agent and session

4. **Queue System Integration**
   - AI_ANALYSIS queue executes via SDK
   - Each queue task = one agent conversation
   - Prevents turn limit exhaustion on large portfolios

### Data vs Execution Separation

| Component | Source | Purpose |
|-----------|--------|---------|
| Portfolio data | Zerodha API | View real holdings, balance |
| Stock prices | Zerodha API | Real-time market data |
| Trade execution | Paper trading | Simulated buys/sells |
| Position tracking | `paper_trades` table | Track simulated positions |
| Performance metrics | Paper trading DB | Calculate P&L on simulated trades |

### Paper Trading Constraints

| Constraint | Implementation |
|------------|----------------|
| No real execution | All trades stored in `paper_trades` table |
| Simulated fills | Instant fill at current market price from Zerodha |
| Real market data | Prices fetched from Zerodha API |
| Account isolation | Multiple paper accounts for testing strategies |

---

*Document Version: 1.0*
*Generated: 2025-11-23*
