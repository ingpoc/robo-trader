"""
Event Router Service

Standalone service for managing event routing configuration with database persistence.
Extracted from core/queues/event_router.py to follow service layer patterns.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from ..core.event_bus import Event, EventType
from ..models.scheduler import QueueName, TaskType
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
from ..core.di import DependencyContainer

logger = logging.getLogger(__name__)


@dataclass
class EventTrigger:
    """Represents an event trigger configuration."""
    trigger_id: str
    source_queue: QueueName
    target_queue: QueueName
    event_type: EventType
    condition: Dict[str, Any]
    is_active: bool = True
    priority: int = 5
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EventRouterService:
    """
    Service for managing event routing between queues.

    Responsibilities:
    - Database persistence of event triggers
    - Dynamic trigger configuration
    - Event routing logic
    - Trigger validation and management
    """

    def __init__(self, container: DependencyContainer):
        """Initialize event router service."""
        self.container = container
        self._triggers: Dict[str, EventTrigger] = {}
        self._running = False
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize service and load triggers from database."""
        if self._initialized:
            return

        self._log_info("Initializing EventRouterService")
        await self._load_triggers_from_db()
        self._initialized = True

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        if not self._initialized:
            return

        self._log_info("Cleaning up EventRouterService")
        self._triggers.clear()
        self._event_handlers.clear()
        self._running = False

    async def start(self) -> None:
        """Start the event router."""
        if self._running:
            return

        if not self._initialized:
            await self.initialize()

        self._running = True
        self._log_info("EventRouterService started")

    async def stop(self) -> None:
        """Stop the event router."""
        self._running = False
        self._log_info("EventRouterService stopped")

    async def register_trigger(
        self,
        source_queue: QueueName,
        target_queue: QueueName,
        event_type: EventType,
        condition: Dict[str, Any],
        trigger_id: Optional[str] = None,
        priority: int = 5
    ) -> str:
        """Register a new event trigger and persist to database."""
        if trigger_id is None:
            trigger_id = f"{source_queue.value}_{target_queue.value}_{event_type.value}"

        # Validate trigger doesn't already exist
        if trigger_id in self._triggers:
            raise TradingError(
                f"Trigger {trigger_id} already exists",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

        trigger = EventTrigger(
            trigger_id=trigger_id,
            source_queue=source_queue,
            target_queue=target_queue,
            event_type=event_type,
            condition=condition,
            priority=priority
        )

        # Persist to database
        await self._persist_trigger(trigger)
        self._triggers[trigger_id] = trigger

        self._log_info(f"Registered event trigger: {trigger_id}")
        return trigger_id

    async def unregister_trigger(self, trigger_id: str) -> None:
        """Unregister an event trigger and remove from database."""
        if trigger_id not in self._triggers:
            raise TradingError(
                f"Trigger {trigger_id} not found",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                recoverable=True
            )

        # Remove from database
        await self._delete_trigger(trigger_id)
        del self._triggers[trigger_id]

        self._log_info(f"Unregistered event trigger: {trigger_id}")

    async def update_trigger_condition(self, trigger_id: str, condition: Dict[str, Any]) -> None:
        """Update trigger condition."""
        if trigger_id not in self._triggers:
            raise TradingError(
                f"Trigger {trigger_id} not found",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                recoverable=True
            )

        trigger = self._triggers[trigger_id]
        trigger.condition = condition

        # Update in database
        await self._update_trigger(trigger)

        self._log_info(f"Updated trigger condition: {trigger_id}")

    async def set_trigger_active(self, trigger_id: str, is_active: bool) -> None:
        """Enable or disable a trigger."""
        if trigger_id not in self._triggers:
            raise TradingError(
                f"Trigger {trigger_id} not found",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                recoverable=True
            )

        trigger = self._triggers[trigger_id]
        trigger.is_active = is_active

        # Update in database
        await self._update_trigger(trigger)

        self._log_info(f"Set trigger {trigger_id} active: {is_active}")

    async def handle_event(self, event: Event) -> List[Dict[str, Any]]:
        """Handle an incoming event and return triggered actions."""
        if not self._running:
            return []

        self._log_debug(f"Handling event: {event.event_type.value}")

        # Find matching triggers
        matching_triggers = self._find_matching_triggers(event)

        triggered_actions = []
        for trigger in matching_triggers:
            try:
                action = await self._execute_trigger(trigger, event)
                if action:
                    triggered_actions.append(action)
            except Exception as e:
                self._log_error(f"Error executing trigger {trigger.trigger_id}: {e}")

        return triggered_actions

    def _find_matching_triggers(self, event: Event) -> List[EventTrigger]:
        """Find triggers that match the given event."""
        matching = []

        for trigger in self._triggers.values():
            if not trigger.is_active:
                continue

            if trigger.event_type != event.event_type:
                continue

            # Check condition matching
            if self._matches_condition(trigger.condition, event.data):
                matching.append(trigger)

        # Sort by priority (highest first)
        matching.sort(key=lambda t: t.priority, reverse=True)
        return matching

    def _matches_condition(self, condition: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if event data matches the trigger condition."""
        for key, expected_value in condition.items():
            if key not in event_data:
                return False

            actual_value = event_data[key]

            # Handle special operators
            if isinstance(expected_value, str) and expected_value.startswith(">"):
                try:
                    threshold = float(expected_value[1:])
                    if not isinstance(actual_value, (int, float)) or actual_value <= threshold:
                        return False
                except ValueError:
                    return False
            elif isinstance(expected_value, str) and expected_value.startswith("<"):
                try:
                    threshold = float(expected_value[1:])
                    if not isinstance(actual_value, (int, float)) or actual_value >= threshold:
                        return False
                except ValueError:
                    return False
            elif isinstance(expected_value, list):
                # Check if actual value is in the list
                if actual_value not in expected_value:
                    return False
            elif expected_value == "all":
                # Special case: always match
                continue
            else:
                # Exact match
                if actual_value != expected_value:
                    return False

        return True

    async def _execute_trigger(self, trigger: EventTrigger, event: Event) -> Optional[Dict[str, Any]]:
        """Execute a trigger based on the event."""
        self._log_info(f"Executing trigger: {trigger.trigger_id} for event {event.event_type.value}")

        # Create appropriate task payload based on trigger and event
        task_payload = self._build_task_payload(trigger, event)

        if task_payload:
            action = {
                "trigger_id": trigger.trigger_id,
                "target_queue": trigger.target_queue.value,
                "task_type": self._determine_task_type(trigger, event).value,
                "payload": task_payload,
                "priority": trigger.priority
            }

            self._log_info(f"Created triggered action: {action}")
            return action

        return None

    def _build_task_payload(self, trigger: EventTrigger, event: Event) -> Optional[Dict[str, Any]]:
        """Build task payload based on trigger and event."""
        base_payload = {
            "triggered_by": trigger.trigger_id,
            "event_type": event.event_type.value,
            "event_data": event.data,
            "source_queue": trigger.source_queue.value,
        }

        # Add event-specific data
        if event.event_type == EventType.TASK_COMPLETED:
            base_payload.update({
                "completed_task_id": event.data.get("task_id"),
                "completed_task_type": event.data.get("task_type"),
                "execution_time": event.data.get("execution_time"),
            })
        elif event.event_type == EventType.MARKET_NEWS:
            base_payload.update({
                "symbol": event.data.get("symbol"),
                "headline": event.data.get("headline"),
                "impact_score": event.data.get("impact_score"),
                "sentiment": event.data.get("sentiment"),
            })
        elif event.event_type == EventType.EARNINGS_ANNOUNCEMENT:
            base_payload.update({
                "symbol": event.data.get("symbol"),
                "quarter": event.data.get("quarter"),
                "year": event.data.get("year"),
                "eps": event.data.get("eps"),
            })

        return base_payload

    def _determine_task_type(self, trigger: EventTrigger, event: Event) -> TaskType:
        """Determine the appropriate task type for the trigger."""
        # Map event types to task types based on target queue
        if trigger.target_queue == QueueName.DATA_FETCHER:
            if event.event_type == EventType.TASK_COMPLETED:
                return TaskType.FUNDAMENTALS_UPDATE
            elif event.event_type == EventType.MARKET_NEWS:
                return TaskType.NEWS_MONITORING
        elif trigger.target_queue == QueueName.AI_ANALYSIS:
            if event.event_type == EventType.TASK_COMPLETED:
                return TaskType.CLAUDE_MORNING_PREP
            elif event.event_type in [EventType.MARKET_NEWS, EventType.EARNINGS_ANNOUNCEMENT]:
                return TaskType.RECOMMENDATION_GENERATION

        # Default fallback
        return TaskType.CLAUDE_MORNING_PREP

    def get_registered_triggers(self) -> List[Dict[str, Any]]:
        """Get list of all registered triggers."""
        return [
            {
                "trigger_id": trigger.trigger_id,
                "source_queue": trigger.source_queue.value,
                "target_queue": trigger.target_queue.value,
                "event_type": trigger.event_type.value,
                "condition": trigger.condition,
                "is_active": trigger.is_active,
                "priority": trigger.priority,
                "created_at": trigger.created_at,
                "updated_at": trigger.updated_at,
            }
            for trigger in self._triggers.values()
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        return {
            "running": self._running,
            "initialized": self._initialized,
            "registered_triggers": len(self._triggers),
            "active_triggers": len([t for t in self._triggers.values() if t.is_active]),
        }

    def is_running(self) -> bool:
        """Check if router is running."""
        return self._running

    # Database operations
    async def _load_triggers_from_db(self) -> None:
        """Load triggers from database."""
        try:
            state_manager = await self.container.get_state_manager()

            # This would query the event_triggers table
            # For now, create default triggers
            await self._create_default_triggers()

        except Exception as e:
            self._log_error(f"Failed to load triggers from database: {e}")
            # Continue with empty triggers

    async def _persist_trigger(self, trigger: EventTrigger) -> None:
        """Persist trigger to database."""
        try:
            state_manager = await self.container.get_state_manager()
            # TODO: Implement database persistence
            # await state_manager.store_event_trigger(trigger)
            pass
        except Exception as e:
            self._log_error(f"Failed to persist trigger {trigger.trigger_id}: {e}")

    async def _update_trigger(self, trigger: EventTrigger) -> None:
        """Update trigger in database."""
        try:
            state_manager = await self.container.get_state_manager()
            # TODO: Implement database update
            # await state_manager.update_event_trigger(trigger)
            pass
        except Exception as e:
            self._log_error(f"Failed to update trigger {trigger.trigger_id}: {e}")

    async def _delete_trigger(self, trigger_id: str) -> None:
        """Delete trigger from database."""
        try:
            state_manager = await self.container.get_state_manager()
            # TODO: Implement database deletion
            # await state_manager.delete_event_trigger(trigger_id)
            pass
        except Exception as e:
            self._log_error(f"Failed to delete trigger {trigger_id}: {e}")

    async def _create_default_triggers(self) -> None:
        """Create default event triggers."""
        try:
            # Portfolio sync → Data fetcher trigger
            await self.register_trigger(
                source_queue=QueueName.PORTFOLIO_SYNC,
                target_queue=QueueName.DATA_FETCHER,
                event_type=EventType.TASK_COMPLETED,
                condition={"task_types": ["sync_account_balances", "update_positions"]}
            )

            # Data fetcher → AI analysis trigger
            await self.register_trigger(
                source_queue=QueueName.DATA_FETCHER,
                target_queue=QueueName.AI_ANALYSIS,
                event_type=EventType.TASK_COMPLETED,
                condition={"task_types": ["fundamentals_update", "news_monitoring"]}
            )

            # Market news trigger
            await self.register_trigger(
                source_queue=QueueName.DATA_FETCHER,
                target_queue=QueueName.AI_ANALYSIS,
                event_type=EventType.MARKET_NEWS,
                condition={"impact_score": ">0.7"}
            )

        except Exception as e:
            self._log_error(f"Failed to create default triggers: {e}")

    def _log_info(self, message: str) -> None:
        """Log info message with service name."""
        logger.info(f"[EventRouterService] {message}")

    def _log_error(self, message: str, exc_info: bool = False) -> None:
        """Log error message with service name."""
        logger.error(f"[EventRouterService] {message}", exc_info=exc_info)

    def _log_warning(self, message: str) -> None:
        """Log warning message with service name."""
        logger.warning(f"[EventRouterService] {message}")

    def _log_debug(self, message: str) -> None:
        """Log debug message with service name."""
        logger.debug(f"[EventRouterService] {message}")