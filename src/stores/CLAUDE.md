# Stores - src/stores/

## Files
| File | Purpose | Type |
|------|---------|------|
| claude_strategy_store.py | Strategy persistence | JSON |
| paper_trading_store.py | Paper trading data | JSON |
| scheduler_task_store.py | Task persistence | JSON |

## Atomic Write Pattern (MANDATORY)
```python
import aiofiles
import json
import os

class MyStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_file = data_dir / "data.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def load(self) -> Dict[str, Any]:
        if not self.data_file.exists():
            return {}
        async with aiofiles.open(self.data_file, 'r') as f:
            content = await f.read()
            return json.loads(content)

    async def save(self, data: Dict[str, Any]) -> None:
        temp_file = f"{self.data_file}.tmp"
        try:
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(data))
            os.replace(temp_file, self.data_file)  # Atomic
        except Exception:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
```

## Rules
| Rule | Requirement |
|------|-------------|
| I/O | Use aiofiles ONLY (no blocking) |
| Writes | MUST use atomic writes (temp + os.replace) |
| Format | JSON only for serialization |
| Max size | 350 lines per store |
| Domains | One domain per file |
| Error handling | Try/except with cleanup |

