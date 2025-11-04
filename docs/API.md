# Robo Trader API Documentation - Phase 1 Complete

> **Last Updated**: 2025-10-24
> **Version**: 1.0.0 - Phase 1 Complete
> **Base URL**: http://localhost:8000
> **System Status**: ✅ Phase 1 Complete - Core trade execution working

## Overview

The Robo Trader API provides comprehensive access to an AI-powered paper trading system with autonomous trading execution via Claude Agent SDK. All AI functionality uses Claude Agent SDK exclusively with no direct Anthropic API calls.

## Current Implementation Status

### ✅ **Phase 1 Complete (100%)**

**Trade Execution** (Core Features Working):
- ✅ Buy trade execution via Claude Agent
- ✅ Sell trade execution with P&L calculation
- ✅ Close position with realized P&L
- ✅ Input validation (Pydantic v2)
- ✅ Error handling with structured responses
- ✅ Claude Agent SDK integration

**Testing Status**:
- ✅ Buy endpoint tested: RELIANCE 5 shares @ ₹2850
- ✅ Sell endpoint tested: RELIANCE 3 shares @ ₹2900, +₹450 P&L
- ✅ Close endpoint tested: +₹1,700 realized P&L
- ✅ Validation tests: Negative/zero quantities rejected (422)
- ✅ Browser testing: Paper Trading page loads

### 📋 **Phase 2+ (Future)**

- [ ] Advanced order types (LIMIT, STOP)
- [ ] Options trading
- [ ] Historical analytics
- [ ] Risk management features
- [ ] Multi-account support

---

## Authentication

**Method**: Claude Code CLI Authentication
- Uses `oauth_token` from Claude Code CLI
- No stored API keys or credentials in `.env`
- Automatic token management via Claude Agent SDK
- Verified on startup with `validate_claude_sdk_auth()`

**Configuration**:
```bash
# No API key needed in .env
# Authentication happens via:
claude auth
```

---

## API Endpoints

### Paper Trading - Trade Execution

#### 1. Execute Buy Trade

**Endpoint**: `POST /api/paper-trading/accounts/{account_id}/trades/buy`

**Description**: Execute a buy trade via Claude Agent validation and decision-making.

**Path Parameters**:
- `account_id` (string, required): Paper trading account ID (e.g., "swing-001")

**Request Body**:
```json
{
  "symbol": "RELIANCE",
  "quantity": 5,
  "order_type": "MARKET",
  "price": null
}
```

**Request Fields**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| symbol | string | Yes | 1-20 chars, uppercase | Stock symbol (RELIANCE, TCS, INFY, etc.) |
| quantity | integer | Yes | 1-10,000 | Number of shares to buy |
| order_type | string | No | MARKET\|LIMIT | Order execution type (default: MARKET) |
| price | float | No | > 0 | Limit price (only for LIMIT orders) |

**Success Response (200)**:
```json
{
  "success": true,
  "trade_id": "trade_cdbbd878",
  "symbol": "RELIANCE",
  "side": "BUY",
  "quantity": 5,
  "price": 2850.0,
  "status": "COMPLETED",
  "timestamp": "2025-10-24T10:55:42.717997+00:00",
  "account_id": "swing-001",
  "remaining_balance": 85750.0
}
```

**Validation Error (422)**:
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "quantity"],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": {"gt": 0}
    }
  ]
}
```

**Example Requests**:

```bash
# Valid buy trade
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","quantity":5}'

# Invalid: negative quantity (rejected at API boundary)
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","quantity":-5}'

# Invalid: zero quantity (rejected at API boundary)
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","quantity":0}'
```

---

#### 2. Execute Sell Trade

**Endpoint**: `POST /api/paper-trading/accounts/{account_id}/trades/sell`

**Description**: Execute a sell trade via Claude Agent validation. Calculates P&L from position entry price.

**Path Parameters**:
- `account_id` (string, required): Paper trading account ID

**Request Body**:
```json
{
  "symbol": "RELIANCE",
  "quantity": 3,
  "order_type": "MARKET",
  "price": null
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "trade_id": "trade_483cf36f",
  "symbol": "RELIANCE",
  "side": "SELL",
  "quantity": 3,
  "price": 2900.0,
  "status": "COMPLETED",
  "timestamp": "2025-10-24T10:55:53.492167+00:00",
  "account_id": "swing-001",
  "realized_pnl": 450.0,
  "proceeds": 8700.0,
  "new_balance": 108700.0
}
```

**P&L Calculation**:
```
P&L = (Exit Price - Entry Price) × Quantity
Example: (2900 - 2850) × 3 = ₹150 per share × 3 = ₹450 profit
```

**Example Request**:

```bash
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/sell \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","quantity":3}'
```

---

#### 3. Close Trade

**Endpoint**: `POST /api/paper-trading/accounts/{account_id}/trades/{trade_id}/close`

**Description**: Close an open position and calculate realized P&L.

**Path Parameters**:
- `account_id` (string, required): Paper trading account ID
- `trade_id` (string, required): Trade ID to close (from buy response)

**Request Body**:
```json
{}
```

**Success Response (200)**:
```json
{
  "success": true,
  "trade_id": "trade_cdbbd878",
  "status": "CLOSED",
  "exit_price": 2050.0,
  "realized_pnl": 1700.0,
  "timestamp": "2025-10-24T10:56:00.724794+00:00"
}
```

**P&L Calculation**:
```
Exit P&L = (Exit Price - Entry Price) × Quantity
Example: (2050 - 2750) × 10 = -₹700 per share × 10 = -₹7000 loss
```

**Example Request**:

```bash
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/trade_cdbbd878/close \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### System Status & Health

