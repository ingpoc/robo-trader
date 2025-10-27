"""
Broadcast Coordinator

Manages broadcasting messages to WebSocket clients.
Extracted from RoboTraderOrchestrator lines 592-594.
"""

from typing import Dict, Any, Optional, Callable

from loguru import logger

from src.config import Config
from .base_coordinator import BaseCoordinator

try:
    from ..web.broadcast_health_monitor import BroadcastHealthMonitor, BroadcastError, BroadcastErrorSeverity
    HEALTH_MONITOR_AVAILABLE = True
except ImportError:
    HEALTH_MONITOR_AVAILABLE = False
    # Define fallback types when import fails
    class BroadcastError:
        def __init__(self, error: Exception, severity: str = "medium"):
            self.error = error
            self.severity = severity

    class BroadcastErrorSeverity:
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    logger.warning("BroadcastHealthMonitor not available - using basic error handling")


class BroadcastCoordinator(BaseCoordinator):
    """
    Coordinates UI broadcasting with health monitoring.

    Responsibilities:
    - Broadcast messages to WebSocket clients
    - Track broadcast callback and health metrics
    - Implement circuit breaker for failed broadcasts
    - Monitor broadcast performance
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self._broadcast_callback: Optional[Callable] = None
        self._circuit_breaker_state = {
            "is_open": False,
            "failure_count": 0,
            "last_failure_time": None,
            "success_count": 0
        }
        self._health_metrics = {
            "total_broadcasts": 0,
            "successful_broadcasts": 0,
            "failed_broadcasts": 0,
            "circuit_breaker_trips": 0,
            "average_broadcast_time": 0.0,
            "last_broadcast_time": None,
            "last_error": None
        }
        self._failure_threshold = 5  # Open circuit after 5 failures
        self._recovery_timeout = 60  # Wait 60 seconds before trying again
        self._broadcast_times = []  # Keep last 100 broadcast times for averaging

        # Health monitor integration
        self._health_monitor = None
        if HEALTH_MONITOR_AVAILABLE:
            self._health_monitor = BroadcastHealthMonitor(
                broadcast_callback=self._internal_broadcast_callback,
                config={
                    'failure_threshold': self._failure_threshold,
                    'recovery_timeout': self._recovery_timeout,
                    'backpressure_threshold': 2.0,
                    'health_check_interval': 30
                }
            )
            # Set up error and recovery handlers
            self._health_monitor.add_error_handler(self._handle_broadcast_error)
            self._health_monitor.add_recovery_handler(self._handle_broadcast_recovery)

    async def initialize(self) -> None:
        """Initialize broadcast coordinator."""
        self._log_info("Initializing BroadcastCoordinator")

        # Start health monitor if available
        if self._health_monitor:
            await self._health_monitor.start()
            self._log_info("Broadcast health monitor started")

        self._initialized = True

    def set_broadcast_callback(self, callback: Callable) -> None:
        """
        Set the broadcast callback function.

        Args:
            callback: Async function to call for broadcasting
        """
        self._broadcast_callback = callback
        self._log_info("Broadcast callback registered")

    async def broadcast_to_ui(self, message: Dict[str, Any]) -> bool:
        """
        Broadcast message to all connected WebSocket clients with comprehensive health monitoring.

        Args:
            message: Message dict to broadcast

        Returns:
            bool: True if broadcast was successful, False otherwise
        """
        # Use health monitor if available
        if self._health_monitor:
            return await self._health_monitor.broadcast(message)

        # Fallback to basic broadcasting
        return await self._basic_broadcast(message)

    async def _basic_broadcast(self, message: Dict[str, Any]) -> bool:
        """Basic broadcast implementation without health monitoring."""
        from datetime import datetime, timezone
        import time

        # Check circuit breaker
        if self._is_circuit_breaker_open():
            self._log_warning("Circuit breaker is open - broadcast blocked")
            return False

        if not self._broadcast_callback:
            self._log_warning("Broadcast callback not set - message not sent")
            return False

        message_type = message.get('type', 'unknown')
        start_time = time.time()

        try:
            self._health_metrics["total_broadcasts"] += 1
            await self._broadcast_callback(message)

            # Record success
            broadcast_time = time.time() - start_time
            self._record_broadcast_success(broadcast_time)
            self._log_info(f"UI Broadcast: {message_type} ({broadcast_time:.3f}s)")

            return True

        except Exception as e:
            self._record_broadcast_failure(e)
            self._log_error(f"Failed to broadcast message: {e}", exc_info=True)
            return False

    async def _internal_broadcast_callback(self, message: Dict[str, Any]) -> None:
        """Internal callback for health monitor to use."""
        if self._broadcast_callback:
            await self._broadcast_callback(message)

    async def broadcast_claude_status_update(self, status_data: Dict[str, Any]) -> None:
        """
        Broadcast Claude SDK status updates to UI.

        Args:
            status_data: Claude status information from session coordinator
        """
        message = {
            "type": "claude_status_update",
            "status": status_data.get("status", "unknown"),
            "auth_method": status_data.get("auth_method"),
            "sdk_connected": status_data.get("sdk_connected", False),
            "cli_process_running": status_data.get("cli_process_running", False),
            "timestamp": status_data.get("timestamp"),
            "data": status_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"Claude status broadcast: {status_data.get('status', 'unknown')}")

    async def broadcast_system_health_update(self, health_data: Dict[str, Any]) -> None:
        """
        Broadcast system health updates to UI.

        Args:
            health_data: System health information
        """
        message = {
            "type": "system_health_update",
            "components": health_data.get("components", {}),
            "status": health_data.get("status", "unknown"),
            "timestamp": health_data.get("timestamp"),
            "data": health_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"System health broadcast: {health_data.get('status', 'unknown')}")

    async def broadcast_queue_status_update(self, queue_data: Dict[str, Any]) -> None:
        """
        Broadcast queue status updates to UI.

        Args:
            queue_data: Queue status information
        """
        message = {
            "type": "queue_status_update",
            "queues": queue_data.get("queues", {}),
            "stats": queue_data.get("stats", {}),
            "timestamp": queue_data.get("timestamp"),
            "data": queue_data
        }

        await self.broadcast_to_ui(message)
        self._log_info(f"Queue status broadcast: {len(queue_data.get('queues', {}))} queues")

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker should be open."""
        from datetime import datetime, timezone
        import time

        if not self._circuit_breaker_state["is_open"]:
            return False

        # Check if recovery timeout has passed
        if self._circuit_breaker_state["last_failure_time"]:
            time_since_failure = time.time() - self._circuit_breaker_state["last_failure_time"]
            if time_since_failure > self._recovery_timeout:
                self._log_info("Circuit breaker recovery timeout reached - attempting reset")
                self._reset_circuit_breaker()
                return False

        return True

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after recovery."""
        self._circuit_breaker_state["is_open"] = False
        self._circuit_breaker_state["failure_count"] = 0
        self._circuit_breaker_state["success_count"] = 0
        self._log_info("Circuit breaker reset")

    def _record_broadcast_success(self, broadcast_time: float) -> None:
        """Record successful broadcast metrics."""
        self._health_metrics["successful_broadcasts"] += 1
        self._health_metrics["last_broadcast_time"] = broadcast_time

        # Update average broadcast time
        self._broadcast_times.append(broadcast_time)
        if len(self._broadcast_times) > 100:
            self._broadcast_times.pop(0)
        self._health_metrics["average_broadcast_time"] = sum(self._broadcast_times) / len(self._broadcast_times)

        # Reset circuit breaker on success
        if self._circuit_breaker_state["is_open"]:
            self._circuit_breaker_state["success_count"] += 1
            if self._circuit_breaker_state["success_count"] >= 3:  # 3 successes to close
                self._reset_circuit_breaker()

    def _record_broadcast_failure(self, error: Exception) -> None:
        """Record failed broadcast metrics."""
        import time

        self._health_metrics["failed_broadcasts"] += 1
        self._health_metrics["last_error"] = str(error)
        self._circuit_breaker_state["failure_count"] += 1
        self._circuit_breaker_state["last_failure_time"] = time.time()

        # Open circuit breaker if threshold reached
        if (self._circuit_breaker_state["failure_count"] >= self._failure_threshold and
            not self._circuit_breaker_state["is_open"]):
            self._circuit_breaker_state["is_open"] = True
            self._health_metrics["circuit_breaker_trips"] += 1
            self._log_error(f"Circuit breaker opened after {self._failure_threshold} failures")

    async def _handle_broadcast_error(self, error: BroadcastError) -> None:
        """Handle broadcast errors from health monitor."""
        self._log_error(f"Broadcast error (severity: {error.severity.value}): {error.error}")

        # Update legacy metrics for compatibility
        self._health_metrics["failed_broadcasts"] += 1
        self._health_metrics["last_error"] = str(error.error)

        # Could trigger additional error handling here
        if error.severity == BroadcastErrorSeverity.CRITICAL:
            self._log_error("Critical broadcast error detected - system may need intervention")

    async def _handle_broadcast_recovery(self, strategy_used: int) -> None:
        """Handle successful recovery from health monitor."""
        self._log_info(f"Broadcast system recovered using strategy {strategy_used}")

        # Reset legacy circuit breaker state
        self._reset_circuit_breaker()

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        if self._health_monitor:
            # Get detailed metrics from health monitor
            monitor_metrics = self._health_monitor.get_health_metrics()
            return {
                **monitor_metrics,
                "legacy_metrics": self._health_metrics,
                "circuit_breaker_state": self._circuit_breaker_state,
                "health_monitor_enabled": True
            }
        else:
            # Fallback to legacy metrics
            return {
                **self._health_metrics,
                "circuit_breaker_state": self._circuit_breaker_state,
                "success_rate": (
                    self._health_metrics["successful_broadcasts"] /
                    max(self._health_metrics["total_broadcasts"], 1) * 100
                ),
                "health_monitor_enabled": False
            }

    async def cleanup(self) -> None:
        """Cleanup broadcast coordinator resources."""
        self._log_info("Cleaning up BroadcastCoordinator")

        # Stop health monitor
        if self._health_monitor:
            await self._health_monitor.stop()
            self._log_info("Health monitor stopped")

        self._broadcast_callback = None
        self._log_info(f"BroadcastCoordinator cleanup complete. Final metrics: {self.get_health_metrics()}")
