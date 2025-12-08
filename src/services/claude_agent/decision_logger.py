"""
Claude Decision Logger Service

Logs all trading decisions made by Claude for full transparency and auditability.
Enables tracking of reasoning, execution results, and decision history.
"""

import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger

from ...core.event_bus import EventBus, Event, EventType
from ...core.database_state.configuration_state import ConfigurationState


class DecisionType(str, Enum):
    """Types of trading decisions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingDecision:
    """A trading decision made by Claude."""

    decision_id: str
    timestamp: str
    decision_type: DecisionType
    symbol: str
    reasoning: str
    confidence_score: float
    context_snapshot: Dict[str, Any]
    execution_result: Optional[Dict[str, Any]] = None
    executed_at: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['decision_type'] = self.decision_type.value
        return data


class ClaudeDecisionLogger:
    """
    Logs and tracks all trading decisions made by Claude.

    Provides full transparency into:
    - Decision reasoning and confidence
    - Market context at decision time
    - Execution results and outcomes
    - Historical decision patterns
    """

    def __init__(
        self,
        config_state: ConfigurationState,
        event_bus: Optional[EventBus] = None
    ):
        self.config_state = config_state
        self.event_bus = event_bus
        self._lock = asyncio.Lock()

    async def log_decision(
        self,
        decision_type: DecisionType,
        symbol: str,
        reasoning: str,
        confidence_score: float,
        context_snapshot: Dict[str, Any]
    ) -> TradingDecision:
        """
        Log a new trading decision before execution.

        Args:
            decision_type: BUY, SELL, or HOLD
            symbol: Stock symbol
            reasoning: Claude's reasoning for the decision
            confidence_score: Confidence level (0-1)
            context_snapshot: Portfolio state, market data at decision time

        Returns:
            TradingDecision with generated ID
        """
        decision = TradingDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision_type=decision_type,
            symbol=symbol,
            reasoning=reasoning,
            confidence_score=min(max(confidence_score, 0.0), 1.0),
            context_snapshot=context_snapshot
        )

        async with self._lock:
            try:
                await self.config_state.db.connection.execute(
                    """INSERT INTO claude_decisions
                       (decision_id, timestamp, decision_type, symbol, reasoning,
                        confidence_score, context_snapshot, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        decision.decision_id,
                        decision.timestamp,
                        decision.decision_type.value,
                        decision.symbol,
                        decision.reasoning,
                        decision.confidence_score,
                        json.dumps(decision.context_snapshot),
                        decision.created_at
                    )
                )
                await self.config_state.db.connection.commit()

                logger.info(f"Logged decision {decision.decision_id}: {decision_type.value} {symbol}")

                # Emit event for UI transparency
                if self.event_bus:
                    await self.event_bus.publish(Event(
                        type=EventType.NOTIFICATION,
                        data={
                            "notification_type": "DECISION_LOGGED",
                            "decision_id": decision.decision_id,
                            "decision_type": decision_type.value,
                            "symbol": symbol,
                            "confidence": confidence_score
                        }
                    ))

                return decision

            except Exception as e:
                logger.error(f"Failed to log decision: {e}")
                raise

    async def update_execution_result(
        self,
        decision_id: str,
        execution_result: Dict[str, Any]
    ) -> bool:
        """
        Update a decision with execution results.

        Args:
            decision_id: The decision to update
            execution_result: Execution outcome (fill price, quantity, errors)

        Returns:
            True if updated successfully
        """
        async with self._lock:
            try:
                executed_at = datetime.now(timezone.utc).isoformat()

                await self.config_state.db.connection.execute(
                    """UPDATE claude_decisions
                       SET execution_result = ?, executed_at = ?
                       WHERE decision_id = ?""",
                    (json.dumps(execution_result), executed_at, decision_id)
                )
                await self.config_state.db.connection.commit()

                logger.info(f"Updated execution result for decision {decision_id}")

                # Emit event for UI
                if self.event_bus:
                    await self.event_bus.publish(Event(
                        type=EventType.NOTIFICATION,
                        data={
                            "notification_type": "DECISION_EXECUTED",
                            "decision_id": decision_id,
                            "success": execution_result.get("success", False)
                        }
                    ))

                return True

            except Exception as e:
                logger.error(f"Failed to update execution result: {e}")
                return False

    async def get_decision_history(
        self,
        symbol: Optional[str] = None,
        decision_type: Optional[DecisionType] = None,
        limit: int = 50
    ) -> List[TradingDecision]:
        """
        Get historical trading decisions.

        Args:
            symbol: Filter by symbol (optional)
            decision_type: Filter by decision type (optional)
            limit: Maximum records to return

        Returns:
            List of TradingDecision objects
        """
        async with self._lock:
            try:
                query = """SELECT decision_id, timestamp, decision_type, symbol,
                                  reasoning, confidence_score, context_snapshot,
                                  execution_result, executed_at, created_at
                           FROM claude_decisions"""
                params = []
                conditions = []

                if symbol:
                    conditions.append("symbol = ?")
                    params.append(symbol)

                if decision_type:
                    conditions.append("decision_type = ?")
                    params.append(decision_type.value)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor = await self.config_state.db.connection.execute(query, params)
                rows = await cursor.fetchall()

                decisions = []
                for row in rows:
                    decisions.append(TradingDecision(
                        decision_id=row[0],
                        timestamp=row[1],
                        decision_type=DecisionType(row[2]),
                        symbol=row[3],
                        reasoning=row[4],
                        confidence_score=row[5],
                        context_snapshot=json.loads(row[6]) if row[6] else {},
                        execution_result=json.loads(row[7]) if row[7] else None,
                        executed_at=row[8],
                        created_at=row[9]
                    ))

                return decisions

            except Exception as e:
                logger.error(f"Failed to get decision history: {e}")
                return []

    async def get_decision_by_id(self, decision_id: str) -> Optional[TradingDecision]:
        """Get a specific decision by ID."""
        async with self._lock:
            try:
                cursor = await self.config_state.db.connection.execute(
                    """SELECT decision_id, timestamp, decision_type, symbol,
                              reasoning, confidence_score, context_snapshot,
                              execution_result, executed_at, created_at
                       FROM claude_decisions WHERE decision_id = ?""",
                    (decision_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    return None

                return TradingDecision(
                    decision_id=row[0],
                    timestamp=row[1],
                    decision_type=DecisionType(row[2]),
                    symbol=row[3],
                    reasoning=row[4],
                    confidence_score=row[5],
                    context_snapshot=json.loads(row[6]) if row[6] else {},
                    execution_result=json.loads(row[7]) if row[7] else None,
                    executed_at=row[8],
                    created_at=row[9]
                )

            except Exception as e:
                logger.error(f"Failed to get decision {decision_id}: {e}")
                return None

    async def get_pending_decisions(self, symbol: Optional[str] = None) -> List[TradingDecision]:
        """Get decisions that haven't been executed yet."""
        async with self._lock:
            try:
                if symbol:
                    cursor = await self.config_state.db.connection.execute(
                        """SELECT decision_id, timestamp, decision_type, symbol,
                                  reasoning, confidence_score, context_snapshot,
                                  execution_result, executed_at, created_at
                           FROM claude_decisions
                           WHERE executed_at IS NULL AND symbol = ?
                           ORDER BY timestamp DESC""",
                        (symbol,)
                    )
                else:
                    cursor = await self.config_state.db.connection.execute(
                        """SELECT decision_id, timestamp, decision_type, symbol,
                                  reasoning, confidence_score, context_snapshot,
                                  execution_result, executed_at, created_at
                           FROM claude_decisions
                           WHERE executed_at IS NULL
                           ORDER BY timestamp DESC"""
                    )

                rows = await cursor.fetchall()

                return [
                    TradingDecision(
                        decision_id=row[0],
                        timestamp=row[1],
                        decision_type=DecisionType(row[2]),
                        symbol=row[3],
                        reasoning=row[4],
                        confidence_score=row[5],
                        context_snapshot=json.loads(row[6]) if row[6] else {},
                        execution_result=json.loads(row[7]) if row[7] else None,
                        executed_at=row[8],
                        created_at=row[9]
                    )
                    for row in rows
                ]

            except Exception as e:
                logger.error(f"Failed to get pending decisions: {e}")
                return []
