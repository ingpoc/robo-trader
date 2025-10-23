"""
Enterprise Security & Compliance Service

Provides enterprise-grade security features including multi-tenancy, audit logging,
data encryption, and regulatory compliance for production deployments.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import secrets
import base64
import os
import aiosqlite
from cryptography.fernet import Fernet
from loguru import logger

from src.config import Config
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError, ValidationError, APIError


class TenantStatus(Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class AuditEventType(Enum):
    """Audit event types."""
    LOGIN = "login"
    LOGOUT = "logout"
    TRADE_EXECUTED = "trade_executed"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    CONFIG_CHANGED = "config_changed"
    RISK_BREACH = "risk_breach"
    SYSTEM_ACCESS = "system_access"


@dataclass
class Tenant:
    """Multi-tenant organization."""
    tenant_id: str
    name: str
    status: TenantStatus
    config: Dict[str, Any]
    created_at: str
    updated_at: str

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class AuditLogEntry:
    """Audit log entry for compliance."""
    id: str
    tenant_id: str
    user_id: Optional[str]
    event_type: AuditEventType
    resource_type: str
    resource_id: str
    action: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: str
    checksum: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.checksum:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """Calculate tamper-proof checksum."""
        data = f"{self.tenant_id}{self.event_type.value}{self.resource_id}{self.action}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()


class EnterpriseSecurityService(EventHandler):
    """
    Enterprise Security & Compliance Service.

    Responsibilities:
    - Multi-tenant architecture support
    - Comprehensive audit logging
    - Data encryption and secure storage
    - Regulatory compliance features
    - Access control and authentication
    - Security monitoring and alerting
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "enterprise_security.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Encryption
        self._encryption_key = self._load_or_generate_key()
        self._cipher = Fernet(self._encryption_key)

        # Tenants and sessions
        self._tenants: Dict[str, Tenant] = {}
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

        # Compliance settings
        self._retention_days = 2555  # 7 years for regulatory compliance
        self._audit_enabled = True

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.RISK_BREACH, self)

    def _load_or_generate_key(self) -> bytes:
        """Load encryption key from environment or generate new one."""
        key_env = "ENCRYPTION_KEY"
        key_b64 = os.getenv(key_env)

        if key_b64:
            try:
                return base64.b64decode(key_b64)
            except Exception as e:
                logger.warning(f"Invalid encryption key in {key_env}, generating new one: {e}")

        # Generate new key
        key = Fernet.generate_key()
        key_b64 = base64.b64encode(key).decode()

        logger.warning(f"Generated new encryption key. Set {key_env}={key_b64} in environment for persistence")
        return key

    async def initialize(self) -> None:
        """Initialize the enterprise security service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            await self._load_tenants()
            await self._setup_default_tenant()
            logger.info("Enterprise security service initialized")

    async def _create_tables(self) -> None:
        """Create enterprise security database tables."""
        schema = """
        -- Tenants
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Audit log
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT,
            event_type TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TEXT NOT NULL,
            checksum TEXT NOT NULL
        );

        -- Encrypted data store
        CREATE TABLE IF NOT EXISTS encrypted_data (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            data_type TEXT NOT NULL,
            encrypted_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT
        );

        -- Access control
        CREATE TABLE IF NOT EXISTS access_control (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            permissions TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            expires_at TEXT
        );

        -- Security alerts
        CREATE TABLE IF NOT EXISTS security_alerts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            resolved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_audit_tenant_timestamp ON audit_log(tenant_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
        CREATE INDEX IF NOT EXISTS idx_encrypted_tenant_type ON encrypted_data(tenant_id, data_type);
        CREATE INDEX IF NOT EXISTS idx_access_tenant_user ON access_control(tenant_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_tenant_created ON security_alerts(tenant_id, created_at);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _load_tenants(self) -> None:
        """Load tenants from database."""
        cursor = await self._db_connection.execute("""
            SELECT tenant_id, name, status, config, created_at, updated_at
            FROM tenants
            WHERE status = 'active'
        """)

        async for row in cursor:
            tenant = Tenant(
                tenant_id=row[0],
                name=row[1],
                status=TenantStatus(row[2]),
                config=json.loads(row[3]),
                created_at=row[4],
                updated_at=row[5]
            )
            self._tenants[row[0]] = tenant

    async def _setup_default_tenant(self) -> None:
        """Setup default tenant if none exists."""
        if not self._tenants:
            default_tenant = Tenant(
                tenant_id="default",
                name="Default Organization",
                status=TenantStatus.ACTIVE,
                config={
                    "max_users": 10,
                    "max_daily_trades": 100,
                    "risk_limits": {
                        "max_portfolio_risk": 0.02,
                        "max_single_position": 0.05
                    }
                }
            )

            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute("""
                INSERT INTO tenants (tenant_id, name, status, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                default_tenant.tenant_id,
                default_tenant.name,
                default_tenant.status.value,
                json.dumps(default_tenant.config),
                now,
                now
            ))
            await self._db_connection.commit()

            self._tenants[default_tenant.tenant_id] = default_tenant
            logger.info("Created default tenant")

    async def create_tenant(self, tenant_id: str, name: str, config: Dict[str, Any]) -> Tenant:
        """Create a new tenant."""
        async with self._lock:
            if tenant_id in self._tenants:
                raise ValidationError(f"Tenant {tenant_id} already exists", recoverable=False)

            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                status=TenantStatus.ACTIVE,
                config=config
            )

            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute("""
                INSERT INTO tenants (tenant_id, name, status, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                tenant.tenant_id,
                tenant.name,
                tenant.status.value,
                json.dumps(tenant.config),
                now,
                now
            ))
            await self._db_connection.commit()

            self._tenants[tenant_id] = tenant

            # Audit log
            await self._audit_log(
                tenant_id=tenant_id,
                event_type=AuditEventType.CONFIG_CHANGED,
                resource_type="tenant",
                resource_id=tenant_id,
                action="created",
                details={"name": name, "config": config}
            )

            logger.info(f"Created tenant: {tenant_id}")
            return tenant

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        async with self._lock:
            return self._tenants.get(tenant_id)

    async def update_tenant_config(self, tenant_id: str, config: Dict[str, Any]) -> None:
        """Update tenant configuration."""
        async with self._lock:
            if tenant_id not in self._tenants:
                raise ValidationError(f"Tenant {tenant_id} not found", recoverable=False)

            tenant = self._tenants[tenant_id]
            tenant.config.update(config)
            tenant.updated_at = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute("""
                UPDATE tenants SET config = ?, updated_at = ? WHERE tenant_id = ?
            """, (json.dumps(tenant.config), tenant.updated_at, tenant_id))
            await self._db_connection.commit()

            # Audit log
            await self._audit_log(
                tenant_id=tenant_id,
                event_type=AuditEventType.CONFIG_CHANGED,
                resource_type="tenant",
                resource_id=tenant_id,
                action="config_updated",
                details={"updated_config": config}
            )

    async def encrypt_data(self, tenant_id: str, data_type: str, data: Dict[str, Any]) -> str:
        """Encrypt and store sensitive data."""
        async with self._lock:
            # Serialize data
            data_json = json.dumps(data)

            # Encrypt
            encrypted_data = self._cipher.encrypt(data_json.encode()).decode()

            # Store in database
            data_id = f"{tenant_id}_{data_type}_{int(datetime.now(timezone.utc).timestamp())}"
            now = datetime.now(timezone.utc).isoformat()
            expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()  # 1 year expiry

            await self._db_connection.execute("""
                INSERT INTO encrypted_data (id, tenant_id, data_type, encrypted_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data_id, tenant_id, data_type, encrypted_data, now, expires_at))
            await self._db_connection.commit()

            return data_id

    async def decrypt_data(self, data_id: str) -> Dict[str, Any]:
        """Decrypt stored data."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT encrypted_data FROM encrypted_data WHERE id = ?
            """, (data_id,))

            row = await cursor.fetchone()
            if not row:
                raise ValidationError(f"Encrypted data {data_id} not found", recoverable=False)

            # Decrypt
            try:
                decrypted_data = self._cipher.decrypt(row[0].encode()).decode()
                return json.loads(decrypted_data)
            except Exception as e:
                raise APIError(f"Failed to decrypt data: {e}", recoverable=False)

    async def _audit_log(self, tenant_id: str, event_type: AuditEventType, resource_type: str,
                        resource_id: str, action: str, details: Dict[str, Any] = None,
                        user_id: str = None, ip_address: str = None, user_agent: str = None) -> None:
        """Create audit log entry."""
        if not self._audit_enabled:
            return

        audit_entry = AuditLogEntry(
            id=f"audit_{int(datetime.now(timezone.utc).timestamp() * 1000000)}",
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )

        await self._db_connection.execute("""
            INSERT INTO audit_log
            (id, tenant_id, user_id, event_type, resource_type, resource_id, action, details,
             ip_address, user_agent, timestamp, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_entry.id,
            audit_entry.tenant_id,
            audit_entry.user_id,
            audit_entry.event_type.value,
            audit_entry.resource_type,
            audit_entry.resource_id,
            audit_entry.action,
            json.dumps(audit_entry.details),
            audit_entry.ip_address,
            audit_entry.user_agent,
            audit_entry.timestamp,
            audit_entry.checksum
        ))
        await self._db_connection.commit()

    async def get_audit_logs(self, tenant_id: str, start_date: str = None, end_date: str = None,
                           event_type: AuditEventType = None, limit: int = 100) -> List[AuditLogEntry]:
        """Get audit logs for a tenant."""
        query = """
            SELECT id, tenant_id, user_id, event_type, resource_type, resource_id, action,
                   details, ip_address, user_agent, timestamp, checksum
            FROM audit_log WHERE tenant_id = ?
        """
        params = [tenant_id]

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = await self._db_connection.execute(query, params)

        audit_logs = []
        async for row in cursor:
            audit_logs.append(AuditLogEntry(
                id=row[0],
                tenant_id=row[1],
                user_id=row[2],
                event_type=AuditEventType(row[3]),
                resource_type=row[4],
                resource_id=row[5],
                action=row[6],
                details=json.loads(row[7]) if row[7] else {},
                ip_address=row[8],
                user_agent=row[9],
                timestamp=row[10],
                checksum=row[11]
            ))

        return audit_logs

    async def check_access_control(self, tenant_id: str, user_id: str, resource_type: str,
                                 resource_id: str, required_permission: str) -> bool:
        """Check if user has access to a resource."""
        cursor = await self._db_connection.execute("""
            SELECT permissions FROM access_control
            WHERE tenant_id = ? AND user_id = ? AND resource_type = ? AND resource_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
        """, (tenant_id, user_id, resource_type, resource_id, datetime.now(timezone.utc).isoformat()))

        row = await cursor.fetchone()
        if not row:
            return False

        permissions = json.loads(row[0])
        return required_permission in permissions

    async def grant_access(self, tenant_id: str, user_id: str, resource_type: str,
                          resource_id: str, permissions: List[str], expires_at: str = None) -> None:
        """Grant access permissions to a user."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute("""
                INSERT OR REPLACE INTO access_control
                (tenant_id, user_id, resource_type, resource_id, permissions, granted_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tenant_id, user_id, resource_type, resource_id,
                  json.dumps(permissions), now, expires_at))
            await self._db_connection.commit()

            # Audit log
            await self._audit_log(
                tenant_id=tenant_id,
                event_type=AuditEventType.CONFIG_CHANGED,
                resource_type="access_control",
                resource_id=f"{user_id}:{resource_type}:{resource_id}",
                action="access_granted",
                details={"permissions": permissions, "expires_at": expires_at}
            )

    async def create_security_alert(self, tenant_id: str, alert_type: str, severity: str,
                                  message: str, details: Dict[str, Any] = None) -> None:
        """Create a security alert."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute("""
                INSERT INTO security_alerts (tenant_id, alert_type, severity, message, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tenant_id, alert_type, severity, message,
                  json.dumps(details) if details else None, now))
            await self._db_connection.commit()

            # Emit security alert event
            await self.event_bus.publish(Event(
                id=f"security_alert_{tenant_id}_{int(datetime.now(timezone.utc).timestamp())}",
                type=EventType.RISK_BREACH,
                timestamp=now,
                source="enterprise_security_service",
                data={
                    "tenant_id": tenant_id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "details": details
                }
            ))

    async def get_security_alerts(self, tenant_id: str, unresolved_only: bool = True) -> List[Dict[str, Any]]:
        """Get security alerts for a tenant."""
        query = """
            SELECT id, alert_type, severity, message, details, resolved, created_at, resolved_at
            FROM security_alerts WHERE tenant_id = ?
        """
        params = [tenant_id]

        if unresolved_only:
            query += " AND resolved = 0"

        query += " ORDER BY created_at DESC"

        cursor = await self._db_connection.execute(query, params)

        alerts = []
        async for row in cursor:
            alerts.append({
                "id": row[0],
                "alert_type": row[1],
                "severity": row[2],
                "message": row[3],
                "details": json.loads(row[4]) if row[4] else None,
                "resolved": bool(row[5]),
                "created_at": row[6],
                "resolved_at": row[7]
            })

        return alerts

    async def cleanup_expired_data(self) -> None:
        """Clean up expired encrypted data and access controls."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            # Clean up expired encrypted data
            await self._db_connection.execute("""
                DELETE FROM encrypted_data WHERE expires_at < ?
            """, (now,))

            # Clean up expired access controls
            await self._db_connection.execute("""
                DELETE FROM access_control WHERE expires_at < ?
            """, (now,))

            # Clean up old audit logs (keep 7 years for compliance)
            retention_cutoff = (datetime.now(timezone.utc) - timedelta(days=self._retention_days)).isoformat()
            await self._db_connection.execute("""
                DELETE FROM audit_log WHERE timestamp < ?
            """, (retention_cutoff,))

            await self._db_connection.commit()

            deleted_count = self._db_connection.total_changes
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired security records")

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events for audit logging."""
        # Extract tenant_id from event data if available
        tenant_id = event.data.get("tenant_id", "default")

        if event.type == EventType.EXECUTION_ORDER_PLACED:
            await self._audit_log(
                tenant_id=tenant_id,
                event_type=AuditEventType.ORDER_PLACED,
                resource_type="order",
                resource_id=event.data.get("order_id", "unknown"),
                action="placed",
                details=event.data
            )

        elif event.type == EventType.EXECUTION_ORDER_FILLED:
            await self._audit_log(
                tenant_id=tenant_id,
                event_type=AuditEventType.TRADE_EXECUTED,
                resource_type="trade",
                resource_id=event.data.get("order_id", "unknown"),
                action="executed",
                details=event.data
            )

        elif event.type == EventType.RISK_BREACH:
            await self._audit_log(
                tenant_id=tenant_id,
                event_type=AuditEventType.RISK_BREACH,
                resource_type="risk",
                resource_id=event.data.get("symbol", "system"),
                action="breach_detected",
                details=event.data
            )

    async def close(self) -> None:
        """Close the enterprise security service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None