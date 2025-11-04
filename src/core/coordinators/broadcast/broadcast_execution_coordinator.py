"""
Broadcast Execution Coordinator

Focused coordinator for broadcast execution.
Extracted from BroadcastCoordinator for single responsibility.
"""

import time
from typing import Dict, Any, Optional, Callable

from loguru import logger

from src.config import Config
from ..base_coordinator import BaseCoordinator

try:
    from ..web.broadcast_health_monitor import BroadcastHealthMonitor, BroadcastError, BroadcastErrorSeverity
    HEALTH_MONITOR_AVAILABLE = True
except ImportError:
    HEALTH_MONITOR_AVAILABLE = False
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


class BroadcastExecutionCoordinator(BaseCoordinator):
    """
    Coordinates broadcast execution.
    
    Responsibilities:
    - Execute broadcasts to WebSocket clients
    - Handle health monitor integration
    - Manage broadcast callbacks
    """

    def __init__(self, config: Config, health_coordinator=None):
        super().__init__(config)
        self._broadcast_callback: Optional[Callable] = None
        self._health_coordinator = health_coordinator

        # Health monitor integration
        self._health_monitor = None
        if HEALTH_MONITOR_AVAILABLE:
            self._health_monitor = BroadcastHealthMonitor(
                broadcast_callback=self._internal_broadcast_callback,
                config={
                    'failure_threshold': 5,
                    'recovery_timeout': 60,
                    'backpressure_threshold': 2.0,
                    'health_check_interval': 30
                }
            )
            # Set up error and recovery handlers
            if health_coordinator:
                self._health_monitor.add_error_handler(health_coordinator.handle_broadcast_error)
                self._health_monitor.add_recovery_handler(health_coordinator.handle_broadcast_recovery)

    async def initialize(self) -> None:
        """Initialize broadcast execution coordinator."""
        self._log_info("Initializing BroadcastExecutionCoordinator")

        # Start health monitor if available
        if self._health_monitor:
            await self._health_monitor.start()
            self._log_info("Broadcast health monitor started")

        self._initialized = True

    def set_broadcast_callback(self, callback: Callable) -> None:
        """Set the broadcast callback function."""
        self._broadcast_callback = callback
        self._log_info("Broadcast callback registered")

    def set_health_coordinator(self, health_coordinator) -> None:
        """Set health coordinator."""
        self._health_coordinator = health_coordinator
        if self._health_monitor and health_coordinator:
            self._health_monitor.add_error_handler(health_coordinator.handle_broadcast_error)
            self._health_monitor.add_recovery_handler(health_coordinator.handle_broadcast_recovery)

    async def broadcast_to_ui(self, message: Dict[str, Any], circuit_breaker_check=None) -> bool:
        """
        Broadcast message to all connected WebSocket clients.

        Args:
            message: Message dict to broadcast
            circuit_breaker_check: Optional circuit breaker check function

        Returns:
            bool: True if broadcast was successful, False otherwise
        """
        # Use health monitor if available
        if self._health_monitor:
            return await self._health_monitor.broadcast(message)

        # Fallback to basic broadcasting
        return await self._basic_broadcast(message, circuit_breaker_check)

    async def _basic_broadcast(self, message: Dict[str, Any], circuit_breaker_check=None) -> bool:
        """Basic broadcast implementation without health monitoring."""
        # Check circuit breaker
        if circuit_breaker_check and circuit_breaker_check():
            self._log_warning("Circuit breaker is open - broadcast blocked")
            return False

        if not self._broadcast_callback:
            self._log_warning("Broadcast callback not set - message not sent")
            return False

        message_type = message.get('type', 'unknown')
        start_time = time.time()

        try:
            await self._broadcast_callback(message)

            # Record success
            broadcast_time = time.time() - start_time
            self._log_info(f"UI Broadcast: {message_type} ({broadcast_time:.3f}s)")

            return True

        except Exception as e:
            self._log_error(f"Failed to broadcast message: {e}", exc_info=True)
            return False

    async def _internal_broadcast_callback(self, message: Dict[str, Any]) -> None:
        """Internal callback for health monitor to use."""
        if self._broadcast_callback:
            await self._broadcast_callback(message)

    async def cleanup(self) -> None:
        """Cleanup broadcast execution coordinator resources."""
        # Stop health monitor
        if self._health_monitor:
            await self._health_monitor.stop()
            self._log_info("Health monitor stopped")

        self._broadcast_callback = None
        self._log_info("BroadcastExecutionCoordinator cleanup complete")

