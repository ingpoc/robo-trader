"""Data Transfer Objects (DTOs) for API responses.

DTOs provide a consistent schema across:
- REST API responses
- WebSocket messages
- Frontend TypeScript interfaces

This ensures no schema mismatches between backend and frontend.
"""

from .queue_status_dto import QueueStatusDTO, CurrentTaskDTO
from .system_status_dto import SystemStatusDTO, ComponentStatusDTO

__all__ = [
    'QueueStatusDTO',
    'CurrentTaskDTO',
    'SystemStatusDTO',
    'ComponentStatusDTO',
]
