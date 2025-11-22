# Background Scheduler Executors Directory Guidelines

> **Scope**: Applies to `src/core/background_scheduler/executors/` directory. Read `src/core/background_scheduler/CLAUDE.md` for context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Purpose

The `executors/` directory contains task executors that orchestrate data flow for background tasks. Executors coordinate API clients, processors, parsers, and stores to complete complex analysis tasks.

## Architecture Pattern

### Executor Pattern

Executors orchestrate the full data flow:
1. **Fetch** - API client fetches raw data
2. **Process** - Domain processor processes data
3. **Parse** - Parser transforms data to structured format
4. **Store** - Store persists results to database

### Directory Structure

```
executors/
└── fundamental_executor.py    # Fundamental analysis executor
```

## Rules

### ✅ DO

- ✅ Orchestrate complete data flow (fetch → process → parse → store)
- ✅ Emit events for task lifecycle
- ✅ Handle errors gracefully with retry logic
- ✅ Check database state before API calls
- ✅ Use async operations throughout
- ✅ Log execution progress
- ✅ Track execution metrics

### ❌ DON'T

- ❌ Mix multiple executor responsibilities
- ❌ Skip state checking before API calls
- ❌ Use blocking operations
- ❌ Skip error handling
- ❌ Omit event emission
- ❌ Create circular dependencies

## Executor Pattern

```python
from src.core.background_scheduler.executors.fundamental_executor import FundamentalExecutor

# Initialize executor
executor = FundamentalExecutor(
    perplexity_client=perplexity_client,
    db_connection=db_connection,
    event_bus=event_bus
)

# Execute earnings fundamentals
result = await executor.execute_earnings_fundamentals(
    symbols=["AAPL", "GOOGL"],
    metadata={"analysis_type": "comprehensive"}
)

# Result contains:
# - fetched_data: Raw API response
# - parsed_data: Structured parsed data
# - stored_data: Database storage confirmation
```

## Data Flow Architecture

```
API Client → Processor → Parser → Store
     ↓           ↓          ↓        ↓
  Fetch      Process    Transform  Persist
```

## Event Emission

Executors emit events for lifecycle tracking:

```python
# Task started
await event_bus.publish(Event(
    type=EventType.TASK_STARTED,
    source="fundamental_executor",
    data={"symbols": symbols}
))

# Task completed
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    source="fundamental_executor",
    data={"result": result}
))

# Task failed
await event_bus.publish(Event(
    type=EventType.TASK_FAILED,
    source="fundamental_executor",
    data={"error": str(error)}
))
```

## Error Handling

Executors implement comprehensive error handling:

```python
try:
    # Execute task
    result = await execute_task()
except APIError as e:
    # Retry with exponential backoff
    result = await retry_with_backoff(execute_task)
except ParseError as e:
    # Log parse error and continue
    logger.error(f"Parse error: {e}")
    result = None
except Exception as e:
    # Emit failure event
    await emit_failure_event(e)
    raise
```

## State Checking

Always check state before API calls:

```python
# Check if data already exists
state = await store.get_stock_state(symbol)
if state.has_recent_fundamentals(within_hours=24):
    # Skip API call
    return state.fundamentals_data

# Fetch fresh data
data = await client.fetch_fundamentals(symbol)
```

## Dependencies

Executor components depend on:
- `PerplexityClient` - For API data fetching
- `EventBus` - For event emission
- `Database` - For state checking and storage
- `Processors` - For domain-specific processing
- `Parsers` - For data transformation
- `Stores` - For data persistence

## Testing

Test executor orchestration:

```python
import pytest
from src.core.background_scheduler.executors.fundamental_executor import FundamentalExecutor

async def test_executor_data_flow():
    """Test executor orchestrates data flow correctly."""
    executor = FundamentalExecutor(...)
    
    result = await executor.execute_earnings_fundamentals(
        symbols=["AAPL"],
        metadata={}
    )
    
    assert result['fetched_data'] is not None
    assert result['parsed_data'] is not None
    assert result['stored_data'] is not None
```

## Maintenance

When adding new executors:

1. Follow executor pattern (fetch → process → parse → store)
2. Emit lifecycle events
3. Implement error handling
4. Check state before API calls
5. Update this CLAUDE.md file

