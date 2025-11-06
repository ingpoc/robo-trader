"""
Broadcast Health Monitor

Provides comprehensive health monitoring and recovery for WebSocket broadcasting system.
Implements circuit breakers, backpressure handling, and automatic recovery mechanisms.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class BroadcastErrorSeverity(Enum):
    """Severity levels for broadcast errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BroadcastError:
    """Structured broadcast error information."""

    error: Exception
    severity: BroadcastErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    recovered: bool = False
    recovery_attempts: int = 0


@dataclass
class HealthMetrics:
    """Broadcast system health metrics."""

    total_broadcasts: int = 0
    successful_broadcasts: int = 0
    failed_broadcasts: int = 0
    circuit_breaker_trips: int = 0
    backpressure_events: int = 0
    recovery_events: int = 0

    # Timing metrics
    average_broadcast_time: float = 0.0
    max_broadcast_time: float = 0.0
    min_broadcast_time: float = float("inf")

    # Recent activity (last 100 broadcasts)
    recent_broadcast_times: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_success_rate: float = 0.0

    # Error tracking
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=50))
    error_rate: float = 0.0

    last_broadcast_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None

    def update_success_rate(self) -> None:
        """Update recent success rate based on last 100 broadcasts."""
        if self.total_broadcasts > 0:
            self.recent_success_rate = (
                self.successful_broadcasts / self.total_broadcasts
            ) * 100
        else:
            self.recent_success_rate = 0.0

    def update_error_rate(self) -> None:
        """Update recent error rate based on last 50 errors."""
        now = datetime.now(timezone.utc)
        recent_errors = [
            e for e in self.recent_errors if (now - e.timestamp).total_seconds() < 300
        ]  # Last 5 minutes
        self.recent_errors = deque(recent_errors, maxlen=50)
        self.error_rate = len(recent_errors) / 50.0 * 100 if recent_errors else 0.0

    def add_broadcast_time(self, duration: float) -> None:
        """Add a new broadcast time measurement."""
        self.recent_broadcast_times.append(duration)
        self.average_broadcast_time = sum(self.recent_broadcast_times) / len(
            self.recent_broadcast_times
        )
        self.max_broadcast_time = max(self.max_broadcast_time, duration)
        self.min_broadcast_time = min(self.min_broadcast_time, duration)
        self.last_broadcast_time = datetime.now(timezone.utc)


