# Portfolio Scan Data Source Analysis

**Date**: January 2025  
**Status**: Current Configuration Analysis

---

## Current Situation

### ✅ What's Configured
- **Zerodha API Key**: ✅ Present in `.env` file
- **Zerodha API Secret**: ✅ Present in `.env` file
- **Authentication Status**: ❌ **NOT Authenticated**

### ❌ What's Missing
- **OAuth Token File**: `data/zerodha_oauth_token.json` does not exist
- **Authentication Flow**: Not completed yet

---

## Current Data Source: CSV File

**Confirmed**: The portfolio scan is currently fetching from **CSV file**, not Zerodha API.

### Evidence:
1. **API Response**: `"source": "csv_fallback"`
2. **Holdings Count**: 81 holdings loaded from CSV
3. **CSV File**: `holdings/holdings (5).csv` (last modified Oct 6)
4. **Authentication Status**: `"authenticated": false`

---

## Why CSV Instead of Zerodha?

The system follows this priority order:

1. **Try Zerodha API** → ❌ Not authenticated (no OAuth token)
2. **Fallback to CSV** → ✅ Using CSV file
3. **Fallback to Database** → Available if CSV missing
4. **Fallback to Empty** → Creates empty portfolio if nothing found

### Code Flow:
```python
# src/services/analytics.py:365-401
async def run_portfolio_scan():
    # 1. Try Zerodha first
    broker = await get_broker(config)
    if is_broker_connected(broker):
        # Fetch from Zerodha API ✅
        return {"source": "zerodha_live"}
    
    # 2. Fallback to CSV
    csv_path = _find_holdings_csv(config)
    holdings = await _load_holdings_rows(csv_path)  # ← Currently here ✅
    return {"source": "csv_fallback"}
```

---

## How to Switch to Zerodha API

### Step 1: Complete OAuth Authentication

You need to complete the Zerodha OAuth flow:

1. **Get Authorization URL**:
   ```bash
   curl "http://localhost:8000/api/auth/zerodha/login?user_id=YOUR_USER_ID"
   ```
   
   This returns an `auth_url` that you need to visit.

2. **Visit Authorization URL**:
   - Open the `auth_url` in your browser
   - Login to Zerodha
   - Grant permissions to your app
   - Zerodha redirects back with a request token

3. **Callback Handled Automatically**:
   - The app receives the callback
   - Exchanges request token for access token
   - Stores token in `data/zerodha_oauth_token.json`

4. **Verify Authentication**:
   ```bash
   curl "http://localhost:8000/api/auth/zerodha/status"
   ```
   
   Should return `"authenticated": true`

### Step 2: Verify Portfolio Scan Uses Zerodha

After authentication, when you click "Scan Portfolio":
- It will check `is_broker_connected()` → ✅ True
- Fetch live holdings from Zerodha API
- Return `"source": "zerodha_live"`

---

## Quick Check Commands

### Check Authentication Status:
```bash
curl http://localhost:8000/api/auth/zerodha/status
```

### Get Authorization URL:
```bash
curl "http://localhost:8000/api/auth/zerodha/login?user_id=YOUR_USER_ID"
```

### Test Portfolio Scan Source:
```bash
curl -X POST http://localhost:8000/api/portfolio-scan
```
Look for `"source"` field in response:
- `"csv_fallback"` = Currently using CSV
- `"zerodha_live"` = Using Zerodha API ✅

---

## Summary

| Item | Status |
|------|--------|
| API Key in .env | ✅ Present |
| API Secret in .env | ✅ Present |
| OAuth Token File | ❌ Missing |
| Authentication Status | ❌ Not Authenticated |
| Current Data Source | ✅ **CSV File** |
| Holdings Loaded | 81 from CSV |

**Next Step**: Complete OAuth authentication flow to switch to Zerodha API.

---

**Last Updated**: January 2025  
**Current Source**: CSV File (`holdings/holdings (5).csv`)

