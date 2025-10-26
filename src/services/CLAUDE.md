# Services Layer Guidelines

> **Scope**: Applies to `src/services/` directory. Read after `src/CLAUDE.md` and `src/core/CLAUDE.md` for context.

Services layer contains domain-specific business logic. Each service manages one core responsibility and communicates with other services through the EventBus, never directly.

## Claude Agent SDK Integration (CRITICAL)

### SDK-Only Services (MANDATORY)

All AI-related services must use **ONLY** Claude Agent SDK. No direct Anthropic API calls are permitted.

**Transparency Services** (SDK-Only):
- `analysis_logger.py` - Logs AI analysis decisions
- `research_tracker.py` - Tracks research activities
- `execution_monitor.py` - Monitors trade execution
- `daily_strategy_evaluator.py` - Evaluates daily strategies
- `activity_summarizer.py` - Summarizes AI activities

**SDK Integration Pattern**:
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

class AIService:
    def __init__(self, container):
        self.container = container
        self.sdk_client = None  # Initialize on first use

    async def _ensure_sdk_client(self):
        """Lazy initialization of SDK client."""
        if not self.sdk_client:
            options = ClaudeAgentOptions(
                allowed_tools=[],  # Define allowed tools
                system_prompt="AI service prompt",
                max_turns=20
            )
            self.sdk_client = ClaudeSDKClient(options=options)
            await self.sdk_client.__aenter__()

    async def perform_ai_task(self, prompt: str) -> Dict[str, Any]:
        """Perform AI task using SDK only."""
        await self._ensure_sdk_client()
        await self.sdk_client.query(prompt)

        response_text = ""
        async for response in self.sdk_client.receive_response():
            if hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

        return self._parse_response(response_text)
```

**❌ FORBIDDEN - Direct API Usage:**
```python
# NEVER DO THIS in services
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key="sk-ant-...")
response = await client.messages.create(...)
```

---

## Service Architecture

### Service Structure

Every service should follow this pattern:

```python
from src.core.event_bus import EventHandler, Event, EventType
from src.core.errors import TradingError

class MyService(EventHandler):
    """Service responsible for [specific responsibility]."""

    def __init__(self, dependency1: Dep1, dependency2: Dep2, event_bus: EventBus):
        """Initialize service with dependencies."""
        self.dependency1 = dependency1
        self.dependency2 = dependency2
        self.event_bus = event_bus
        self._initialized = False

        # Subscribe to relevant events
        event_bus.subscribe(EventType.EVENT_A, self)
        event_bus.subscribe(EventType.EVENT_B, self)

    async def initialize(self) -> None:
        """Initialize service resources."""
        # Setup async resources
        self._initialized = True

    async def cleanup(self) -> None:
        """Cleanup resources and unsubscribe."""
        if not self._initialized:
            return

        # Unsubscribe from all events
        self.event_bus.unsubscribe(EventType.EVENT_A)
        self.event_bus.unsubscribe(EventType.EVENT_B)

        # Cleanup resources
```

### Rules for Services

- ✅ Inherit from `EventHandler` if subscribing to events
- ✅ Keep one responsibility per service
- ✅ Receive all dependencies via `__init__()`
- ✅ Implement `initialize()` and `cleanup()` methods
- ✅ Subscribe to events in `__init__()`, unsubscribe in `cleanup()`
- ✅ Emit events for significant business operations
- ✅ Handle all errors with `TradingError` and derivatives
- ✅ Use async/await throughout
- ✅ Use `aiofiles` for all file I/O
- ✅ Max 400 lines per service file
- ❌ NEVER call other services directly (emit events instead)
- ❌ NEVER create global/module-level instances
- ❌ NEVER use synchronous I/O
- ❌ NEVER subscribe without unsubscribe in cleanup
- ❌ NEVER hardcode configuration values

---

## Current Services

| Service | Responsibility | Key Events |
|---------|----------------|------------|
| `portfolio_service.py` | Portfolio operations and tracking | PORTFOLIO_* |
| `risk_service.py` | Risk management and monitoring | RISK_* |
| `execution_service.py` | Order execution and lifecycle | EXECUTION_* |
| `analytics_service.py` | Data analysis and reporting | ANALYTICS_* |
| `learning_service.py` | AI/ML model integration | LEARNING_* |
| `strategy_evolution_engine.py` | Strategy performance tracking & optimization | EXECUTION_*, PAPER_TRADING_* |
| `paper_trading/` | Paper trading with performance metrics | PAPER_TRADING_* |

---

## Event Handler Pattern

When a service needs to react to events, implement the `handle_event()` method:

```python
async def handle_event(self, event: Event) -> None:
    """Route events to appropriate handlers."""
    try:
        if event.type == EventType.PORTFOLIO_CHANGE:
            await self._handle_portfolio_change(event)
        elif event.type == EventType.MARKET_UPDATE:
            await self._handle_market_update(event)
        else:
            # Unknown event type - log and ignore
            logger.debug(f"Ignoring event type: {event.type}")
    except TradingError as e:
        logger.error(f"Error handling {event.type}: {e.context.code}")
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in event handler: {e}")

