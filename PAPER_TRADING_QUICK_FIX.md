# Paper Trading - Quick Fix Guide

## Problem Summary

Paper Trading page shows error: "Failed to load paper trading account. Please try again."

**Root Cause**: API Gateway routing misconfiguration blocks frontend requests from reaching the Paper Trading microservice.

---

## Quick Fix (5 minutes)

### Option A: Remove Dead Code (Recommended - Simplest)

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/services/api_gateway/main.py`

**Action**: Delete lines 459-680 (paper trading endpoints section)

**Why**:
- These endpoints are unreachable (generic proxy route matches first)
- Paper Trading microservice already has working endpoints
- Uses temporary database location

**After deletion**, requests will flow correctly:
```
Frontend → API Gateway (generic proxy) → Paper Trading Service (port 8008)
```

---

### Option B: Route Reordering (Keeps endpoints in API Gateway)

If you want to keep paper trading endpoints in API Gateway, move them BEFORE the generic proxy route.

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/services/api_gateway/main.py`

**Current structure**:
```
Line 151-276: Specific aggregation endpoints
Line 281:     Generic proxy route ← CATCHES PAPER TRADING REQUESTS
Line 328+:    Other endpoints
Line 553+:    Paper trading endpoints ← NEVER REACHED
```

**Change to**:
```
Line 151-276: Specific aggregation endpoints
Line 281+:    Paper trading endpoints ← MOVED HERE (BEFORE generic proxy)
Line ???:     Generic proxy route ← MOVED HERE (at the end)
```

**How to do it**:
1. Cut lines 553-680 (paper trading endpoints)
2. Paste them after line 276 (before generic proxy)
3. Adjust line numbers in documentation

---

## Testing the Fix

After applying the fix:

### Test 1: Direct curl
```bash
curl http://localhost:8000/api/paper-trading/accounts/paper_swing_main/overview
```

Expected response (HTTP 200):
```json
{
  "account_id": "paper_swing_main",
  "account_type": "swing",
  "strategy_type": "swing",
  "balance": 100000.0,
  "buying_power": 100000.0,
  "deployed_capital": 0.0,
  "total_pnl": 0.0,
  "total_pnl_pct": 0.0,
  "monthly_pnl": 0.0,
  "monthly_pnl_pct": 0.0,
  "open_positions_count": 0,
  "today_trades": 0,
  "win_rate": 0.0,
  "created_at": "2025-10-20T19:54:13.169243",
  "reset_date": ""
}
```

### Test 2: Frontend
1. Navigate to http://localhost:3001
2. Click "Paper Trading" in sidebar
3. Should see account overview with:
   - Balance: ₹100,000
   - Buying Power: ₹100,000
   - P&L: 0% (starting balance)

### Test 3: Browser Console
No errors should appear. All API calls should return 200.

---

## Why This Happened

The API Gateway was designed for two deployment scenarios:

1. **Monolithic Mode**: All endpoints in single API Gateway service
2. **Microservices Mode**: Routes requests to dedicated microservices

The codebase has hardcoded paper trading endpoints (Option 1) that conflict with the generic proxy route, which prevents them from working. Meanwhile, the Paper Trading microservice (Option 2) is fully functional but unreachable.

**Current setup**: Microservices mode with dead code from monolithic mode.

---

## Additional Improvements (Optional)

After fixing the routing, consider these improvements:

1. **Fix database location** (line 466):
   ```python
   PAPER_TRADING_DB = "/shared/db/robo_trader_paper_trading.db"
   ```
   Instead of `/tmp/robo_trader_paper_trading.db`

2. **Use environment variables for service URLs** (line 50):
   ```python
   SERVICES = {
       "paper-trading": os.getenv("PAPER_TRADING_URL", "http://paper-trading:8008"),
       ...
   }
   ```
   Instead of hardcoded DNS names

3. **Remove error suppression** (lines 587-591):
   Add proper error logging if endpoints are kept in API Gateway

---

## Expected Results

**Before Fix**:
- Paper Trading page shows "Failed to load paper trading account"
- Browser console: Multiple 404 errors
- No account data displayed

**After Fix**:
- Paper Trading page loads successfully
- Shows account overview (balance, buying power, P&L)
- All tabs functional (Positions, Trades, Performance)
- Can execute paper trades
- Real-time updates via WebSocket

---

## Verification Checklist

- [ ] Applied fix (deleted lines 459-680 or reordered routes)
- [ ] Restarted API Gateway service
  ```bash
  docker restart robo-trader-api-gateway
  ```
- [ ] Tested direct curl to `/api/paper-trading/...` endpoint
- [ ] Navigated to Paper Trading page and confirmed no errors
- [ ] Checked browser console for errors (should be clean)
- [ ] Verified account data displays correctly

---

## Rollback Plan

If something breaks after the fix:

1. Restore original file:
   ```bash
   git checkout services/api_gateway/main.py
   ```

2. Restart API Gateway:
   ```bash
   docker restart robo-trader-api-gateway
   ```

3. Page will go back to showing error (but without introducing new issues)

---

## Files Involved

- **API Gateway**: `/Users/gurusharan/Documents/remote-claude/robo-trader/services/api_gateway/main.py`
  - Lines 281-326: Generic proxy route
  - Lines 459-680: Paper trading endpoints (delete this)
  - Line 50: Service registry
  - Line 466: Database path

- **Paper Trading Service**: `/Users/gurusharan/Documents/remote-claude/robo-trader/services/paper_trading/main.py`
  - Already working correctly
  - No changes needed

- **Frontend**: `/Users/gurusharan/Documents/remote-claude/robo-trader/ui/vite.config.ts`
  - Proxy already configured correctly: `/api/* → http://localhost:8000`
  - No changes needed

---

## Questions?

Refer to the detailed test report: `/Users/gurusharan/Documents/remote-claude/robo-trader/PAPER_TRADING_TEST_REPORT.md`