class BroadcastHealthMonitor:
    """
    Comprehensive health monitoring for WebSocket broadcasting system.

    Features:
    - Circuit breaker with configurable thresholds
    - Backpressure detection and handling
    - Automatic recovery mechanisms
    - Health metrics and analytics
    - Error classification and tracking
    """

    def __init__(
        self, broadcast_callback: Callable, config: Optional[Dict[str, Any]] = None
    ):
        self.broadcast_callback = broadcast_callback
        self.config = config or {}

        # Circuit breaker state
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time: Optional[datetime] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0

        # Backpressure handling
        self._backpressure_detected = False
        self._slow_clients: set = set()
        self._broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

        # Health metrics
        self._metrics = HealthMetrics()

        # Configuration
        self._failure_threshold = self.config.get("failure_threshold", 5)
        self._recovery_timeout = self.config.get("recovery_timeout", 60)
        self._success_threshold = self.config.get("success_threshold", 3)
        self._backpressure_threshold = self.config.get(
            "backpressure_threshold", 2.0
        )  # seconds
        self._health_check_interval = self.config.get("health_check_interval", 30)

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._backpressure_monitor_task: Optional[asyncio.Task] = None
        self._recovery_task: Optional[asyncio.Task] = None

        # Error recovery strategies
        self._recovery_strategies: List[Callable] = [
            self._attempt_basic_recovery,
            self._attempt_connection_recovery,
            self._attempt_full_reset,
        ]

        # Event handlers
        self._error_handlers: List[Callable] = []
        self._recovery_handlers: List[Callable] = []

        self._running = False

    async def start(self) -> None:
        """Start the health monitor."""
        if self._running:
            return

        self._running = True

        # Start background monitoring tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._backpressure_monitor_task = asyncio.create_task(
            self._backpressure_monitor_loop()
        )

        logger.info("BroadcastHealthMonitor started")

    async def stop(self) -> None:
        """Stop the health monitor."""
        self._running = False

        # Cancel background tasks
        for task in [
            self._health_check_task,
            self._backpressure_monitor_task,
            self._recovery_task,
        ]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("BroadcastHealthMonitor stopped")

    async def broadcast(self, message: Dict[str, Any]) -> bool:
        """
        Broadcast a message with health monitoring and circuit breaker protection.

        Args:
            message: Message to broadcast

        Returns:
            True if broadcast was successful, False otherwise
        """
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            logger.warning("Circuit breaker is open - broadcast blocked")
            return False

        # Check backpressure
        if self._backpressure_detected:
            await self._handle_backpressure(message)
            return False

        start_time = time.time()

        try:
            self._metrics.total_broadcasts += 1

            # Add to queue for backpressure handling
            await self._broadcast_queue.put(message)

            # Actually send the message
            await self.broadcast_callback(message)

            # Record success
            duration = time.time() - start_time
            self._record_success(duration)

            return True

        except Exception as e:
            # Record failure
            await self._record_failure(e, message)
            return False

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker should be open."""
        if not self._circuit_breaker_open:
            return False

        # Check if recovery timeout has passed
        if self._circuit_breaker_open_time:
            time_since_open = (
                datetime.now(timezone.utc) - self._circuit_breaker_open_time
            ).total_seconds()
            if time_since_open > self._recovery_timeout:
                logger.info(
                    "Circuit breaker recovery timeout reached - attempting reset"
                )
                self._reset_circuit_breaker()
                return False

        return True

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker."""
        self._circuit_breaker_open = False
        self._circuit_breaker_open_time = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        logger.info("Circuit breaker reset")

    def _open_circuit_breaker(self) -> None:
        """Open circuit breaker."""
        self._circuit_breaker_open = True
        self._circuit_breaker_open_time = datetime.now(timezone.utc)
        self._metrics.circuit_breaker_trips += 1
        logger.error(
            f"Circuit breaker opened after {self._consecutive_failures} consecutive failures"
        )

        # Start recovery task
        if not self._recovery_task or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._attempt_recovery())

    def _record_success(self, duration: float) -> None:
        """Record a successful broadcast."""
        self._metrics.successful_broadcasts += 1
        self._metrics.add_broadcast_time(duration)
        self._consecutive_successes += 1
        self._consecutive_failures = 0

        # Close circuit breaker if we've had enough successes
        if (
            self._circuit_breaker_open
            and self._consecutive_successes >= self._success_threshold
        ):
            self._reset_circuit_breaker()

        # Check for slow broadcast (potential backpressure)
        if duration > self._backpressure_threshold:
            self._handle_slow_broadcast(duration)

        self._metrics.update_success_rate()

    async def _record_failure(self, error: Exception, context: Dict[str, Any]) -> None:
        """Record a failed broadcast."""
        self._metrics.failed_broadcasts += 1
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        self._metrics.last_error_time = datetime.now(timezone.utc)

        # Classify error
        severity = self._classify_error(error)
        broadcast_error = BroadcastError(
            error=error,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            context=context,
        )

        self._metrics.recent_errors.append(broadcast_error)

        # Open circuit breaker if threshold reached
        if self._consecutive_failures >= self._failure_threshold:
            self._open_circuit_breaker()

        # Notify error handlers
        await self._notify_error_handlers(broadcast_error)

        self._metrics.update_error_rate()

        logger.error(f"Broadcast failed: {error} (severity: {severity.value})")

    def _classify_error(self, error: Exception) -> BroadcastErrorSeverity:
        """Classify error severity based on type and message."""
        error_str = str(error).lower()

        # Network-related errors
        if any(
            keyword in error_str for keyword in ["connection", "network", "timeout"]
        ):
            return BroadcastErrorSeverity.HIGH

        # Client-related errors
        if any(keyword in error_str for keyword in ["client", "websocket", "closed"]):
            return BroadcastErrorSeverity.MEDIUM

        # System errors
        if any(keyword in error_str for keyword in ["memory", "disk", "system"]):
            return BroadcastErrorSeverity.CRITICAL

        # Default to medium
        return BroadcastErrorSeverity.MEDIUM

    def _handle_slow_broadcast(self, duration: float) -> None:
        """Handle slow broadcast detection."""
        self._backpressure_detected = True
        self._metrics.backpressure_events += 1
        logger.warning(
            f"Slow broadcast detected: {duration:.3f}s (threshold: {self._backpressure_threshold}s)"
        )

    async def _handle_backpressure(self, message: Dict[str, Any]) -> None:
        """Handle backpressure situation."""
        try:
            # Try to wait for space in queue
            await asyncio.wait_for(self._broadcast_queue.put(message), timeout=1.0)
            logger.info("Backpressure handled - message queued")
        except asyncio.TimeoutError:
            logger.warning("Backpressure - message dropped due to full queue")

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)

    async def _backpressure_monitor_loop(self) -> None:
        """Monitor and resolve backpressure situations."""
        while self._running:
            try:
                await self._monitor_backpressure()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Backpressure monitor error: {e}")
                await asyncio.sleep(10)

    async def _perform_health_check(self) -> None:
        """Perform comprehensive health check."""
        current_time = datetime.now(timezone.utc)

        # Check if we haven't had successful broadcasts recently
        if (
            self._metrics.last_broadcast_time
            and (current_time - self._metrics.last_broadcast_time).total_seconds() > 120
        ):
            logger.warning("No successful broadcasts in last 2 minutes")

        # Update metrics
        self._metrics.update_success_rate()
        self._metrics.update_error_rate()

        # Log health status
        logger.debug(
            f"Broadcast health: {self._metrics.successful_broadcasts} successful, "
            f"{self._metrics.failed_broadcasts} failed, "
            f"success rate: {self._metrics.recent_success_rate:.1f}%"
        )

    async def _monitor_backpressure(self) -> None:
        """Monitor backpressure and attempt resolution."""
        if not self._backpressure_detected:
            return

        # Check if queue size is reducing
        queue_size = self._broadcast_queue.qsize()
        if queue_size < self._broadcast_queue.maxsize * 0.5:
            self._backpressure_detected = False
            logger.info("Backpressure resolved")

    async def _attempt_recovery(self) -> None:
        """Attempt to recover from circuit breaker state."""
        logger.info("Starting broadcast system recovery")

        for i, strategy in enumerate(self._recovery_strategies):
            try:
                logger.info(f"Attempting recovery strategy {i + 1}")
                await strategy()

                # Test recovery with a simple broadcast
                test_message = {
                    "type": "health_check",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test": True,
                }

                if await self.broadcast(test_message):
                    logger.info(f"Recovery successful with strategy {i + 1}")
                    self._metrics.recovery_events += 1
                    await self._notify_recovery_handlers(i + 1)
                    return

            except Exception as e:
                logger.warning(f"Recovery strategy {i + 1} failed: {e}")
                await asyncio.sleep(5)  # Wait before trying next strategy

        logger.error("All recovery strategies failed")

    async def _attempt_basic_recovery(self) -> None:
        """Basic recovery attempt."""
        logger.info("Attempting basic recovery")
        await asyncio.sleep(2)  # Brief pause

    async def _attempt_connection_recovery(self) -> None:
        """Connection recovery attempt."""
        logger.info("Attempting connection recovery")
        # Could be enhanced to reconnect WebSocket clients, etc.
        await asyncio.sleep(5)

    async def _attempt_full_reset(self) -> None:
        """Full system reset recovery attempt."""
        logger.info("Attempting full system reset")
        self._reset_circuit_breaker()
        self._backpressure_detected = False
        await asyncio.sleep(10)

    async def _notify_error_handlers(self, error: BroadcastError) -> None:
        """Notify all registered error handlers."""
        for handler in self._error_handlers:
            try:
                await handler(error)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")

    async def _notify_recovery_handlers(self, strategy_used: int) -> None:
        """Notify all registered recovery handlers."""
        for handler in self._recovery_handlers:
            try:
                await handler(strategy_used)
            except Exception as e:
                logger.error(f"Recovery handler failed: {e}")

    def add_error_handler(self, handler: Callable) -> None:
        """Add an error handler callback."""
        self._error_handlers.append(handler)

    def add_recovery_handler(self, handler: Callable) -> None:
        """Add a recovery handler callback."""
        self._recovery_handlers.append(handler)

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        return {
            "total_broadcasts": self._metrics.total_broadcasts,
            "successful_broadcasts": self._metrics.successful_broadcasts,
            "failed_broadcasts": self._metrics.failed_broadcasts,
            "success_rate": self._metrics.recent_success_rate,
            "error_rate": self._metrics.error_rate,
            "average_broadcast_time": self._metrics.average_broadcast_time,
            "max_broadcast_time": self._metrics.max_broadcast_time,
            "min_broadcast_time": (
                self._metrics.min_broadcast_time
                if self._metrics.min_broadcast_time != float("inf")
                else 0
            ),
            "circuit_breaker_trips": self._metrics.circuit_breaker_trips,
            "backpressure_events": self._metrics.backpressure_events,
            "recovery_events": self._metrics.recovery_events,
            "circuit_breaker_open": self._circuit_breaker_open,
            "backpressure_detected": self._backpressure_detected,
            "last_broadcast_time": (
                self._metrics.last_broadcast_time.isoformat()
                if self._metrics.last_broadcast_time
                else None
            ),
            "last_error_time": (
                self._metrics.last_error_time.isoformat()
                if self._metrics.last_error_time
                else None
            ),
            "queue_size": self._broadcast_queue.qsize(),
            "recent_errors": len(self._metrics.recent_errors),
        }
