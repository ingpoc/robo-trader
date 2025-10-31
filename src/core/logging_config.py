"""
Logging configuration for Robo Trader
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(logs_dir: Path, log_level: str = "INFO"):
    """
    Configure logging to output to both console and files.

    Args:
        logs_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default handler
    logger.remove()

    # Add console handler with colorful output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # Add file handler for backend logs
    backend_log = logs_dir / "backend.log"
    logger.add(
        backend_log,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True  # Async logging to prevent blocking
    )

    # Add error-only file handler
    error_log = logs_dir / "errors.log"
    logger.add(
        error_log,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="WARNING",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True  # Async logging to prevent blocking
    )

    # Add critical error handler that catches everything
    critical_log = logs_dir / "critical.log"
    logger.add(
        critical_log,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | CRITICAL | {name}:{function}:{line} - {message}\n{exception}",
        level="ERROR",
        rotation="1 MB",
        retention="90 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )

    logger.info(f"Logging configured: level={log_level}, logs_dir={logs_dir}")
    logger.info("Logs are being written to both console and files")

    # Setup global exception handler to catch unhandled errors
    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions that would otherwise be lost."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            f"Uncaught exception: {exc_value}",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    # Install global exception handler
    sys.excepthook = handle_uncaught_exception

    # Handle asyncio exceptions
    import asyncio
    def handle_asyncio_exception(loop, context):
        """Handle asyncio exceptions."""
        logger.error(f"Asyncio exception: {context}")
        if 'exception' in context:
            logger.error(f"Exception details: {context['exception']}", exc_info=context['exception'])

    # Store original exception handler and replace it
    original_handler = asyncio.get_event_loop_policy().get_event_loop().get_exception_handler()
    asyncio.get_event_loop().set_exception_handler(handle_asyncio_exception)


def ensure_logging_setup(logs_dir: Path = None, log_level: str = "INFO"):
    """
    Ensure logging is set up, using default logs directory if not provided.

    This is a convenience function for scripts and tests that need logging
    but don't want to worry about configuration details.
    """
    if logs_dir is None:
        # Use default logs directory
        logs_dir = Path.cwd() / "logs"

    # Create logs directory if it doesn't exist
    logs_dir.mkdir(exist_ok=True)

    setup_logging(logs_dir, log_level)
