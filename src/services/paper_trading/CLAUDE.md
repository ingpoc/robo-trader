# Paper Trading Services Guidelines

> **Scope**: Applies to `src/services/paper_trading/` directory. Read `src/services/CLAUDE.md` for parent context.

## Purpose

The `paper_trading/` directory contains **paper trading services** that handle simulated trading operations, account management, performance calculation, and price monitoring.

## Architecture Pattern

### Service Layer Pattern

The paper trading services use a **service layer architecture** with focused services:

- **Core Services**:
  - `account_manager.py` - Account management and state
  - `trade_executor.py` - Trade execution logic
  - `performance_calculator.py` - Performance metrics calculation
  - `price_monitor.py` - Price monitoring and updates

## File Structure

```
paper_trading/
├── __init__.py
├── account_manager.py        # Account management (max 350 lines)
├── trade_executor.py         # Trade execution (max 350 lines)
├── performance_calculator.py # Performance calculation (max 350 lines)
└── price_monitor.py          # Price monitoring (max 350 lines)
```

## Rules

### ✅ DO

- ✅ **Keep services < 350 lines** - Refactor if exceeds limit
- ✅ **Use dependency injection** - Inject dependencies via constructor
- ✅ **Emit events** - Use `EventBus` for cross-cutting concerns
- ✅ **Handle errors gracefully** - Wrap in `TradingError` with proper categories
- ✅ **Use database locking** - Use locked state methods for database operations
- ✅ **Track state** - Maintain account and trade state consistently
- ✅ **Calculate metrics** - Provide accurate performance metrics

### ❌ DON'T

- ❌ **Access database directly** - Use locked state methods
- ❌ **Exceed line limits** - Refactor if service exceeds 350 lines
- ❌ **Mix concerns** - Keep services focused
- ❌ **Skip validation** - Always validate trades and account operations

## Dependencies

- `EventBus` - For event-driven communication
- `Config` - For configuration
- `DatabaseStateManager` - For state management (via locked methods)
- `PaperTradingStore` - For data persistence
- `MarketDataService` - For market data

## Testing

- Test account management operations
- Test trade execution
- Test performance calculation
- Test price monitoring
- Test error handling and recovery

## Maintenance

- **When service grows**: Split into focused services or extract supporting modules
- **When patterns change**: Update this CLAUDE.md and parent `src/services/CLAUDE.md`
- **When new features needed**: Add to appropriate service or create new focused service

