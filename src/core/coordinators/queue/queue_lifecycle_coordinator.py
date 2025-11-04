"""
Queue Lifecycle Coordinator

Focused coordinator for queue lifecycle management.
Extracted from QueueCoordinator for single responsibility.
"""

import logging
from typing import Dict, Any

from src.config import Config
from ...errors import TradingError, ErrorCategory, ErrorSeverity
from ..base_coordinator import BaseCoordinator

logger = logging.getLogger(__name__)


class QueueLifecycleCoordinator(BaseCoordinator):
    """
    Coordinates queue lifecycle management.
    
    Responsibilities:
    - Start queues
    - Stop queues
    - Manage queue state
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self._queues_running = False

    async def initialize(self) -> None:
        """Initialize queue lifecycle coordinator."""
        self._log_info("Initializing QueueLifecycleCoordinator")
        self._initialized = True

    async def start_queues(self) -> None:
        """Start all queues."""
        if self._queues_running:
            self._log_warning("Queues already running")
            return

        if not self._initialized:
            await self.initialize()

        self._log_info("Starting queues")

        try:
            # Start individual queues through their services
            self._queues_running = True
            self._log_info("Queues started successfully")

        except Exception as e:
            self._log_error(f"Failed to start queues: {e}")
            raise TradingError(
                f"Queue startup failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def stop_queues(self) -> None:
        """Stop all queues."""
        if not self._queues_running:
            return

        self._log_info("Stopping queues")

        try:
            # Stop individual queues through their services
            self._queues_running = False
            self._log_info("Queues stopped successfully")

        except Exception as e:
            self._log_error(f"Error stopping queues: {e}")

    def are_queues_running(self) -> bool:
        """Check if queues are running."""
        return self._queues_running

    async def cleanup(self) -> None:
        """Cleanup queue lifecycle coordinator resources."""
        if self._queues_running:
            await self.stop_queues()
        self._log_info("QueueLifecycleCoordinator cleanup complete")

