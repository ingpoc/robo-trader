# Background Scheduler Events Directory Guidelines

> **Scope**: Applies to `src/core/background_scheduler/events/` directory. Read `src/core/background_scheduler/CLAUDE.md` for context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Purpose

The `events/` directory contains event handling components for the background scheduler. It provides event routing, handler registration, and event dispatching for background task lifecycle events.

## Architecture Pattern

### Event-Driven Background Tasks

The event handler system routes events from background tasks to registered handlers, enabling decoupled communication between components.

### Directory Structure

```
events/
└── event_handler.py    # Event routing and handler registration
```

## Rules

### ✅ DO

- ✅ Register handlers for valid event types only
- ✅ Use async handlers for event processing
- ✅ Emit events for task lifecycle (started, completed, failed)
- ✅ Validate event types before registration
- ✅ Log event routing for debugging
- ✅ Handle event handler errors gracefully

### ❌ DON'T

- ❌ Register handlers for invalid event types
- ❌ Use blocking operations in event handlers
- ❌ Skip event validation
- ❌ Ignore handler errors
- ❌ Create circular event dependencies

## Event Handler Pattern

```python
from src.core.background_scheduler.events.event_handler import EventHandler

# Initialize event handler
handler = EventHandler()

# Register handler for event type
async def handle_earnings_announced(event_data: Dict) -> None:
    """Handle earnings announcement event."""
    symbol = event_data.get('symbol')
    earnings = event_data.get('earnings')
    # Process earnings data
    await process_earnings(symbol, earnings)

# Register handler
handler.register_handler("earnings_announced", handle_earnings_announced)

# Emit event
await handler.emit_event("earnings_announced", {
    "symbol": "AAPL",
    "earnings": {...}
})
```

## Valid Event Types

- `earnings_announced` - Earnings announcement detected
- `stop_loss_triggered` - Stop loss triggered
- `price_movement` - Significant price movement
- `news_alert` - Important news detected
- `market_open` - Market opened
- `market_close` - Market closed

## Event Data Structure

```python
event_data = {
    "symbol": str,          # Stock symbol
    "timestamp": str,       # ISO timestamp
    "source": str,          # Event source
    "data": Dict           # Event-specific data
}
```

## Error Handling

Event handlers should handle errors gracefully:

```python
async def safe_handler(event_data: Dict) -> None:
    """Safe event handler with error handling."""
    try:
        # Process event
        await process_event(event_data)
    except Exception as e:
        logger.error(f"Event handler error: {e}", exc_info=True)
        # Emit error event
        await handler.emit_event("handler_error", {
            "event_type": "earnings_announced",
            "error": str(e)
        })
```

## Dependencies

Event handler components depend on:
- `EventBus` - For event emission (if using global event bus)
- `Logger` - For event logging
- Background task components - For event sources

## Testing

Test event handling:

```python
import pytest
from src.core.background_scheduler.events.event_handler import EventHandler

async def test_event_handler_registration():
    """Test event handler registration."""
    handler = EventHandler()
    
    async def handler_fn(data):
        assert data['symbol'] == 'AAPL'
    
    # Register handler
    assert handler.register_handler("earnings_announced", handler_fn)
    
    # Emit event
    await handler.emit_event("earnings_announced", {"symbol": "AAPL"})
```

## Maintenance

When adding new event types:

1. Add event type to `VALID_EVENTS` in `event_handler.py`
2. Document event data structure
3. Add event handler examples
4. Update this CLAUDE.md file

