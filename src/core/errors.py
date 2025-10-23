"""
Core Error Hierarchy for Robo Trader

Structured error context for debugging and proper error handling.
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    TRADING = "trading"
    MARKET_DATA = "market_data"
    API = "api"
    VALIDATION = "validation"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    SDK = "sdk"  # Added for Claude Agent SDK errors


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorContext:
    """Structured error context for debugging."""
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True
    retry_after_seconds: Optional[int] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "metadata": self.metadata,
            "recoverable": self.recoverable,
            "retry_after_seconds": self.retry_after_seconds,
            "correlation_id": self.correlation_id
        }


class TradingError(Exception):
    """
    Base exception for all trading-related errors.

    Provides structured error context for better debugging and error handling.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        code: Optional[str] = None,
        details: Optional[str] = None,
        recoverable: bool = True,
        retry_after_seconds: Optional[int] = None,
        correlation_id: Optional[str] = None,
        **metadata
    ):
        super().__init__(message)

        if code is None:
            code = f"{category.value.upper()}_{severity.value.upper()}"

        self.context = ErrorContext(
            category=category,
            severity=severity,
            code=code,
            message=message,
            details=details,
            metadata=metadata,
            recoverable=recoverable,
            retry_after_seconds=retry_after_seconds,
            correlation_id=correlation_id
        )

        # Log the error with context
        self._log_error()

    def _log_error(self) -> None:
        """Log the error with appropriate level based on severity."""
        log_data = {
            "category": self.context.category.value,
            "severity": self.context.severity.value,
            "code": self.context.code,
            "message": self.context.message,
            "recoverable": self.context.recoverable,
            "correlation_id": self.context.correlation_id
        }

        if self.context.metadata:
            log_data["metadata"] = self.context.metadata

        if self.context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {self.context.message}", extra=log_data)
        elif self.context.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {self.context.message}", extra=log_data)
        elif self.context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {self.context.message}", extra=log_data)
        else:
            logger.info(f"Low severity error: {self.context.message}", extra=log_data)


# Specific error types

class MarketDataError(TradingError):
    """Errors related to market data fetching and processing."""

    def __init__(self, message: str, symbol: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.MARKET_DATA,
            symbol=symbol,
            **kwargs
        )


class APIError(TradingError):
    """Errors related to external API calls."""

    def __init__(self, message: str, api_name: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            api_name=api_name,
            status_code=status_code,
            **kwargs
        )


class ValidationError(TradingError):
    """Errors related to input validation."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            field=field,
            value=value,
            **kwargs
        )


class ResourceError(TradingError):
    """Errors related to resource management (database, files, etc.)."""

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs
        )


class ConfigurationError(TradingError):
    """Errors related to configuration issues."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            config_key=config_key,
            **kwargs
        )


class SDKError(TradingError):
    """Errors related to Claude Agent SDK operations."""

    def __init__(
        self,
        message: str,
        sdk_operation: Optional[str] = None,
        tool_name: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            category=ErrorCategory.SDK,
            sdk_operation=sdk_operation,
            tool_name=tool_name,
            session_id=session_id,
            **kwargs
        )


class SDKAUTHError(SDKError):
    """SDK authentication errors."""

    def __init__(self, message: str, auth_method: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            sdk_operation="authentication",
            auth_method=auth_method,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )


class SDKToolError(SDKError):
    """SDK tool execution errors."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        tool_input: Optional[Dict[str, Any]] = None,
        execution_error: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            sdk_operation="tool_execution",
            tool_name=tool_name,
            tool_input=tool_input,
            execution_error=execution_error,
            **kwargs
        )


class SDKSessionError(SDKError):
    """SDK session management errors."""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        session_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            sdk_operation="session_management",
            session_id=session_id,
            session_type=session_type,
            **kwargs
        )


class SDKRateLimitError(SDKError):
    """SDK rate limiting errors."""

    def __init__(
        self,
        message: str,
        retry_after_seconds: int,
        limit_type: str = "requests_per_minute",
        **kwargs
    ):
        super().__init__(
            message,
            sdk_operation="rate_limiting",
            retry_after_seconds=retry_after_seconds,
            limit_type=limit_type,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class FeatureManagementError(TradingError):
    """Errors related to feature management operations."""

    def __init__(self, message: str, feature_id: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            feature_id=feature_id,
            operation=operation,
            **kwargs
        )


# Error recovery utilities

def is_recoverable_error(error: Exception) -> bool:
    """Check if an error is recoverable."""
    if isinstance(error, TradingError):
        return error.context.recoverable
    return False


def get_retry_delay(error: Exception) -> Optional[int]:
    """Get retry delay in seconds for recoverable errors."""
    if isinstance(error, TradingError) and error.context.recoverable:
        return error.context.retry_after_seconds
    return None


def get_error_category(error: Exception) -> ErrorCategory:
    """Get error category from exception."""
    if isinstance(error, TradingError):
        return error.context.category
    return ErrorCategory.SYSTEM


def get_error_severity(error: Exception) -> ErrorSeverity:
    """Get error severity from exception."""
    if isinstance(error, TradingError):
        return error.context.severity
    return ErrorSeverity.MEDIUM


# Error handling decorator

def handle_errors(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recoverable: bool = True
):
    """
    Decorator to handle errors and convert them to TradingError.

    Usage:
        @handle_errors(category=ErrorCategory.API, severity=ErrorSeverity.HIGH)
        async def api_call():
            # Function that might raise exceptions
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except TradingError:
                # Re-raise TradingError as-is
                raise
            except Exception as e:
                # Convert other exceptions to TradingError
                raise TradingError(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    category=category,
                    severity=severity,
                    recoverable=recoverable,
                    function_name=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                ) from e
        return wrapper
    return decorator


class ErrorHandler:
    """Global error handler for consistent error responses."""

    @staticmethod
    def handle_error(error: Exception) -> ErrorContext:
        """Handle any exception and return structured error context."""
        if isinstance(error, TradingError):
            return error.context

        # Handle common exception types
        if isinstance(error, ValueError):
            return ErrorContext(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VALIDATION_ERROR",
                message=str(error),
                recoverable=True
            )
        elif isinstance(error, ConnectionError) or isinstance(error, TimeoutError):
            return ErrorContext(
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                code="CONNECTION_ERROR",
                message=str(error),
                recoverable=True,
                retry_after_seconds=30
            )
        elif isinstance(error, PermissionError):
            return ErrorContext(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                code="PERMISSION_ERROR",
                message=str(error),
                recoverable=False
            )
        else:
            return ErrorContext(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                code="SYSTEM_ERROR",
                message=str(error),
                recoverable=False
            )

    @staticmethod
    def format_error_response(error: Exception) -> Dict[str, Any]:
        """Format error for API response."""
        context = ErrorHandler.handle_error(error)
        return {
            "error": context.message,
            "category": context.category.value,
            "severity": context.severity.value,
            "code": context.code,
            "recoverable": context.recoverable,
            "retry_after_seconds": context.retry_after_seconds
        }