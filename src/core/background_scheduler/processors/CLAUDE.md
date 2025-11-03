# Background Scheduler Processors Guidelines

> **Scope**: Applies to `src/core/background_scheduler/processors/` directory. Read `src/core/background_scheduler/CLAUDE.md` for parent context.

## Purpose

The `processors/` directory contains **domain-specific processors** that handle data processing for news, earnings, and fundamental analysis.

## Architecture Pattern

### Domain-Separated Architecture

The processors use a **domain-separated architecture** where each domain has its own processor:

- **Domain Processors**:
  - `news_processor.py` - News processing
  - `earnings_processor.py` - Earnings processing
  - `fundamental_analyzer.py` - Fundamental analysis processing
  - `deep_fundamental_processor.py` - Deep fundamental analysis

## File Structure

```
processors/
├── __init__.py
├── news_processor.py              # News processing (max 350 lines)
├── earnings_processor.py          # Earnings processing (max 350 lines)
├── fundamental_analyzer.py        # Fundamental analysis (max 350 lines)
└── deep_fundamental_processor.py  # Deep fundamental (max 350 lines)
```

## Rules

### ✅ DO

- ✅ **Keep processors < 350 lines** - Refactor if exceeds limit
- ✅ **One domain per processor** - Don't mix domains
- ✅ **Check stock state** - Check state before processing
- ✅ **Emit events** - Emit events for task lifecycle
- ✅ **Use async operations** - Use async throughout
- ✅ **Handle errors gracefully** - Wrap in `TradingError`

### ❌ DON'T

- ❌ **Exceed line limits** - Refactor if processor exceeds 350 lines
- ❌ **Mix domains** - Keep processors domain-specific
- ❌ **Skip state checking** - Always check state before processing
- ❌ **Use blocking I/O** - Use async operations only

## Dependencies

- Domain-specific clients - For API calls
- Domain-specific parsers - For data parsing
- Domain-specific stores - For data persistence
- `StockStateStore` - For state checking
- `EventBus` - For event emission

## Testing

- Test processor handles tasks correctly
- Test state checking works
- Test event emission
- Test error handling

## Maintenance

- **When processor grows**: Split into focused processors or extract supporting modules
- **When patterns change**: Update this CLAUDE.md and parent `src/core/background_scheduler/CLAUDE.md`
- **When new domains needed**: Create new focused processor

