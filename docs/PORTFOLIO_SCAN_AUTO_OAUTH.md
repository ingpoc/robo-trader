# Portfolio Scan Auto-OAuth Implementation

## Summary

Implemented automatic OAuth flow for portfolio scan when Zerodha credentials are present but OAuth token is missing.

---

## Changes Made

### 1. **Environment Variable Token Management** (`src/core/env_helpers.py`)

Created new helper module for managing OAuth tokens in `.env` file:

- `find_env_file()` - Locates `.env` file in project root
- `update_env_file(key, value)` - Updates or adds environment variable
- `save_zerodha_token_to_env(token_data)` - Saves OAuth token to `.env`
- `get_zerodha_token_from_env()` - Retrieves token from ENV (with expiry check)
- `remove_zerodha_token_from_env()` - Removes tokens from `.env`

### 2. **Broker Client Enhancement** (`src/mcp/broker.py`)

Modified `_get_stored_token()` to check ENV variables first, then fallback to token file:

```python
# Priority order:
1. Check ENV variable (ZERODHA_ACCESS_TOKEN)
2. Fallback to token file (data/zerodha_oauth_token.json)
```

### 3. **OAuth Service Updates** (`src/services/zerodha_oauth_service.py`)

- `get_stored_token()` - Now checks ENV first, then file
- `_store_tokens()` - Saves to both ENV file and token file (backup)
- `_delete_token_file()` - Removes from both ENV and file

### 4. **Portfolio Scan Endpoint** (`src/web/routes/execution.py`)

Enhanced `/api/portfolio-scan` endpoint with automatic OAuth flow:

**Priority Logic:**
1. ✅ Check for OAuth token in ENV variable
2. ✅ If not found, check for API key/secret in ENV
3. ✅ If API credentials present → Auto-trigger OAuth flow
4. ✅ Return auth URL to frontend
5. ✅ Fallback to CSV if neither available

**Response Types:**
- `oauth_required` - When OAuth is needed (returns `auth_url`)
- `Portfolio scan completed` - When scan succeeds

### 5. **Frontend Integration** (`ui/src/hooks/usePortfolio.ts`)

Updated `portfolioScan` mutation to handle OAuth flow:

- Detects `oauth_required` status
- Opens OAuth URL in popup window
- Shows informative toast message
- Guides user to complete auth and retry scan

### 6. **TypeScript Types** (`ui/src/api/endpoints.ts`)

Updated `portfolioScan` response type to include OAuth fields:

```typescript
{
  status: string
  message?: string
  auth_url?: string
  state?: string
  redirect_url?: string
  instructions?: string
  source?: string
  holdings_count?: number
  portfolio?: unknown
}
```

---

## How It Works

### Flow Diagram

```
User clicks "Scan Portfolio"
    ↓
Check ZERODHA_ACCESS_TOKEN in ENV
    ↓
No Token? → Check API Key/Secret in ENV
    ↓
API Credentials Present? → Generate OAuth URL
    ↓
Return auth_url to frontend
    ↓
Frontend opens auth URL in popup
    ↓
User approves in Zerodha
    ↓
OAuth callback saves token to ENV
    ↓
User clicks "Scan Portfolio" again
    ↓
Token found → Connect to Zerodha API
    ↓
Fetch holdings from Zerodha ✅
```

### Example Scenarios

#### Scenario 1: No Token, Has Credentials
```
1. User clicks "Scan Portfolio"
2. Backend: No token in ENV
3. Backend: API key/secret found
4. Backend: Returns {status: "oauth_required", auth_url: "..."}
5. Frontend: Opens auth URL in popup
6. User: Approves in Zerodha
7. Backend: Saves token to .env file
8. User: Clicks "Scan Portfolio" again
9. Backend: Token found → Connects to Zerodha → Fetches holdings ✅
```

#### Scenario 2: Token Present
```
1. User clicks "Scan Portfolio"
2. Backend: Token found in ENV
3. Backend: Connects to Zerodha
4. Backend: Fetches holdings ✅
```

#### Scenario 3: No Credentials
```
1. User clicks "Scan Portfolio"
2. Backend: No token in ENV
3. Backend: No API credentials
4. Backend: Falls back to CSV file ✅
```

---

## Environment Variables

The following variables are managed automatically:

- `ZERODHA_ACCESS_TOKEN` - OAuth access token (saved after approval)
- `ZERODHA_USER_ID` - User ID from Zerodha
- `ZERODHA_TOKEN_EXPIRES_AT` - Token expiry timestamp

**Required (Manual):**
- `ZERODHA_API_KEY` - Your Zerodha API key
- `ZERODHA_API_SECRET` - Your Zerodha API secret

---

## Testing

To test the implementation:

1. **Ensure API credentials are in `.env`**:
   ```bash
   ZERODHA_API_KEY=your_key
   ZERODHA_API_SECRET=your_secret
   ```

2. **Remove any existing token** (if testing OAuth flow):
   ```bash
   # Remove from .env
   unset ZERODHA_ACCESS_TOKEN
   
   # Or remove from file
   rm data/zerodha_oauth_token.json
   ```

3. **Click "Scan Portfolio" in UI**:
   - Should detect no token
   - Should find API credentials
   - Should open OAuth popup
   - After approval, token saved to `.env`
   - Next scan should use Zerodha API

4. **Verify token saved**:
   ```bash
   grep ZERODHA_ACCESS_TOKEN .env
   ```

---

## Benefits

1. **Seamless UX** - No manual OAuth initiation needed
2. **Persistent Storage** - Token saved to `.env` (survives restarts)
3. **Fallback Support** - CSV fallback if credentials missing
4. **Secure** - Token stored in `.env` (not committed to git)
5. **Automatic** - System auto-detects when OAuth is needed

---

## Files Modified

- `src/core/env_helpers.py` (NEW)
- `src/mcp/broker.py`
- `src/services/zerodha_oauth_service.py`
- `src/web/routes/execution.py`
- `ui/src/hooks/usePortfolio.ts`
- `ui/src/api/endpoints.ts`

---

## Notes

- Token expiry is checked automatically (24 hours for Zerodha)
- Both ENV and file storage maintained for compatibility
- Frontend opens OAuth URL in popup window
- User must complete OAuth and click "Scan Portfolio" again after approval

---

**Last Updated**: January 2025

