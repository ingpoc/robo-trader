"""
Intent Ledger Store

Focused store managing only trading intent records.
Part of StateManager refactoring to follow Single Responsibility Principle.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from ..state import Intent, Signal


class IntentLedger:
    """
    Manages trading intent records with atomic operations.

    Responsibilities:
    - Intent creation and updates
    - Intent retrieval by ID or filters
    - Thread-safe intent access
    """

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.intents_file = self.state_dir / "intents.json"

        self._intents: Dict[str, Intent] = {}
        self._lock = asyncio.Lock()

        self._load_intents_sync()

    def _load_intents_sync(self) -> None:
        """Load intents from file synchronously for __init__."""
        try:
            from ..state import StateManager
            temp_manager = StateManager.__new__(StateManager)
            data = temp_manager._read_json_sync(self.intents_file)

            if data:
                self._intents = {}
                for intent_id, intent_data in data.items():
                    self._intents[intent_id] = Intent.from_dict(intent_data)
                logger.info(f"Loaded {len(self._intents)} intents from file")
            else:
                self._intents = {}
        except Exception as e:
            logger.error(f"Failed to load intents: {e}")
            self._intents = {}

    async def _save_intents(self) -> bool:
        """Save intents to disk."""
        from ..state import StateManager
        temp_manager = StateManager.__new__(StateManager)
        temp_manager.state_dir = self.state_dir
        temp_manager._file_locks = {}

        success = await temp_manager._write_json_atomic(
            self.intents_file,
            {k: v.to_dict() for k, v in self._intents.items()}
        )

        return success

    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        async with self._lock:
            return self._intents.get(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """Get all intents."""
        async with self._lock:
            return list(self._intents.values())

    async def get_intents_by_status(self, status: str) -> List[Intent]:
        """Get intents filtered by status."""
        async with self._lock:
            return [intent for intent in self._intents.values() if intent.status == status]

    async def get_intents_by_symbol(self, symbol: str) -> List[Intent]:
        """Get intents for a specific symbol."""
        async with self._lock:
            return [intent for intent in self._intents.values() if intent.symbol == symbol]

    async def create_intent(
        self,
        symbol: str,
        signal: Optional[Signal] = None,
        source: str = "system"
    ) -> Intent:
        """Create new trading intent."""
        async with self._lock:
            intent_id = f"intent_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}"

            intent = Intent(
                id=intent_id,
                symbol=symbol,
                signal=signal,
                source=source,
                created_at=datetime.now(timezone.utc).isoformat()
            )

            self._intents[intent_id] = intent

            success = await self._save_intents()

            if success:
                logger.info(f"Created intent {intent_id} for {symbol}")
            else:
                logger.error(f"Failed to save intent {intent_id} to disk")

            return intent

    async def update_intent(self, intent: Intent) -> None:
        """Update existing intent."""
        async with self._lock:
            self._intents[intent.id] = intent

            success = await self._save_intents()

            if success:
                logger.info(f"Updated intent {intent.id}")
            else:
                logger.error(f"Failed to save intent {intent.id} to disk")

    async def delete_intent(self, intent_id: str) -> bool:
        """Delete an intent."""
        async with self._lock:
            if intent_id not in self._intents:
                return False

            del self._intents[intent_id]
            success = await self._save_intents()

            if success:
                logger.info(f"Deleted intent {intent_id}")
            else:
                logger.error(f"Failed to save after deleting intent {intent_id}")

            return success

    async def get_stats(self) -> Dict[str, int]:
        """Get intent statistics."""
        async with self._lock:
            stats = {
                "total": len(self._intents),
                "pending": 0,
                "approved": 0,
                "executed": 0,
                "rejected": 0
            }

            for intent in self._intents.values():
                status = intent.status
                if status in stats:
                    stats[status] += 1

            return stats

    async def cleanup_old_intents(self, days: int = 30) -> int:
        """Remove intents older than specified days."""
        from datetime import timedelta

        async with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff.isoformat()

            initial_count = len(self._intents)

            self._intents = {
                k: v for k, v in self._intents.items()
                if v.created_at > cutoff_str or v.status == "pending"
            }

            removed_count = initial_count - len(self._intents)

            if removed_count > 0:
                await self._save_intents()
                logger.info(f"Cleaned up {removed_count} old intents")

            return removed_count