async def _handle_portfolio_change(self, event: Event) -> None:
    """Handle portfolio change event."""
    try:
        data = event.data
        portfolio_id = data.get("portfolio_id")
        # Process change

        # Emit follow-up event if needed
        await self.event_bus.publish(Event(
            id=str(uuid.uuid4()),
            type=EventType.PORTFOLIO_ANALYZED,
            source=self.__class__.__name__,
            data={"portfolio_id": portfolio_id, "result": analysis}
        ))
    except Exception as e:
        raise TradingError(f"Portfolio change handling failed: {e}")
```

### Rules for Event Handlers

- ✅ Catch `TradingError` explicitly for domain errors
- ✅ Log errors with full context
- ✅ Emit follow-up events when significant work completes
- ✅ Never block the event handler (no long computations)
- ✅ Always include error handling
- ❌ NEVER raise unhandled exceptions
- ❌ NEVER perform I/O without proper async/await
- ❌ NEVER directly call other services (emit events instead)

---

## Error Handling in Services

Services must use the error hierarchy for all failures:

```python
from src.core.errors import (
    TradingError,
    APIError,
    ValidationError,
    ErrorSeverity
)

async def validate_trade(self, trade_request: TradeRequest) -> None:
    """Validate trade request."""
    try:
        if not trade_request.symbol:
            raise ValidationError(
                "Symbol is required",
                severity=ErrorSeverity.MEDIUM,
                recoverable=False,
                details={"received": trade_request}
            )

        # Validate against portfolio
        portfolio = await self._get_portfolio(trade_request.portfolio_id)
        if not portfolio:
            raise ValidationError(
                "Portfolio not found",
                severity=ErrorSeverity.HIGH,
                recoverable=False,
                portfolio_id=trade_request.portfolio_id
            )
    except TradingError:
        raise  # Re-raise domain errors
    except Exception as e:
        raise TradingError(
            f"Trade validation failed: {e}",
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            retry_after_seconds=5
        )
```

---

## Pre-Commit Checklist - Services

- [ ] Inherits from `EventHandler` (if handling events)
- [ ] Implements `initialize()` and `cleanup()`
- [ ] All dependencies injected via `__init__()`
- [ ] Unsubscribes from all events in `cleanup()`
- [ ] No direct service-to-service calls
- [ ] Emits events for significant operations
- [ ] All errors inherit from `TradingError`
- [ ] No synchronous I/O (use `aiofiles`)
- [ ] No hardcoded configuration
- [ ] Max 400 lines per file
- [ ] Proper async/await usage throughout
- [ ] Performance metrics use `PerformanceCalculator`

---

## Common Service Mistakes

### Mistake 1: Forgetting to Unsubscribe
```python
# WRONG - Memory leak
class MyService(EventHandler):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        event_bus.subscribe(EventType.ORDER_FILLED, self)

    # No cleanup() method!
```
**Fix**: Always implement `cleanup()` with unsubscribe

### Mistake 2: Direct Service Calls
```python
# WRONG - Tight coupling
class MyService:
    def __init__(self, other_service: OtherService):
        self.other_service = other_service

    async def do_something(self):
        result = await self.other_service.get_data()  # Direct call!
```
**Fix**: Emit event, let other service subscribe and handle it

### Mistake 3: Blocking I/O in Service
```python
# WRONG - Blocks event loop
async def load_data(self):
    with open("data.json") as f:  # BLOCKS!
        return json.load(f)
