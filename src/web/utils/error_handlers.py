"""
Error handling utilities for web routes.

Provides standardized error handling for FastAPI routes following
the TradingError hierarchy pattern from CLAUDE.md.
"""

import logging

from fastapi.responses import JSONResponse

from src.core.errors import ErrorSeverity, TradingError

logger = logging.getLogger(__name__)


async def handle_trading_error(error: TradingError) -> JSONResponse:
    """
    Convert TradingError to standardized JSON response.

    Args:
        error: TradingError with rich context

    Returns:
        JSONResponse with error details and appropriate status code
    """
    status_code = _get_status_code_for_severity(error.context.severity)

    response_data = {
        "error": error.context.message,
        "code": error.context.code,
        "category": error.context.category.value,
        "severity": error.context.severity.value,
        "recoverable": error.context.recoverable,
    }

    # Add retry guidance if available
    if error.context.retry_after_seconds:
        response_data["retry_after_seconds"] = error.context.retry_after_seconds

    # Add metadata if available
    if error.context.metadata:
        response_data["metadata"] = error.context.metadata

    # Log with appropriate level
    _log_trading_error(error)

    return JSONResponse(status_code=status_code, content=response_data)


async def handle_validation_error(error: ValueError) -> JSONResponse:
    """
    Handle validation errors (invalid input, bad parameters).

    Args:
        error: ValueError from validation logic

    Returns:
        JSONResponse with 400 status
    """
    logger.warning(f"Validation error: {error}")

    return JSONResponse(
        status_code=400,
        content={"error": str(error), "category": "validation", "recoverable": True},
    )


async def handle_not_found_error(error: KeyError) -> JSONResponse:
    """
    Handle not found errors (missing resources).

    Args:
        error: KeyError from resource lookup

    Returns:
        JSONResponse with 404 status
    """
    logger.info(f"Resource not found: {error}")

    return JSONResponse(
        status_code=404,
        content={
            "error": f"Resource not found: {error}",
            "category": "not_found",
            "recoverable": False,
        },
    )


async def handle_unexpected_error(error: Exception, context: str = "") -> JSONResponse:
    """
    Handle unexpected errors safely without exposing internals.

    Args:
        error: Unexpected exception
        context: Optional context about where error occurred

    Returns:
        JSONResponse with 500 status and safe error message
    """
    # Log full exception with stack trace
    logger.exception(f"Unexpected error in {context}: {error}")

    # Return safe error message to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "category": "system",
            "recoverable": False,
            "message": "An unexpected error occurred. Please try again or contact support.",
        },
    )


def _get_status_code_for_severity(severity: ErrorSeverity) -> int:
    """Map error severity to HTTP status code."""
    severity_to_status = {
        ErrorSeverity.CRITICAL: 500,
        ErrorSeverity.HIGH: 500,
        ErrorSeverity.MEDIUM: 400,
        ErrorSeverity.LOW: 400,
    }
    return severity_to_status.get(severity, 500)


def _log_trading_error(error: TradingError) -> None:
    """Log trading error with appropriate log level."""
    log_message = (
        f"TradingError [{error.context.code}]: {error.context.message} "
        f"(category={error.context.category.value}, severity={error.context.severity.value})"
    )

    if error.context.metadata:
        log_message += f" metadata={error.context.metadata}"

    # Map severity to log level
    if error.context.severity == ErrorSeverity.CRITICAL:
        logger.critical(log_message)
    elif error.context.severity == ErrorSeverity.HIGH:
        logger.error(log_message)
    elif error.context.severity == ErrorSeverity.MEDIUM:
        logger.warning(log_message)
    else:
        logger.info(log_message)


def create_error_response(
    message: str,
    status_code: int = 400,
    category: str = "error",
    recoverable: bool = False,
    **kwargs,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code
        category: Error category
        recoverable: Whether error is recoverable
        **kwargs: Additional fields to include in response

    Returns:
        JSONResponse with error details
    """
    response_data = {
        "error": message,
        "category": category,
        "recoverable": recoverable,
        **kwargs,
    }

    return JSONResponse(status_code=status_code, content=response_data)
