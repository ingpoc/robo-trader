# Background Scheduler Processors - src/core/background_scheduler/processors/

Domain-specific processors for data processing (news, earnings, fundamentals). Max 350 lines per processor.

## Domain-Separated Architecture
```
processors/
├── news_processor.py              # News processing
├── earnings_processor.py          # Earnings processing
├── fundamental_analyzer.py        # Fundamental analysis
└── deep_fundamental_processor.py  # Deep fundamentals
```

## Pattern
```python
# Check state before processing
state = await store.get_stock_state(symbol)
if state.has_recent_news:
    return task  # Skip if cached

# Process data
data = await process_news(response)
parsed = await parser.parse(data)
await store.save(symbol, parsed)
await event_bus.publish(Event(type=EventType.NEWS_PROCESSED, data={...}))
```

## Rules
| DO | DON'T |
|----|-------|
| Keep < 350 lines | Exceed line limits |
| One domain per processor | Mix domains |
| Check stock state | Skip state checking |
| Emit lifecycle events | Use blocking I/O |
| Use async throughout | Return TradingError |
| Handle errors gracefully | |

## Dependencies
Domain-specific clients, parsers, stores, StockStateStore, EventBus

