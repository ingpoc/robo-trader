"""Domain models for repository layer.

These models represent pure domain concepts with no database coupling.
They are used by repositories to return rich, typed objects instead of dictionaries.
"""

from .queue_state import QueueState, QueueStatus
from .task_state import TaskState

__all__ = [
    'QueueState',
    'QueueStatus',
    'TaskState',
]
