"""
WebSocket Broadcast Throttler

Prevents buffer overload by throttling, batching, and debouncing broadcasts.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from loguru import logger


@dataclass
class ThrottleConfig:
    """Throttle configuration."""
    max_messages_per_second: int = 10
    batch_window_ms: int = 100
    debounce_keys: List[str] = field(default_factory=lambda: ["type"])
    max_batch_size: int = 50
    drop_duplicates: bool = True


class BroadcastThrottler:
    """
    Throttles and batches WebSocket broadcasts to prevent buffer overload.

    Features:
    - Rate limiting: Max N messages per second
    - Batching: Collect messages in time window and send together
    - Debouncing: Prevent duplicate rapid updates
    - Priority queuing: Critical messages bypass throttling
    """

    def __init__(
        self,
        broadcast_callback: Callable,
        config: Optional[ThrottleConfig] = None
    ):
        self.broadcast_callback = broadcast_callback
        self.config = config or ThrottleConfig()

        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._last_sent: Dict[str, datetime] = {}
        self._pending_batch: List[Dict[str, Any]] = []
        self._last_batch_time = datetime.now(timezone.utc)

        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._batch_task: Optional[asyncio.Task] = None

        self._stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "messages_dropped": 0,
            "messages_batched": 0,
            "batches_sent": 0
        }

    async def start(self) -> None:
        """Start the throttler."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        self._batch_task = asyncio.create_task(self._batch_processor())
        logger.info("BroadcastThrottler started")

    async def stop(self) -> None:
        """Stop the throttler."""
        self._running = False

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        await self._flush_pending_batch()
        logger.info("BroadcastThrottler stopped")

    async def broadcast(
        self,
        message: Dict[str, Any],
        priority: bool = False
    ) -> None:
        """
        Queue a message for broadcast.

        Args:
            message: Message to broadcast
            priority: If True, bypass throttling and send immediately
        """
        self._stats["messages_received"] += 1

        if priority:
            await self._send_immediately(message)
            return

        if self._should_drop(message):
            self._stats["messages_dropped"] += 1
            logger.debug(f"Dropped duplicate message: {message.get('type')}")
            return

        await self._message_queue.put(message)

    def _should_drop(self, message: Dict[str, Any]) -> bool:
        """Check if message should be dropped as duplicate."""
        if not self.config.drop_duplicates:
            return False

        key = self._get_dedup_key(message)
        now = datetime.now(timezone.utc)

        if key in self._last_sent:
            time_since_last = (now - self._last_sent[key]).total_seconds()

            min_interval = 1.0 / self.config.max_messages_per_second
            if time_since_last < min_interval:
                return True

        self._last_sent[key] = now

        self._cleanup_old_keys()

        return False

    def _get_dedup_key(self, message: Dict[str, Any]) -> str:
        """Get deduplication key for message."""
        key_parts = []
        for key in self.config.debounce_keys:
            value = message.get(key)
            if value is not None:
                key_parts.append(f"{key}:{value}")

        return "|".join(key_parts) if key_parts else str(message)

    def _cleanup_old_keys(self) -> None:
        """Remove old keys from dedup tracking."""
        if len(self._last_sent) > 1000:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=10)

            self._last_sent = {
                k: v for k, v in self._last_sent.items()
                if v > cutoff
            }

    async def _process_queue(self) -> None:
        """Process queued messages with throttling."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=0.1
                )

                self._pending_batch.append(message)
                self._stats["messages_batched"] += 1

                if len(self._pending_batch) >= self.config.max_batch_size:
                    await self._flush_pending_batch()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")

    async def _batch_processor(self) -> None:
        """Periodically flush pending batch."""
        while self._running:
            try:
                await asyncio.sleep(self.config.batch_window_ms / 1000.0)

                if self._pending_batch:
                    await self._flush_pending_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")

    async def _flush_pending_batch(self) -> None:
        """Flush pending batch to broadcast."""
        if not self._pending_batch:
            return

        batch = self._pending_batch.copy()
        self._pending_batch.clear()

        if len(batch) == 1:
            await self._send_immediately(batch[0])
        else:
            await self._send_batch(batch)

    async def _send_immediately(self, message: Dict[str, Any]) -> None:
        """Send a single message immediately."""
        try:
            await self.broadcast_callback(message)
            self._stats["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")

    async def _send_batch(self, messages: List[Dict[str, Any]]) -> None:
        """Send a batch of messages."""
        try:
            batch_message = {
                "type": "batch_update",
                "messages": messages,
                "count": len(messages),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await self.broadcast_callback(batch_message)
            self._stats["messages_sent"] += len(messages)
            self._stats["batches_sent"] += 1

            logger.debug(f"Sent batch of {len(messages)} messages")

        except Exception as e:
            logger.error(f"Failed to broadcast batch: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get throttler statistics."""
        return {
            **self._stats,
            "queue_size": self._message_queue.qsize(),
            "pending_batch_size": len(self._pending_batch),
            "dedup_keys_tracked": len(self._last_sent),
            "config": {
                "max_messages_per_second": self.config.max_messages_per_second,
                "batch_window_ms": self.config.batch_window_ms,
                "max_batch_size": self.config.max_batch_size,
                "drop_duplicates": self.config.drop_duplicates
            }
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "messages_dropped": 0,
            "messages_batched": 0,
            "batches_sent": 0
        }
