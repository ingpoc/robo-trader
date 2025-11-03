"""
Queue Event Coordinator

Focused coordinator for queue event routing and handlers.
Extracted from QueueCoordinator for single responsibility.
"""

import logging
from typing import Dict, List, Optional, Any

from src.config import Config
from ...event_bus import EventBus, Event, EventType
from src.services.event_router_service import EventRouterService
from ..base_coordinator import BaseCoordinator

logger = logging.getLogger(__name__)


class QueueEventCoordinator(BaseCoordinator):
    """
    Coordinates queue event routing and handlers.
    
    Responsibilities:
    - Handle event routing
    - Manage event handlers
    - Process queue-related events
    """

    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        event_router_service: Optional[EventRouterService] = None
    ):
        super().__init__(config)
        self.event_bus = event_bus
        self.event_router_service = event_router_service

    async def initialize(self) -> None:
        """Initialize queue event coordinator."""
        self._log_info("Initializing QueueEventCoordinator")

        # Subscribe to relevant events
        if self.event_bus:
            self.event_bus.subscribe(EventType.MARKET_NEWS, self._handle_market_event)
            self.event_bus.subscribe(EventType.MARKET_EARNINGS, self._handle_earnings_event)

        # Start event router service
        if self.event_router_service:
            await self.event_router_service.start()

        self._initialized = True
        self._log_info("QueueEventCoordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup queue event coordinator resources."""
        if self.event_router_service:
            await self.event_router_service.stop()

        # Unsubscribe from events
        if self.event_bus:
            self.event_bus.unsubscribe(EventType.MARKET_NEWS)
            self.event_bus.unsubscribe(EventType.MARKET_EARNINGS)

        self._log_info("QueueEventCoordinator cleanup complete")

    async def trigger_event_routing(self, event: Event) -> List[Dict[str, Any]]:
        """Manually trigger event routing for testing."""
        if not self.event_router_service:
            raise TradingError(
                "Event router service not available",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=False
            )

        try:
            return await self.event_router_service.handle_event(event)

        except Exception as e:
            self._log_error(f"Event routing failed: {e}")
            raise TradingError(
                f"Event routing failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def _handle_market_event(self, event: Event) -> None:
        """Handle market news events."""
        try:
            symbol = event.data.get("symbol")
            impact_score = event.data.get("impact_score", 0)

            self._log_info(f"Market event for {symbol}: impact_score={impact_score}")

            # Trigger event routing for high-impact events
            if impact_score > 0.7 and self.event_router_service:
                triggered_actions = await self.event_router_service.handle_event(event)
                if triggered_actions:
                    self._log_info(f"Triggered {len(triggered_actions)} actions from market event")

        except Exception as e:
            self._log_error(f"Error handling market event: {e}")

    async def _handle_earnings_event(self, event: Event) -> None:
        """Handle earnings announcement events."""
        try:
            symbol = event.data.get("symbol")
            self._log_info(f"Earnings event for {symbol}")

            # Trigger event routing
            if self.event_router_service:
                triggered_actions = await self.event_router_service.handle_event(event)
                if triggered_actions:
                    self._log_info(f"Triggered {len(triggered_actions)} actions from earnings event")

        except Exception as e:
            self._log_error(f"Error handling earnings event: {e}")

    def set_event_router_service(self, service: EventRouterService) -> None:
        """Set event router service."""
        self.event_router_service = service

    def get_event_router_status(self) -> str:
        """Get event router status."""
        if self.event_router_service:
            status = self.event_router_service.get_status()
            return "healthy" if status.get("running") else "stopped"
        return "not_available"

