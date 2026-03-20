"""Web API routes for Robo Trader."""

from .dashboard import router as dashboard_router
from .monitoring import router as monitoring_router

__all__ = [
    'dashboard_router',
    'monitoring_router',
]
