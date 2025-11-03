# Database State Directory Guidelines

> **Scope**: Applies to `src/core/database_state/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `database_state/` directory contains async SQLite state management classes. Each state class manages a specific domain of persistent data with proper locking to prevent concurrent access issues.

## Architecture Pattern

### Async State Management with Locking

Each state class:
- Manages one domain of data (portfolio, intent, approval, etc.)
- Uses `asyncio.Lock()` for concurrent operations (CRITICAL)
- Inherits from `BaseState` for common patterns
- Provides domain-specific methods with proper locking

### Directory Structure

```
database_state/
├── base.py                    # Base state class with locking
├── database_state.py          # Unified state manager
├── portfolio_state.py         # Portfolio data management
├── intent_state.py            # Trading intent tracking
├── approval_state.py          # Approval queue management
├── configuration_state.py     # Configuration management
├── analysis_state.py          # Analysis data management
└── news_earnings_state.py     # News and earnings data
```

## CRITICAL: Database Locking Pattern

### Problem

SQLite "database is locked" errors occur when multiple async operations access the database concurrently without proper synchronization.

### Solution

**Every state class MUST implement its own `asyncio.Lock()` and use `async with self._lock:` for ALL database operations.**

### Implementation Pattern

```python
import asyncio
from src.core.database_state.base import BaseState

class MyState(BaseState):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self._lock = asyncio.Lock()  # CRITICAL: Each class needs its own lock
    
    async def my_operation(self, param: str) -> Dict[str, Any]:
        """Database operation with locking."""
        async with self._lock:  # CRITICAL: Always acquire lock
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM my_table WHERE param = ?", 
                    (param,)
                )
                rows = await cursor.fetchall()
                return self._process_rows(rows)
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                raise
    
    async def initialize(self) -> None:
        """Initialize tables (also needs locking)."""
        async with self._lock:  # CRITICAL: Even init needs locking
            # Create tables, initialize data
            pass
```

## Rules

### ✅ DO

- ✅ Inherit from `BaseState` for common patterns
- ✅ Use `asyncio.Lock()` for ALL database operations
- ✅ Use `async with self._lock:` for every database call
- ✅ Wrap initialization in lock
- ✅ Use async SQLite operations
- ✅ Use `aiofiles` for file I/O
- ✅ Atomic writes with temp files
- ✅ Max 350 lines per state class

### ❌ DON'T

- ❌ Access database without acquiring lock
- ❌ Share locks between state classes
- ❌ Skip locking on initialization
- ❌ Use synchronous database operations
- ❌ Write directly to database files (use atomic writes)
- ❌ Exceed file size limits

## Atomic Write Pattern

Always use atomic writes for file operations:

```python
import tempfile
import os
import aiofiles

async def save_data(self, data: Dict[str, Any]) -> None:
    """Save data atomically."""
    temp_file = f"{self.data_file}.tmp"
    
    async with aiofiles.open(temp_file, 'w') as f:
        await f.write(json.dumps(data, indent=2))
    
    # Atomic replace
    os.replace(temp_file, self.data_file)
```

## State Class Pattern

Each state class should follow this pattern:

```python
import asyncio
from src.core.database_state.base import BaseState

class PortfolioState(BaseState):
    """Manages portfolio data state."""
    
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize portfolio tables."""
        async with self._lock:
            # Create tables
            await self.db.connection.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL,
                    avg_price REAL,
                    updated_at TIMESTAMP
                )
            """)
            await self.db.connection.commit()
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio data."""
        async with self._lock:
            cursor = await self.db.connection.execute(
                "SELECT * FROM portfolio"
            )
            rows = await cursor.fetchall()
            return self._process_portfolio(rows)
    
    async def update_position(self, symbol: str, quantity: float, price: float) -> None:
        """Update position atomically."""
        async with self._lock:
            await self.db.connection.execute(
                "INSERT OR REPLACE INTO portfolio VALUES (?, ?, ?, ?)",
                (symbol, quantity, price, datetime.utcnow())
            )
            await self.db.connection.commit()
```

## Best Practices

1. **Always Lock**: Every database operation must use `async with self._lock:`
2. **Separate Locks**: Each state class needs its own lock (don't share)
3. **Initialize Safely**: Lock initialization operations too
4. **Atomic Writes**: Use temp files and `os.replace()` for atomicity
5. **Error Handling**: Wrap operations in try/except, log errors
6. **Transaction Safety**: Use transactions for multi-step operations
7. **Resource Cleanup**: Close connections properly in cleanup

## Why Locking Matters

- **SQLite Limitation**: Only one writer at a time
- **Concurrent Access**: Multiple async operations can cause locks
- **Prevention**: Proper locking prevents "database is locked" errors
- **Performance**: Locking ensures data integrity without blocking unnecessarily

## Dependencies

State classes depend on:
- `DatabaseConnection` - For database access
- `BaseState` - For common patterns
- `aiofiles` - For async file I/O
- `asyncio` - For locking

