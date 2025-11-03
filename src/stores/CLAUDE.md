# Stores Directory Guidelines

> **Scope**: Applies to `src/stores/` directory. Read `src/CLAUDE.md` and `src/core/CLAUDE.md` for context.

## Purpose

The `stores/` directory contains data store implementations for persistence. These stores provide async file-based or database-based storage for domain-specific data.

## Architecture Pattern

### Async Data Stores

Stores in this directory provide:
- **Async File Persistence** - For JSON-based data storage
- **Strategy Storage** - For Claude strategy persistence
- **Task Storage** - For scheduler task persistence
- **State Persistence** - For application state

### Directory Structure

```
stores/
├── __init__.py                # Store exports
├── claude_strategy_store.py   # Claude strategy persistence
├── paper_trading_store.py      # Paper trading data persistence
└── scheduler_task_store.py    # Scheduler task persistence
```

## Rules

### ✅ DO

- ✅ Use `aiofiles` for all file I/O
- ✅ Implement atomic writes with temp files
- ✅ Provide async methods for all operations
- ✅ Handle file operations with proper error handling
- ✅ Keep stores focused (one domain per store)
- ✅ Max 350 lines per store file
- ✅ Use JSON for data serialization

### ❌ DON'T

- ❌ Use blocking file operations
- ❌ Write directly to files (use atomic writes)
- ❌ Skip error handling
- ❌ Mix multiple domains in one store
- ❌ Exceed file size limits
- ❌ Cache data indefinitely

## Store Pattern

Each store should follow this pattern:

```python
import aiofiles
import json
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

class MyStore:
    """Store for domain-specific data."""
    
    def __init__(self, data_dir: Path):
        """Initialize store with data directory."""
        self.data_dir = data_dir
        self.data_file = data_dir / "my_data.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def load(self) -> Dict[str, Any]:
        """Load data from file."""
        if not self.data_file.exists():
            return {}
        
        try:
            async with aiofiles.open(self.data_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return {}
    
    async def save(self, data: Dict[str, Any]) -> None:
        """Save data atomically."""
        temp_file = f"{self.data_file}.tmp"
        
        try:
            # Write to temp file
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
            
            # Atomic replace
            os.replace(temp_file, self.data_file)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            # Clean up temp file on error
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
```

## Atomic Write Pattern

Always use atomic writes:

```python
async def save_atomic(self, data: Dict[str, Any]) -> None:
    """Save data with atomic write."""
    temp_file = f"{self.data_file}.tmp"
    
    # Write to temp file first
    async with aiofiles.open(temp_file, 'w') as f:
        await f.write(json.dumps(data, indent=2))
    
    # Atomic replace (single operation)
    os.replace(temp_file, self.data_file)
```

## Best Practices

1. **Atomic Writes**: Always use temp files and `os.replace()`
2. **Error Handling**: Handle file operations with try/except
3. **Directory Creation**: Ensure directories exist before writes
4. **Cleanup**: Clean up temp files on errors
5. **Lazy Loading**: Load data on demand, not at initialization
6. **Validation**: Validate data before saving
7. **Backup**: Consider backup strategies for critical data

## Dependencies

Stores typically depend on:
- `aiofiles` - For async file I/O
- `json` - For data serialization
- `pathlib` - For path management
- `os` - For atomic file operations

