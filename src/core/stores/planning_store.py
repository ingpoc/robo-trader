"""
Planning Store

Focused store managing AI planning and recommendation data.
Part of StateManager refactoring to follow Single Responsibility Principle.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger


class PlanningStore:
    """
    Manages AI planning, recommendations, and approval queue.

    Responsibilities:
    - Daily/weekly plan storage
    - Recommendation approval queue
    - Priority items tracking
    - Learning insights storage
    """

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.daily_plans_dir = self.state_dir / "daily_plans"
        self.approval_queue_file = self.state_dir / "approval_queue.json"
        self.priority_queue_file = self.state_dir / "priority_queue.json"
        self.weekly_plan_file = self.state_dir / "weekly_plan.json"
        self.learning_insights_file = self.state_dir / "learning_insights.json"

        self.daily_plans_dir.mkdir(exist_ok=True)

        self._approval_queue: List[Dict] = []
        self._priority_queue: List[Dict] = []
        self._weekly_plan: Optional[Dict] = None
        self._lock = asyncio.Lock()

        self._load_state_sync()

    def _load_state_sync(self) -> None:
        """Load planning state synchronously for __init__."""
        try:
            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)

            data = temp_manager._read_json_sync(self.approval_queue_file)
            self._approval_queue = data if data else []

            data = temp_manager._read_json_sync(self.priority_queue_file)
            self._priority_queue = data if data else []

            self._weekly_plan = temp_manager._read_json_sync(self.weekly_plan_file)

            logger.info("Planning store state loaded")
        except Exception as e:
            logger.error(f"Failed to load planning state: {e}")
            self._approval_queue = []
            self._priority_queue = []
            self._weekly_plan = None

    async def _save_approval_queue(self) -> bool:
        """Save approval queue to disk."""
        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        return await temp_manager._write_json_atomic(
            self.approval_queue_file,
            self._approval_queue
        )

    async def _save_priority_queue(self) -> bool:
        """Save priority queue to disk."""
        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        return await temp_manager._write_json_atomic(
            self.priority_queue_file,
            self._priority_queue
        )

    async def save_daily_plan(self, plan: Dict) -> None:
        """Save AI-generated daily work plan."""
        plan_file = self.daily_plans_dir / f"{plan['date']}.json"

        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        success = await temp_manager._write_json_atomic(plan_file, plan)

        if success:
            logger.debug(f"Saved daily plan for {plan['date']}")
        else:
            logger.error(f"Failed to save daily plan for {plan['date']}")

    async def load_daily_plan(self, date: str) -> Optional[Dict]:
        """Load daily plan for specific date."""
        plan_file = self.daily_plans_dir / f"{date}.json"

        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        return await temp_manager._read_json_atomic(plan_file)

    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """Add AI recommendation to user approval queue with deduplication."""
        async with self._lock:
            symbol = recommendation.get("symbol", "")
            action = recommendation.get("action", "")

            for existing in self._approval_queue:
                existing_rec = existing.get("recommendation", {})
                if (existing.get("status") == "pending" and
                    existing_rec.get("symbol") == symbol and
                    existing_rec.get("action") == action):
                    logger.debug(f"Skipping duplicate recommendation for {symbol} {action}")
                    return

            new_item = {
                "id": f"rec_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}_{action}",
                "recommendation": recommendation,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._approval_queue.append(new_item)

            await self._save_approval_queue()

    async def get_pending_approvals(self) -> List[Dict]:
        """Get recommendations awaiting user approval."""
        async with self._lock:
            return [item for item in self._approval_queue if item["status"] == "pending"]

    async def update_approval_status(
        self,
        recommendation_id: str,
        status: str,
        user_feedback: Optional[str] = None
    ) -> bool:
        """Update approval status for a recommendation."""
        async with self._lock:
            for item in self._approval_queue:
                if item["id"] == recommendation_id:
                    item["status"] = status
                    item["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if user_feedback:
                        item["user_feedback"] = user_feedback

                    success = await self._save_approval_queue()
                    return success

            return False

    async def add_priority_item(self, symbol: str, reason: str, priority: str) -> None:
        """Add item to priority queue for urgent analysis."""
        async with self._lock:
            self._priority_queue.append({
                "symbol": symbol,
                "reason": reason,
                "priority": priority,
                "added_at": datetime.now(timezone.utc).isoformat()
            })

            await self._save_priority_queue()

    async def get_priority_items(self) -> List[Dict]:
        """Get items needing urgent attention."""
        async with self._lock:
            return self._priority_queue.copy()

    async def clear_priority_item(self, symbol: str) -> bool:
        """Remove item from priority queue."""
        async with self._lock:
            initial_len = len(self._priority_queue)
            self._priority_queue = [
                item for item in self._priority_queue
                if item.get("symbol") != symbol
            ]

            if len(self._priority_queue) < initial_len:
                await self._save_priority_queue()
                return True

            return False

    async def save_weekly_plan(self, plan: Dict) -> None:
        """Save AI-generated weekly work distribution plan."""
        async with self._lock:
            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            temp_manager.state_dir = self.state_dir
            temp_manager._file_locks = {}

            success = await temp_manager._write_json_atomic(self.weekly_plan_file, plan)

            if success:
                self._weekly_plan = plan
                logger.debug("Saved weekly plan")
            else:
                logger.error("Failed to save weekly plan to disk")

    async def load_weekly_plan(self) -> Optional[Dict]:
        """Load current weekly plan."""
        async with self._lock:
            return self._weekly_plan.copy() if self._weekly_plan else None

    async def save_learning_insights(self, insights: Dict) -> None:
        """Save AI learning insights from recommendation outcomes."""
        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        def modify_insights(current_insights):
            if not isinstance(current_insights, list):
                current_insights = []

            current_insights.append(insights)
            return current_insights[-50:]

        success = await temp_manager._read_modify_write_atomic(
            self.learning_insights_file,
            modify_insights
        )

        if success:
            logger.debug("Saved learning insights")
        else:
            logger.error("Failed to save learning insights")

    async def get_learning_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent learning insights."""
        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        insights = await temp_manager._read_json_atomic(self.learning_insights_file)

        if insights and isinstance(insights, list):
            return insights[-limit:]

        return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get planning store statistics."""
        async with self._lock:
            return {
                "pending_approvals": len([
                    item for item in self._approval_queue
                    if item["status"] == "pending"
                ]),
                "total_recommendations": len(self._approval_queue),
                "priority_items": len(self._priority_queue),
                "has_weekly_plan": self._weekly_plan is not None
            }
