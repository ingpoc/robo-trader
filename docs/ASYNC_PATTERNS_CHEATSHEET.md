# Async Patterns Cheat Sheet

Quick reference for common async/await patterns in the Robo Trader project.

## ✅ File Operations in Async Methods

### Reading Files
```python
import aiofiles

async def read_config(self) -> Dict[str, Any]:
    async with aiofiles.open(self.config_file, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)
```

### Writing Files
```python
import aiofiles

async def save_config(self, config: Dict[str, Any]) -> None:
    async with aiofiles.open(self.config_file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(config, indent=2, ensure_ascii=False))
```

### ❌ NEVER DO THIS
```python
# WRONG - Blocks event loop
async def read_config(self):
    with open(self.config_file, 'r') as f:  # BLOCKING!
        return json.load(f)
```

## ✅ Task Timeout with Cancellation Protection

### Correct Pattern
```python
async def run_with_timeout(self, task_coro, timeout_seconds: int):
    execution_task = None
    try:
        execution_task = asyncio.create_task(task_coro)
        await asyncio.wait_for(execution_task, timeout=timeout_seconds)

    except asyncio.TimeoutError:
        if execution_task and not execution_task.done():
            execution_task.cancel()
            try:
                # CRITICAL: Add timeout when awaiting cancelled task
                await asyncio.wait_for(execution_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.error(f"Task timed out after {timeout_seconds}s")
        raise
```

### ❌ NEVER DO THIS
```python
# WRONG - Missing timeout protection when awaiting cancelled task
async def run_with_timeout(self, task_coro, timeout_seconds: int):
    try:
        execution_task = asyncio.create_task(task_coro)
        await asyncio.wait_for(execution_task, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        execution_task.cancel()
        await execution_task  # CAN HANG INDEFINITELY!
```

## ✅ WebSocket Cleanup

### Correct Pattern
```python
async def websocket_endpoint(websocket: WebSocket):
    heartbeat_task = None
    try:
        await connection_manager.connect(websocket)
        heartbeat_task = asyncio.create_task(send_heartbeat())

        # Main WebSocket loop
        while True:
            data = await get_dashboard_data()
            await websocket.send_json(data)
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        # Proper cleanup with timeout protection
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await asyncio.wait_for(heartbeat_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        await connection_manager.disconnect(websocket)
```

## ✅ Background Task Error Handling

### Correct Pattern
```python
class BackgroundTaskManager:
    async def start_task(self, name: str, coro):
        task = asyncio.create_task(self._task_wrapper(name, coro))
        self._tasks[name] = task

        # Monitor completion
        task.add_done_callback(lambda t: self._handle_completion(name, t))

    async def _task_wrapper(self, name: str, coro):
        try:
            await coro
        except Exception as e:
            logger.error(f"Background task '{name}' failed: {e}", exc_info=True)
            raise

    def _handle_completion(self, name: str, task: asyncio.Task):
        try:
            if task.exception() is not None:
                logger.error(f"Task '{name}' completed with exception")
        except Exception as e:
            logger.error(f"Error handling completion: {e}")
```

## ✅ Lazy Async Loading (for __init__)

### Correct Pattern
```python
class AsyncStore:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self._data = None
        self._loaded = False  # Lazy loading flag

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with aiofiles.open(self.data_file, 'r') as f:
            self._data = await f.read()
        self._loaded = True

    async def get_data(self):
        await self._ensure_loaded()
        return self._data
```

### ❌ NEVER DO THIS
```python
# WRONG - Blocking I/O in __init__
class AsyncStore:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        with open(self.data_file, 'r') as f:  # BLOCKS EVENT LOOP!
            self._data = f.read()
```

## 🔍 Quick Detection Checklist

Before committing code, search for these patterns:

```bash
# Check for blocking file I/O in async context
grep -r "with open(" src/ | grep -v "def " | grep "async def"

# Check for json.load/dump in async files
grep -r "json.load\|json.dump" src/ | grep -v "# "

# Check for await after cancel without wait_for
grep -A 3 "\.cancel()" src/ | grep "await" | grep -v "wait_for"
```

## 📚 Rule References

- **File I/O**: `.kilocode/rules/async-file-operations-rules.md` Section 4
- **Timeouts**: `.kilocode/rules/background-task-error-handling-rules.md` Section 3.1
- **Background Tasks**: `.kilocode/rules/background-task-error-handling-rules.md` Section 1-2

## 🚨 Common Mistakes to Avoid

1. ❌ Using `open()` instead of `aiofiles.open()` in async methods
2. ❌ Using `json.load()` instead of `json.loads(await f.read())` in async methods
3. ❌ Awaiting cancelled tasks without timeout protection
4. ❌ Performing file I/O in `__init__()` methods
5. ❌ Starting background tasks without error handling

## 💡 Remember

- **ALL file I/O in async methods MUST use `aiofiles`**
- **ALL cancelled task awaits MUST have timeout protection**
- **ALL background tasks MUST have error handling**
- **ALL `__init__()` methods MUST avoid blocking I/O**

When in doubt, check the rule files!
