"""
Risk Management Service

Handles position sizing, risk limit enforcement, stop-loss monitoring,
and pre-trade risk checks.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite
from loguru import logger

from src.config import Config

from ..core.event_bus import Event, EventBus, EventHandler, EventType
from ..core.state_models import RiskDecision


@dataclass
class RiskCheck:
    """Risk check result."""

    approved: bool
    reason: str
    suggested_size: Optional[int] = None
    risk_metrics: Dict[str, Any] = None


@dataclass
class RiskLimit:
    """Risk limit configuration."""

    name: str
    value: float
    current: float = 0.0
    breached: bool = False


class RiskService(EventHandler):
    """
    Risk Management Service - handles all risk-related operations.

    Responsibilities:
    - Position sizing calculations
    - Risk limit enforcement
    - Stop-loss monitoring
    - Pre-trade risk checks
    - Real-time risk aggregation
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "risk.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Risk limits
        self._risk_limits: Dict[str, RiskLimit] = {}

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.PORTFOLIO_POSITION_CHANGE, self)
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)

    async def initialize(self) -> None:
        """Initialize the risk service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            await self._load_risk_limits()
            logger.info("Risk service initialized")

    async def _create_tables(self) -> None:
        """Create risk database tables."""
        schema = """
        -- Risk decisions
        CREATE TABLE IF NOT EXISTS risk_decisions (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            decision TEXT NOT NULL,
            size_qty INTEGER,
            max_risk_inr REAL,
            stop_loss REAL,
            targets TEXT,
            constraints TEXT,
            reasons TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Risk limits
        CREATE TABLE IF NOT EXISTS risk_limits (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            value REAL NOT NULL,
            current REAL DEFAULT 0.0,
            breached INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        );

        -- Stop loss orders
        CREATE TABLE IF NOT EXISTS stop_losses (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            trigger_price REAL NOT NULL,
            quantity REAL NOT NULL,
            order_type TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            triggered_at TEXT
        );

        -- Risk alerts
        CREATE TABLE IF NOT EXISTS risk_alerts (
            id INTEGER PRIMARY KEY,
            alert_type TEXT NOT NULL,
            symbol TEXT,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            resolved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON risk_decisions(symbol);
        CREATE INDEX IF NOT EXISTS idx_limits_name ON risk_limits(name);
        CREATE INDEX IF NOT EXISTS idx_stop_losses_symbol ON stop_losses(symbol);
        CREATE INDEX IF NOT EXISTS idx_alerts_type ON risk_alerts(alert_type);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _load_risk_limits(self) -> None:
        """Load risk limits from database."""
        cursor = await self._db_connection.execute(
            "SELECT name, value, current, breached FROM risk_limits"
        )
        async for row in cursor:
            self._risk_limits[row[0]] = RiskLimit(
                name=row[0], value=row[1], current=row[2], breached=bool(row[3])
            )

        # Initialize default limits if not present
        if not self._risk_limits:
            await self._initialize_default_limits()

    async def _initialize_default_limits(self) -> None:
        """Initialize default risk limits."""
        default_limits = {
            "max_portfolio_risk": RiskLimit("max_portfolio_risk", 0.02),  # 2% max risk
            "max_single_position": RiskLimit(
                "max_single_position", 0.05
            ),  # 5% max per position
            "max_daily_loss": RiskLimit("max_daily_loss", 0.01),  # 1% max daily loss
            "max_sector_exposure": RiskLimit(
                "max_sector_exposure", 0.20
            ),  # 20% max sector
        }

        now = datetime.now(timezone.utc).isoformat()
        for limit in default_limits.values():
            await self._db_connection.execute(
                """
                INSERT OR REPLACE INTO risk_limits (name, value, current, breached, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (limit.name, limit.value, limit.current, int(limit.breached), now),
            )

        await self._db_connection.commit()
        self._risk_limits = default_limits

    async def check_risk(
        self, symbol: str, quantity: int, price: float, portfolio_value: float
    ) -> RiskCheck:
        """Perform pre-trade risk check."""
        async with self._lock:
            position_risk = (quantity * price) / portfolio_value
            max_position_risk = self._risk_limits.get(
                "max_single_position", RiskLimit("", 0.05)
            ).value

            if position_risk > max_position_risk:
                suggested_size = int((max_position_risk * portfolio_value) / price)
                return RiskCheck(
                    approved=False,
                    reason=f"Position risk {position_risk:.1%} exceeds limit {max_position_risk:.1%}",
                    suggested_size=suggested_size,
                    risk_metrics={
                        "position_risk": position_risk,
                        "max_allowed": max_position_risk,
                    },
                )

            # Check portfolio concentration
            # This would need current portfolio data

            return RiskCheck(
                approved=True,
                reason="Risk check passed",
                suggested_size=quantity,
                risk_metrics={"position_risk": position_risk},
            )

    async def create_risk_decision(
        self, symbol: str, size_qty: Optional[int] = None
    ) -> RiskDecision:
        """Create a risk decision for a trade."""
        async with self._lock:
            # Simple risk decision logic - in real implementation this would be more sophisticated
            decision = "approve" if size_qty and size_qty <= 100 else "defer"

            risk_decision = RiskDecision(
                symbol=symbol,
                decision=decision,
                size_qty=size_qty,
                max_risk_inr=5000.0,  # Example limit
                stop=0.95,  # 5% stop loss
                targets=[1.05, 1.10],  # 5% and 10% targets
                constraints=["max_5_percent_risk"],
                reasons=["Standard risk parameters"],
            )

            # Save to database
            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute(
                """
                INSERT INTO risk_decisions
                (symbol, decision, size_qty, max_risk_inr, stop_loss, targets, constraints, reasons, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol,
                    decision,
                    size_qty,
                    risk_decision.max_risk_inr,
                    risk_decision.stop,
                    json.dumps(risk_decision.targets),
                    json.dumps(risk_decision.constraints),
                    json.dumps(risk_decision.reasons),
                    now,
                    now,
                ),
            )
            await self._db_connection.commit()

            return risk_decision

    async def set_stop_loss(
        self,
        symbol: str,
        trigger_price: float,
        quantity: float,
        order_type: str = "MARKET",
    ) -> None:
        """Set a stop loss order."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute(
                """
                INSERT INTO stop_losses (symbol, trigger_price, quantity, order_type, active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
            """,
                (symbol, trigger_price, quantity, order_type, now),
            )
            await self._db_connection.commit()

            logger.info(f"Stop loss set for {symbol} at {trigger_price}")

    async def check_stop_losses(
        self, current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Check if any stop losses should be triggered."""
        async with self._lock:
            triggered = []

            cursor = await self._db_connection.execute(
                """
                SELECT id, symbol, trigger_price, quantity, order_type
                FROM stop_losses
                WHERE active = 1
            """
            )

            async for row in cursor:
                stop_id, symbol, trigger_price, quantity, order_type = row

                if symbol in current_prices:
                    current_price = current_prices[symbol]
                    if current_price <= trigger_price:
                        # Trigger stop loss
                        triggered.append(
                            {
                                "stop_id": stop_id,
                                "symbol": symbol,
                                "trigger_price": trigger_price,
                                "current_price": current_price,
                                "quantity": quantity,
                                "order_type": order_type,
                            }
                        )

                        # Mark as triggered
                        now = datetime.now(timezone.utc).isoformat()
                        await self._db_connection.execute(
                            """
                            UPDATE stop_losses SET active = 0, triggered_at = ? WHERE id = ?
                        """,
                            (now, stop_id),
                        )

            await self._db_connection.commit()

            if triggered:
                # Publish risk breach event
                await self.event_bus.publish(
                    Event(
                        id=f"stop_loss_trigger_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        type=EventType.RISK_STOP_LOSS_TRIGGER,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source="risk_service",
                        data={"triggered_stops": triggered},
                    )
                )

            return triggered

    async def update_risk_limits(self, limits: Dict[str, float]) -> None:
        """Update risk limits."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            for name, value in limits.items():
                await self._db_connection.execute(
                    """
                    INSERT OR REPLACE INTO risk_limits (name, value, updated_at)
                    VALUES (?, ?, ?)
                """,
                    (name, value, now),
                )

                if name in self._risk_limits:
                    self._risk_limits[name].value = value

            await self._db_connection.commit()
            logger.info(f"Updated risk limits: {limits}")

    async def get_risk_limits(self) -> Dict[str, RiskLimit]:
        """Get current risk limits."""
        async with self._lock:
            return self._risk_limits.copy()

    async def create_risk_alert(
        self, alert_type: str, message: str, severity: str, symbol: Optional[str] = None
    ) -> None:
        """Create a risk alert."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute(
                """
                INSERT INTO risk_alerts (alert_type, symbol, message, severity, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (alert_type, symbol, message, severity, now),
            )
            await self._db_connection.commit()

            # Publish risk breach event
            await self.event_bus.publish(
                Event(
                    id=f"risk_alert_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.RISK_BREACH,
                    timestamp=now,
                    source="risk_service",
                    data={
                        "alert_type": alert_type,
                        "symbol": symbol,
                        "message": message,
                        "severity": severity,
                    },
                )
            )

            logger.warning(f"Risk alert created: {alert_type} - {message}")

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.PORTFOLIO_POSITION_CHANGE:
            await self._handle_portfolio_change(event)
        elif event.type == EventType.MARKET_PRICE_UPDATE:
            await self._handle_price_update(event)
        elif event.type == EventType.EXECUTION_ORDER_PLACED:
            await self._handle_order_placed(event)

    async def _handle_portfolio_change(self, event: Event) -> None:
        """Handle portfolio position change."""
        # Check if risk limits are breached
        # This would analyze the portfolio change and check limits
        pass

    async def _handle_price_update(self, event: Event) -> None:
        """Handle market price update."""
        data = event.data
        prices = data.get("prices", {})

        # Check stop losses
        triggered = await self.check_stop_losses(prices)
        if triggered:
            logger.warning(f"Stop losses triggered: {len(triggered)} orders")

    async def _handle_order_placed(self, event: Event) -> None:
        """Handle order placed event."""
        # Perform pre-trade risk check
        data = event.data
        symbol = data.get("symbol")
        quantity = data.get("quantity")
        price = data.get("price")

        if symbol and quantity and price:
            # This would integrate with portfolio service to get current value
            portfolio_value = 100000  # Placeholder
            risk_check = await self.check_risk(symbol, quantity, price, portfolio_value)

            if not risk_check.approved:
                await self.create_risk_alert(
                    "pre_trade_risk_breach",
                    f"Order for {symbol} failed risk check: {risk_check.reason}",
                    "high",
                    symbol,
                )

    async def close(self) -> None:
        """Close the risk service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
