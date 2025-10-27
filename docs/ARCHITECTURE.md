# Robo-Trader Architecture - Phase 1 Complete

## Project Overview

**Robo-Trader** is a Claude AI-powered paper trading system designed for desktop-only deployment. The system enables Claude to autonomously execute trades with strategy learning and performance tracking.

**Key Characteristics**:
- **Paper trading only** (no live trading)
- **Claude Agent SDK exclusively** (no direct Anthropic API calls)
- **Claude makes autonomous trade decisions** via validated prompts
- **Swing trading account** (₹1,00,000 initial capital)
- **Monthly capital reset** for performance tracking
- **Strategy learning** via daily reflections and effectiveness tracking
- **Desktop deployment only** (localhost networking)
- **Phase 1 Complete**: Core trade execution fully functional

---

## System Architecture Layers

### 1. Core Layer (`src/core/`)

**Responsibility**: Infrastructure, service coordination, event management.

#### Components:

| Component | File | Purpose |
|-----------|------|---------|
| **Orchestrator** | `orchestrator.py` | Thin facade, delegates to coordinators |
| **Coordinators** | `coordinators/` | Service orchestration (11 focused coordinators) |
| **Dependency Injection** | `di.py` | Centralized dependency management |
| **Event Bus** | `event_bus.py` | Pub/sub event infrastructure |
| **Error Handling** | `errors.py` | Rich error hierarchy with context |
| **Background Scheduler** | `background_scheduler/` | Periodic task processing (modularized) |
| **Claude Integration** | `conversation_manager.py` | Multi-turn conversation support |
| **AI Planner** | `ai_planner.py` | Strategic planning engine |
| **Learning Engine** | `learning_engine.py` | Strategy effectiveness tracking |

#### Key Patterns:

**Coordinator Pattern** - Thin coordinators delegate to services:
```python
class MyCoordinator(BaseCoordinator):
    async def initialize(self): ...
    async def cleanup(self): ...
    # Delegates to injected services
```

**Event-Driven Communication** - Services communicate via events, not direct calls:
- Services emit events via `EventBus`
- Services subscribe to events via `EventHandler`
- No direct service-to-service coupling

**Dependency Injection** - All services receive dependencies via constructor:
```python
service = await container.get("service_name")
```

---

### 2. Services Layer (`src/services/`)

**Responsibility**: Domain-specific business logic.

#### Core Services:

