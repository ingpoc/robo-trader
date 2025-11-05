"""
Base Coordinator Abstract Class

All coordinators inherit from this base class to ensure consistent
initialization and cleanup patterns.
"""

from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger

from src.config import Config
from ..event_bus import EventBus


class BaseCoordinator(ABC):
    """
    Abstract base class for all coordinators.

    Provides common initialization and cleanup lifecycle hooks.
    """

    def __init__(self, config: Config, event_bus: Optional[EventBus] = None):
        self.config = config
        self.event_bus = event_bus
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the coordinator. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup coordinator resources. Must be implemented by subclasses."""
        pass

    def _log_debug(self, message: str) -> None:
        """Log debug message with coordinator name for detailed internal operations."""
        logger.debug(f"[{self.__class__.__name__}] {message}")

    def _log_info(self, message: str) -> None:
        """Log info message with coordinator name for important milestones and user actions."""
        logger.info(f"[{self.__class__.__name__}] {message}")

    def _log_error(self, message: str, exc_info: bool = False) -> None:
        """Log error message with coordinator name."""
        logger.error(f"[{self.__class__.__name__}] {message}", exc_info=exc_info)

    def _log_warning(self, message: str) -> None:
        """Log warning message with coordinator name."""
        logger.warning(f"[{self.__class__.__name__}] {message}")
