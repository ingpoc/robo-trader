"""
Lifecycle Coordinator

Manages emergency stop/resume and autonomous operation control.
Extracted from RoboTraderOrchestrator lines 424-445.
"""


from src.config import Config

from ...background_scheduler import BackgroundScheduler
from ..base_coordinator import BaseCoordinator


class LifecycleCoordinator(BaseCoordinator):
    """
    Coordinates system lifecycle operations.

    Responsibilities:
    - Emergency stop all operations
    - Resume autonomous operations
    - Trigger market events
    """

    def __init__(self, config: Config, background_scheduler: BackgroundScheduler):
        super().__init__(config)
        self.background_scheduler = background_scheduler

    async def initialize(self) -> None:
        """Initialize lifecycle coordinator."""
        self._log_info("Initializing LifecycleCoordinator")
        self._initialized = True

    async def emergency_stop(self) -> None:
        """Emergency stop all autonomous operations."""
        self._log_warning("Emergency stop triggered - halting all operations")

        await self.background_scheduler.stop()

    async def resume_operations(self) -> None:
        """Resume autonomous operations after emergency stop."""
        self._log_info("Resuming autonomous operations")

        await self.background_scheduler.start()

    async def trigger_market_event(self, event_type: str, event_data: dict) -> None:
        """Trigger market event for autonomous response."""
        await self.background_scheduler.trigger_event(event_type, event_data)

    async def cleanup(self) -> None:
        """Cleanup lifecycle coordinator resources."""
        self._log_info("LifecycleCoordinator cleanup complete")
