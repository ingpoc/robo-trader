"""
Background Scheduler for Robo Trader - Backward Compatibility Layer

This module maintains backward compatibility by re-exporting from the new modular structure.
All imports from this file will continue to work as before.

New Code: Use modular imports from src.core.background_scheduler.* directly
Legacy Code: Can continue using imports from this file
"""

from src.core.background_scheduler.background_scheduler import \
    BackgroundScheduler
from src.core.background_scheduler.models import (BackgroundTask, TaskPriority,
                                                  TaskType)

__all__ = ["BackgroundScheduler", "TaskType", "TaskPriority", "BackgroundTask"]
