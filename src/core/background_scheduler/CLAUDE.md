# Background Scheduler Directory Guidelines

> **Scope**: Applies to `src/core/background_scheduler/` directory. Read `src/core/CLAUDE.md` for context.
>
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference + How-To
>
> **Read in this order**:
> 1. `src/core/CLAUDE.md` - Initialization error handling pattern (CRITICAL for background scheduler)
> 2. This file - Background scheduler structure and modules
> 3. `src/core/background_scheduler/stores/CLAUDE.md` - File persistence patterns

## Purpose

The `background_scheduler/` directory contains the modular background task processing system. It handles periodic tasks, data fetching, analysis, and maintenance operations in a domain-separated architecture.

## Architecture Pattern

### Modular Domain Separation

The background scheduler uses a **domain-separated architecture** where each domain (news, earnings, fundamentals) has its own:
- **Processor** - Domain-specific processing logic
- **Client** - Unified API client for that domain
- **Parser** - Data parsing and transformation
- **Store** - Async file persistence
- **Monitor** - Health monitoring

### Directory Structure

```
background_scheduler/
├── background_scheduler.py    # Main facade
├── models.py                  # Task and state models
├── backup_scheduler.py         # Backup scheduling
├── triggers.py                 # Trigger definitions
├── clients/                    # Unified API clients
│   ├── perplexity_client.py    # Perplexity API client
│   └── retry_handler.py        # Retry logic
├── processors/                 # Domain-specific processors
│   ├── news_processor.py       # News processing
│   ├── earnings_processor.py   # Earnings processing
│   └── fundamental_analyzer.py # Fundamental analysis
├── parsers/                    # Data parsers
│   ├── news.py                 # News parsing
│   ├── earnings.py             # Earnings parsing
│   └── fundamental_analysis.py # Fundamental parsing
├── stores/                     # Async file persistence
│   ├── task_store.py           # Task persistence
│   ├── stock_state_store.py    # Stock state persistence
│   └── strategy_log_store.py   # Strategy log persistence
├── monitors/                   # Health monitoring
│   ├── health_monitor.py       # General health
│   ├── market_monitor.py       # Market monitoring
│   └── risk_monitor.py         # Risk monitoring
├── events/                     # Event handling
│   └── event_handler.py        # Event handlers
└── executors/                  # Task executors
    └── fundamental_executor.py # Fundamental execution
```

## Rules

### ✅ DO

- ✅ Max 350 lines per module
- ✅ One domain per module
- ✅ Use `aiofiles` for all file I/O
- ✅ Consolidate duplicate API calls
- ✅ Implement exponential backoff retry
- ✅ Check stock state before API calls
- ✅ Use async operations throughout
- ✅ Emit events for task lifecycle

### ❌ DON'T

- ❌ Create monolithic files
- ❌ Mix multiple domains in one module
- ❌ Use blocking I/O operations
- ❌ Make redundant API calls
- ❌ Skip state checking before API calls
- ❌ Exceed file size limits

## Processing Pattern

Each processor follows this pattern:

```python
from src.core.background_scheduler.models import Task, TaskStatus
from src.core.background_scheduler.stores.stock_state_store import StockStateStore

class NewsProcessor:
    """Processes news data for stocks."""
    
    def __init__(self, client, parser, store):
        self.client = client
        self.parser = parser
        self.store = store
    
    async def process(self, task: Task) -> Task:
        """Process news task."""
        # Check state before processing
        state = await self.store.get_stock_state(task.symbol)
        if state.has_recent_news:
            task.status = TaskStatus.SKIPPED
            return task
        
        # Fetch data
        data = await self.client.fetch_news(task.symbol)
        
        # Parse data
        parsed = await self.parser.parse(data)
        
        # Store result
        await self.store.save_news(task.symbol, parsed)
        
        task.status = TaskStatus.COMPLETED
        return task
```

## State Management Pattern

Always check state before API calls:

