"""
API key rotation management for Perplexity API.

Handles round-robin key rotation with error tracking.
"""

from typing import List, Optional
from loguru import logger


class APIKeyRotator:
    """Manages API key rotation with round-robin strategy and error tracking."""

    def __init__(self, api_keys: List[str]):
        """Initialize API key rotator.

        Args:
            api_keys: List of API keys to rotate through
        """
        if not api_keys:
            logger.warning("No API keys provided to APIKeyRotator")

        self.api_keys = api_keys
        self.current_index = 0
        self.error_counts = {i: 0 for i in range(len(api_keys))}

    def get_next_key(self) -> Optional[str]:
        """Get next API key in rotation.

        Returns:
            Next API key, or None if no keys available
        """
        if not self.api_keys:
            return None

        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key

    def get_current_key(self) -> Optional[str]:
        """Get current API key without advancing rotation.

        Returns:
            Current API key, or None if no keys available
        """
        if not self.api_keys:
            return None

        return self.api_keys[self.current_index]

    def rotate_on_error(self, key: Optional[str]) -> None:
        """Track error for key and rotate to next key.

        Args:
            key: API key that encountered error
        """
        if not key or not self.api_keys:
            return

        try:
            key_index = self.api_keys.index(key)
            self.error_counts[key_index] += 1
            logger.warning(f"Error count for key {key_index + 1}: {self.error_counts[key_index]}")
        except ValueError:
            pass

        self.current_index = (self.current_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to key index {self.current_index + 1}")

    def get_error_stats(self) -> dict:
        """Get error statistics for all keys.

        Returns:
            Dictionary with error counts per key
        """
        return self.error_counts.copy()

    def reset_errors(self) -> None:
        """Reset error counts for all keys."""
        self.error_counts = {i: 0 for i in range(len(self.api_keys))}
        logger.info("API key error counts reset")

    def get_key_count(self) -> int:
        """Get total number of available keys.

        Returns:
            Number of API keys
        """
        return len(self.api_keys)

    def get_healthy_keys(self, error_threshold: int = 5) -> List[str]:
        """Get list of keys with error count below threshold.

        Args:
            error_threshold: Maximum error count for a key to be considered healthy

        Returns:
            List of healthy API keys
        """
        healthy = []
        for i, key in enumerate(self.api_keys):
            if self.error_counts.get(i, 0) < error_threshold:
                healthy.append(key)
        return healthy
