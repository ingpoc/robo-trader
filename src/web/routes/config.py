"""Configuration management routes."""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError

from ..dependencies import get_container
from ..utils.error_handlers import (handle_trading_error,
                                    handle_unexpected_error)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["config"])
limiter = Limiter(key_func=get_remote_address)

config_limit = os.getenv("RATE_LIMIT_CONFIG", "10/minute")


@router.get("/config/scheduler")
@limiter.limit(config_limit)
async def get_scheduler_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get scheduler configuration."""
    try:
        return {
            "portfolioScanFrequency": 60,
            "newsMonitoringTime": "16:00",
            "earningsCheckFrequency": 7,
            "fundamentalRecheck": True,
            "marketHours": {"start": "09:15", "end": "15:30", "timezone": "IST"},
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/config/trading")
@limiter.limit(config_limit)
async def get_trading_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get trading configuration."""
    try:
        return {
            "environment": "paper_trading",
            "paperCapital": {"swing": 100000, "options": 100000},
            "riskSettings": {
                "maxPositionSize": 5,
                "maxPortfolioRisk": 10,
                "stopLossDefault": 2,
            },
            "autoApprove": False,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/config/agent")
@limiter.limit(config_limit)
async def get_agent_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get AI agent configuration."""
    try:
        return {
            "dailyTokenBudget": 15000,
            "dailyPlanningTime": "09:15 IST",
            "weeklyPlanningDay": "Monday",
            "tokenAllocations": {"swing": 40, "options": 35, "analysis": 25},
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/config/data-source")
@limiter.limit(config_limit)
async def get_data_source_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get data source configuration."""
    try:
        return {
            "perplexityApiKey": "[****]",
            "queryTemplates": {
                "news": "Fetch latest news on [SYMBOL]",
                "earnings": "Fetch earnings date for [SYMBOL]",
                "fundamentals": "Fetch current fundamentals for [SYMBOL]",
            },
            "queryVersioning": True,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/config/database")
@limiter.limit(config_limit)
async def get_database_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get database configuration."""
    try:
        return {
            "databasePath": "/data/robo-trader.db",
            "backupFrequency": "daily",
            "backupRetention": 7,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/config")
@limiter.limit(config_limit)
async def get_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get all configuration - matches frontend expectation."""
    try:
        return {
            "scheduler": {
                "portfolioScanFrequency": 60,
                "newsMonitoringTime": "16:00",
                "earningsCheckFrequency": 7,
                "fundamentalRecheck": True,
                "marketHours": {"start": "09:15", "end": "15:30", "timezone": "IST"},
            },
            "trading": {
                "environment": "paper_trading",
                "paperCapital": {"swing": 100000, "options": 100000},
                "riskSettings": {
                    "maxPositionSize": 5,
                    "maxPortfolioRisk": 10,
                    "stopLossDefault": 2,
                },
                "autoApprove": False,
            },
            "agent": {
                "dailyTokenBudget": 15000,
                "dailyPlanningTime": "09:15 IST",
                "weeklyPlanningDay": "Monday",
                "tokenAllocations": {"swing": 40, "options": 35, "analysis": 25},
            },
            "dataSource": {
                "perplexityApiKey": "[****]",
                "queryTemplates": {
                    "news": "Fetch latest news on [SYMBOL]",
                    "earnings": "Fetch earnings date for [SYMBOL]",
                    "fundamentals": "Fetch current fundamentals for [SYMBOL]",
                },
                "queryVersioning": True,
            },
            "database": {
                "databasePath": "/data/robo-trader.db",
                "backupFrequency": "daily",
                "backupRetention": 7,
            },
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")
