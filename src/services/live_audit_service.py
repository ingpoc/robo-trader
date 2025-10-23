"""
Live Audit Service

Handles audit logging, compliance tracking, and trade audit trails.
Provides focused audit functionality with proper dependency injection.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import aiosqlite
from loguru import logger

from src.config import Config
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError


class AuditEventType(Enum):
    """Audit event types for live trading."""
    ORDER_PLACED = "order_placed"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    POSITION_UPDATED = "position_updated"
    TRADE_EXECUTED = "trade_executed"
    RISK_BREACH = "risk_breach"
    MODE_CHANGE = "mode_change"


@dataclass
class AuditEntry:
    """Audit log entry."""
    id: str
    timestamp: str
    event_type: AuditEventType
    symbol: Optional[str]
    quantity: Optional[int]
    price: Optional[float]
    order_id: Optional[str]
    broker_order_id: Optional[str]
    correlation_id: Optional[str]
    details: Dict[str, Any]

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class LiveAuditService(EventHandler):
    """
    Live Audit Service - Focused audit logging and compliance tracking.

    Responsibilities:
    - Comprehensive audit trail logging
    - Compliance event tracking
    - Audit data retention and cleanup
    - Audit report generation
    """

    def __init__(self, config: Config, event_bus: EventBus, db_connection: aiosqlite.Connection):
        self.config = config
        self.event_bus = event_bus
        self.db = db_connection
        self._lock = asyncio.Lock()

        # Audit configuration
        self._retention_days = config.get("audit", {}).get("retention_days", 2555)  # 7 years

        # Subscribe to all trading events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.RISK_BREACH, self)
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)

    async def initialize(self) -> None:
        """Initialize the audit service."""
        async with self._lock:
            # Ensure audit table exists
            await self._ensure_audit_table()
            logger.info("Live audit service initialized")

    async def _ensure_audit_table(self) -> None:
        """Ensure audit table exists."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS live_trade_audit (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                symbol TEXT,
                quantity INTEGER,
                price REAL,
                order_id TEXT,
                broker_order_id TEXT,
                correlation_id TEXT,
                details TEXT
            )
        """)

        # Create indexes for performance
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON live_trade_audit(timestamp)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event_type ON live_trade_audit(event_type)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_order_id ON live_trade_audit(order_id)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_correlation_id ON live_trade_audit(correlation_id)
        """)

        await self.db.commit()

    async def log_event(self, event_type: AuditEventType, correlation_id: Optional[str] = None,
                       symbol: Optional[str] = None, quantity: Optional[int] = None,
                       price: Optional[float] = None, order_id: Optional[str] = None,
                       broker_order_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an audit event."""
        async with self._lock:
            audit_entry = AuditEntry(
                id=f"audit_{int(datetime.now(timezone.utc).timestamp() * 1000000)}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type=event_type,
                symbol=symbol,
                quantity=quantity,
                price=price,
                order_id=order_id,
                broker_order_id=broker_order_id,
                correlation_id=correlation_id,
                details=details or {}
            )

            # Insert into database
            await self.db.execute("""
                INSERT INTO live_trade_audit
                (id, timestamp, event_type, symbol, quantity, price, order_id, broker_order_id, correlation_id, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit_entry.id,
                audit_entry.timestamp,
                audit_entry.event_type.value,
                audit_entry.symbol,
                audit_entry.quantity,
                audit_entry.price,
                audit_entry.order_id,
                audit_entry.broker_order_id,
                audit_entry.correlation_id,
                json.dumps(audit_entry.details)
            ))

            await self.db.commit()

            logger.debug(f"Audit logged: {event_type.value} - {audit_entry.id}")

    async def get_audit_logs(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                           event_type: Optional[AuditEventType] = None, order_id: Optional[str] = None,
                           correlation_id: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        """Get audit logs with optional filtering."""
        query = """
            SELECT id, timestamp, event_type, symbol, quantity, price, order_id, broker_order_id, correlation_id, details
            FROM live_trade_audit WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if order_id:
            query += " AND order_id = ?"
            params.append(order_id)

        if correlation_id:
            query += " AND correlation_id = ?"
            params.append(correlation_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = await self.db.execute(query, params)

        audit_logs = []
        async for row in cursor:
            audit_logs.append(AuditEntry(
                id=row[0],
                timestamp=row[1],
                event_type=AuditEventType(row[2]),
                symbol=row[3],
                quantity=row[4],
                price=row[5],
                order_id=row[6],
                broker_order_id=row[7],
                correlation_id=row[8],
                details=json.loads(row[9]) if row[9] else {}
            ))

        return audit_logs

    async def get_order_audit_trail(self, order_id: str) -> List[AuditEntry]:
        """Get complete audit trail for an order."""
        return await self.get_audit_logs(order_id=order_id, limit=1000)

    async def get_correlation_audit_trail(self, correlation_id: str) -> List[AuditEntry]:
        """Get complete audit trail for a correlation ID."""
        return await self.get_audit_logs(correlation_id=correlation_id, limit=1000)

    async def generate_audit_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate comprehensive audit report for a date range."""
        # Get all audit logs for the period
        audit_logs = await self.get_audit_logs(start_date=start_date, end_date=end_date, limit=10000)

        # Aggregate statistics
        event_counts = {}
        orders_placed = 0
        orders_filled = 0
        orders_cancelled = 0
        orders_rejected = 0
        total_volume = 0
        total_value = 0

        for entry in audit_logs:
            event_type = entry.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            if entry.event_type == AuditEventType.ORDER_PLACED:
                orders_placed += 1
            elif entry.event_type == AuditEventType.ORDER_FILLED:
                orders_filled += 1
            elif entry.event_type == AuditEventType.ORDER_CANCELLED:
                orders_cancelled += 1
            elif entry.event_type == AuditEventType.ORDER_REJECTED:
                orders_rejected += 1

            if entry.quantity and entry.price:
                total_volume += entry.quantity
                total_value += entry.quantity * entry.price

        return {
            "report_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_events": len(audit_logs),
                "orders_placed": orders_placed,
                "orders_filled": orders_filled,
                "orders_cancelled": orders_cancelled,
                "orders_rejected": orders_rejected,
                "fill_rate": orders_filled / orders_placed if orders_placed > 0 else 0,
                "total_volume": total_volume,
                "total_value": total_value
            },
            "event_breakdown": event_counts,
            "audit_logs": [
                {
                    "id": entry.id,
                    "timestamp": entry.timestamp,
                    "event_type": entry.event_type.value,
                    "symbol": entry.symbol,
                    "quantity": entry.quantity,
                    "price": entry.price,
                    "order_id": entry.order_id,
                    "correlation_id": entry.correlation_id,
                    "details": entry.details
                }
                for entry in audit_logs[:100]  # Include first 100 entries in detail
            ]
        }

    async def cleanup_old_audit_logs(self) -> int:
        """Clean up audit logs older than retention period."""
        async with self._lock:
            cutoff_date = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) -
                          timedelta(days=self._retention_days)).isoformat()

            cursor = await self.db.execute("""
                DELETE FROM live_trade_audit WHERE timestamp < ?
            """, (cutoff_date,))

            deleted_count = cursor.rowcount
            await self.db.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old audit log entries")

            return deleted_count

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events for audit logging."""
        correlation_id = getattr(event, 'correlation_id', None)

        if event.type == EventType.EXECUTION_ORDER_PLACED:
            await self.log_event(
                event_type=AuditEventType.ORDER_PLACED,
                correlation_id=correlation_id,
                symbol=event.data.get("symbol"),
                quantity=event.data.get("quantity"),
                price=event.data.get("price"),
                order_id=event.data.get("order_id"),
                details=event.data
            )

        elif event.type == EventType.EXECUTION_ORDER_FILLED:
            # Determine specific event type based on data
            status = event.data.get("status", "")
            if status == "filled":
                event_type = AuditEventType.ORDER_FILLED
            elif status == "cancelled":
                event_type = AuditEventType.ORDER_CANCELLED
            elif status == "rejected":
                event_type = AuditEventType.ORDER_REJECTED
            else:
                event_type = AuditEventType.ORDER_SUBMITTED

            await self.log_event(
                event_type=event_type,
                correlation_id=correlation_id,
                symbol=event.data.get("symbol"),
                quantity=event.data.get("quantity"),
                price=event.data.get("price"),
                order_id=event.data.get("order_id"),
                broker_order_id=event.data.get("broker_order_id"),
                details=event.data
            )

        elif event.type == EventType.RISK_BREACH:
            await self.log_event(
                event_type=AuditEventType.RISK_BREACH,
                correlation_id=correlation_id,
                symbol=event.data.get("symbol"),
                details=event.data
            )

        elif event.type == EventType.MARKET_PRICE_UPDATE and event.data.get("updated_positions"):
            # Log position updates
            await self.log_event(
                event_type=AuditEventType.POSITION_UPDATED,
                correlation_id=correlation_id,
                details=event.data
            )

    async def close(self) -> None:
        """Close the audit service."""
        # Perform final cleanup
        await self.cleanup_old_audit_logs()