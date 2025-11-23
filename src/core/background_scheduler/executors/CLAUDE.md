# Background Scheduler Executors - src/core/background_scheduler/executors/

Task executors orchestrate data flow for background tasks. Coordinate API clients, processors, parsers, and stores.

## Data Flow
```
API Client → Processor → Parser → Store
     ↓           ↓          ↓        ↓
  Fetch      Process    Transform  Persist
```

## Pattern
```python
# Check state before API call
state = await store.get_stock_state(symbol)
if state.has_recent_fundamentals(within_hours=24):
    return state.fundamentals_data

# Fetch → Process → Parse → Store
data = await client.fetch_fundamentals(symbol)
processed = await processor.process(data)
parsed = await parser.parse(processed)
await store.save(symbol, parsed)
```

## Rules
| DO | DON'T |
|----|-------|
| Orchestrate complete data flow | Mix executor responsibilities |
| Emit lifecycle events | Skip state checking before API |
| Handle errors with retry logic | Use blocking operations |
| Check state before API calls | Skip error handling |
| Use async throughout | Omit event emission |
| Log progress | Create circular dependencies |

## Event Types
task_started, task_completed, task_failed (emit for all lifecycle events)

## Dependencies
PerplexityClient, EventBus, Database, Processors, Parsers, Stores

