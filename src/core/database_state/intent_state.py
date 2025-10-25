"""
Intent state management for Robo Trader.

Handles trading intent tracking with database persistence.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from loguru import logger

from src.core.state_models import Intent, Signal
from src.core.event_bus import EventBus, Event, EventType
from .base import DatabaseConnection


class IntentStateManager:
    """
    Manages trading intents with database persistence.

    Responsibilities:
    - Create, read, update intents
    - Track intent lifecycle (created -> approved -> executed)
    - Cache intents in memory
    - Emit events on intent changes
    """

    def __init__(self, db: DatabaseConnection, event_bus: Optional[EventBus] = None):
        """
        Initialize intent state manager.

        Args:
            db: Database connection manager
            event_bus: Optional event bus for emitting intent events
        """
        self.db = db
        self.event_bus = event_bus
        self._intents: Dict[str, Intent] = {}
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load initial intents from database."""
        await self._load_intents()

    async def _load_intents(self) -> None:
        """Load all intents from database into memory cache."""
        async with self._lock:
            async with self.db.connection.execute("SELECT * FROM intents") as cursor:
                async for row in cursor:
                    intent_data = {
                        "id": row[0],
                        "symbol": row[1],
                        "created_at": row[2],
                        "signal": json.loads(row[3]) if row[3] else None,
                        "risk_decision": json.loads(row[4]) if row[4] else None,
                        "order_commands": json.loads(row[5]),
                        "execution_reports": json.loads(row[6]),
                        "status": row[7],
                        "approved_at": row[8],
                        "executed_at": row[9],
                        "source": row[10]
                    }
                    self._intents[row[0]] = Intent.from_dict(intent_data)

            logger.info(f"Loaded {len(self._intents)} intents from database")

    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """
        Get intent by ID.

        Args:
            intent_id: Intent identifier

        Returns:
            Intent if found, None otherwise
        """
        async with self._lock:
            return self._intents.get(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """
        Get all intents.

        Returns:
            List of all intents
        """
        async with self._lock:
            return list(self._intents.values())

    async def create_intent(
        self,
        symbol: str,
        signal: Optional[Signal] = None,
        source: str = "system"
    ) -> Intent:
        """
        Create new trading intent.

        Args:
            symbol: Stock symbol
            signal: Optional trading signal
            source: Source of the intent (system, user, ai)

        Returns:
            Created intent
        """
        async with self._lock:
            # Generate unique intent ID
            intent_id = f"intent_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}"

            intent = Intent(
                id=intent_id,
                symbol=symbol,
                signal=signal,
                source=source
            )

            self._intents[intent_id] = intent
            await self._save_intent(intent)

            logger.info(f"Created intent {intent_id} for {symbol}")

            # Emit event
            if self.event_bus:
                await self._emit_intent_created(intent)

            return intent

    async def update_intent(self, intent: Intent) -> None:
        """
        Update existing intent.

        Args:
            intent: Intent with updated data
        """
        async with self._lock:
            self._intents[intent.id] = intent
            await self._save_intent(intent)

            logger.info(f"Updated intent {intent.id} (status: {intent.status})")

            # Emit event
            if self.event_bus:
                await self._emit_intent_updated(intent)

    async def _save_intent(self, intent: Intent) -> None:
        """
        Save intent to database.

        Args:
            intent: Intent to save
        """
        async with self.db.connection.execute("""
            INSERT OR REPLACE INTO intents
            (id, symbol, created_at, signal, risk_decision, order_commands,
             execution_reports, status, approved_at, executed_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            intent.id,
            intent.symbol,
            intent.created_at,
            json.dumps(intent.signal.to_dict()) if intent.signal else None,
            json.dumps(intent.risk_decision.to_dict()) if intent.risk_decision else None,
            json.dumps([cmd.to_dict() for cmd in intent.order_commands]),
            json.dumps([rep.to_dict() for rep in intent.execution_reports]),
            intent.status,
            intent.approved_at,
            intent.executed_at,
            intent.source
        )):
            await self.db.connection.commit()

    async def _emit_intent_created(self, intent: Intent) -> None:
        """Emit intent created event."""
        try:
            event = Event(
                type=EventType.TRADE_SUBMITTED,
                source="IntentStateManager",
                data={
                    "intent_id": intent.id,
                    "symbol": intent.symbol,
                    "source": intent.source,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await self.event_bus.emit(event)
        except Exception as e:
            logger.warning(f"Failed to emit intent created event: {e}")

    async def _emit_intent_updated(self, intent: Intent) -> None:
        """Emit intent updated event."""
        try:
            # Emit different events based on status
            event_type = EventType.TRADE_SUBMITTED
            if intent.status == "approved":
                event_type = EventType.TRADE_APPROVED
            elif intent.status == "executed":
                event_type = EventType.TRADE_EXECUTED
            elif intent.status == "rejected":
                event_type = EventType.TRADE_REJECTED

            event = Event(
                type=event_type,
                source="IntentStateManager",
                data={
                    "intent_id": intent.id,
                    "symbol": intent.symbol,
                    "status": intent.status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await self.event_bus.emit(event)
        except Exception as e:
            logger.warning(f"Failed to emit intent updated event: {e}")