| Service | Responsibility | Key Methods |
|---------|-----------------|-------------|
| **paper_trading_execution_service.py** | Trade execution | `execute_buy_trade()`, `execute_sell_trade()`, `close_trade()` |
| **paper_trading/** | Paper trading operations | Account management, performance tracking, position management |
| **portfolio_service.py** | Portfolio management | `get_portfolio()`, `update_holdings()` |
| **execution_service.py** | Trade execution | `execute()`, `validate()` |
| **market_data_service.py** | Market data integration | `get_price()`, `get_technical_indicators()` |
| **analytics_service.py** | Performance analytics | `calculate_metrics()` |
| **learning_service.py** | Strategy learning | `log_strategy()`, `get_effectiveness()` |
| **recommendation_service.py** | Trade recommendations | `generate_recommendation()` |

#### Service Communication Pattern:

```python
class MyService(EventHandler):
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        # Subscribe to events
        event_bus.subscribe(EventType.TRADE_EXECUTED, self)

    async def handle_event(self, event: Event):
        # React to events
        await self.process_event(event)
        # Emit follow-up event
        await self.event_bus.emit(Event(...))

    async def cleanup(self):
        # Unsubscribe from all events
        self.event_bus.unsubscribe(EventType.TRADE_EXECUTED, self)
```

---

### 3. Paper Trading Service (`src/services/paper_trading_execution_service.py`)

**Responsibility**: Execute buy/sell/close trades via Claude Agent SDK.

#### Key Features:

**Phase 1 Implementation**:
- Single persistent Claude SDK client (properly initialized with `__aenter__`)
- System prompt with explicit constraints for trade validation
- Three-layer JSON response parsing (markdown blocks → brace-counting → fallback)
- Proper async client lifecycle management

**Trade Execution Flow**:
```
Request → Validate Input (Pydantic) → Ensure Client → Send to Claude
→ Parse Response → Return Result → Handle Errors
```

**Supported Operations**:
1. **Buy Trade** - Execute buy with symbol, quantity, order type, optional price
2. **Sell Trade** - Execute sell with position validation and P&L calculation
3. **Close Trade** - Close position and calculate realized P&L

#### Error Handling:

- **TradingError** with category (TRADING, SYSTEM, API, VALIDATION, RESOURCE)
- **Severity levels** (CRITICAL, HIGH, MEDIUM, LOW)
- **Recoverable flag** for retry logic
- **Metadata** for debugging and context

---

### 4. Web Layer (`src/web/`)

**Responsibility**: FastAPI application, HTTP endpoints, WebSocket connections.

#### API Endpoints - Phase 1:

**Paper Trading Trade Execution** (✅ Complete):
- `POST /api/paper-trading/accounts/{account_id}/trades/buy` - Execute buy trade
- `POST /api/paper-trading/accounts/{account_id}/trades/sell` - Execute sell trade
- `POST /api/paper-trading/accounts/{account_id}/trades/{trade_id}/close` - Close position

**Request/Response**:

Buy Trade:
```json
POST /api/paper-trading/accounts/swing-001/trades/buy
{
  "symbol": "RELIANCE",
  "quantity": 5,
  "order_type": "MARKET",
  "price": null
}

Response:
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

#### Error Handling:

**Middleware Pattern**:
```python
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except TradingError as e:
        # Domain errors - structured response
        return JSONResponse(
            status_code=500 if e.context.severity.value == "critical" else 400,
            content=e.to_dict()
        )
    except Exception as e:
        # Generic errors - safe response
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
```

#### Input Validation:

**Pydantic v2 Models** with field constraints:
```python
class BuyTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: int = Field(..., gt=0, le=10000)
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")
    price: Optional[float] = Field(None, gt=0)
```

**Validation Results**:
- ✅ Negative quantities rejected (422)
- ✅ Zero quantities rejected (422)
- ✅ Lowercase symbols normalized to uppercase
- ✅ Symbol length validated (1-20 chars)
- ✅ Order type pattern validated

---

### 5. Claude Agent SDK Integration

**Mandate**: ONLY Claude Agent SDK for all AI functionality. No direct Anthropic API calls.

#### Authentication:

- **Method**: Claude Code CLI authentication (oauth_token)
- **Configuration**: Loaded from environment on startup
- **Verification**: `validate_claude_sdk_auth()` confirms token availability

#### Client Lifecycle:

**Proper Pattern**:
```python
async def _ensure_client(self) -> None:
    """Lazy initialization with proper lifecycle."""
    if self._client is None:
        options = ClaudeAgentOptions(
            allowed_tools=[],
            system_prompt=self._get_trading_prompt(),
            max_turns=1,
            disallowed_tools=["WebSearch", "WebFetch", "Bash", "Read", "Write"]
        )
        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()  # CRITICAL: Proper initialization

async def cleanup(self) -> None:
    """Proper cleanup."""
    if self._client:
        await self._client.__aexit__(None, None, None)
        self._client = None
```

**Anti-Pattern** (Per-request clients):
- ❌ Creating fresh client for each request
- ❌ Missing `__aenter__()` call
- ❌ No proper cleanup

---

## Data Flow Architecture

### Trade Execution Flow:

```
1. Browser → POST /api/paper-trading/accounts/{id}/trades/buy
2. API Handler → Validate Input (Pydantic models)
3. Service → Ensure Client (lazy init if needed)
4. Service → Build Trade Prompt with constraints
5. Claude SDK → Query Claude with prompt
6. Service → Parse JSON response from Claude
7. Service → Create trade record with P&L tracking
8. API → Return success response with trade ID
9. WebSocket → Broadcast trade event to UI
10. Frontend → Display new trade in UI
```

### Event Flow:

```
Trade Executed Event
    ├→ Portfolio Service → Update holdings
    ├→ Analytics Service → Calculate metrics
    ├→ Learning Service → Log strategy effectiveness
    └→ WebSocket Broadcaster → Send to UI
```

---

## Phase 1 - Completion Status

### ✅ Implemented:

1. **Trade Execution Service**
   - ✅ `execute_buy_trade()` - Full implementation
   - ✅ `execute_sell_trade()` - Full implementation with P&L
   - ✅ `close_trade()` - Full implementation
   - ✅ Claude Agent SDK integration
   - ✅ Proper client lifecycle management

2. **API Endpoints**
   - ✅ Buy trade endpoint (POST)
   - ✅ Sell trade endpoint (POST)
   - ✅ Close trade endpoint (POST)
   - ✅ Input validation (Pydantic v2)
   - ✅ Error handling (TradingError hierarchy)

3. **Testing**
   - ✅ Buy trade test (RELIANCE 5 shares @ ₹2850)
   - ✅ Sell trade test (RELIANCE 3 shares @ ₹2900, +₹450 P&L)
   - ✅ Close trade test (+₹1,700 realized P&L)
   - ✅ Validation tests (negative/zero quantities rejected)
   - ✅ Browser testing (Paper Trading page loads)

4. **Documentation**
   - ✅ ARCHITECTURE.md (this file)
   - ✅ API.md (updated)
   - ✅ Code comments and docstrings
   - ✅ Error handling patterns

### 📋 Not Yet Implemented (Phase 2+):

- Advanced order types (LIMIT, STOP, STOP-LOSS)
- Options trading execution
- Historical analytics and reporting
- Risk management advanced features
- Multi-account strategies
- Live market data integration
- Performance attribution analysis

---

## Key Design Decisions

### 1. Claude Agent SDK Only

**Decision**: Use ONLY Claude Agent SDK, no direct Anthropic API calls.

**Rationale**:
- Consistent authentication via Claude CLI
- Proper tool execution patterns
- Built-in session management
- Official Claude integration patterns

### 2. Single Persistent Client

**Decision**: One client per service, initialized once, properly cleaned up.

**Rationale**:
- Avoids authentication issues from fresh client creation
- Proper resource management
- Consistent session context
- Better performance

### 3. Lazy Client Initialization

**Decision**: Client initialized on first use (in `_ensure_client`), not in `__init__`.

**Rationale**:
- Async operations can't happen in `__init__`
- Client created only if actually needed
- Proper async/await patterns
- Clean initialization flow

### 4. Coordinator Pattern

**Decision**: Thin coordinators that delegate to services.

**Rationale**:
- Clear separation of concerns
- Easy to test
- Services remain reusable
- Coordinator can orchestrate complex workflows

### 5. Event-Driven Communication

**Decision**: Services communicate via EventBus, not direct calls.

**Rationale**:
- Loose coupling between services
- Easy to add new service consumers
- Clear event contract
- Testable in isolation

---

## Security Considerations

### Authentication

- ✅ Claude Code CLI auth only (no stored API keys)
- ✅ No credentials in environment variables
- ✅ No API key hardcoding
- ✅ OAuth token properly managed

### Input Validation

- ✅ Pydantic models with field constraints
- ✅ Type validation
- ✅ Range validation (quantity > 0)
- ✅ Pattern validation (order type)
- ✅ Length validation (symbol)

### Error Handling

- ✅ No stack traces to clients
- ✅ Safe error messages
- ✅ Error categorization
- ✅ Correlation IDs for tracing

---

## Testing Coverage

### Unit Tests

- ✅ Buy trade validation
- ✅ Sell trade validation
- ✅ Close trade validation
- ✅ Input validation (negative, zero quantities)

### Integration Tests

- ✅ Buy trade endpoint (curl)
- ✅ Sell trade endpoint (curl)
- ✅ Close trade endpoint (curl)
- ✅ Error response format
- ✅ Validation error responses

### Browser Tests

- ✅ Paper Trading page loads
- ✅ Account selector displays
- ✅ WebSocket connection established
- ✅ Connected status visible

---

## Future Enhancements

### Phase 2 - Advanced Trading

- [ ] Limit order execution
- [ ] Stop-loss orders
- [ ] Options trading
- [ ] Advanced risk management
- [ ] Strategy optimization
- [ ] Performance attribution

### Phase 3 - Analytics & Reporting

- [ ] Historical trade analytics
- [ ] Performance reporting
- [ ] Strategy effectiveness analysis
- [ ] Risk metrics and dashboards
- [ ] Monthly performance summaries

### Phase 4 - Production Ready

- [ ] Comprehensive error recovery
- [ ] Rate limiting and throttling
- [ ] Monitoring and alerting
- [ ] Audit logging
- [ ] Performance optimization
- [ ] Load testing

---

## References

- **CLAUDE.md** - Project memory and standards
- **src/CLAUDE.md** - Backend architecture guidelines
- **src/web/CLAUDE.md** - Web layer guidelines
- **API.md** - API endpoint documentation
- **IMPLEMENTATION_PLAN.md** - Detailed implementation tasks
