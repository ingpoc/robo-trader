"""
Event trigger state management for Robo Trader.

Handles persistence of event triggers for the EventRouterService.
Event triggers define rules for routing events between queues based on conditions.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from loguru import logger

from .base import DatabaseConnection


class EventTriggerStateManager:
    """
    Manages event trigger persistence for the EventRouterService.

    Responsibilities:
    - Store event triggers in database
    - Load triggers on startup
    - Update and delete triggers
    - Ensure triggers survive application restarts
    """

    def __init__(self, db: DatabaseConnection):
        """
        Initialize event trigger state manager.

        Args:
            db: Database connection manager
        """
        self.db = db
        self._triggers: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Create table and load triggers from database."""
        await self._ensure_table_exists()
        await self._load_triggers()

    async def _ensure_table_exists(self) -> None:
        """Create event_triggers table if it doesn't exist."""
        async with self._lock:
            await self.db.connection.execute("""
                CREATE TABLE IF NOT EXISTS event_triggers (
                    trigger_id TEXT PRIMARY KEY,
                    source_queue TEXT NOT NULL,
                    target_queue TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    condition JSON,
                    enabled INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await self.db.connection.commit()
            logger.debug("Event triggers table ensured")

    async def _load_triggers(self) -> None:
        """Load all triggers from database."""
        async with self._lock:
            self._triggers = {}
            async with self.db.connection.execute(
                "SELECT * FROM event_triggers WHERE enabled = 1 ORDER BY priority DESC"
            ) as cursor:
                async for row in cursor:
                    trigger = {
                        "trigger_id": row[0],
                        "source_queue": row[1],
                        "target_queue": row[2],
                        "event_type": row[3],
                        "condition": json.loads(row[4]) if row[4] else None,
                        "enabled": bool(row[5]),
                        "priority": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    }
                    self._triggers[trigger["trigger_id"]] = trigger

            logger.info(f"Loaded {len(self._triggers)} event triggers from database")

    async def store_trigger(self, trigger: Dict[str, Any]) -> bool:
        """
        Store a new event trigger in database.

        Args:
            trigger: Trigger dict with trigger_id, source_queue, target_queue, etc.

        Returns:
            True if stored successfully, False otherwise
        """
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()
                trigger_id = trigger.get("trigger_id")

                if not trigger_id:
                    logger.error("Cannot store trigger without trigger_id")
                    return False

                condition_json = json.dumps(trigger.get("condition")) if trigger.get("condition") else None

                # Use 'or now' to handle both missing key AND None value
                created_at = trigger.get("created_at") or now

                await self.db.connection.execute("""
                    INSERT OR REPLACE INTO event_triggers
                    (trigger_id, source_queue, target_queue, event_type, condition, enabled, priority, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trigger_id,
                    trigger.get("source_queue", ""),
                    trigger.get("target_queue", ""),
                    trigger.get("event_type", ""),
                    condition_json,
                    1 if trigger.get("enabled", True) else 0,
                    trigger.get("priority", 0),
                    created_at,
                    now
                ))
                await self.db.connection.commit()

                # Update in-memory cache
                trigger["updated_at"] = now
                if "created_at" not in trigger:
                    trigger["created_at"] = now
                self._triggers[trigger_id] = trigger

                logger.info(f"Stored event trigger: {trigger_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to store trigger {trigger.get('trigger_id')}: {e}")
                return False

    async def update_trigger(self, trigger_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing event trigger.

        Args:
            trigger_id: ID of trigger to update
            updates: Dict of fields to update

        Returns:
            True if updated successfully, False otherwise
        """
        async with self._lock:
            try:
                if trigger_id not in self._triggers:
                    logger.warning(f"Trigger {trigger_id} not found for update")
                    return False

                now = datetime.now(timezone.utc).isoformat()
                existing = self._triggers[trigger_id]

                # Merge updates
                updated_trigger = {**existing, **updates, "updated_at": now}

                condition_json = json.dumps(updated_trigger.get("condition")) if updated_trigger.get("condition") else None

                await self.db.connection.execute("""
                    UPDATE event_triggers
                    SET source_queue = ?, target_queue = ?, event_type = ?,
                        condition = ?, enabled = ?, priority = ?, updated_at = ?
                    WHERE trigger_id = ?
                """, (
                    updated_trigger.get("source_queue", ""),
                    updated_trigger.get("target_queue", ""),
                    updated_trigger.get("event_type", ""),
                    condition_json,
                    1 if updated_trigger.get("enabled", True) else 0,
                    updated_trigger.get("priority", 0),
                    now,
                    trigger_id
                ))
                await self.db.connection.commit()

                # Update in-memory cache
                self._triggers[trigger_id] = updated_trigger

                logger.info(f"Updated event trigger: {trigger_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to update trigger {trigger_id}: {e}")
                return False

    async def delete_trigger(self, trigger_id: str) -> bool:
        """
        Delete an event trigger from database.

        Args:
            trigger_id: ID of trigger to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        async with self._lock:
            try:
                await self.db.connection.execute(
                    "DELETE FROM event_triggers WHERE trigger_id = ?",
                    (trigger_id,)
                )
                await self.db.connection.commit()

                # Remove from in-memory cache
                if trigger_id in self._triggers:
                    del self._triggers[trigger_id]

                logger.info(f"Deleted event trigger: {trigger_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to delete trigger {trigger_id}: {e}")
                return False

    async def get_trigger(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific trigger by ID.

        Args:
            trigger_id: ID of trigger to retrieve

        Returns:
            Trigger dict or None if not found
        """
        async with self._lock:
            return self._triggers.get(trigger_id)

    async def get_all_triggers(self) -> List[Dict[str, Any]]:
        """
        Get all enabled triggers.

        Returns:
            List of trigger dicts
        """
        async with self._lock:
            return list(self._triggers.values())

    async def get_triggers_by_source(self, source_queue: str) -> List[Dict[str, Any]]:
        """
        Get triggers filtered by source queue.

        Args:
            source_queue: Name of source queue

        Returns:
            List of matching triggers
        """
        async with self._lock:
            return [
                t for t in self._triggers.values()
                if t.get("source_queue") == source_queue and t.get("enabled", True)
            ]

    async def get_triggers_by_event_type(self, event_type: str) -> List[Dict[str, Any]]:
        """
        Get triggers filtered by event type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of matching triggers
        """
        async with self._lock:
            return [
                t for t in self._triggers.values()
                if t.get("event_type") == event_type and t.get("enabled", True)
            ]

    async def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger without deleting it."""
        return await self.update_trigger(trigger_id, {"enabled": False})

    async def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a previously disabled trigger."""
        return await self.update_trigger(trigger_id, {"enabled": True})
