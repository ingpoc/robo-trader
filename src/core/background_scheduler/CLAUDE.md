# Background Scheduler - src/core/background_scheduler/

Domain-separated architecture for periodic tasks (news, earnings, fundamentals).

## Structure
| Module | Purpose | Max Size |
|--------|---------|----------|
| background_scheduler.py | Main facade | 300 lines |
| processors/ | Domain logic (news, earnings) | 350 lines each |
| clients/ | API clients (Perplexity) | 350 lines |
| parsers/ | Data parsing | 300 lines |
| stores/ | Async file persistence | 250 lines |
| monitors/ | Health monitoring | 300 lines |

## Pattern
```python
state = await store.get_stock_state(task.symbol)
if state.has_recent_news:
    return task  # Skip if cached
data = await client.fetch_news(task.symbol)
parsed = await parser.parse(data)
await store.save_news(task.symbol, parsed)
```

## Critical Rules
| Rule | Requirement |
|------|-------------|
| State checking | Check before API calls (avoid duplicates) |
| Retry | Always use exponential backoff (RetryHandler) |
| File I/O | Use aiofiles + atomic writes (temp → os.replace) |
| Events | Emit for task lifecycle |
| Max size | <350 lines per module, one domain per module |

## Common Errors
| Error | Fix |
|-------|-----|
| Init fails silently | Check _initialization_complete flag in logs |
| API 429 rate limit | Wrap with RetryHandler(max_retries=3) |
| Duplicate API calls | Verify state.has_recent_data() check |
| File corruption | Use temp file + os.replace() pattern |
