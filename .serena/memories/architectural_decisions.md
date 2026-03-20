# Robo Trader - Architectural Decisions

## Database Access (Critical)

| Decision | Context | Pattern |
|----------|---------|---------|
| Row objects | Commit `5a23bad` | Always set `row_factory = aiosqlite.Row` after connection |
| Direct access | Prevents locks | Use `config_state.store_*()` methods, never direct DB connection |
| Attribute access | Commit `61c5916` | `DatabaseStateManager.paper_trading` not `paper_trading_state` |

### Implementation
```python
# src/core/database_state/base.py:78
self._connection_pool.row_factory = aiosqlite.Row

# Usage in coordinators
state_manager = container.get("state_manager")
await state_manager.store_trade_execution(trade_data)
```

## Dependency Injection Services

| Decision | Context | Pattern |
|----------|---------|---------|
| Dev mode fallback | Commit `b6afa9c` | Register services with graceful None return for missing config |
| Service names | DI registry | Use short names from `di_registry_*.py` (e.g., `"state_manager"`) |
| Registration order | Avoids circular deps | Core first, then services |

### Implementation
```python
# src/core/di_registry_services.py
container.register(
    "perplexity_service",
    lambda: PerplexityService() if api_keys else None
)
container.register(
    "kite_connect_service", 
    lambda: KiteConnectService() if credentials else None
)
```

## Session Recovery

| Decision | Context | Pattern |
|----------|---------|---------|
| Abnormal exit | Commit `ef0a5b0` | Mark session as completed after successful recovery |
| Heartbeat | Detects stale sessions | Update every 5 min, stale if >30 min |
| Resume logic | `session-state.json` | Check git status + partial changes before resuming |

### Implementation
```python
# After recovering from abnormal session
session_state["status"] = "completed"
session_state["ended_at"] = datetime.now().isoformat()
```

## AI Integration

| Decision | Context | Pattern |
|----------|---------|---------|
| SDK usage | Project rule | Use `ClaudeSDKClientManager.get_instance()` NEVER `import anthropic` |
| Missing data | Commit `d53f19c` | Handle missing price data gracefully in prompts |
| Queue tasks | Token control | Use AI_ANALYSIS queue for all AI tasks (max 3 stocks per task) |

### Implementation
```python
# Always use SDK manager
sdk_manager = ClaudeSDKClientManager.get_instance()
client = sdk_manager.get_client()

# Queue AI tasks
task = Task(
    queue_name=QueueName.AI_ANALYSIS,
    payload={"symbols": ["AAPL", "GOOGL", "MSFT"]}  # Max 3
)
```

## Async Patterns

| Decision | Context | Pattern |
|----------|---------|---------|
| Event loop | Async context | Use `asyncio.get_running_loop()` NOT `get_event_loop()` |
| File I/O | Non-blocking | Use `async with aiofiles.open()` |
| Service extension | Event-driven | Extend `EventHandler` class for EventBus integration |

### Implementation
```python
# Correct event loop access
loop = asyncio.get_running_loop()

# Non-blocking file read
async with aiofiles.open("file.json") as f:
    data = await f.read()

# Event-driven service
class MyService(EventHandler):
    @subscribe("event_name")
    async def handle_event(self, data):
        pass
```

## Error Handling

| Decision | Context | Pattern |
|----------|---------|---------|
| Structured errors | Project-wide | Use `TradingError(category=ErrorCategory.*)` |
| Queue execution | Commit `70d6956` | Remove "limit" from `get_pending_tasks()` |
| Missing services | Commit `b6afa9c` | Coordinators handle None gracefully |

### Implementation
```python
# Structured error
from src.models.error import TradingError, ErrorCategory
raise TradingError(
    category=ErrorCategory.DATA_FETCH_ERROR,
    message="Failed to fetch market data"
)

# Queue processing fix (remove limit)
tasks = await queue_manager.get_pending_tasks(
    queue_name=QueueName.PORTFOLIO_SYNC,
    limit=None  # Was causing "execution in progress" errors
)
```

## Frontend Integration

| Decision | Context | Pattern |
|----------|---------|---------|
| WebSocket | Real-time | Use Socket.IO for live updates |
| State management | UI store | Zustand for React state |
| API calls | Backend | FastAPI routes in `src/web/routes/` |

## Environment Variables (Critical Decision - 2025-12-26)

| Decision | Context | Pattern |
|----------|---------|---------|
| Single source of truth | Consolidated from shell | ALL credentials in `.env` file ONLY |
| Load mechanism | `python-dotenv` | `load_dotenv()` reads .env into process memory |
| Shell exports | Removed from `~/.zshrc`, `~/.bash_profile` | NOT needed - backend reads .env directly |
| OAuth tokens | Auto-saved | `ZERODHA_ACCESS_TOKEN` added to .env after auth |

### Implementation
```bash
# .env file (ONLY place for credentials)
ZERODHA_API_KEY=xxx
ZERODHA_API_SECRET=xxx
ZERODHA_ACCESS_TOKEN=<auto-added by OAuth>
PERPLEXITY_API_KEYS=pplx-xxx,pplx-yyy  # comma-separated
```

**NEVER** export in shell startup files - `load_dotenv()` in `config.py` handles everything.

## Naming Conventions (Canonical)

| Constant | Value | Source |
|----------|-------|--------|
| Paper trading account | `paper_swing_main` | `paper_trading_state.py` |
| Queue names | `QueueName.*` enum | `src/models/queue.py` |
| Service names | DI registry | `src/core/di_registry_*.py` |

## Common Bugs & Fixes (From session-state.json)

