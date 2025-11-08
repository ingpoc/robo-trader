"""Repository layer for data access.

Repositories provide clean, domain-focused data access patterns:
- Single source of truth (always query database)
- Efficient SQL queries (optimized for performance)
- Rich domain objects (not raw dictionaries)
- Reusable patterns (BaseRepository)

Usage:
    queue_repo = QueueStateRepository(database)
    await queue_repo.initialize()

    # Get all queue statuses in single query
    statuses = await queue_repo.get_all_statuses()

    # Get specific queue status
    ai_queue = await queue_repo.get_status("ai_analysis")
"""

from .base_repository import BaseRepository
from .queue_state_repository import QueueStateRepository
from .task_repository import TaskRepository

__all__ = [
    'BaseRepository',
    'QueueStateRepository',
    'TaskRepository',
]
