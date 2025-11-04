"""
Approval workflow state management for Robo Trader.

Handles user approval queue for AI trading recommendations.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from loguru import logger

from src.core.event_bus import EventBus, Event, EventType
from .base import DatabaseConnection


class ApprovalStateManager:
    """
    Manages approval workflow for trading recommendations.

    Responsibilities:
    - Queue AI recommendations for user approval
    - Track approval status (pending, approved, rejected)
    - Prevent duplicate recommendations
    - Emit events on approval decisions
    """

    def __init__(self, db: DatabaseConnection, event_bus: Optional[EventBus] = None):
        """
        Initialize approval state manager.

        Args:
            db: Database connection manager
            event_bus: Optional event bus for emitting approval events
        """
        self.db = db
        self.event_bus = event_bus
        self._approval_queue: List[Dict] = []
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load initial approval queue from database."""
        await self._load_approval_queue()

    async def _load_approval_queue(self) -> None:
        """Load approval queue from database."""
        async with self._lock:
            async with self.db.connection.execute(
                "SELECT * FROM approval_queue WHERE status = 'pending' ORDER BY created_at DESC"
            ) as cursor:
                async for row in cursor:
                    item = {
                        "id": row[0],
                        "recommendation": json.loads(row[1]),
                        "status": row[2],
                        "created_at": row[3],
                        "updated_at": row[4],
                        "user_feedback": row[5]
                    }
                    self._approval_queue.append(item)

            logger.info(f"Loaded {len(self._approval_queue)} pending approvals")

    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """
        Add AI recommendation to user approval queue.

        Prevents duplicate recommendations for same symbol/action.

        Args:
            recommendation: Recommendation dict with symbol, action, etc.
        """
        async with self._lock:
            symbol = recommendation.get("symbol", "")
            action = recommendation.get("action", "")
            now = datetime.now(timezone.utc).isoformat()

            # Check for duplicates
            for existing in self._approval_queue:
                existing_rec = existing.get("recommendation", {})
                if (existing.get("status") == "pending" and
                    existing_rec.get("symbol") == symbol and
                    existing_rec.get("action") == action):
                    logger.debug(f"Skipping duplicate recommendation for {symbol} {action}")
                    return

            # Add new recommendation
            rec_id = f"rec_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}_{action}"
            new_item = {
                "id": rec_id,
                "recommendation": recommendation,
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
            self._approval_queue.append(new_item)

            # Save to database
            async with self.db.connection.execute("""
                INSERT INTO approval_queue (id, recommendation, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (rec_id, json.dumps(recommendation), "pending", now, now)):
                await self.db.connection.commit()

            logger.info(f"Added recommendation {rec_id} to approval queue")

            # Emit event
            if self.event_bus:
                await self._emit_approval_queued(recommendation)

    async def get_pending_approvals(self) -> List[Dict]:
        """
        Get recommendations awaiting user approval.

        Returns:
            List of pending approval items
        """
        async with self._lock:
            return [item for item in self._approval_queue if item["status"] == "pending"]

    async def update_approval_status(
        self,
        recommendation_id: str,
        status: str,
        user_feedback: Optional[str] = None
    ) -> bool:
        """
        Update approval status for a recommendation.

        Args:
            recommendation_id: ID of recommendation to update
            status: New status (approved, rejected)
            user_feedback: Optional user feedback/comments

        Returns:
            True if updated successfully, False if not found
        """
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            for item in self._approval_queue:
                if item["id"] == recommendation_id:
                    item["status"] = status
                    item["updated_at"] = now
                    if user_feedback:
                        item["user_feedback"] = user_feedback

                    # Update database
                    async with self.db.connection.execute("""
                        UPDATE approval_queue
                        SET status = ?, updated_at = ?, user_feedback = ?
                        WHERE id = ?
                    """, (status, now, user_feedback, recommendation_id)):
                        await self.db.connection.commit()

                    logger.info(f"Updated approval {recommendation_id} to {status}")

                    # Emit event
                    if self.event_bus:
                        await self._emit_approval_decision(item, status)

                    return True

            logger.warning(f"Approval {recommendation_id} not found")
            return False

    async def _emit_approval_queued(self, recommendation: Dict) -> None:
        """Emit event when recommendation is queued for approval."""
        try:
            event = Event(
                type=EventType.TRADE_SUBMITTED,
                source="ApprovalStateManager",
                data={
                    "symbol": recommendation.get("symbol"),
                    "action": recommendation.get("action"),
                    "status": "pending_approval",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await self.event_bus.publish(event)
        except Exception as e:
            logger.warning(f"Failed to emit approval queued event: {e}")

    async def _emit_approval_decision(self, item: Dict, status: str) -> None:
        """Emit event when approval decision is made."""
        try:
            event_type = EventType.TRADE_APPROVED if status == "approved" else EventType.TRADE_REJECTED
            recommendation = item.get("recommendation", {})

            event = Event(
                type=event_type,
                source="ApprovalStateManager",
                data={
                    "recommendation_id": item["id"],
                    "symbol": recommendation.get("symbol"),
                    "action": recommendation.get("action"),
                    "status": status,
                    "user_feedback": item.get("user_feedback"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await self.event_bus.publish(event)
        except Exception as e:
            logger.warning(f"Failed to emit approval decision event: {e}")