| Bug ID | Location | Issue | Fix |
|--------|----------|-------|-----|
| BUG-001 | `morning_session_coordinator.py:639` | Used `paper_trading_main` but DB has `paper_swing_main` | Use canonical constant from `paper_trading_state.py` |
| BUG-002 | `paper_trading_execution_service.py:183-194` | Returns success but never writes to DB tables | Implement actual DB persistence to `paper_positions` + `paper_trades` |
| Tuple conversion | `base.py:76` | DB returns tuples instead of Row objects | Set `row_factory = aiosqlite.Row` |
| Service not found | DI registry | Service not registered, coordinator gets None | Register with graceful fallback for dev |
| Attribute name | State manager | Used `paper_trading_state` instead of `paper_trading` | Correct attribute: `DatabaseStateManager.paper_trading` |

### Pattern: Prevent Account ID Mismatches (Commit dc20b52)

```python
# WRONG - hardcoded, can mismatch
result = await self.execution_service.execute_buy_trade(
    account_id="paper_trading_main",  # ❌ Wrong - doesn't match DB
    symbol=symbol,
    quantity=quantity
)

# CORRECT - use canonical constant from paper_trading_state.py
from src.core.database_state.paper_trading_state import PAPER_TRADING_ACCOUNT
# PAPER_TRADING_ACCOUNT = "paper_swing_main" (defined in state file)

result = await self.execution_service.execute_buy_trade(
    account_id="paper_swing_main",  # ✅ Matches canonical constant
    symbol=symbol,
    quantity=quantity
)
```

**Source of Truth**: `src/core/database_state/paper_trading_state.py` defines `PAPER_TRADING_ACCOUNT = "paper_swing_main"`

### Pattern: Verify DB Persistence (Commit dc20b52 - BUG-002)

```python
# BEFORE - returned success but never wrote to DB (BUG)
async def execute_buy_trade(self, account_id, symbol, quantity, ...):
    # ... AI prompt execution ...
    trade_id = f"trade_{uuid.uuid4().hex[:8]}"
    # ❌ No DB write - just logged and returned
    loguru_logger.info(f"Buy trade executed: {trade_id}")
    return {"trade_id": trade_id, "status": "success"}

# AFTER - actually persists to paper_trades table
async def execute_buy_trade(self, account_id, symbol, quantity, ...):
    # ... AI prompt execution ...
    trade_id = f"trade_{uuid.uuid4().hex[:8]}"
    
    # ✅ Write to database via state_manager
    if self._state_manager and hasattr(self._state_manager, 'paper_trading_state'):
        db_success = await self._state_manager.paper_trading_state.create_trade(
            trade_id=trade_id,
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            entry_price=float(trade_price),
            entry_reason=strategy_rationale,
            strategy_tag="morning_session",
            confidence_score=0.7,
            research_sources=["claude_agent_sdk"],
            market_conditions={"order_type": order_type},
            risk_metrics={"account_id": account_id}
        )
        if db_success:
            loguru_logger.info(f"Buy trade persisted to DB: {trade_id}")
        else:
            loguru_logger.warning(f"Buy trade executed but DB write failed: {trade_id}")
    else:
        loguru_logger.warning(f"No state_manager available for persistence: {trade_id}")
    
    return {"trade_id": trade_id, "status": "success"}
```

**Key Pattern**: Always verify `state_manager.paper_trading_state` is available and actually call `create_trade()` for persistence.
```python
# WRONG - hardcoded, can mismatch
account_id = "paper_trading_main"

# CORRECT - use canonical constant
from src.core.database_state.paper_trading_state import PAPER_TRADING_ACCOUNT
account_id = PAPER_TRADING_ACCOUNT  # "paper_swing_main"
```

### Pattern: Verify DB Persistence
```python
# After mock execution, verify actual DB writes
async def verify_trade_persistence(trade_id: str):
    position = await state_manager.get_paper_position(trade_id)
    if not position:
        raise TradingError("Mock execution didn't write to DB")
```

## Integration Patterns (From Gap Analysis Session)

| Pattern | Location | Purpose |
|---------|----------|---------|
| Loguru logging | `di_registry_services.py` | Proper log routing vs print() |
| Token efficiency rules | `CLAUDE.md` | Use MCP tools for large datasets |
| Canonical constants | `CLAUDE.md` | Single source for account IDs, service names |
| Implementation status | `src/services/CLAUDE.md` | Track what's implemented vs planned |
| Data flow contracts | `src/core/coordinators/CLAUDE.md` | Document expected data flow |

### Pattern: Check Implementation Before Using
```python
# Before calling a service, check implementation status
# See: src/services/CLAUDE.md for what's actually implemented

if not hasattr(service, 'method_name'):
    logger.warning(f"Service {service_name} missing {method_name}")
    return fallback_response
```

### Pattern: Document Data Flow
```markdown
## Paper Trading Data Flow (coordinators/CLAUDE.md)
1. MorningSessionCoordinator triggers
2. KiteConnectService fetches live prices
3. AIService generates trade ideas
4. PaperTradingExecutionService executes (MOCK → DB)
5. StateManager persists to paper_positions + paper_trades
```

## When Adding New Features

1. **Check this memory first** for relevant patterns
2. **Search codebase** for similar implementations
3. **Apply learned patterns** consistently
4. **Update this memory** with new decisions after user feedback

## Token Efficiency Rules

| Task | Tool | When to Use |
|------|------|-------------|
| Code execution | `execute_code` | Experimental code, sandbox first |
| Log analysis | `process_logs` | Pattern matching, pagination |
| CSV/data | `process_csv` | >50 items, use offset/limit |
| Find tools | `search_tools` | 95% token savings vs loading all |
