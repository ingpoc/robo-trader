# Background Scheduler Clients Guidelines

> **Scope**: Applies to `src/core/background_scheduler/clients/` directory. Read `src/core/background_scheduler/CLAUDE.md` for parent context.

## Purpose

The `clients/` directory contains **unified API clients** for external services used by the background scheduler. These clients handle API communication, retry logic, and error handling.

## Architecture Pattern

### Client Layer Pattern

The clients use a **client layer architecture** with focused client modules:

- **Core Clients**:
  - `perplexity_client.py` - Perplexity API client
  - `retry_handler.py` - Retry logic and error handling
  - `perplexity_*_queries.py` - Domain-specific query builders

## File Structure

```
clients/
├── __init__.py
├── perplexity_client.py              # Main Perplexity client (max 350 lines)
├── retry_handler.py                  # Retry logic (max 350 lines)
├── perplexity_analysis_queries.py   # Analysis queries (max 350 lines)
├── perplexity_earnings_queries.py   # Earnings queries (max 350 lines)
├── perplexity_market_queries.py     # Market queries (max 350 lines)
└── perplexity_prompt_manager.py      # Prompt management (max 350 lines)
```

## Rules

### ✅ DO

- ✅ **Keep clients < 350 lines** - Refactor if exceeds limit
- ✅ **Use retry logic** - Always use `RetryHandler` for API calls
- ✅ **Handle errors gracefully** - Wrap in `TradingError` with proper categories
- ✅ **Use exponential backoff** - Implement exponential backoff for retries
- ✅ **Cache responses** - Cache API responses when appropriate
- ✅ **Log API calls** - Log API calls for debugging

### ❌ DON'T

- ❌ **Exceed line limits** - Refactor if client exceeds 350 lines
- ❌ **Skip retry logic** - Always use retry handler
- ❌ **Mix concerns** - Keep clients focused
- ❌ **Hardcode API keys** - Use configuration

## Dependencies

- `RetryHandler` - For retry logic
- `Config` - For configuration
- Domain-specific parsers - For response parsing

## Testing

- Test API client integration
- Test retry logic works correctly
- Test error handling and recovery
- Test caching behavior

## Maintenance

- **When client grows**: Split into focused clients or extract supporting modules
- **When patterns change**: Update this CLAUDE.md and parent `src/core/background_scheduler/CLAUDE.md`
- **When API changes**: Update client to match new API patterns