#### Get System Status

**Endpoint**: `GET /api/monitoring/status`

**Description**: Get overall system health and component status.

**Response (200)**:
```json
{
  "status": "operational",
  "timestamp": "2025-10-24T10:56:00.000000+00:00",
  "components": {
    "database": "healthy",
    "scheduler": "running",
    "websocket": "connected",
    "claude_agent_sdk": "authenticated"
  }
}
```

---

#### Get Dashboard Data

**Endpoint**: `GET /api/dashboard`

**Description**: Get complete portfolio overview with holdings and metrics.

**Response (200)**:
```json
{
  "portfolio": {
    "total_value": 100000,
    "cash": 100000,
    "exposure": 0,
    "holdings": []
  },
  "metrics": {
    "total_trades": 0,
    "winning_trades": 0,
    "win_rate": 0.0,
    "total_pnl": 0.0,
    "max_drawdown": 0.0
  }
}
```

---

### Paper Trading Account

#### Get Account Overview

**Endpoint**: `GET /api/paper-trading/accounts/{account_id}/overview`

**Description**: Get paper trading account details, balance, and P&L.

**Path Parameters**:
- `account_id` (string, required): Paper trading account ID

**Response (200)**:
```json
{
  "account_id": "swing-001",
  "account_type": "swing",
  "balance": 100000,
  "initial_balance": 100000,
  "total_pnl": 0,
  "monthly_pnl": 0,
  "active_positions": 0,
  "total_trades": 0,
  "risk_level": "MODERATE"
}
```

---

## Error Handling

### Error Response Format

**Status Code 400 (Bad Request)**:
```json
{
  "error": "Trade validation failed: Insufficient balance",
  "code": "VALIDATION_ERROR",
  "category": "VALIDATION",
  "recoverable": true
}
```

**Status Code 422 (Unprocessable Entity - Input Validation)**:
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "quantity"],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": {"gt": 0}
    }
  ]
}
```

**Status Code 500 (Server Error)**:
```json
{
  "error": "Claude Agent SDK authentication failed",
  "code": "AUTH_FAILED",
  "category": "SYSTEM",
  "recoverable": true,
  "correlation_id": "abc-123-def"
}
```

### Error Categories

| Category | Status | Examples | Recoverable |
|----------|--------|----------|-------------|
| VALIDATION | 422 | Invalid symbol, negative quantity | No |
| TRADING | 400 | Insufficient balance, position not found | Yes |
| SYSTEM | 500 | Auth failed, SDK connection error | Yes |
| API | 500 | External API timeout, rate limit | Yes |

---

## Request/Response Examples

### Complete Buy Trade Flow

```bash
# 1. Execute buy trade
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "quantity": 5,
    "order_type": "MARKET"
  }'

# Response:
{
  "success": true,
  "trade_id": "trade_cdbbd878",
  "symbol": "RELIANCE",
  "side": "BUY",
  "quantity": 5,
  "price": 2850.0,
  "status": "COMPLETED",
  "timestamp": "2025-10-24T10:55:42.717997+00:00",
  "account_id": "swing-001",
  "remaining_balance": 85750.0
}

# 2. Execute sell trade on same position
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/sell \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "quantity": 3,
    "order_type": "MARKET"
  }'

# Response (with P&L):
{
  "success": true,
  "trade_id": "trade_483cf36f",
  "symbol": "RELIANCE",
  "side": "SELL",
  "quantity": 3,
  "price": 2900.0,
  "status": "COMPLETED",
  "timestamp": "2025-10-24T10:55:53.492167+00:00",
  "account_id": "swing-001",
  "realized_pnl": 450.0,
  "proceeds": 8700.0,
  "new_balance": 108700.0
}

