# Background Scheduler Events - src/core/background_scheduler/events/

Event routing and handler registration for background task lifecycle.

## Purpose
Event handler system routes events from background tasks to registered handlers. Enables decoupled communication.

## Pattern
```python
handler = EventHandler()
async def handle_earnings(event_data: Dict):
    await process_earnings(event_data['symbol'], event_data['earnings'])
handler.register_handler("earnings_announced", handle_earnings)
await handler.emit_event("earnings_announced", {"symbol": "AAPL"})
```

## Valid Event Types
earnings_announced, stop_loss_triggered, price_movement, news_alert, market_open, market_close

## Event Structure
```python
{"symbol": str, "timestamp": str, "source": str, "data": Dict}
```

## Rules
| DO | DON'T |
|----|-------|
| Register handlers for valid types | Register invalid event types |
| Use async handlers | Use blocking operations |
| Emit lifecycle events | Skip event validation |
| Validate event types | Ignore handler errors |
| Log event routing | Create circular dependencies |
| Handle errors gracefully | |

## Dependencies
EventBus, Logger, Background task components

