from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class ErrorCategory(Enum):
    TRADING = "trading"
    MARKET_DATA = "market_data"
    API = "api"
    VALIDATION = "validation"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


class ErrorSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorContext:
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    recoverable: bool = True
    retry_after_seconds: Optional[int] = None


class TradingError(Exception):
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        code: str = "UNKNOWN_ERROR",
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_after_seconds: Optional[int] = None
    ):
        super().__init__(message)
        self.context = ErrorContext(
            category=category,
            severity=severity,
            code=code,
            message=message,
            details=details,
            metadata=metadata or {},
            recoverable=recoverable,
            retry_after_seconds=retry_after_seconds
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.context.message,
            "category": self.context.category.value,
            "severity": self.context.severity.value,
            "code": self.context.code,
            "details": self.context.details,
            "metadata": self.context.metadata,
            "recoverable": self.context.recoverable,
            "retry_after_seconds": self.context.retry_after_seconds
        }


class OrderError(TradingError):
    def __init__(self, message: str, order_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.TRADING,
            code="ORDER_ERROR",
            metadata={"order_id": order_id} if order_id else {},
            **kwargs
        )


class MarketDataError(TradingError):
    def __init__(self, message: str, symbol: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.MARKET_DATA,
            code="MARKET_DATA_ERROR",
            metadata={"symbol": symbol} if symbol else {},
            **kwargs
        )


class APIError(TradingError):
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            code="API_ERROR",
            metadata={"api_name": api_name, "status_code": status_code},
            **kwargs
        )


class ValidationError(TradingError):
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            code="VALIDATION_ERROR",
            metadata={"field": field} if field else {},
            recoverable=False,
            **kwargs
        )


class ResourceError(TradingError):
    def __init__(self, message: str, resource_type: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            code="RESOURCE_ERROR",
            metadata={"resource_type": resource_type},
            **kwargs
        )


class ConfigurationError(TradingError):
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            code="CONFIG_ERROR",
            metadata={"config_key": config_key} if config_key else {},
            recoverable=False,
            **kwargs
        )


class ErrorHandler:
    @staticmethod
    def handle_error(error: Exception) -> ErrorContext:
        if isinstance(error, TradingError):
            return error.context

        if isinstance(error, ValueError):
            return ErrorContext(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                code="VALUE_ERROR",
                message=str(error),
                recoverable=False
            )

        if isinstance(error, KeyError):
            return ErrorContext(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="KEY_ERROR",
                message=f"Missing required key: {error}",
                recoverable=False
            )

        if isinstance(error, ConnectionError):
            return ErrorContext(
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                code="CONNECTION_ERROR",
                message=str(error),
                recoverable=True,
                retry_after_seconds=30
            )

        if isinstance(error, TimeoutError):
            return ErrorContext(
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                code="TIMEOUT_ERROR",
                message=str(error),
                recoverable=True,
                retry_after_seconds=10
            )

        return ErrorContext(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            code="UNKNOWN_ERROR",
            message=str(error),
            recoverable=True
        )

    @staticmethod
    def should_retry(error: Exception) -> bool:
        context = ErrorHandler.handle_error(error)
        return context.recoverable

    @staticmethod
    def get_retry_delay(error: Exception) -> int:
        context = ErrorHandler.handle_error(error)
        return context.retry_after_seconds or 0

    @staticmethod
    def format_error_response(error: Exception) -> Dict[str, Any]:
        if isinstance(error, TradingError):
            return error.to_dict()

        context = ErrorHandler.handle_error(error)
        return {
            "error": context.message,
            "category": context.category.value,
            "severity": context.severity.value,
            "code": context.code,
            "details": context.details,
            "metadata": context.metadata,
            "recoverable": context.recoverable,
            "retry_after_seconds": context.retry_after_seconds
        }
