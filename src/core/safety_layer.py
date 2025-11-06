"""
Safety & Compliance Layer

Provides multi-layer safety for the trading system including:
- Pre-execution hooks and validation
- Circuit breakers for external API failures
- Immutable audit logging
- Multi-stage approval workflows
- Emergency kill switches
- Compliance rule enforcement
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiosqlite
from loguru import logger

from src.config import Config

from ..core.event_bus import Event, EventBus, EventHandler, EventType


class SafetyLevel(Enum):
    """Safety levels for operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    """Approval workflow status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class SafetyRule:
    """Safety rule definition."""

    name: str
    description: str
    level: SafetyLevel
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], None]
    enabled: bool = True


@dataclass
class ApprovalWorkflow:
    """Multi-stage approval workflow."""

    workflow_id: str
    name: str
    stages: List[Dict[str, Any]] = field(default_factory=list)
    current_stage: int = 0
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at


@dataclass
class AuditLogEntry:
    """Immutable audit log entry."""

    event_type: str
    actor: str
    resource: str
    action: str
    details: Dict[str, Any]
    timestamp: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker for external service failures."""

    def __init__(
        self, service_name: str, failure_threshold: int = 5, recovery_timeout: int = 300
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened for {self.service_name}")

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            # Check if recovery timeout has passed
            if (
                self.last_failure_time
                and (asyncio.get_event_loop().time() - self.last_failure_time)
                > self.recovery_timeout
            ):
                self.state = "half-open"
                return True
            return False
        elif self.state == "half-open":
            return True
        return False


class SafetyLayer(EventHandler):
    """
    Safety & Compliance Layer - provides multiple protection layers.

    Responsibilities:
    - Pre-execution validation hooks
    - Circuit breakers for external services
    - Immutable audit logging
    - Multi-stage approval workflows
    - Emergency kill switches
    - Compliance rule enforcement
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "safety.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Safety components
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._safety_rules: List[SafetyRule] = []
        self._kill_switch_active = False

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)
        self.event_bus.subscribe(EventType.RISK_BREACH, self)
        self.event_bus.subscribe(EventType.SYSTEM_ERROR, self)

    async def initialize(self) -> None:
        """Initialize the safety layer."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            await self._initialize_circuit_breakers()
            await self._initialize_safety_rules()
            logger.info("Safety layer initialized")

    async def _create_tables(self) -> None:
        """Create safety database tables."""
        schema = """
        -- Audit log (immutable append-only)
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT
        );

        -- Approval workflows
        CREATE TABLE IF NOT EXISTS approval_workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            stages TEXT NOT NULL,
            current_stage INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Kill switch state
        CREATE TABLE IF NOT EXISTS kill_switch (
            id INTEGER PRIMARY KEY,
            active INTEGER NOT NULL,
            activated_by TEXT,
            reason TEXT,
            activated_at TEXT,
            deactivated_at TEXT
        );

        -- Circuit breaker state
        CREATE TABLE IF NOT EXISTS circuit_breaker_state (
            service_name TEXT PRIMARY KEY,
            failure_count INTEGER NOT NULL,
            last_failure_time REAL,
            state TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor);
        CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource);
        CREATE INDEX IF NOT EXISTS idx_workflows_status ON approval_workflows(status);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _initialize_circuit_breakers(self) -> None:
        """Initialize circuit breakers for external services."""
        # Load from database or create defaults
        cursor = await self._db_connection.execute(
            "SELECT * FROM circuit_breaker_state"
        )
        existing = {}
        async for row in cursor:
            existing[row[0]] = {
                "failure_count": row[1],
                "last_failure_time": row[2],
                "state": row[3],
            }

        # Initialize standard circuit breakers
        services = ["zerodha_api", "market_data_feed", "claude_api", "database"]
        for service in services:
            if service in existing:
                cb = CircuitBreaker(service)
                cb.failure_count = existing[service]["failure_count"]
                cb.last_failure_time = existing[service]["last_failure_time"]
                cb.state = existing[service]["state"]
            else:
                cb = CircuitBreaker(service)

            self._circuit_breakers[service] = cb

    async def _initialize_safety_rules(self) -> None:
        """Initialize safety rules."""
        self._safety_rules = [
            SafetyRule(
                name="max_order_value_check",
                description="Check maximum order value limits",
                level=SafetyLevel.HIGH,
                condition=lambda data: data.get("order_value", 0)
                > 50000,  # ₹50,000 limit
                action=self._reject_high_value_order,
            ),
            SafetyRule(
                name="market_hours_check",
                description="Ensure trading only during market hours",
                level=SafetyLevel.MEDIUM,
                condition=self._is_outside_market_hours,
                action=self._reject_outside_hours,
            ),
            SafetyRule(
                name="circuit_breaker_check",
                description="Check if external services are available",
                level=SafetyLevel.CRITICAL,
                condition=self._are_critical_services_down,
                action=self._trigger_emergency_stop,
            ),
            SafetyRule(
                name="duplicate_order_check",
                description="Prevent duplicate orders within short time",
                level=SafetyLevel.MEDIUM,
                condition=self._is_duplicate_order,
                action=self._reject_duplicate_order,
            ),
        ]

    async def validate_operation(
        self, operation: str, data: Dict[str, Any], actor: str = "system"
    ) -> Dict[str, Any]:
        """Validate an operation against safety rules."""
        async with self._lock:
            if self._kill_switch_active:
                return {
                    "approved": False,
                    "reason": "Kill switch is active",
                    "safety_level": SafetyLevel.CRITICAL.value,
                }

            # Log the validation attempt
            await self._audit_log(
                "operation_validation",
                actor,
                operation,
                "validate",
                {"operation": operation, "data": data},
            )

            # Check safety rules
            for rule in self._safety_rules:
                if rule.enabled and rule.condition(data):
                    await rule.action(data)
                    return {
                        "approved": False,
                        "reason": f"Safety rule violation: {rule.description}",
                        "safety_level": rule.level.value,
                        "rule": rule.name,
                    }

            # Check circuit breakers
            if operation in ["place_order", "get_market_data"]:
                service = (
                    "zerodha_api" if operation == "place_order" else "market_data_feed"
                )
                if not self._circuit_breakers[service].can_execute():
                    return {
                        "approved": False,
                        "reason": f"Circuit breaker open for {service}",
                        "safety_level": SafetyLevel.CRITICAL.value,
                    }

            return {
                "approved": True,
                "reason": "Validation passed",
                "safety_level": SafetyLevel.LOW.value,
            }

    async def _audit_log(
        self,
        event_type: str,
        actor: str,
        resource: str,
        action: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Create an immutable audit log entry."""
        entry = AuditLogEntry(
            event_type=event_type,
            actor=actor,
            resource=resource,
            action=action,
            details=details,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self._db_connection.execute(
            """
            INSERT INTO audit_log
            (event_type, actor, resource, action, details, timestamp, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entry.event_type,
                entry.actor,
                entry.resource,
                entry.action,
                json.dumps(entry.details),
                entry.timestamp,
                entry.ip_address,
                entry.user_agent,
            ),
        )
        await self._db_connection.commit()

    async def create_approval_workflow(
        self, name: str, stages: List[Dict[str, Any]]
    ) -> str:
        """Create a multi-stage approval workflow."""
        async with self._lock:
            workflow_id = (
                f"workflow_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            )

            workflow = ApprovalWorkflow(
                workflow_id=workflow_id,
                name=name,
                stages=stages,
                status=ApprovalStatus.PENDING,
            )

            await self._db_connection.execute(
                """
                INSERT INTO approval_workflows
                (id, name, stages, current_stage, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    workflow.workflow_id,
                    workflow.name,
                    json.dumps(workflow.stages),
                    workflow.current_stage,
                    workflow.status.value,
                    workflow.created_at,
                    workflow.updated_at,
                ),
            )
            await self._db_connection.commit()

            await self._audit_log(
                "workflow_created",
                "system",
                workflow_id,
                "create",
                {"name": name, "stages": len(stages)},
            )

            return workflow_id

    async def approve_workflow_stage(
        self, workflow_id: str, approver: str, approved: bool, comments: str = ""
    ) -> bool:
        """Approve or reject a workflow stage."""
        async with self._lock:
            # Get current workflow
            cursor = await self._db_connection.execute(
                """
                SELECT stages, current_stage, status FROM approval_workflows WHERE id = ?
            """,
                (workflow_id,),
            )

            row = await cursor.fetchone()
            if not row:
                return False

            stages = json.loads(row[0])
            current_stage = row[1]
            status = ApprovalStatus(row[2])

            if status != ApprovalStatus.PENDING:
                return False

            # Update stage
            if current_stage < len(stages):
                stages[current_stage]["approved"] = approved
                stages[current_stage]["approved_by"] = approver
                stages[current_stage]["approved_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
                stages[current_stage]["comments"] = comments

                new_status = (
                    ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
                )

                if approved and current_stage + 1 < len(stages):
                    # Move to next stage
                    new_current_stage = current_stage + 1
                    new_status = ApprovalStatus.PENDING
                else:
                    # Final stage or rejected
                    new_current_stage = current_stage

                # Update database
                await self._db_connection.execute(
                    """
                    UPDATE approval_workflows
                    SET stages = ?, current_stage = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (
                        json.dumps(stages),
                        new_current_stage,
                        new_status.value,
                        datetime.now(timezone.utc).isoformat(),
                        workflow_id,
                    ),
                )
                await self._db_connection.commit()

                await self._audit_log(
                    "workflow_stage_approved",
                    approver,
                    workflow_id,
                    "approve" if approved else "reject",
                    {
                        "stage": current_stage,
                        "approved": approved,
                        "comments": comments,
                    },
                )

                return True

            return False

    async def activate_kill_switch(self, activated_by: str, reason: str) -> None:
        """Activate emergency kill switch."""
        async with self._lock:
            self._kill_switch_active = True

            await self._db_connection.execute(
                """
                INSERT INTO kill_switch (active, activated_by, reason, activated_at)
                VALUES (?, ?, ?, ?)
            """,
                (1, activated_by, reason, datetime.now(timezone.utc).isoformat()),
            )
            await self._db_connection.commit()

            # Publish emergency stop event
            await self.event_bus.publish(
                Event(
                    id=f"kill_switch_activated_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.SYSTEM_ERROR,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="safety_layer",
                    data={
                        "kill_switch": True,
                        "activated_by": activated_by,
                        "reason": reason,
                    },
                )
            )

            await self._audit_log(
                "kill_switch", activated_by, "system", "activate", {"reason": reason}
            )

            logger.critical(
                f"EMERGENCY KILL SWITCH ACTIVATED by {activated_by}: {reason}"
            )

    async def deactivate_kill_switch(self, deactivated_by: str) -> None:
        """Deactivate emergency kill switch."""
        async with self._lock:
            self._kill_switch_active = False

            await self._db_connection.execute(
                """
                UPDATE kill_switch SET active = 0, deactivated_at = ? WHERE active = 1
            """,
                (datetime.now(timezone.utc).isoformat(),),
            )
            await self._db_connection.commit()

            await self._audit_log(
                "kill_switch", deactivated_by, "system", "deactivate", {}
            )

            logger.warning(f"KILL SWITCH DEACTIVATED by {deactivated_by}")

    def is_kill_switch_active(self) -> bool:
        """Check if kill switch is active."""
        return self._kill_switch_active

    # Safety rule condition functions
    def _is_outside_market_hours(self, data: Dict[str, Any]) -> bool:
        """Check if current time is outside market hours."""
        now = datetime.now(timezone.utc)
        # Simplified market hours check (9:15 AM - 3:30 PM IST)
        hour = now.hour
        minute = now.minute
        return not (9 <= hour <= 15)

    async def _are_critical_services_down(self, data: Dict[str, Any]) -> bool:
        """Check if critical services are down."""
        critical_services = ["zerodha_api", "database"]
        return any(
            not cb.can_execute()
            for name, cb in self._circuit_breakers.items()
            if name in critical_services
        )

    async def _is_duplicate_order(self, data: Dict[str, Any]) -> bool:
        """Check for duplicate orders."""
        # Simplified check - in real implementation would check recent orders
        return False

    # Safety rule action functions
    async def _reject_high_value_order(self, data: Dict[str, Any]) -> None:
        """Reject high value orders."""
        logger.warning(f"Rejected high value order: {data}")

    async def _reject_outside_hours(self, data: Dict[str, Any]) -> None:
        """Reject orders outside market hours."""
        logger.warning(f"Rejected order outside market hours: {data}")

    async def _trigger_emergency_stop(self, data: Dict[str, Any]) -> None:
        """Trigger emergency stop."""
        await self.activate_kill_switch("safety_layer", "Critical services down")

    async def _reject_duplicate_order(self, data: Dict[str, Any]) -> None:
        """Reject duplicate orders."""
        logger.warning(f"Rejected duplicate order: {data}")

    async def record_service_failure(self, service_name: str) -> None:
        """Record a service failure for circuit breaker."""
        if service_name in self._circuit_breakers:
            self._circuit_breakers[service_name].record_failure()

            # Save state
            await self._db_connection.execute(
                """
                INSERT OR REPLACE INTO circuit_breaker_state
                (service_name, failure_count, last_failure_time, state, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    service_name,
                    self._circuit_breakers[service_name].failure_count,
                    self._circuit_breakers[service_name].last_failure_time,
                    self._circuit_breakers[service_name].state,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await self._db_connection.commit()

    async def record_service_success(self, service_name: str) -> None:
        """Record a service success for circuit breaker."""
        if service_name in self._circuit_breakers:
            self._circuit_breakers[service_name].record_success()

            # Save state
            await self._db_connection.execute(
                """
                INSERT OR REPLACE INTO circuit_breaker_state
                (service_name, failure_count, last_failure_time, state, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    service_name,
                    self._circuit_breakers[service_name].failure_count,
                    self._circuit_breakers[service_name].last_failure_time,
                    self._circuit_breakers[service_name].state,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await self._db_connection.commit()

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.EXECUTION_ORDER_PLACED:
            # Validate order placement
            data = event.data
            validation = await self.validate_operation("place_order", data)
            if not validation["approved"]:
                logger.warning(f"Order validation failed: {validation['reason']}")

        elif event.type == EventType.RISK_BREACH:
            # Handle risk breaches
            data = event.data
            severity = data.get("severity", "low")
            if severity in ["high", "critical"]:
                logger.warning(f"High severity risk breach: {data}")

        elif event.type == EventType.SYSTEM_ERROR:
            # Handle system errors
            data = event.data
            if data.get("kill_switch"):
                logger.critical("Kill switch event received")

    async def close(self) -> None:
        """Close the safety layer."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
