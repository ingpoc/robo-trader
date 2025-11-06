"""
Event Broadcasting for Feature Management

Provides real-time notifications for feature state changes, progress updates
during deactivation, error notifications, and recovery status updates.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from ...core.event_bus import Event, EventBus, EventType
from .models import FeatureConfig


class BroadcastEventType(Enum):
    """Types of broadcast events."""

    FEATURE_DEACTIVATION_STARTED = "feature_deactivation_started"
    FEATURE_DEACTIVATION_PROGRESS = "feature_deactivation_progress"
    FEATURE_DEACTIVATION_COMPLETED = "feature_deactivation_completed"
    FEATURE_DEACTIVATION_FAILED = "feature_deactivation_failed"
    FEATURE_DEACTIVATION_ROLLBACK = "feature_deactivation_rollback"
    ERROR_OCCURRED = "error_occurred"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    RESOURCE_CLEANUP_STARTED = "resource_cleanup_started"
    RESOURCE_CLEANUP_COMPLETED = "resource_cleanup_completed"
    SERVICE_STOPPED = "service_stopped"
    AGENT_STOPPED = "agent_stopped"
    TASK_CANCELLED = "task_cancelled"


@dataclass
class BroadcastEvent:
    """A broadcast event for real-time notifications."""

    event_id: str
    event_type: BroadcastEventType
    feature_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical
    source: str = "feature_management"
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "feature_id": self.feature_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "severity": self.severity,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


@dataclass
class EventSubscription:
    """A subscription to broadcast events."""

    subscription_id: str
    subscriber_id: str
    event_types: List[BroadcastEventType]
    feature_ids: Optional[List[str]] = None  # None means all features
    min_severity: str = "info"
    callback: Optional[callable] = None
    websocket: Optional[Any] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def matches_event(self, event: BroadcastEvent) -> bool:
        """Check if this subscription matches an event."""
        # Check event type
        if event.event_type not in self.event_types:
            return False

        # Check feature ID
        if self.feature_ids and event.feature_id not in self.feature_ids:
            return False

        # Check severity
        severity_levels = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        if severity_levels.get(event.severity, 0) < severity_levels.get(
            self.min_severity, 0
        ):
            return False

        return True


@dataclass
class ProgressUpdate:
    """Progress update for long-running operations."""

    operation_id: str
    feature_id: str
    operation_type: str
    current_stage: str
    progress_percentage: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation_id": self.operation_id,
            "feature_id": self.feature_id,
            "operation_type": self.operation_type,
            "current_stage": self.current_stage,
            "progress_percentage": self.progress_percentage,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class EventBroadcastingService:
    """
    Provides real-time event broadcasting for feature management operations.

    Responsibilities:
    - Real-time notifications for feature state changes
    - Progress updates during deactivation
    - Error notifications and recovery status
    - WebSocket broadcasting for web clients
    - Event filtering and routing
    - Subscription management
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus

        # Subscription management
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.websocket_connections: Dict[str, Any] = {}  # connection_id -> websocket

        # Event history
        self.event_history: List[BroadcastEvent] = []
        self.progress_updates: Dict[str, ProgressUpdate] = {}  # operation_id -> update

        # Configuration
        self.config = {
            "max_event_history": 1000,
            "enable_websocket_broadcast": True,
            "enable_event_bus_forwarding": True,
            "default_retention_hours": 24,
        }

        # Statistics
        self.statistics = {
            "events_broadcast": 0,
            "subscriptions_active": 0,
            "websocket_connections": 0,
            "events_filtered": 0,
        }

        logger.info("Event Broadcasting Service initialized")

    async def subscribe_to_events(
        self,
        subscriber_id: str,
        event_types: List[BroadcastEventType],
        feature_ids: Optional[List[str]] = None,
        min_severity: str = "info",
        callback: Optional[callable] = None,
        websocket: Optional[Any] = None,
    ) -> str:
        """
        Subscribe to broadcast events.

        Args:
            subscriber_id: ID of the subscriber
            event_types: List of event types to subscribe to
            feature_ids: Optional list of feature IDs to filter by
            min_severity: Minimum severity level to receive
            callback: Optional callback function for events
            websocket: Optional WebSocket connection for real-time updates

        Returns:
            Subscription ID
        """
        subscription_id = (
            f"sub_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{subscriber_id}"
        )

        subscription = EventSubscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            event_types=event_types,
            feature_ids=feature_ids,
            min_severity=min_severity,
            callback=callback,
            websocket=websocket,
        )

        self.subscriptions[subscription_id] = subscription

        # Track WebSocket connection
        if websocket:
            self.websocket_connections[subscription_id] = websocket
            self.statistics["websocket_connections"] += 1

        self.statistics["subscriptions_active"] += 1

        logger.info(
            f"Created subscription {subscription_id} for subscriber {subscriber_id}"
        )

        return subscription_id

    async def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Unsubscribe from broadcast events."""
        if subscription_id not in self.subscriptions:
            return False

        subscription = self.subscriptions[subscription_id]

        # Remove WebSocket connection
        if subscription.websocket and subscription_id in self.websocket_connections:
            del self.websocket_connections[subscription_id]
            self.statistics["websocket_connections"] -= 1

        del self.subscriptions[subscription_id]
        self.statistics["subscriptions_active"] -= 1

        logger.info(f"Removed subscription {subscription_id}")
        return True

    async def broadcast_event(
        self,
        event_type: BroadcastEventType,
        feature_id: str,
        data: Dict[str, Any],
        severity: str = "info",
        source: str = "feature_management",
        correlation_id: Optional[str] = None,
    ) -> BroadcastEvent:
        """
        Broadcast an event to all subscribers.

        Args:
            event_type: Type of the event
            feature_id: ID of the feature
            data: Event data
            severity: Event severity
            source: Event source
            correlation_id: Optional correlation ID for tracking

        Returns:
            The broadcast event that was sent
        """
        # Create event
        event = BroadcastEvent(
            event_id=f"evt_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            event_type=event_type,
            feature_id=feature_id,
            data=data,
            severity=severity,
            source=source,
            correlation_id=correlation_id,
        )

        # Add to history
        self._add_to_history(event)

        # Update statistics
        self.statistics["events_broadcast"] += 1

        # Broadcast to subscribers
        await self._broadcast_to_subscribers(event)

        # Forward to event bus if enabled
        if self.config["enable_event_bus_forwarding"] and self.event_bus:
            await self._forward_to_event_bus(event)

        logger.debug(
            f"Broadcasted event {event.event_type.value} for feature {feature_id}"
        )

        return event

    async def broadcast_progress_update(
        self,
        operation_id: str,
        feature_id: str,
        operation_type: str,
        current_stage: str,
        progress_percentage: float,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> ProgressUpdate:
        """
        Broadcast a progress update for a long-running operation.

        Args:
            operation_id: ID of the operation
            feature_id: ID of the feature
            operation_type: Type of operation
            current_stage: Current stage of the operation
            progress_percentage: Progress percentage (0-100)
            message: Progress message
            details: Additional details

        Returns:
            The progress update that was broadcast
        """
        update = ProgressUpdate(
            operation_id=operation_id,
            feature_id=feature_id,
            operation_type=operation_type,
            current_stage=current_stage,
            progress_percentage=progress_percentage,
            message=message,
            details=details or {},
        )

        # Store update
        self.progress_updates[operation_id] = update

        # Broadcast as event
        await self.broadcast_event(
            event_type=BroadcastEventType.FEATURE_DEACTIVATION_PROGRESS,
            feature_id=feature_id,
            data={
                "progress_update": update.to_dict(),
                "operation_type": operation_type,
            },
            severity="info",
            correlation_id=operation_id,
        )

        logger.debug(
            f"Broadcasted progress update for operation {operation_id}: {progress_percentage}% - {message}"
        )

        return update

    async def broadcast_feature_deactivation_started(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        reason: Optional[str] = None,
    ) -> BroadcastEvent:
        """Broadcast that feature deactivation has started."""
        return await self.broadcast_event(
            event_type=BroadcastEventType.FEATURE_DEACTIVATION_STARTED,
            feature_id=feature_id,
            data={
                "feature_config": feature_config.to_dict(),
                "reason": reason,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="info",
        )

    async def broadcast_feature_deactivation_completed(
        self, feature_id: str, duration_ms: int, resources_cleaned: Dict[str, int]
    ) -> BroadcastEvent:
        """Broadcast that feature deactivation has completed."""
        return await self.broadcast_event(
            event_type=BroadcastEventType.FEATURE_DEACTIVATION_COMPLETED,
            feature_id=feature_id,
            data={
                "duration_ms": duration_ms,
                "resources_cleaned": resources_cleaned,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="info",
        )

    async def broadcast_feature_deactivation_failed(
        self,
        feature_id: str,
        error_message: str,
        stage: str,
        partial_success: bool = False,
    ) -> BroadcastEvent:
        """Broadcast that feature deactivation has failed."""
        return await self.broadcast_event(
            event_type=BroadcastEventType.FEATURE_DEACTIVATION_FAILED,
            feature_id=feature_id,
            data={
                "error_message": error_message,
                "stage": stage,
                "partial_success": partial_success,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="error",
        )

    async def broadcast_error_occurred(
        self,
        feature_id: str,
        error_message: str,
        error_type: str,
        context: Dict[str, Any],
    ) -> BroadcastEvent:
        """Broadcast that an error has occurred."""
        return await self.broadcast_event(
            event_type=BroadcastEventType.ERROR_OCCURRED,
            feature_id=feature_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "context": context,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="error",
        )

    async def broadcast_recovery_started(
        self, feature_id: str, error_id: str, recovery_strategy: str
    ) -> BroadcastEvent:
        """Broadcast that recovery has started."""
        return await self.broadcast_event(
            event_type=BroadcastEventType.RECOVERY_STARTED,
            feature_id=feature_id,
            data={
                "error_id": error_id,
                "recovery_strategy": recovery_strategy,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="warning",
        )

    async def broadcast_recovery_completed(
        self,
        feature_id: str,
        error_id: str,
        recovery_strategy: str,
        success: bool,
        message: str,
    ) -> BroadcastEvent:
        """Broadcast that recovery has completed."""
        return await self.broadcast_event(
            event_type=BroadcastEventType.RECOVERY_COMPLETED,
            feature_id=feature_id,
            data={
                "error_id": error_id,
                "recovery_strategy": recovery_strategy,
                "success": success,
                "message": message,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            severity="info" if success else "error",
        )

    async def _broadcast_to_subscribers(self, event: BroadcastEvent) -> None:
        """Broadcast event to all matching subscribers."""
        matching_subscriptions = []
        filtered_count = 0

        for subscription in self.subscriptions.values():
            if subscription.matches_event(event):
                matching_subscriptions.append(subscription)
            else:
                filtered_count += 1

        self.statistics["events_filtered"] += filtered_count

        # Send to matching subscribers
        for subscription in matching_subscriptions:
            try:
                # Call callback if provided
                if subscription.callback:
                    await self._call_callback_safely(subscription.callback, event)

                # Send to WebSocket if provided
                if subscription.websocket and self.config["enable_websocket_broadcast"]:
                    await self._send_to_websocket_safely(subscription.websocket, event)

            except Exception as e:
                logger.error(
                    f"Failed to send event to subscription {subscription.subscription_id}: {str(e)}"
                )

    async def _call_callback_safely(
        self, callback: callable, event: BroadcastEvent
    ) -> None:
        """Safely call a callback function."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"Callback function failed: {str(e)}")

    async def _send_to_websocket_safely(
        self, websocket: Any, event: BroadcastEvent
    ) -> None:
        """Safely send event to WebSocket."""
        try:
            message = json.dumps(event.to_dict())

            if hasattr(websocket, "send"):
                if asyncio.iscoroutinefunction(websocket.send):
                    await websocket.send(message)
                else:
                    websocket.send(message)
            else:
                logger.warning("WebSocket object does not have send method")

        except Exception as e:
            logger.error(f"Failed to send event to WebSocket: {str(e)}")

    async def _forward_to_event_bus(self, event: BroadcastEvent) -> None:
        """Forward event to the main event bus."""
        try:
            # Map broadcast event types to event bus types
            event_type_mapping = {
                BroadcastEventType.FEATURE_DEACTIVATION_STARTED: EventType.FEATURE_DISABLED,
                BroadcastEventType.FEATURE_DEACTIVATION_COMPLETED: EventType.FEATURE_DISABLED,
                BroadcastEventType.FEATURE_DEACTIVATION_FAILED: EventType.SYSTEM_ERROR,
                BroadcastEventType.ERROR_OCCURRED: EventType.SYSTEM_ERROR,
                BroadcastEventType.RECOVERY_COMPLETED: EventType.SYSTEM_HEALTH_CHECK,
            }

            bus_event_type = event_type_mapping.get(
                event.event_type, EventType.SYSTEM_HEALTH_CHECK
            )

            await self.event_bus.publish(
                Event(
                    id=f"broadcast_{event.event_id}",
                    type=bus_event_type,
                    timestamp=event.timestamp,
                    source="event_broadcasting",
                    data=event.to_dict(),
                )
            )

        except Exception as e:
            logger.error(f"Failed to forward event to event bus: {str(e)}")

    def _add_to_history(self, event: BroadcastEvent) -> None:
        """Add event to history with size limit."""
        self.event_history.append(event)

        # Maintain size limit
        if len(self.event_history) > self.config["max_event_history"]:
            self.event_history = self.event_history[-self.config["max_event_history"] :]

    async def get_event_history(
        self,
        feature_id: Optional[str] = None,
        event_type: Optional[BroadcastEventType] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BroadcastEvent]:
        """Get event history with optional filtering."""
        events = self.event_history

        # Filter by feature ID
        if feature_id:
            events = [e for e in events if e.feature_id == feature_id]

        # Filter by event type
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Filter by timestamp
        if since:
            events = [e for e in events if datetime.fromisoformat(e.timestamp) >= since]

        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    async def get_progress_update(self, operation_id: str) -> Optional[ProgressUpdate]:
        """Get progress update for an operation."""
        return self.progress_updates.get(operation_id)

    async def get_active_subscriptions(self) -> List[EventSubscription]:
        """Get all active subscriptions."""
        return list(self.subscriptions.values())

    async def get_broadcasting_statistics(self) -> Dict[str, Any]:
        """Get broadcasting statistics."""
        return {
            **self.statistics,
            "event_history_size": len(self.event_history),
            "active_progress_updates": len(self.progress_updates),
            "config": self.config,
        }

    async def cleanup_old_events(self, older_than_hours: int = None) -> int:
        """Clean up old events from history."""
        hours = older_than_hours or self.config["default_retention_hours"]
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        initial_count = len(self.event_history)
        self.event_history = [
            event
            for event in self.event_history
            if datetime.fromisoformat(event.timestamp) >= cutoff_time
        ]

        cleaned_count = initial_count - len(self.event_history)
        logger.info(f"Cleaned up {cleaned_count} old events")
        return cleaned_count

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update broadcasting configuration."""
        self.config.update(new_config)
        logger.info(f"Updated broadcasting configuration: {new_config}")

    async def close(self) -> None:
        """Close the event broadcasting service."""
        logger.info("Closing Event Broadcasting Service")

        # Close all WebSocket connections
        for subscription_id, websocket in self.websocket_connections.items():
            try:
                if hasattr(websocket, "close"):
                    if asyncio.iscoroutinefunction(websocket.close):
                        await websocket.close()
                    else:
                        websocket.close()
            except Exception as e:
                logger.error(f"Failed to close WebSocket {subscription_id}: {str(e)}")

        # Clear all data
        self.subscriptions.clear()
        self.websocket_connections.clear()
        self.event_history.clear()
        self.progress_updates.clear()

        # Reset statistics
        self.statistics = {
            "events_broadcast": 0,
            "subscriptions_active": 0,
            "websocket_connections": 0,
            "events_filtered": 0,
        }

        logger.info("Event Broadcasting Service closed")
