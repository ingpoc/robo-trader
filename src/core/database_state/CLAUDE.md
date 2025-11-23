# Database State - src/core/database_state/

Async SQLite state management. Max 350 lines per state class. **CRITICAL: Use asyncio.Lock() for ALL database operations.**

## CRITICAL: Locking Pattern
```python
class MyState(BaseState):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self._lock = asyncio.Lock()  # Each class needs own lock

    async def my_operation(self, param: str):
        async with self._lock:  # Always lock
            cursor = await self.db.connection.execute(...)
            return await cursor.fetchall()
```

## State Classes
| Class | Purpose |
|-------|---------|
| portfolio_state.py | Portfolio data |
| intent_state.py | Trading intents |
| approval_state.py | Approvals queue |
| configuration_state.py | Config data |
| analysis_state.py | Analysis results |
| news_earnings_state.py | News/earnings |

## Atomic Writes
```python
temp = f"{file}.tmp"
async with aiofiles.open(temp, 'w') as f:
    await f.write(json.dumps(data))
os.replace(temp, file)  # Atomic
```

## Rules
| DO | DON'T |
|----|-------|
| Inherit BaseState | Access without lock |
| asyncio.Lock() per class | Share locks |
| Lock all DB ops | Sync operations |
| Lock initialization | Direct DB writes |
| Use aiofiles | Exceed 350 lines |
| Atomic writes | Global state |

## Why: SQLite one-writer constraint + async ops = "database is locked" errors. Proper locking prevents them.

## Dependencies
DatabaseConnection, BaseState, aiofiles, asyncio

