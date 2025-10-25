"""Web utilities for error handling and common patterns."""

from .error_handlers import (
    handle_trading_error,
    handle_validation_error,
    handle_not_found_error,
    handle_unexpected_error,
    create_error_response,
)

__all__ = [
    "handle_trading_error",
    "handle_validation_error",
    "handle_not_found_error",
    "handle_unexpected_error",
    "create_error_response",
]
