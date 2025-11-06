"""Web API routes for Robo Trader."""

from .agents import router as agents_router
from .analytics import router as analytics_router
from .dashboard import router as dashboard_router
from .execution import router as execution_router
from .monitoring import router as monitoring_router

__all__ = [
    "dashboard_router",
    "execution_router",
    "monitoring_router",
    "agents_router",
    "analytics_router",
]
