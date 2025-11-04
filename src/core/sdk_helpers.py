"""
SDK Operation Helpers - Timeout and error handling wrappers.

Provides safe wrappers for common SDK operations with comprehensive
error handling and timeout protection.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional, Any, Dict, Tuple

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeSDKError,
    CLINotFoundError,
    CLIConnectionError,
    ProcessError,
    CLIJSONDecodeError,
)

from ..core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


def _handle_sdk_error(e: Exception, timeout: Optional[float] = None) -> TradingError:
    """Convert SDK errors to TradingError with appropriate context."""
    if isinstance(e, asyncio.TimeoutError):
        return TradingError(
            f"Operation timed out after {timeout}s",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            metadata={"timeout": timeout}
        )
    elif isinstance(e, CLINotFoundError):
        return TradingError(
            "Claude Code CLI not installed",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False
        )
    elif isinstance(e, CLIConnectionError):
        return TradingError(
            f"Claude SDK connection failed: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            metadata={"error": str(e)}
        )
    elif isinstance(e, ProcessError):
        return TradingError(
            f"Claude SDK process failed: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            metadata={"exit_code": getattr(e, "exit_code", None)}
        )
    elif isinstance(e, CLIJSONDecodeError):
        return TradingError(
            f"Claude SDK JSON decode error: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            metadata={"error": str(e)}
        )
    elif isinstance(e, ClaudeSDKError):
        return TradingError(
            f"Claude SDK error: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            metadata={"error": str(e)}
        )
    else:
        return TradingError(
            f"Unexpected error: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            metadata={"error": str(e)}
        )


async def query_with_timeout(
    client: ClaudeSDKClient,
    prompt: str,
    timeout: float = 60.0
) -> str:
    """
    Execute query with timeout protection and return response.

    Args:
        client: ClaudeSDKClient instance
        prompt: Query prompt
        timeout: Timeout in seconds (default: 60.0)

    Returns:
        Claude's response as string

    Raises:
        TradingError: If query times out or fails
    """
    try:
        await asyncio.wait_for(client.query(prompt), timeout=timeout)

        response_parts = []
        async for message in client.receive_response():
            # Skip SystemMessage objects - they're session metadata, not content
            if hasattr(message, 'subtype') and message.subtype == 'init':
                continue

            if hasattr(message, 'content'):
                for content_block in message.content:
                    if hasattr(content_block, 'text'):
                        response_parts.append(content_block.text)
            elif hasattr(message, 'text'):
                response_parts.append(message.text)
            elif hasattr(message, 'data') and isinstance(message.data, dict):
                # Handle SystemMessage data objects
                if message.data.get('type') == 'system':
                    continue  # Skip system messages
                else:
                    response_parts.append(str(message.data))
            else:
                # Only add non-system messages
                if not (hasattr(message, 'subtype') and message.subtype == 'init'):
                    response_parts.append(str(message))

        return "\n".join(response_parts) if response_parts else "No response content received"
    except Exception as e:
        raise _handle_sdk_error(e, timeout)


async def query_only_with_timeout(
    client: ClaudeSDKClient,
    prompt: str,
    timeout: float = 60.0
) -> None:
    """
    Send query with timeout protection only (does not receive response).

    Use this when you need raw response objects and will handle receive_response() separately.

    Args:
        client: ClaudeSDKClient instance
        prompt: Query prompt
        timeout: Timeout in seconds (default: 60.0)

    Raises:
        TradingError: If query times out or fails
    """
    try:
        await asyncio.wait_for(client.query(prompt), timeout=timeout)
    except Exception as e:
        raise _handle_sdk_error(e, timeout)


async def receive_response_with_timeout(
    client: ClaudeSDKClient,
    timeout: float = 120.0
) -> AsyncIterator[Any]:
    """
    Receive responses with timeout protection.

    Note: This wraps the iterator but timeout applies to each individual
    response read, not the entire iteration. For full conversation timeout,
    wrap the entire iteration in asyncio.wait_for() externally.

    Args:
        client: ClaudeSDKClient instance
        timeout: Timeout in seconds per response (default: 120.0)

    Yields:
        Response objects from client

    Raises:
        TradingError: If response reception times out or fails
    """
    try:
        iterator = client.receive_response()
        while True:
            try:
                response = await asyncio.wait_for(
                    iterator.__anext__(),
                    timeout=timeout
                )
                yield response
            except StopAsyncIteration:
                break
            except Exception as e:
                raise _handle_sdk_error(e, timeout)
    except Exception as e:
        if not isinstance(e, TradingError):
            raise _handle_sdk_error(e, timeout)
        raise


async def sdk_operation_with_retry(
    operation: callable,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    max_backoff: float = 30.0,
    **kwargs
) -> Any:
    """
    Execute SDK operation with exponential backoff retry.

    Args:
        operation: Async function to execute
        max_retries: Maximum number of retries
        initial_backoff: Initial backoff delay in seconds
        max_backoff: Maximum backoff delay in seconds
        **kwargs: Arguments to pass to operation

    Returns:
        Result from operation

    Raises:
        TradingError: If operation fails after retries
    """
    backoff = initial_backoff
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await operation(**kwargs)
        except TradingError as e:
            if not e.context.recoverable or attempt >= max_retries:
                raise

            last_error = e
            logger.warning(
                f"SDK operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                f"Retrying in {backoff:.1f}s"
            )

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

        except Exception as e:
            raise TradingError(
                f"SDK operation failed with unrecoverable error: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
                metadata={"error": str(e), "attempt": attempt + 1}
            )

    raise TradingError(
        f"SDK operation failed after {max_retries} retries: {last_error}",
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        recoverable=False,
        metadata={"max_retries": max_retries, "last_error": str(last_error)}
    )


def estimate_token_count(text: str) -> int:
    """
    Estimate token count for text (rough approximation).

    Args:
        text: Text to estimate

    Returns:
        Estimated token count (1 token ≈ 4 characters)
    """
    return len(text) // 4


def validate_system_prompt_size(prompt: str, max_tokens: int = 8000) -> Tuple[bool, int]:
    """
    Validate system prompt size.

    Args:
        prompt: System prompt text
        max_tokens: Maximum allowed tokens (default: 8000, safe limit is 10000)

    Returns:
        Tuple of (is_valid, estimated_tokens)
    """
    estimated_tokens = estimate_token_count(prompt)
    is_valid = estimated_tokens <= max_tokens

    if not is_valid:
        logger.warning(
            f"System prompt is {estimated_tokens} tokens (limit: {max_tokens}). "
            f"Consider shortening to prevent initialization failures."
        )

    return is_valid, estimated_tokens
