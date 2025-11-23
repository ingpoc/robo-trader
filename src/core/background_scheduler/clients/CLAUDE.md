# Scheduler Clients - src/core/background_scheduler/clients/

Unified API clients for external services (Perplexity, data providers).

## Files
| File | Purpose | Max Size |
|------|---------|----------|
| perplexity_client.py | Main Perplexity API client | 350 lines |
| retry_handler.py | Exponential backoff retry logic | 350 lines |
| perplexity_*_queries.py | Domain-specific queries | 350 lines each |
| perplexity_prompt_manager.py | Prompt management | 350 lines |

## Pattern
```python
async def fetch_with_retry(symbol: str):
    handler = RetryHandler(max_retries=3, base_delay=1.0)
    return await handler.retry(lambda: client.fetch(symbol))
```

## Rules
| Rule | Requirement |
|------|-------------|
| Retry | Always use RetryHandler + exponential backoff |
| Errors | Wrap in TradingError with context |
| Cache | Cache API responses when appropriate |
| Lines | <350 per file, keep focused |
| Logging | Log all API calls for debugging |
