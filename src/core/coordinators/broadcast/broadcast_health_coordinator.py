"""
Broadcast Health Coordinator

Focused coordinator for broadcast health monitoring.
Extracted from BroadcastCoordinator for single responsibility.
"""

import time
from typing import Any, Dict


from src.config import Config

from ..base_coordinator import BaseCoordinator

try:
    from src.web.broadcast_health_monitor import BroadcastErrorSeverity

    HEALTH_MONITOR_AVAILABLE = True
except ImportError:
    HEALTH_MONITOR_AVAILABLE = False

    class BroadcastErrorSeverity:
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"


class BroadcastHealthCoordinator(BaseCoordinator):
    """
    Coordinates broadcast health monitoring.

    Responsibilities:
    - Circuit breaker management
    - Health metrics tracking
    - Error and recovery handling
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self._circuit_breaker_state = {
            "is_open": False,
            "failure_count": 0,
            "last_failure_time": None,
            "success_count": 0,
        }
        self._health_metrics = {
            "total_broadcasts": 0,
            "successful_broadcasts": 0,
            "failed_broadcasts": 0,
            "circuit_breaker_trips": 0,
            "average_broadcast_time": 0.0,
            "last_broadcast_time": None,
            "last_error": None,
        }
        self._failure_threshold = 5  # Open circuit after 5 failures
        self._recovery_timeout = 60  # Wait 60 seconds before trying again
        self._broadcast_times = []  # Keep last 100 broadcast times for averaging

    async def initialize(self) -> None:
        """Initialize broadcast health coordinator."""
        self._log_info("Initializing BroadcastHealthCoordinator")
        self._initialized = True

    def is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker should be open."""
        if not self._circuit_breaker_state["is_open"]:
            return False

        # Check if recovery timeout has passed
        if self._circuit_breaker_state["last_failure_time"]:
            time_since_failure = (
                time.time() - self._circuit_breaker_state["last_failure_time"]
            )
            if time_since_failure > self._recovery_timeout:
                self._log_info(
                    "Circuit breaker recovery timeout reached - attempting reset"
                )
                self.reset_circuit_breaker()
                return False

        return True

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after recovery."""
        self._circuit_breaker_state["is_open"] = False
        self._circuit_breaker_state["failure_count"] = 0
        self._circuit_breaker_state["success_count"] = 0
        self._log_info("Circuit breaker reset")

    def record_broadcast_success(self, broadcast_time: float) -> None:
        """Record successful broadcast metrics."""
        self._health_metrics["total_broadcasts"] += 1
        self._health_metrics["successful_broadcasts"] += 1
        self._health_metrics["last_broadcast_time"] = broadcast_time

        # Update average broadcast time
        self._broadcast_times.append(broadcast_time)
        if len(self._broadcast_times) > 100:
            self._broadcast_times.pop(0)
        self._health_metrics["average_broadcast_time"] = sum(
            self._broadcast_times
        ) / len(self._broadcast_times)

        # Reset circuit breaker on success
        if self._circuit_breaker_state["is_open"]:
            self._circuit_breaker_state["success_count"] += 1
            if (
                self._circuit_breaker_state["success_count"] >= 3
            ):  # 3 successes to close
                self.reset_circuit_breaker()

    def record_broadcast_failure(self, error: Exception) -> None:
        """Record failed broadcast metrics."""
        self._health_metrics["total_broadcasts"] += 1
        self._health_metrics["failed_broadcasts"] += 1
        self._health_metrics["last_error"] = str(error)
        self._circuit_breaker_state["failure_count"] += 1
        self._circuit_breaker_state["last_failure_time"] = time.time()

        # Open circuit breaker if threshold reached
        if (
            self._circuit_breaker_state["failure_count"] >= self._failure_threshold
            and not self._circuit_breaker_state["is_open"]
        ):
            self._circuit_breaker_state["is_open"] = True
            self._health_metrics["circuit_breaker_trips"] += 1
            self._log_error(
                f"Circuit breaker opened after {self._failure_threshold} failures"
            )

    async def handle_broadcast_error(self, error) -> None:
        """Handle broadcast errors from health monitor."""
        if hasattr(error, "severity"):
            severity = (
                error.severity.value
                if hasattr(error.severity, "value")
                else str(error.severity)
            )
            self._log_error(f"Broadcast error (severity: {severity}): {error.error}")
        else:
            self._log_error(f"Broadcast error: {error}")

        # Update legacy metrics for compatibility
        error_obj = error.error if hasattr(error, "error") else error
        self.record_broadcast_failure(error_obj)

        # Could trigger additional error handling here
        if (
            hasattr(error, "severity")
            and error.severity == BroadcastErrorSeverity.CRITICAL
        ):
            self._log_error(
                "Critical broadcast error detected - system may need intervention"
            )

    async def handle_broadcast_recovery(self, strategy_used: int) -> None:
        """Handle successful recovery from health monitor."""
        self._log_info(f"Broadcast system recovered using strategy {strategy_used}")

        # Reset legacy circuit breaker state
        self.reset_circuit_breaker()

    def get_health_metrics(
        self, monitor_metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        if monitor_metrics:
            # Get detailed metrics from health monitor
            return {
                **monitor_metrics,
                "legacy_metrics": self._health_metrics,
                "circuit_breaker_state": self._circuit_breaker_state,
                "health_monitor_enabled": True,
            }
        else:
            # Fallback to legacy metrics
            return {
                **self._health_metrics,
                "circuit_breaker_state": self._circuit_breaker_state,
                "success_rate": (
                    self._health_metrics["successful_broadcasts"]
                    / max(self._health_metrics["total_broadcasts"], 1)
                    * 100
                ),
                "health_monitor_enabled": False,
            }

    async def cleanup(self) -> None:
        """Cleanup broadcast health coordinator resources."""
        self._log_info("BroadcastHealthCoordinator cleanup complete")
