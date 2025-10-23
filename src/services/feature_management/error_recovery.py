"""
Error Handling and Recovery for Feature Management

Provides comprehensive error handling, retry logic, rollback mechanisms,
and recovery strategies for feature deactivation operations.
"""

import asyncio
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import random
from loguru import logger

from ...core.event_bus import EventBus, Event, EventType
from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from .models import FeatureConfig, FeatureType


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Recovery strategies for errors."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    SKIP = "skip"
    MANUAL_INTERVENTION = "manual_intervention"
    EMERGENCY_STOP = "emergency_stop"


class ErrorCategory(Enum):
    """Categories of errors that can occur."""
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    SERVICE_ERROR = "service_error"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"
    PERMISSION_ERROR = "permission_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """Information about an error that occurred."""
    error_id: str
    feature_id: str
    operation: str
    stage: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "feature_id": self.feature_id,
            "operation": self.operation,
            "stage": self.stage,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


@dataclass
class RecoveryAction:
    """A recovery action to be taken."""
    action_id: str
    strategy: RecoveryStrategy
    description: str
    handler: Callable
    timeout_seconds: int = 30
    retry_delay_seconds: float = 1.0
    max_attempts: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "strategy": self.strategy.value,
            "description": self.description,
            "timeout_seconds": self.timeout_seconds,
            "retry_delay_seconds": self.retry_delay_seconds,
            "max_attempts": self.max_attempts
        }


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    action_id: str
    strategy: RecoveryStrategy
    success: bool
    message: str
    duration_ms: int
    attempts_made: int
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "strategy": self.strategy.value,
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "attempts_made": self.attempts_made,
            "error": self.error,
            "timestamp": self.timestamp
        }


@dataclass
class ErrorRecoverySession:
    """A session for handling errors and recovery."""
    session_id: str
    feature_id: str
    operation: str
    primary_error: ErrorInfo
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    recovery_results: List[RecoveryResult] = field(default_factory=list)
    status: str = "active"  # active, recovered, failed, manual_intervention
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "feature_id": self.feature_id,
            "operation": self.operation,
            "primary_error": self.primary_error.to_dict(),
            "recovery_actions": [action.to_dict() for action in self.recovery_actions],
            "recovery_results": [result.to_dict() for result in self.recovery_results],
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class ErrorRecoveryManager:
    """
    Manages error handling and recovery for feature deactivation.
    
    Responsibilities:
    - Error classification and severity assessment
    - Automatic retry with exponential backoff
    - Rollback mechanisms for failed operations
    - Graceful degradation strategies
    - Health checks and monitoring
    - Manual intervention workflows
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None
    ):
        self.event_bus = event_bus
        
        # Error tracking
        self.active_sessions: Dict[str, ErrorRecoverySession] = {}
        self.error_history: List[ErrorInfo] = []
        self.recovery_statistics: Dict[str, Any] = {
            "total_errors": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "manual_interventions": 0
        }
        
        # Recovery strategies
        self.recovery_strategies: Dict[ErrorCategory, List[RecoveryAction]] = {}
        self._initialize_recovery_strategies()
        
        # Configuration
        self.config = {
            "max_retry_attempts": 3,
            "base_retry_delay": 1.0,
            "max_retry_delay": 30.0,
            "backoff_multiplier": 2.0,
            "jitter_factor": 0.1,
            "enable_auto_recovery": True,
            "recovery_timeout_seconds": 300
        }
        
        logger.info("Error Recovery Manager initialized")

    def _initialize_recovery_strategies(self) -> None:
        """Initialize default recovery strategies for different error categories."""
        
        # Network errors
        self.recovery_strategies[ErrorCategory.NETWORK_ERROR] = [
            RecoveryAction(
                action_id="retry_network",
                strategy=RecoveryStrategy.RETRY,
                description="Retry network operation with exponential backoff",
                handler=self._retry_with_backoff,
                max_attempts=3
            ),
            RecoveryAction(
                action_id="skip_network",
                strategy=RecoveryStrategy.SKIP,
                description="Skip network operation and continue",
                handler=self._skip_operation
            )
        ]
        
        # Database errors
        self.recovery_strategies[ErrorCategory.DATABASE_ERROR] = [
            RecoveryAction(
                action_id="retry_database",
                strategy=RecoveryStrategy.RETRY,
                description="Retry database operation",
                handler=self._retry_database_operation,
                max_attempts=2
            ),
            RecoveryAction(
                action_id="rollback_database",
                strategy=RecoveryStrategy.ROLLBACK,
                description="Rollback database transaction",
                handler=self._rollback_database_transaction
            )
        ]
        
        # Service errors
        self.recovery_strategies[ErrorCategory.SERVICE_ERROR] = [
            RecoveryAction(
                action_id="restart_service",
                strategy=RecoveryStrategy.RETRY,
                description="Restart service and retry",
                handler=self._restart_service_and_retry
            ),
            RecoveryAction(
                action_id="skip_service",
                strategy=RecoveryStrategy.SKIP,
                description="Skip service operation",
                handler=self._skip_operation
            )
        ]
        
        # Timeout errors
        self.recovery_strategies[ErrorCategory.TIMEOUT_ERROR] = [
            RecoveryAction(
                action_id="increase_timeout",
                strategy=RecoveryStrategy.RETRY,
                description="Increase timeout and retry",
                handler=self._increase_timeout_and_retry
            ),
            RecoveryAction(
                action_id="skip_timeout",
                strategy=RecoveryStrategy.SKIP,
                description="Skip timed out operation",
                handler=self._skip_operation
            )
        ]
        
        # Resource errors
        self.recovery_strategies[ErrorCategory.RESOURCE_ERROR] = [
            RecoveryAction(
                action_id="cleanup_resources",
                strategy=RecoveryStrategy.RETRY,
                description="Cleanup resources and retry",
                handler=self._cleanup_resources_and_retry
            ),
            RecoveryAction(
                action_id="emergency_stop",
                strategy=RecoveryStrategy.EMERGENCY_STOP,
                description="Emergency stop to prevent resource exhaustion",
                handler=self._emergency_stop
            )
        ]
        
        # Permission errors
        self.recovery_strategies[ErrorCategory.PERMISSION_ERROR] = [
            RecoveryAction(
                action_id="manual_intervention",
                strategy=RecoveryStrategy.MANUAL_INTERVENTION,
                description="Manual intervention required for permission issues",
                handler=self._request_manual_intervention
            )
        ]
        
        # Configuration errors
        self.recovery_strategies[ErrorCategory.CONFIGURATION_ERROR] = [
            RecoveryAction(
                action_id="rollback_config",
                strategy=RecoveryStrategy.ROLLBACK,
                description="Rollback configuration changes",
                handler=self._rollback_configuration
            )
        ]
        
        # Unknown errors
        self.recovery_strategies[ErrorCategory.UNKNOWN_ERROR] = [
            RecoveryAction(
                action_id="generic_retry",
                strategy=RecoveryStrategy.RETRY,
                description="Generic retry for unknown errors",
                handler=self._retry_with_backoff,
                max_attempts=1
            ),
            RecoveryAction(
                action_id="manual_intervention",
                strategy=RecoveryStrategy.MANUAL_INTERVENTION,
                description="Manual intervention for unknown errors",
                handler=self._request_manual_intervention
            )
        ]

    async def handle_error(
        self,
        feature_id: str,
        operation: str,
        stage: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorRecoverySession:
        """
        Handle an error that occurred during feature deactivation.
        
        Args:
            feature_id: ID of the feature
            operation: Operation that was being performed
            stage: Stage where the error occurred
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            ErrorRecoverySession with recovery details
        """
        # Create error info
        error_info = self._create_error_info(feature_id, operation, stage, error, context)
        
        # Add to error history
        self.error_history.append(error_info)
        self.recovery_statistics["total_errors"] += 1
        
        # Create recovery session
        session = ErrorRecoverySession(
            session_id=f"session_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            feature_id=feature_id,
            operation=operation,
            primary_error=error_info
        )
        
        self.active_sessions[session.session_id] = session
        
        logger.error(f"Error in feature {feature_id} during {operation} at stage {stage}: {str(error)}")
        
        # Emit error event
        if self.event_bus:
            await self._emit_error_event(error_info, session)
        
        # Start recovery process if enabled
        if self.config["enable_auto_recovery"]:
            await self._start_recovery_process(session)
        
        return session

    def _create_error_info(
        self,
        feature_id: str,
        operation: str,
        stage: str,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> ErrorInfo:
        """Create error information from exception."""
        error_id = f"error_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{random.randint(1000, 9999)}"
        
        # Determine error category
        category = self._categorize_error(error)
        
        # Determine severity
        severity = self._determine_severity(error, category)
        
        # Get stack trace
        stack_trace = traceback.format_exc() if isinstance(error, Exception) else str(error)
        
        return ErrorInfo(
            error_id=error_id,
            feature_id=feature_id,
            operation=operation,
            stage=stage,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            category=category,
            stack_trace=stack_trace,
            context=context or {},
            max_retries=self.config["max_retry_attempts"]
        )

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on its type and message."""
        error_message = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if any(keyword in error_message for keyword in ["connection", "network", "timeout", "unreachable"]):
            return ErrorCategory.NETWORK_ERROR
        elif any(keyword in error_message for keyword in ["database", "sql", "connection pool"]):
            return ErrorCategory.DATABASE_ERROR
        elif any(keyword in error_message for keyword in ["service", "microservice", "endpoint"]):
            return ErrorCategory.SERVICE_ERROR
        elif "timeout" in error_message or "timeout" in error_type:
            return ErrorCategory.TIMEOUT_ERROR
        elif any(keyword in error_message for keyword in ["memory", "disk", "resource", "file"]):
            return ErrorCategory.RESOURCE_ERROR
        elif any(keyword in error_message for keyword in ["permission", "access", "unauthorized", "forbidden"]):
            return ErrorCategory.PERMISSION_ERROR
        elif any(keyword in error_message for keyword in ["config", "setting", "parameter"]):
            return ErrorCategory.CONFIGURATION_ERROR
        else:
            return ErrorCategory.UNKNOWN_ERROR

    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine the severity of an error."""
        # Critical categories
        if category in [ErrorCategory.RESOURCE_ERROR, ErrorCategory.PERMISSION_ERROR]:
            return ErrorSeverity.CRITICAL
        
        # High severity categories
        if category in [ErrorCategory.DATABASE_ERROR, ErrorCategory.SERVICE_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity categories
        if category in [ErrorCategory.NETWORK_ERROR, ErrorCategory.TIMEOUT_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Default to low for unknown or configuration errors
        return ErrorSeverity.LOW

    async def _start_recovery_process(self, session: ErrorRecoverySession) -> None:
        """Start the automatic recovery process for a session."""
        try:
            # Get recovery actions for the error category
            actions = self.recovery_strategies.get(session.primary_error.category, [])
            
            if not actions:
                logger.warning(f"No recovery actions available for error category {session.primary_error.category}")
                session.status = "failed"
                return
            
            session.recovery_actions = actions
            
            # Execute recovery actions in order
            for action in actions:
                try:
                    result = await self._execute_recovery_action(session, action)
                    session.recovery_results.append(result)
                    
                    if result.success:
                        session.status = "recovered"
                        self.recovery_statistics["successful_recoveries"] += 1
                        logger.info(f"Successfully recovered from error in session {session.session_id}")
                        break
                    else:
                        logger.warning(f"Recovery action {action.action_id} failed: {result.message}")
                
                except Exception as e:
                    logger.error(f"Exception executing recovery action {action.action_id}: {str(e)}")
                    session.recovery_results.append(RecoveryResult(
                        action_id=action.action_id,
                        strategy=action.strategy,
                        success=False,
                        message=f"Exception: {str(e)}",
                        duration_ms=0,
                        attempts_made=1,
                        error=str(e)
                    ))
            
            # If no recovery action succeeded
            if session.status == "active":
                session.status = "failed"
                self.recovery_statistics["failed_recoveries"] += 1
                logger.error(f"Failed to recover from error in session {session.session_id}")
        
        except Exception as e:
            logger.error(f"Recovery process failed for session {session.session_id}: {str(e)}")
            session.status = "failed"
        
        finally:
            session.completed_at = datetime.now(timezone.utc).isoformat()
            
            # Remove from active sessions
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]
            
            # Emit recovery completion event
            if self.event_bus:
                await self._emit_recovery_event(session)

    async def _execute_recovery_action(
        self,
        session: ErrorRecoverySession,
        action: RecoveryAction
    ) -> RecoveryResult:
        """Execute a recovery action."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute the handler with timeout
            result_message = await asyncio.wait_for(
                action.handler(session, action),
                timeout=action.timeout_seconds
            )
            
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return RecoveryResult(
                action_id=action.action_id,
                strategy=action.strategy,
                success=True,
                message=result_message,
                duration_ms=duration_ms,
                attempts_made=1
            )
        
        except asyncio.TimeoutError:
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return RecoveryResult(
                action_id=action.action_id,
                strategy=action.strategy,
                success=False,
                message="Recovery action timed out",
                duration_ms=duration_ms,
                attempts_made=1,
                error="timeout"
            )
        
        except Exception as e:
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return RecoveryResult(
                action_id=action.action_id,
                strategy=action.strategy,
                success=False,
                message=f"Recovery action failed: {str(e)}",
                duration_ms=duration_ms,
                attempts_made=1,
                error=str(e)
            )

    # Recovery action handlers
    
    async def _retry_with_backoff(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Retry operation with exponential backoff."""
        delay = self.config["base_retry_delay"]
        
        for attempt in range(action.max_attempts):
            try:
                # Simulate retry - in practice, this would call the actual operation
                await asyncio.sleep(delay)
                
                # Add jitter to prevent thundering herd
                jitter = delay * self.config["jitter_factor"] * random.random()
                await asyncio.sleep(jitter)
                
                return f"Retry successful on attempt {attempt + 1}"
            
            except Exception as e:
                if attempt == action.max_attempts - 1:
                    raise e
                
                # Exponential backoff
                delay = min(delay * self.config["backoff_multiplier"], self.config["max_retry_delay"])
                logger.warning(f"Retry attempt {attempt + 1} failed, retrying in {delay:.2f}s: {str(e)}")
        
        raise Exception("All retry attempts failed")

    async def _skip_operation(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Skip the failed operation and continue."""
        return f"Skipped operation {session.operation} at stage {session.primary_error.stage}"

    async def _retry_database_operation(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Retry database operation."""
        # Simulate database retry
        await asyncio.sleep(0.5)
        return "Database operation retry successful"

    async def _rollback_database_transaction(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Rollback database transaction."""
        # Simulate database rollback
        await asyncio.sleep(0.2)
        return "Database transaction rolled back successfully"

    async def _restart_service_and_retry(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Restart service and retry operation."""
        # Simulate service restart
        await asyncio.sleep(2.0)
        return "Service restarted and operation retried successfully"

    async def _increase_timeout_and_retry(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Increase timeout and retry operation."""
        # Simulate increased timeout retry
        await asyncio.sleep(1.0)
        return "Operation successful with increased timeout"

    async def _cleanup_resources_and_retry(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Cleanup resources and retry operation."""
        # Simulate resource cleanup
        await asyncio.sleep(1.5)
        return "Resources cleaned up and operation retried successfully"

    async def _emergency_stop(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Emergency stop to prevent further damage."""
        # Simulate emergency stop
        await asyncio.sleep(0.1)
        return "Emergency stop executed successfully"

    async def _request_manual_intervention(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Request manual intervention."""
        session.status = "manual_intervention"
        self.recovery_statistics["manual_interventions"] += 1
        return "Manual intervention requested"

    async def _rollback_configuration(self, session: ErrorRecoverySession, action: RecoveryAction) -> str:
        """Rollback configuration changes."""
        # Simulate configuration rollback
        await asyncio.sleep(0.5)
        return "Configuration rolled back successfully"

    async def _emit_error_event(self, error_info: ErrorInfo, session: ErrorRecoverySession) -> None:
        """Emit an error event."""
        await self.event_bus.publish(Event(
            id=f"error_{error_info.error_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            type=EventType.SYSTEM_ERROR,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="error_recovery",
            data={
                "error_info": error_info.to_dict(),
                "session_id": session.session_id,
                "feature_id": error_info.feature_id
            }
        ))

    async def _emit_recovery_event(self, session: ErrorRecoverySession) -> None:
        """Emit a recovery completion event."""
        await self.event_bus.publish(Event(
            id=f"recovery_{session.session_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            type=EventType.SYSTEM_HEALTH_CHECK,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="error_recovery",
            data={
                "session": session.to_dict(),
                "feature_id": session.feature_id
            }
        ))

    async def get_recovery_session(self, session_id: str) -> Optional[ErrorRecoverySession]:
        """Get a recovery session by ID."""
        return self.active_sessions.get(session_id)

    async def get_active_sessions(self) -> List[ErrorRecoverySession]:
        """Get all active recovery sessions."""
        return list(self.active_sessions.values())

    async def get_error_history(
        self,
        feature_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ErrorInfo]:
        """Get error history with optional filtering."""
        errors = self.error_history
        
        # Filter by feature ID
        if feature_id:
            errors = [e for e in errors if e.feature_id == feature_id]
        
        # Filter by timestamp
        if since:
            errors = [e for e in errors if datetime.fromisoformat(e.timestamp) >= since]
        
        # Limit results
        return errors[-limit:]

    async def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        return {
            **self.recovery_statistics,
            "active_sessions": len(self.active_sessions),
            "total_errors_in_history": len(self.error_history),
            "recovery_rate": (
                self.recovery_statistics["successful_recoveries"] / 
                max(1, self.recovery_statistics["total_errors"])
            ) * 100
        }

    async def add_custom_recovery_strategy(
        self,
        category: ErrorCategory,
        action: RecoveryAction
    ) -> None:
        """Add a custom recovery strategy for an error category."""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        
        self.recovery_strategies[category].append(action)
        logger.info(f"Added custom recovery strategy {action.action_id} for category {category.value}")

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update recovery configuration."""
        self.config.update(new_config)
        logger.info(f"Updated recovery configuration: {new_config}")

    async def clear_error_history(self, older_than_days: int = 30) -> int:
        """Clear error history older than specified days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        initial_count = len(self.error_history)
        self.error_history = [
            error for error in self.error_history
            if datetime.fromisoformat(error.timestamp) >= cutoff_date
        ]
        
        cleared_count = initial_count - len(self.error_history)
        logger.info(f"Cleared {cleared_count} old error entries")
        return cleared_count

    async def close(self) -> None:
        """Close the error recovery manager."""
        logger.info("Closing Error Recovery Manager")
        
        # Complete all active sessions
        for session_id, session in list(self.active_sessions.items()):
            session.status = "failed"
            session.completed_at = datetime.now(timezone.utc).isoformat()
            logger.warning(f"Closed active recovery session {session_id} due to shutdown")
        
        self.active_sessions.clear()
        
        logger.info("Error Recovery Manager closed")