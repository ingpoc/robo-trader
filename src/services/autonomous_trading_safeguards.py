"""
Autonomous Trading Safeguards Service

Enforces position limits, daily trading limits, and circuit breakers
for autonomous paper trading execution. Prevents runaway losses.
"""

import asyncio
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from ..core.event_bus import EventBus, Event, EventType
from ..core.database_state.configuration_state import ConfigurationState


class SafeguardViolation(str, Enum):
    """Types of safeguard violations."""
    MAX_TRADES_EXCEEDED = "MAX_TRADES_EXCEEDED"
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    CIRCUIT_BREAKER_ACTIVE = "CIRCUIT_BREAKER_ACTIVE"
    MAX_POSITION_SIZE = "MAX_POSITION_SIZE"
    MAX_POSITIONS = "MAX_POSITIONS"


@dataclass
class SafeguardStatus:
    """Current safeguard state for trading decisions."""
    can_trade: bool
    violation: Optional[SafeguardViolation]
    reason: str
    trades_today: int
    daily_pnl: float
    consecutive_losses: int
    circuit_breaker_active: bool


class AutonomousTradingSafeguards:
    """
    Enforces trading limits and circuit breakers for autonomous execution.

    Safeguards:
    - Max trades per day (default: 10)
    - Max daily loss (default: -5000 INR)
    - Consecutive loss limit (default: 3)
    - Max position size per stock (default: 20% of portfolio)
    - Max total positions (default: 10)
    """

    # Default limits (can be overridden via database)
    DEFAULT_MAX_TRADES = 10
    DEFAULT_MAX_DAILY_LOSS = -5000.0
    DEFAULT_MAX_CONSECUTIVE_LOSSES = 3
    DEFAULT_MAX_POSITION_PCT = 0.20  # 20% of portfolio
    DEFAULT_MAX_POSITIONS = 10

    def __init__(
        self,
        config_state: ConfigurationState,
        event_bus: Optional[EventBus] = None
    ):
        self.config_state = config_state
        self.event_bus = event_bus
        self._lock = asyncio.Lock()
        self._today_date: Optional[str] = None
        self._cached_state: Optional[Dict[str, Any]] = None

    async def check_trade_allowed(
        self,
        symbol: str,
        trade_type: str,
        quantity: int,
        estimated_value: float,
        portfolio_value: float = 100000.0
    ) -> SafeguardStatus:
        """
        Check if a trade is allowed under current safeguards.

        Args:
            symbol: Stock symbol
            trade_type: BUY or SELL
            quantity: Number of shares
            estimated_value: Estimated trade value
            portfolio_value: Current portfolio value

        Returns:
            SafeguardStatus with can_trade flag and details
        """
        today = date.today().isoformat()
        state = await self._get_or_create_today_state(today)

        # Check circuit breaker first
        if state.get("circuit_breaker_active"):
            return SafeguardStatus(
                can_trade=False,
                violation=SafeguardViolation.CIRCUIT_BREAKER_ACTIVE,
                reason=state.get("circuit_breaker_reason", "Circuit breaker triggered"),
                trades_today=state.get("trades_today", 0),
                daily_pnl=state.get("daily_pnl", 0.0),
                consecutive_losses=state.get("consecutive_losses", 0),
                circuit_breaker_active=True
            )

        # Check max trades per day
        max_trades = state.get("max_trades_limit", self.DEFAULT_MAX_TRADES)
        if state.get("trades_today", 0) >= max_trades:
            return SafeguardStatus(
                can_trade=False,
                violation=SafeguardViolation.MAX_TRADES_EXCEEDED,
                reason=f"Max daily trades ({max_trades}) reached",
                trades_today=state.get("trades_today", 0),
                daily_pnl=state.get("daily_pnl", 0.0),
                consecutive_losses=state.get("consecutive_losses", 0),
                circuit_breaker_active=False
            )

        # Check max daily loss
        max_loss = state.get("max_daily_loss", self.DEFAULT_MAX_DAILY_LOSS)
        if state.get("daily_pnl", 0.0) <= max_loss:
            await self._activate_circuit_breaker(today, "Max daily loss exceeded")
            return SafeguardStatus(
                can_trade=False,
                violation=SafeguardViolation.MAX_DAILY_LOSS,
                reason=f"Daily loss limit ({max_loss} INR) exceeded",
                trades_today=state.get("trades_today", 0),
                daily_pnl=state.get("daily_pnl", 0.0),
                consecutive_losses=state.get("consecutive_losses", 0),
                circuit_breaker_active=True
            )

        # Check consecutive losses
        max_consecutive = state.get("max_consecutive_losses", self.DEFAULT_MAX_CONSECUTIVE_LOSSES)
        if state.get("consecutive_losses", 0) >= max_consecutive:
            await self._activate_circuit_breaker(today, "Consecutive loss limit exceeded")
            return SafeguardStatus(
                can_trade=False,
                violation=SafeguardViolation.CONSECUTIVE_LOSSES,
                reason=f"Consecutive losses ({max_consecutive}) limit reached",
                trades_today=state.get("trades_today", 0),
                daily_pnl=state.get("daily_pnl", 0.0),
                consecutive_losses=state.get("consecutive_losses", 0),
                circuit_breaker_active=True
            )

        # Check position size limit (for BUY orders)
        if trade_type == "BUY":
            max_position_value = portfolio_value * self.DEFAULT_MAX_POSITION_PCT
            if estimated_value > max_position_value:
                return SafeguardStatus(
                    can_trade=False,
                    violation=SafeguardViolation.MAX_POSITION_SIZE,
                    reason=f"Position size ({estimated_value}) exceeds {self.DEFAULT_MAX_POSITION_PCT*100}% limit",
                    trades_today=state.get("trades_today", 0),
                    daily_pnl=state.get("daily_pnl", 0.0),
                    consecutive_losses=state.get("consecutive_losses", 0),
                    circuit_breaker_active=False
                )

            # Check max positions
            if state.get("positions_count", 0) >= self.DEFAULT_MAX_POSITIONS:
                return SafeguardStatus(
                    can_trade=False,
                    violation=SafeguardViolation.MAX_POSITIONS,
                    reason=f"Max positions ({self.DEFAULT_MAX_POSITIONS}) reached",
                    trades_today=state.get("trades_today", 0),
                    daily_pnl=state.get("daily_pnl", 0.0),
                    consecutive_losses=state.get("consecutive_losses", 0),
                    circuit_breaker_active=False
                )

        # All checks passed
        return SafeguardStatus(
            can_trade=True,
            violation=None,
            reason="Trade allowed",
            trades_today=state.get("trades_today", 0),
            daily_pnl=state.get("daily_pnl", 0.0),
            consecutive_losses=state.get("consecutive_losses", 0),
            circuit_breaker_active=False
        )

    async def record_trade_result(
        self,
        trade_id: str,
        realized_pnl: float,
        is_position_opened: bool = False,
        is_position_closed: bool = False
    ) -> None:
        """
        Record trade result and update safeguard state.

        Args:
            trade_id: Trade identifier
            realized_pnl: Realized P&L from trade
            is_position_opened: True if new position opened
            is_position_closed: True if position was closed
        """
        today = date.today().isoformat()
        async with self._lock:
            state = await self._get_or_create_today_state(today)

            # Update counters
            trades_today = state.get("trades_today", 0) + 1
            daily_pnl = state.get("daily_pnl", 0.0) + realized_pnl
            positions_count = state.get("positions_count", 0)

            if is_position_opened:
                positions_count += 1
            if is_position_closed:
                positions_count = max(0, positions_count - 1)

            # Update consecutive losses
            consecutive_losses = state.get("consecutive_losses", 0)
            if realized_pnl < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0  # Reset on profit

            now = datetime.now(timezone.utc).isoformat()

            await self.config_state.db.connection.execute(
                """UPDATE trading_safeguards SET
                   trades_today = ?, daily_pnl = ?, consecutive_losses = ?,
                   positions_count = ?, last_trade_timestamp = ?, updated_at = ?
                   WHERE safeguard_date = ?""",
                (trades_today, daily_pnl, consecutive_losses, positions_count, now, now, today)
            )
            await self.config_state.db.connection.commit()

            # Clear cache
            self._cached_state = None

            logger.info(f"Trade {trade_id} recorded: pnl={realized_pnl}, total={daily_pnl}, losses={consecutive_losses}")

            # Emit event for UI
            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=EventType.NOTIFICATION,
                    data={
                        "notification_type": "SAFEGUARD_UPDATE",
                        "trades_today": trades_today,
                        "daily_pnl": daily_pnl,
                        "consecutive_losses": consecutive_losses
                    }
                ))

    async def get_remaining_daily_trades(self) -> int:
        """Get remaining trades allowed for today."""
        today = date.today().isoformat()
        state = await self._get_or_create_today_state(today)
        max_trades = state.get("max_trades_limit", self.DEFAULT_MAX_TRADES)
        trades_today = state.get("trades_today", 0)
        return max(0, max_trades - trades_today)

    async def get_current_status(self) -> Dict[str, Any]:
        """Get current safeguard status for today."""
        today = date.today().isoformat()
        state = await self._get_or_create_today_state(today)
        return {
            "date": today,
            "trades_today": state.get("trades_today", 0),
            "daily_pnl": state.get("daily_pnl", 0.0),
            "consecutive_losses": state.get("consecutive_losses", 0),
            "circuit_breaker_active": bool(state.get("circuit_breaker_active")),
            "circuit_breaker_reason": state.get("circuit_breaker_reason"),
            "positions_count": state.get("positions_count", 0),
            "limits": {
                "max_trades": state.get("max_trades_limit", self.DEFAULT_MAX_TRADES),
                "max_daily_loss": state.get("max_daily_loss", self.DEFAULT_MAX_DAILY_LOSS),
                "max_consecutive_losses": state.get("max_consecutive_losses", self.DEFAULT_MAX_CONSECUTIVE_LOSSES),
                "max_position_pct": self.DEFAULT_MAX_POSITION_PCT,
                "max_positions": self.DEFAULT_MAX_POSITIONS
            }
        }

    async def reset_circuit_breaker(self, reason: str = "Manual reset") -> bool:
        """Manually reset circuit breaker (for emergency override)."""
        today = date.today().isoformat()
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()
                await self.config_state.db.connection.execute(
                    """UPDATE trading_safeguards SET
                       circuit_breaker_active = 0, circuit_breaker_reason = ?,
                       consecutive_losses = 0, updated_at = ?
                       WHERE safeguard_date = ?""",
                    (f"Reset: {reason}", now, today)
                )
                await self.config_state.db.connection.commit()
                self._cached_state = None
                logger.warning(f"Circuit breaker reset: {reason}")
                return True
            except Exception as e:
                logger.error(f"Failed to reset circuit breaker: {e}")
                return False

    async def _get_or_create_today_state(self, today: str) -> Dict[str, Any]:
        """Get or create today's safeguard state."""
        # Use cache if same day
        if self._today_date == today and self._cached_state:
            return self._cached_state

        async with self._lock:
            cursor = await self.config_state.db.connection.execute(
                "SELECT * FROM trading_safeguards WHERE safeguard_date = ?", (today,)
            )
            row = await cursor.fetchone()

            if not row:
                # Create new day record
                now = datetime.now(timezone.utc).isoformat()
                await self.config_state.db.connection.execute(
                    """INSERT INTO trading_safeguards
                       (safeguard_date, trades_today, daily_pnl, consecutive_losses,
                        circuit_breaker_active, positions_count, max_trades_limit,
                        max_daily_loss, max_consecutive_losses, created_at, updated_at)
                       VALUES (?, 0, 0.0, 0, 0, 0, ?, ?, ?, ?, ?)""",
                    (today, self.DEFAULT_MAX_TRADES, self.DEFAULT_MAX_DAILY_LOSS,
                     self.DEFAULT_MAX_CONSECUTIVE_LOSSES, now, now)
                )
                await self.config_state.db.connection.commit()

                self._cached_state = {
                    "safeguard_date": today, "trades_today": 0, "daily_pnl": 0.0,
                    "consecutive_losses": 0, "circuit_breaker_active": 0,
                    "positions_count": 0, "max_trades_limit": self.DEFAULT_MAX_TRADES,
                    "max_daily_loss": self.DEFAULT_MAX_DAILY_LOSS,
                    "max_consecutive_losses": self.DEFAULT_MAX_CONSECUTIVE_LOSSES
                }
            else:
                columns = [desc[0] for desc in cursor.description]
                self._cached_state = dict(zip(columns, row))

            self._today_date = today
            return self._cached_state

    async def _activate_circuit_breaker(self, today: str, reason: str) -> None:
        """Activate circuit breaker."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            await self.config_state.db.connection.execute(
                """UPDATE trading_safeguards SET
                   circuit_breaker_active = 1, circuit_breaker_reason = ?, updated_at = ?
                   WHERE safeguard_date = ?""",
                (reason, now, today)
            )
            await self.config_state.db.connection.commit()
            self._cached_state = None
            logger.warning(f"Circuit breaker activated: {reason}")

            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=EventType.NOTIFICATION,
                    data={
                        "notification_type": "CIRCUIT_BREAKER_ACTIVATED",
                        "reason": reason,
                        "timestamp": now
                    }
                ))
