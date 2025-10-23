"""Exponential backoff and retry logic for API calls."""

import asyncio
import random
from typing import Callable, TypeVar, Any, Optional
from loguru import logger

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 32.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_backoff_seconds: Initial backoff delay
            max_backoff_seconds: Maximum backoff delay cap
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to backoff
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff_seconds
        self.max_backoff = max_backoff_seconds
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay for the given attempt number.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_backoff * (base ^ attempt)
        delay = self.initial_backoff * (self.exponential_base ** attempt)
        delay = min(delay, self.max_backoff)

        # Add jitter: ±20% randomness
        if self.jitter:
            jitter_amount = delay * 0.2
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)  # Ensure non-negative


class RetryableError(Exception):
    """Exception that can be retried."""
    pass


class NonRetryableError(Exception):
    """Exception that should not be retried."""
    pass


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    retryable_exceptions: tuple = (RetryableError,),
    **kwargs
) -> T:
    """Execute function with exponential backoff retry.

    Args:
        func: Async function to execute
        args: Positional arguments for function
        config: Retry configuration (uses default if None)
        retryable_exceptions: Tuple of exceptions that trigger retry
        kwargs: Keyword arguments for function

    Returns:
        Result from function execution

    Raises:
        The last exception if all retries failed
    """
    if config is None:
        config = RetryConfig()

    last_exception: Optional[Exception] = None

    for attempt in range(config.max_retries):
        try:
            return await func(*args, **kwargs)

        except NonRetryableError as e:
            logger.warning(f"Non-retryable error: {e}")
            raise

        except Exception as e:
            if not isinstance(e, retryable_exceptions):
                logger.warning(f"Non-retryable exception type: {type(e).__name__}: {e}")
                raise

            last_exception = e

            if attempt < config.max_retries - 1:
                delay = config.get_backoff_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_retries} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_retries} attempts failed. Last error: {e}"
                )

    # Should not reach here, but raise last exception if we do
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited unexpectedly")


async def retry_on_rate_limit(
    func: Callable[..., Any],
    *args,
    max_retries: int = 5,
    **kwargs
) -> T:
    """Retry specifically on rate limit errors with longer backoff.

    Args:
        func: Async function to execute
        args: Positional arguments
        max_retries: Maximum retry attempts
        kwargs: Keyword arguments

    Returns:
        Result from function execution
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_backoff_seconds=2.0,
        max_backoff_seconds=120.0,
        exponential_base=2.0,
        jitter=True
    )

    from openai import RateLimitError
    return await retry_with_backoff(
        func,
        *args,
        config=config,
        retryable_exceptions=(RateLimitError,),
        **kwargs
    )
