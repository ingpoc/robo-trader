# Background Scheduler Stores - src/core/background_scheduler/stores/

Async file persistence stores for tasks, stock state, strategy logs. Max 350 lines per store.

## Stores
| Store | Persists |
|-------|----------|
| task_store.py | Task data |
| stock_state_store.py | Stock state |
| strategy_log_store.py | Strategy logs |
| fundamental_store.py | Fundamentals |

## Pattern
```python
# Atomic writes: temp → replace
async with aiofiles.open(temp, 'w') as f:
    await f.write(data)
os.replace(temp, final)  # Atomic
```

## Rules
| DO | DON'T |
|----|-------|
| Keep < 350 lines | Exceed line limits |
| Use aiofiles | Blocking I/O |
| Atomic writes | Direct file access |
| Lock operations | Skip locks |
| Cache in memory | No error handling |
| Use TradingError | Use generic errors |

## Dependencies
aiofiles, asyncio.Lock, Domain models

