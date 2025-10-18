"""
Event handling service for Background Scheduler.

Routes and dispatches events to registered handlers.
"""

from typing import Dict, Callable, List, Any, Optional
from loguru import logger


class EventHandler:
    """Manages event routing and handler registration."""

    VALID_EVENTS = {
        "earnings_announced",
        "stop_loss_triggered",
        "price_movement",
        "news_alert",
        "market_open",
        "market_close"
    }

    def __init__(self):
        """Initialize event handler."""
        self._handlers: Dict[str, List[Callable]] = {event: [] for event in self.VALID_EVENTS}

    def register_handler(self, event_type: str, handler: Callable) -> bool:
        """Register a handler for an event type.

        Args:
            event_type: Type of event to handle
            handler: Async callable(event_data: Dict) -> None

        Returns:
            True if registered successfully, False if invalid event type
        """
        if event_type not in self.VALID_EVENTS:
            logger.warning(f"Unknown event type: {event_type}")
            return False

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.info(f"Registered handler for event: {event_type}")
            return True

        return False

    def unregister_handler(self, event_type: str, handler: Callable) -> bool:
        """Unregister a handler from an event type.

        Args:
            event_type: Type of event
            handler: Handler to unregister

        Returns:
            True if unregistered, False if handler not found
        """
        if event_type not in self.VALID_EVENTS:
            return False

        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.info(f"Unregistered handler for event: {event_type}")
            return True

        return False

    async def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger an event and invoke all registered handlers.

        Args:
            event_type: Type of event to trigger
            event_data: Event data to pass to handlers
        """
        logger.info(f"Event triggered: {event_type} - {event_data}")

        if event_type not in self.VALID_EVENTS:
            logger.warning(f"Unknown event type: {event_type}")
            return

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug(f"No handlers registered for event: {event_type}")
            return

        for handler in handlers:
            try:
                if hasattr(handler, '__call__'):
                    result = handler(event_data)
                    if hasattr(result, '__await__'):
                        await result
            except Exception as e:
                logger.error(f"Error invoking handler for {event_type}: {e}")

    def get_registered_events(self) -> Dict[str, int]:
        """Get list of registered events and handler counts.

        Returns:
            Dictionary with event types and their handler counts
        """
        return {event: len(handlers) for event, handlers in self._handlers.items()}

    def get_handlers_for_event(self, event_type: str) -> List[Callable]:
        """Get all handlers registered for an event type.

        Args:
            event_type: Type of event

        Returns:
            List of handlers for the event
        """
        return self._handlers.get(event_type, []).copy()

    def clear_handlers(self, event_type: Optional[str] = None) -> None:
        """Clear all handlers for an event type, or all events.

        Args:
            event_type: Event type to clear, or None to clear all
        """
        if event_type is None:
            for event in self._handlers:
                self._handlers[event].clear()
            logger.info("Cleared all event handlers")
        elif event_type in self.VALID_EVENTS:
            self._handlers[event_type].clear()
            logger.info(f"Cleared handlers for event: {event_type}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get event handler statistics.

        Returns:
            Statistics dictionary
        """
        total_handlers = sum(len(handlers) for handlers in self._handlers.values())
        events_with_handlers = sum(1 for handlers in self._handlers.values() if handlers)

        return {
            "total_handlers": total_handlers,
            "events_with_handlers": events_with_handlers,
            "total_events": len(self.VALID_EVENTS),
            "handlers_per_event": self.get_registered_events()
        }