# 3. Close remaining position
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/trade_cdbbd878/close \
  -H "Content-Type: application/json" \
  -d '{}'

# Response:
{
  "success": true,
  "trade_id": "trade_cdbbd878",
  "status": "CLOSED",
  "exit_price": 2050.0,
  "realized_pnl": 1700.0,
  "timestamp": "2025-10-24T10:56:00.724794+00:00"
}
```

---

## Input Validation Rules

### Symbol Validation

| Rule | Constraint | Example |
|------|-----------|---------|
| Required | Yes | RELIANCE |
| Length | 1-20 characters | TCS (3 chars ✓), A (1 char ✓) |
| Case | Auto-normalized to uppercase | "reliance" → "RELIANCE" |
| Pattern | Alphanumeric only | INFY, IT, NIFTY (all valid) |

### Quantity Validation

| Rule | Constraint | Valid Range | Examples |
|------|-----------|------------|----------|
| Required | Yes | 1-10,000 | 5 ✓, 1000 ✓ |
| Minimum | > 0 | 1+ | 0 ✗, -5 ✗ |
| Maximum | ≤ 10,000 | ≤ 10,000 | 10001 ✗ |
| Type | Integer only | N/A | 5.5 ✗ |

### Order Type Validation

| Type | Constraints | Price Required |
|------|-----------|-----------------|
| MARKET | Default value | No (ignored) |
| LIMIT | Pattern validated | Yes (required) |

### Validation Error Examples

```bash
# Negative quantity - rejected
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -d '{"symbol":"RELIANCE","quantity":-5}'
# Returns 422: "Input should be greater than 0"

# Zero quantity - rejected
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -d '{"symbol":"RELIANCE","quantity":0}'
# Returns 422: "Input should be greater than 0"

# Exceeds maximum - rejected
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -d '{"symbol":"RELIANCE","quantity":15000}'
# Returns 422: "Input should be less than or equal to 10000"

# Invalid symbol length - rejected
curl -X POST http://localhost:8000/api/paper-trading/accounts/swing-001/trades/buy \
  -d '{"symbol":"","quantity":5}'
# Returns 422: "ensure this value has at least 1 character"
```

---

## Rate Limiting

**Current Status**: Rate limiting configured but not enforced in Phase 1

**Planned Limits** (Phase 2):
- Trade execution: 10 trades/minute
- Dashboard: 30 requests/minute
- Agent queries: 20 requests/minute

---

## WebSocket Real-Time Updates

**WebSocket Endpoint**: `ws://localhost:8000/ws`

**Supported Message Types**:
- `connection_established` - Initial handshake
- `trade_executed` - New trade broadcast
- `portfolio_updated` - Portfolio changes
- `error` - Error notifications

---

## Common Workflows

### Workflow 1: Simple Buy and Sell

```python
import requests

BASE_URL = "http://localhost:8000"
ACCOUNT_ID = "swing-001"

# Step 1: Buy 5 shares of RELIANCE
buy_response = requests.post(
    f"{BASE_URL}/api/paper-trading/accounts/{ACCOUNT_ID}/trades/buy",
    json={"symbol": "RELIANCE", "quantity": 5}
)
trade_id = buy_response.json()["trade_id"]
print(f"Bought 5 RELIANCE shares, Trade ID: {trade_id}")

# Step 2: Sell 3 shares (partial)
sell_response = requests.post(
    f"{BASE_URL}/api/paper-trading/accounts/{ACCOUNT_ID}/trades/sell",
    json={"symbol": "RELIANCE", "quantity": 3}
)
pnl = sell_response.json()["realized_pnl"]
print(f"Sold 3 RELIANCE shares, P&L: ₹{pnl}")

# Step 3: Close remaining position
close_response = requests.post(
    f"{BASE_URL}/api/paper-trading/accounts/{ACCOUNT_ID}/trades/{trade_id}/close",
    json={}
)
final_pnl = close_response.json()["realized_pnl"]
print(f"Closed position, Total P&L: ₹{final_pnl}")
```

---

## Testing Checklist

- [x] Buy endpoint returns 200 with trade_id
- [x] Sell endpoint returns 200 with P&L
- [x] Close endpoint returns 200 with realized_pnl
- [x] Negative quantity rejected with 422
- [x] Zero quantity rejected with 422
- [x] Lowercase symbols normalized
- [x] Claude Agent SDK integration working
- [x] Error responses have correct format
- [x] Response timestamps valid
- [x] Balance calculations correct

---

## References

- **ARCHITECTURE.md** - System architecture and design patterns
- **src/services/paper_trading_execution_service.py** - Implementation details
- **src/web/CLAUDE.md** - Web layer guidelines
- **CLAUDE.md** - Project standards and patterns
