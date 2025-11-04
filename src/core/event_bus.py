"""
Event Bus Infrastructure for Robo Trader

Provides event-driven communication between services with proper
event schemas, persistence, and distributed processing capabilities.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import aiosqlite
from loguru import logger

from src.config import Config


class EventType(Enum):
    """Event types for the trading system."""
    # Market events
    MARKET_PRICE_UPDATE = "market.price_update"
    MARKET_VOLUME_SPIKE = "market.volume_spike"
    MARKET_NEWS = "market.news"
    MARKET_EARNINGS = "market.earnings"
    # Portfolio events
    PORTFOLIO_POSITION_CHANGE = "portfolio.position_change"
    PORTFOLIO_PNL_UPDATE = "portfolio.pnl_update"
    PORTFOLIO_CASH_CHANGE = "portfolio.cash_change"
    # Risk events
    RISK_BREACH = "risk.breach"
    RISK_STOP_LOSS_TRIGGER = "risk.stop_loss_trigger"
    RISK_EXPOSURE_CHANGE = "risk.exposure_change"
    # Execution events
    EXECUTION_ORDER_PLACED = "execution.order_placed"
    EXECUTION_ORDER_FILLED = "execution.order_filled"
    EXECUTION_ORDER_REJECTED = "execution.order_rejected"
    EXECUTION_ORDER_CANCELLED = "execution.order_cancelled"
    # AI events
    AI_RECOMMENDATION = "ai.recommendation"
    AI_ANALYSIS_COMPLETE = "ai.analysis_complete"
    AI_LEARNING_UPDATE = "ai.learning_update"
    # Feature Management events
    FEATURE_CREATED = "feature.created"
    FEATURE_UPDATED = "feature.updated"
    FEATURE_DELETED = "feature.deleted"
    FEATURE_ENABLED = "feature.enabled"
    FEATURE_DISABLED = "feature.disabled"
    FEATURE_ERROR = "feature.error"
    FEATURE_HEALTH_CHANGE = "feature.health_change"
    FEATURE_DEPENDENCY_RESOLVED = "feature.dependency_resolved"
    FEATURE_BULK_UPDATE = "feature.bulk_update"
    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"
    # Prompt Optimization events
    PROMPT_OPTIMIZED = "prompt.optimized"
    PROMPT_QUALITY_ANALYSIS = "prompt.quality_analysis"
    CLAUDE_SESSION_STARTED = "claude.session_started"
    CLAUDE_DATA_QUALITY_ANALYSIS = "claude.data_quality_analysis"
    STRATEGY_FORMED = "strategy.formed"
    DATA_ACQUISITION_COMPLETED = "data.acquisition_completed"
    MARKET_OPEN = "market.open"
    MARKET_CLOSE = "market.close"
    # OAuth events
    OAUTH_INITIATED = "oauth.initiated"
    OAUTH_SUCCESS = "oauth.success"
    OAUTH_ERROR = "oauth.error"
    OAUTH_LOGOUT = "oauth.logout"
    OAUTH_TOKEN_EXPIRED = "oauth.token_expired"
    OAUTH_TOKEN_REFRESHED = "oauth.token_refreshed"


@dataclass
class Event:
    """Event data structure."""
    id: str
    type: EventType
    timestamp: str
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        data_copy = data.copy()
        data_copy['type'] = EventType(data['type'])
        return cls(**data_copy)
class EventHandler:
    """Base class for event handlers."""

    async def handle_event(self, event: Event) -> None:
        """Handle an event. Override in subclasses."""
        raise NotImplementedError
class EventBus:
    """
    Event Bus for service communication.

    Features:
    - Event publishing and subscription
    - Event persistence for replay
    - Dead letter queue for failed events
    - Event correlation and tracing
    """

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.state_dir / "event_bus.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory subscriptions
        self._subscriptions: Dict[EventType, Set[EventHandler]] = {}
        self._lock = asyncio.Lock()

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize the event bus."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            logger.info("Event bus initialized")

    async def _create_tables(self) -> None:
        """Create event bus database tables."""
        schema = """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            data TEXT NOT NULL,
            correlation_id TEXT,
            version TEXT NOT NULL,
            processed_at TEXT,
            retry_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS dead_letter_queue (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            error_message TEXT NOT NULL,
            failed_at TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events(id)
        );
        CREATE TABLE IF NOT EXISTS event_handlers (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            handler_name TEXT NOT NULL,
            last_processed_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
        CREATE INDEX IF NOT EXISTS idx_dead_letter_event_id ON dead_letter_queue(event_id);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def publish(self, event: Event) -> None:
        """Publish an event to the bus."""
        async with self._lock:
            # Store event in database
            await self._persist_event(event)

            # Notify subscribers
            await self._notify_subscribers(event)

            logger.debug(f"Published event {event.id} of type {event.type.value}")

    async def _persist_event(self, event: Event) -> None:
        """Persist event to database."""
        event_dict = event.to_dict()
        await self._db_connection.execute("""
            INSERT INTO events (id, type, timestamp, source, data, correlation_id, version, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            event_dict['id'],
            event_dict['type'],
            event_dict['timestamp'],
            event_dict['source'],
            json.dumps(event_dict['data']),
            event_dict.get('correlation_id'),
            event_dict['version']
        ))
        await self._db_connection.commit()

    async def _notify_subscribers(self, event: Event) -> None:
        """Notify all subscribers of an event."""
        if event.type in self._subscriptions:
            tasks = []
            for handler in self._subscriptions[event.type]:
                task = asyncio.create_task(self._safe_handle_event(handler, event))
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_handle_event(self, handler: EventHandler, event: Event) -> None:
        """Safely handle an event with error handling."""
        try:
            await handler.handle_event(event)
            await self._mark_event_processed(event.id)
        except Exception as e:
            logger.error(f"Event handler {type(handler).__name__} failed for event {event.id}: {e}")
            await self._handle_failed_event(event, str(e))

    async def _mark_event_processed(self, event_id: str) -> None:
        """Mark an event as processed."""
        await self._db_connection.execute("""
            UPDATE events SET status = 'processed', processed_at = ?
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), event_id))
        await self._db_connection.commit()

    async def _handle_failed_event(self, event: Event, error_message: str) -> None:
        """Handle a failed event by moving to dead letter queue."""
        # Increment retry count
        await self._db_connection.execute("""
            UPDATE events SET retry_count = retry_count + 1
            WHERE id = ?
        """, (event.id,))

        # Move to dead letter queue if max retries exceeded
        cursor = await self._db_connection.execute(
            "SELECT retry_count FROM events WHERE id = ?", (event.id,)
        )
        row = await cursor.fetchone()

        if row and row[0] >= 3:  # Max 3 retries
            await self._db_connection.execute("""
                INSERT INTO dead_letter_queue (id, event_id, error_message, failed_at, retry_count)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"dlq_{event.id}_{row[0]}",
                event.id,
                error_message,
                datetime.now(timezone.utc).isoformat(),
                row[0]
            ))
            logger.warning(f"Event {event.id} moved to dead letter queue after {row[0]} retries")

        await self._db_connection.commit()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = set()
        self._subscriptions[event_type].add(handler)
        logger.debug(f"Handler {type(handler).__name__} subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscriptions:
            self._subscriptions[event_type].discard(handler)
            if not self._subscriptions[event_type]:
                del self._subscriptions[event_type]

    async def get_pending_events(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get pending events for processing."""
        query = "SELECT * FROM events WHERE status = 'pending'"
        params = []

        if event_type:
            query += " AND type = ?"
            params.append(event_type.value)

        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)

        cursor = await self._db_connection.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            event_dict = {
                'id': row[0],
                'type': row[1],
                'timestamp': row[2],
                'source': row[3],
                'data': json.loads(row[4]),
                'correlation_id': row[5],
                'version': row[6]
            }
            events.append(Event.from_dict(event_dict))

        return events

    async def replay_events(self, from_timestamp: str, to_timestamp: Optional[str] = None) -> List[Event]:
        """Replay events within a time range."""
        query = "SELECT * FROM events WHERE timestamp >= ?"
        params = [from_timestamp]

        if to_timestamp:
            query += " AND timestamp <= ?"
            params.append(to_timestamp)

        query += " ORDER BY timestamp ASC"

        cursor = await self._db_connection.execute(query, params)
        rows = await cursor.fetchall()

        events = []
        for row in rows:
            event_dict = {
                'id': row[0],
                'type': row[1],
                'timestamp': row[2],
                'source': row[3],
                'data': json.loads(row[4]),
                'correlation_id': row[5],
                'version': row[6]
            }
            events.append(Event.from_dict(event_dict))

        return events

    async def close(self) -> None:
        """Close the event bus."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
# Global event bus instance
_event_bus_instance: Optional[EventBus] = None
async def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    if _event_bus_instance is None:
        raise RuntimeError("Event bus not initialized. Call initialize_event_bus() first.")
    return _event_bus_instance
async def initialize_event_bus(config: Config) -> EventBus:
    """Initialize the global event bus."""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus(config)
        await _event_bus_instance.initialize()
    return _event_bus_instance