```
**Fix**: Use `aiofiles` with `async with`

### Mistake 4: No Error Handling in Event Handler
```python
# WRONG - Unhandled exception crashes handler
async def handle_event(self, event: Event):
    await self.process_event(event)  # Can raise!
```
**Fix**: Wrap in try/except, catch specific errors

### Mistake 5: Hardcoding Configuration
```python
# WRONG - Can't change without redeployment
RETRY_COUNT = 3
TIMEOUT_SECONDS = 30
```
**Fix**: Load from config via DI

---

## Quick Reference - Service Development

| Task | Pattern | Reference |
|------|---------|-----------|
| React to events | Inherit `EventHandler`, implement `handle_event()` | Event Handler Pattern |
| Emit event | Create `Event`, await `event_bus.publish()` | Event Structure |
| Handle error | Raise specific error type, inherit from `TradingError` | Error Handling |
| Async file I/O | Use `aiofiles` with `async with` | Async Pattern |
| Initialize service | Implement `initialize()` and `cleanup()` | Service Structure |
| Share data | Emit event with data, don't direct call | Communication |

---

## Service Lifecycle Example

```python
# 1. Service registered in DI container
container.register_singleton(MyService)

# 2. Orchestrator gets service from container
service = await container.get(MyService)

# 3. Service subscribes to events in __init__
# Events flow through EventBus

# 4. On shutdown, service cleanup called
await service.cleanup()  # Unsubscribes from events
```

---

## Strategy Evolution Engine Pattern

**Responsibility**: Track strategy performance per tag and provide Claude with optimization insights.

**Pattern**: Maintain in-memory metrics cache with async file persistence.

**Implementation**:
```python
class StrategyEvolutionEngine(EventHandler):
    """Tracks strategy effectiveness and provides learnings to Claude."""

    async def track_trade(self, trade: PaperTrade, strategy_tag: str) -> None:
        """Track a closed trade, update metrics, calculate effectiveness."""
        async with self._lock:
            # Calculate P&L
            pnl = (trade.exit_price - trade.entry_price) * trade.quantity

            # Update or create strategy metrics
            metrics = self._strategies.get(strategy_tag, StrategyMetrics(...))
            metrics.total_trades += 1
            metrics.total_pnl += pnl
            if pnl > 0:
                metrics.winning_trades += 1

            # Save to file
            await self._save_strategies()

    async def analyze_strategy(self, strategy_tag: str) -> StrategyEvolution:
        """Calculate effectiveness score and recommendations."""
        # Score = 40 (win rate) + 30 (profit factor) + 20 (consistency) + 10 (volume)
        # Recommendation: increase_use, maintain_use, modify_parameters, reduce_use, retire

    async def get_strategy_context_for_claude(self) -> Dict[str, Any]:
        """Return full strategy context for Claude's decision making."""
        # Include: top performers, underperformers, trends, recommendations
```

**Rules**:
- ✅ Track metrics per strategy_tag (from trade event data)
- ✅ Update in-memory cache first, then persist to file
- ✅ Use atomic file writes for consistency
- ✅ Cache latest metrics in memory for fast queries
- ✅ Calculate effectiveness score (0-100) based on win rate + profit factor
- ✅ Provide Claude with top performers and underperformers
- ✅ Emit events on strategy changes (optional, for UI updates)
- ❌ NEVER lock during I/O (use atomic operations)
- ❌ NEVER block calculating metrics (keep math operations quick)

**Integration Points**:
- Subscribes to `EXECUTION_ORDER_FILLED` and `PAPER_TRADING_CLOSED` events
- Called by TradeExecutor after closing a trade with strategy_tag
- Queried by Claude Agent for strategy context before decisions
- Called by UI endpoints to display strategy analytics

**Claude Context Usage**:
```python
# Claude calls before making trading decisions
context = await engine.get_strategy_context_for_claude()
# Returns: {
#   "top_performers": [{"strategy": "RSI_oversold", "win_rate": "72%"}],
#   "underperformers": [{"strategy": "MACD_divergence", "win_rate": "35%"}],
#   "recommendations": ["increase_use", "retire"]
# }
```

---

**Key Principle**: Services are independent, event-driven units. They don't know about other services, only about the events they emit and handle. This loose coupling makes the system scalable and testable.
