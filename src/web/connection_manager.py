"""
WebSocket Connection Manager for Robo Trader

Thread-safe WebSocket connection manager with atomic snapshot mechanism
and concurrent broadcasting to eliminate race conditions.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import WebSocket
from loguru import logger


@dataclass
class BroadcastResult:
    """Result of a broadcast operation."""

    total_connections: int
    successful_sends: int
    failed_sends: int
    dead_connections: int
    duration_ms: float


class ConnectionManager:
    """
    Thread-safe WebSocket connection manager.

    Features:
    - Atomic snapshot mechanism prevents race conditions during broadcast
    - Concurrent message sending with asyncio.gather
    - Background cleanup of dead connections
    - Graceful error handling for stale connections
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._dead_connections: Set[str] = set()
        self._generation_counter = 0
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval_seconds = 10

    async def connect(
        self, websocket: WebSocket, client_id: Optional[str] = None
    ) -> str:
        """
        Add a new WebSocket connection.

        Args:
            websocket: WebSocket instance to add
            client_id: Optional client identifier

        Returns:
            connection_id: Unique identifier for this connection
        """
        await websocket.accept()

        connection_id = client_id or f"ws_{id(websocket)}"

        async with self._lock:
            self.active_connections[connection_id] = websocket
            self._generation_counter += 1

        logger.info(
            f"WebSocket connected: {connection_id} (total: {len(self.active_connections)})"
        )

        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        return connection_id

    async def disconnect(
        self, websocket: WebSocket, connection_id: Optional[str] = None
    ) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket instance to remove
            connection_id: Optional connection identifier
        """
        if connection_id is None:
            connection_id = f"ws_{id(websocket)}"

        async with self._lock:
            removed = self.active_connections.pop(connection_id, None)
            self._dead_connections.discard(connection_id)
            if removed:
                self._generation_counter += 1

        if removed:
            logger.info(
                f"WebSocket disconnected: {connection_id} (remaining: {len(self.active_connections)})"
            )

    async def broadcast(self, message: Dict[str, Any]) -> BroadcastResult:
        """
        Broadcast message to all connected clients with atomic snapshot and concurrent sends.

        Args:
            message: Message dict to broadcast

        Returns:
            BroadcastResult with broadcast statistics
        """
        start_time = datetime.now(timezone.utc)

        snapshot, generation = await self._get_snapshot()

        if not snapshot:
            return BroadcastResult(
                total_connections=0,
                successful_sends=0,
                failed_sends=0,
                dead_connections=0,
                duration_ms=0.0,
            )

        tasks = [
            self._send_message(websocket, message, conn_id)
            for conn_id, websocket in snapshot.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False or isinstance(r, Exception))

        newly_dead = [
            conn_id
            for conn_id, result in zip(snapshot.keys(), results)
            if result is False or isinstance(result, Exception)
        ]

        if newly_dead:
            async with self._lock:
                for conn_id in newly_dead:
                    self._dead_connections.add(conn_id)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return BroadcastResult(
            total_connections=len(snapshot),
            successful_sends=successful,
            failed_sends=failed,
            dead_connections=len(newly_dead),
            duration_ms=duration,
        )

    async def _get_snapshot(self) -> Tuple[Dict[str, WebSocket], int]:
        """
        Get atomic snapshot of active connections.

        Returns:
            (snapshot dict, generation counter)
        """
        async with self._lock:
            snapshot = self.active_connections.copy()
            generation = self._generation_counter

        return snapshot, generation

    async def _send_message(
        self, websocket: WebSocket, message: Dict[str, Any], connection_id: str
    ) -> bool:
        """
        Send message to single WebSocket with timeout.

        Args:
            websocket: Target WebSocket
            message: Message to send
            connection_id: Connection identifier for logging

        Returns:
            True if successful, False if failed
        """
        try:
            await asyncio.wait_for(websocket.send_json(message), timeout=2.0)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket send timeout: {connection_id}")
            return False
        except Exception as e:
            error_msg = str(e).lower()
            if (
                "close message has been sent" in error_msg
                or "connection is closed" in error_msg
                or "websocket is closed" in error_msg
            ):
                logger.debug(f"WebSocket closed normally: {connection_id}")
            else:
                logger.warning(f"WebSocket send failed for {connection_id}: {e}")
            return False

    async def _cleanup_dead_connections(self) -> int:
        """
        Remove dead connections from active connections dict.

        Returns:
            Number of connections cleaned up
        """
        async with self._lock:
            dead_ids = list(self._dead_connections)

            if not dead_ids:
                return 0

            removed_count = 0
            for conn_id in dead_ids:
                if conn_id in self.active_connections:
                    del self.active_connections[conn_id]
                    removed_count += 1
                self._dead_connections.discard(conn_id)

            if removed_count > 0:
                self._generation_counter += 1

        if removed_count > 0:
            logger.debug(f"Cleaned up {removed_count} dead WebSocket connections")

        return removed_count

    async def _cleanup_loop(self) -> None:
        """Background cleanup task that runs every N seconds."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_seconds)
                await self._cleanup_dead_connections()

                async with self._lock:
                    active_count = len(self.active_connections)
                    dead_count = len(self._dead_connections)

                if active_count == 0 and dead_count == 0:
                    logger.debug("No active connections, stopping cleanup task")
                    break

            except asyncio.CancelledError:
                logger.debug("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    async def get_connection_count(self) -> int:
        """Get current number of active connections."""
        async with self._lock:
            return len(self.active_connections)

    async def shutdown(self) -> None:
        """Gracefully shutdown connection manager."""
        logger.debug("Shutting down WebSocket ConnectionManager")

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        async with self._lock:
            connection_count = len(self.active_connections)
            self.active_connections.clear()
            self._dead_connections.clear()

        logger.debug(
            f"ConnectionManager shutdown complete ({connection_count} connections closed)"
        )
