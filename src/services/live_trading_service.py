"""
Live Trading Service - Orchestrator

Orchestrates live trading operations using focused services with proper dependency injection.
Provides unified interface while delegating to specialized services.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from loguru import logger

from src.config import Config
from ..core.state_models import OrderCommand
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError, ValidationError
from ..core.di import DependencyContainer
from ..mcp.broker import ZerodhaBroker
from .live_order_service import LiveOrderService
from .live_position_service import LivePositionService
from .live_audit_service import LiveAuditService


class LiveTradingMode(Enum):
    """Live trading operational modes."""
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"


class LiveTradingService(EventHandler):
    """
    Live Trading Service - Orchestrator for live trading operations.

    Uses dependency injection to coordinate focused services:
    - LiveOrderService: Order execution and management
    - LivePositionService: Position tracking and P&L
    - LiveAuditService: Audit logging and compliance

    Responsibilities:
    - Service orchestration and coordination
    - Trading mode management
    - Unified API interface
    - Cross-service event handling
    """

    def __init__(self, config: Config, event_bus: EventBus, container: DependencyContainer):
        self.config = config
        self.event_bus = event_bus
        self.container = container

        # Services (resolved via DI)
        self.order_service: Optional[LiveOrderService] = None
        self.position_service: Optional[LivePositionService] = None
        self.audit_service: Optional[LiveAuditService] = None
        self.broker: Optional[ZerodhaBroker] = None

        # Trading state
        self._trading_mode = LiveTradingMode.PAPER_TRADING
        self._lock = asyncio.Lock()

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)
        self.event_bus.subscribe(EventType.RISK_BREACH, self)

    async def initialize(self) -> None:
        """Initialize the live trading service and resolve dependencies."""
        async with self._lock:
            # Resolve services from container
            db_connection = await self.container.get("live_trading_db")
            self.broker = await self.container.get("zerodha_broker")

            # Initialize focused services
            self.order_service = LiveOrderService(self.config, self.event_bus, self.broker, db_connection)
            self.position_service = LivePositionService(self.config, self.event_bus, self.broker, db_connection)
            self.audit_service = LiveAuditService(self.config, self.event_bus, db_connection)

            # Initialize all services
            await self.order_service.initialize()
            await self.position_service.initialize()
            await self.audit_service.initialize()

            logger.info("Live trading service initialized with focused services")

    async def set_trading_mode(self, mode: LiveTradingMode) -> None:
        """Set the trading mode."""
        async with self._lock:
            if mode == LiveTradingMode.LIVE_TRADING and not self.broker.is_authenticated():
                raise ValidationError(
                    "Cannot enable live trading without authenticated broker connection",
                    recoverable=False
                )

            self._trading_mode = mode

            # Audit the mode change
            correlation_id = str(uuid.uuid4())
            await self.audit_service.log_event(
                event_type=self.audit_service.AuditEventType.MODE_CHANGE,
                correlation_id=correlation_id,
                details={"new_mode": mode.value}
            )

            logger.info(f"Trading mode changed to: {mode.value}")

    async def place_live_order(self, order_command: OrderCommand) -> str:
        """Place a live order through the broker."""
        async with self._lock:
            # Validate trading mode
            if self._trading_mode != LiveTradingMode.LIVE_TRADING:
                raise ValidationError(
                    f"Live orders not allowed in {self._trading_mode.value} mode",
                    recoverable=False
                )

            # Generate correlation ID for this operation
            correlation_id = str(uuid.uuid4())

            # Delegate to order service
            return await self.order_service.place_order(order_command, correlation_id)

    async def cancel_live_order(self, order_id: str) -> bool:
        """Cancel a live order."""
        correlation_id = str(uuid.uuid4())
        return await self.order_service.cancel_order(order_id, correlation_id)

    async def update_positions_from_broker(self) -> None:
        """Update positions from broker API."""
        correlation_id = str(uuid.uuid4())
        await self.position_service.update_positions_from_broker(correlation_id)

    async def update_market_prices(self, price_updates: Dict[str, float]) -> None:
        """Update market prices and recalculate P&L."""
        correlation_id = str(uuid.uuid4())
        await self.position_service.update_market_prices(price_updates, correlation_id)

    async def get_live_positions(self) -> Dict[str, Any]:
        """Get current live positions."""
        positions = await self.position_service.get_positions()
        return {symbol: position.__dict__ for symbol, position in positions.items()}

    async def get_active_orders(self) -> Dict[str, Any]:
        """Get active live orders."""
        orders = await self.order_service.get_active_orders()
        return {order_id: order.__dict__ for order_id, order in orders.items()}

    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance."""
        # This would integrate with account service
        return {"equity": 100000.0, "cash": 95000.0}

    async def get_trading_mode(self) -> LiveTradingMode:
        """Get current trading mode."""
        return self._trading_mode

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        return await self.position_service.get_portfolio_summary()

    async def get_audit_logs(self, start_date: str = None, end_date: str = None,
                           event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs."""
        from .live_audit_service import AuditEventType

        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type)
            except ValueError:
                pass

        logs = await self.audit_service.get_audit_logs(
            start_date=start_date,
            end_date=end_date,
            event_type=event_type_enum,
            limit=limit
        )

        return [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "event_type": log.event_type.value,
                "symbol": log.symbol,
                "quantity": log.quantity,
                "price": log.price,
                "order_id": log.order_id,
                "correlation_id": log.correlation_id,
                "details": log.details
            }
            for log in logs
        ]

    async def generate_audit_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate comprehensive audit report."""
        return await self.audit_service.generate_audit_report(start_date, end_date)

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events - delegate to appropriate services."""
        # Services handle their own events, but orchestrator can coordinate cross-service actions

        if event.type == EventType.RISK_BREACH:
            # Handle risk breach - may need to cancel orders
            severity = event.data.get("severity")
            if severity == "high":
                logger.warning("High severity risk breach - coordinating emergency actions")
                # Could coordinate emergency order cancellation across services

    async def close(self) -> None:
        """Close the live trading service and all focused services."""
        if self.order_service:
            await self.order_service.close()

        if self.position_service:
            await self.position_service.close()

        if self.audit_service:
            await self.audit_service.close()

        logger.info("Live trading service closed")