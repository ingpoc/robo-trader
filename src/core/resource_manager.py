from __future__ import annotations
import asyncio
from typing import Dict, Set, Optional, Any, Callable
from pathlib import Path
from loguru import logger
from contextlib import asynccontextmanager
import weakref


class ResourceManager:
    """
    Centralized resource lifecycle management for proper cleanup.

    Tracks:
    - File handles
    - WebSocket connections
    - Database connections
    - Background tasks
    - Memory allocations
    """

    def __init__(self):
        self._file_handles: Set[Any] = set()
        self._websockets: Set[weakref.ref] = set()
        self._tasks: Set[asyncio.Task] = set()
        self._cleanup_callbacks: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._shutdown = False

    async def register_file_handle(self, handle: Any, name: str = "") -> None:
        """Register a file handle for tracking."""
        async with self._lock:
            self._file_handles.add(handle)
            logger.debug(f"Registered file handle: {name or id(handle)}")

    async def unregister_file_handle(self, handle: Any) -> None:
        """Unregister a file handle."""
        async with self._lock:
            self._file_handles.discard(handle)

    async def register_websocket(self, ws: Any) -> None:
        """Register a WebSocket connection using weak reference."""
        async with self._lock:
            self._websockets.add(weakref.ref(ws))
            logger.debug(f"Registered WebSocket: {id(ws)}")

    async def register_task(self, task: asyncio.Task, name: str = "") -> None:
        """Register a background task."""
        async with self._lock:
            self._tasks.add(task)
            logger.debug(f"Registered task: {name or task.get_name()}")

    async def unregister_task(self, task: asyncio.Task) -> None:
        """Unregister a completed task."""
        async with self._lock:
            self._tasks.discard(task)

    async def register_cleanup_callback(self, name: str, callback: Callable) -> None:
        """Register a cleanup callback."""
        async with self._lock:
            self._cleanup_callbacks[name] = callback
            logger.debug(f"Registered cleanup callback: {name}")

    async def get_resource_stats(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        async with self._lock:
            active_websockets = sum(1 for ref in self._websockets if ref() is not None)
            return {
                "file_handles": len(self._file_handles),
                "websockets": active_websockets,
                "tasks": len(self._tasks),
                "cleanup_callbacks": len(self._cleanup_callbacks)
            }

    async def cleanup(self) -> None:
        """Clean up all tracked resources."""
        if self._shutdown:
            return

        self._shutdown = True
        logger.info("ResourceManager: Starting cleanup")

        async with self._lock:
            for name, callback in self._cleanup_callbacks.items():
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                    logger.debug(f"Cleanup callback completed: {name}")
                except Exception as e:
                    logger.error(f"Cleanup callback failed for {name}: {e}")

            for task in list(self._tasks):
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=5.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                    except Exception as e:
                        logger.error(f"Task cleanup error: {e}")

            for ref in list(self._websockets):
                ws = ref()
                if ws is not None:
                    try:
                        await ws.close()
                    except Exception as e:
                        logger.debug(f"WebSocket close error: {e}")

            for handle in list(self._file_handles):
                try:
                    if hasattr(handle, 'close'):
                        if asyncio.iscoroutinefunction(handle.close):
                            await handle.close()
                        else:
                            handle.close()
                except Exception as e:
                    logger.debug(f"File handle close error: {e}")

        logger.info("ResourceManager: Cleanup complete")

    @asynccontextmanager
    async def managed_file(self, file_path: Path, mode: str = 'r'):
        """Context manager for tracked file handles."""
        import aiofiles
        async with aiofiles.open(file_path, mode) as f:
            await self.register_file_handle(f, str(file_path))
            try:
                yield f
            finally:
                await self.unregister_file_handle(f)