```python
# Check if we already have recent data
state = await stock_state_store.get_stock_state(symbol)
if state.has_recent_news(within_hours=24):
    # Skip API call - use cached data
    return state.news_data

# Only fetch if we don't have recent data
data = await client.fetch_news(symbol)
```

## Retry Pattern

Use exponential backoff for API calls:

```python
from src.core.background_scheduler.clients.retry_handler import RetryHandler

async def fetch_with_retry(symbol: str) -> Dict:
    """Fetch data with exponential backoff retry."""
    handler = RetryHandler(max_retries=3, base_delay=1.0)
    
    async def attempt():
        return await client.fetch(symbol)
    
    return await handler.retry(attempt)
```

## Event Pattern

Emit events for task lifecycle:

```python
from src.core.event_bus import Event, EventType

# Emit task started
await event_bus.publish(Event(
    type=EventType.TASK_STARTED,
    source="news_processor",
    data={"task_id": task.id, "symbol": task.symbol}
))

# Emit task completed
await event_bus.publish(Event(
    type=EventType.TASK_COMPLETED,
    source="news_processor",
    data={"task_id": task.id, "result": result}
))
```

## Best Practices

1. **Domain Separation**: Keep domains separate (news, earnings, fundamentals)
2. **State Checking**: Always check state before API calls
3. **Retry Logic**: Implement exponential backoff for API calls
4. **Async File I/O**: Use `aiofiles` for all file operations
5. **Event Emission**: Emit events for monitoring and coordination
6. **Error Handling**: Handle errors gracefully, emit error events
7. **Resource Cleanup**: Clean up resources in cleanup methods

## Dependencies

Background scheduler components depend on:
- `EventBus` - For event emission
- `DatabaseStateManager` - For state persistence
- API clients - For external data fetching
- File stores - For async file persistence

## Quick Fix Guide - Common Background Scheduler Errors

**Error: "Background scheduler task created but never runs"**
- **Cause**: Fire-and-forget `asyncio.create_task()` initialization failed, _initialization_complete flag never set to True
- **Fix**: Check initialization status in logs - if "_initialization_complete = False", implementation lacks proper status tracking
- **Prevention**: Implement full initialization status tracking pattern (see src/core/CLAUDE.md Initialization Error Handling Pattern)

**Error: "API call rate limited - 429 Too Many Requests"**
- **Cause**: Retry logic not implemented or exponential backoff interval too aggressive
- **Fix**: Use RetryHandler with max_retries=3 and base_delay=1.0, verify exponential backoff calculation
- **Prevention**: Always wrap API calls with RetryHandler, never make direct requests without retry

**Error: "Duplicate API calls for same stock"**
- **Cause**: State not checked before API calls, or state cache not updated after fetches
- **Fix**: Verify state.has_recent_data() check before API call AND state update after successful fetch
- **Prevention**: Use "check → fetch → update" pattern consistently in all processors

**Error: "File persistence corruption or missing data"**
- **Cause**: Atomic write pattern not used, concurrent writes overwriting each other
- **Fix**: Use temp file → os.replace() pattern, verify with aiofiles
- **Prevention**: See src/core/background_scheduler/stores/CLAUDE.md for atomic write patterns

## Maintenance Instructions

**For Contributors**: This CLAUDE.md is a living document. When you:
- ✅ Add new processor → Document domain, pattern, state checking strategy
- ✅ Fix background scheduler bug → Add to Quick Fix Guide with cause/fix/prevention
- ✅ Change retry strategy → Update Retry Pattern section with new exponential backoff values
- ✅ Add new data source → Document in Architecture Pattern
- ⚠️ Update this file → Run changes through prompt optimizer tool
- ⚠️ Share improvements → Commit alongside code changes so team benefits

**CRITICAL Invariants**:
- ✅ All background scheduler tasks implement initialization status tracking
- ✅ All API calls wrapped with retry logic (RetryHandler or equivalent)
- ✅ All processors check state before API calls
- ✅ All file operations use atomic write pattern
- ✅ All domains kept separate (never mix news + earnings in one processor)

**Last Review**: 2025-11-03

