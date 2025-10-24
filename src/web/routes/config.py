"""Configuration management routes."""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["config"])
limiter = Limiter(key_func=get_remote_address)

config_limit = os.getenv("RATE_LIMIT_CONFIG", "10/minute")


@router.get("/config/scheduler")
@limiter.limit(config_limit)
async def get_scheduler_config(request: Request) -> Dict[str, Any]:
    """Get scheduler configuration."""
    try:
        return {
            "portfolioScanFrequency": 60,
            "newsMonitoringTime": "16:00",
            "earningsCheckFrequency": 7,
            "fundamentalRecheck": True,
            "marketHours": {
                "start": "09:15",
                "end": "15:30",
                "timezone": "IST"
            }
        }
    except Exception as e:
        logger.error(f"Scheduler config retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/config/trading")
@limiter.limit(config_limit)
async def get_trading_config(request: Request) -> Dict[str, Any]:
    """Get trading configuration."""
    try:
        return {
            "environment": "paper_trading",
            "paperCapital": {
                "swing": 100000,
                "options": 100000
            },
            "riskSettings": {
                "maxPositionSize": 5,
                "maxPortfolioRisk": 10,
                "stopLossDefault": 2
            },
            "autoApprove": False
        }
    except Exception as e:
        logger.error(f"Trading config retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/config/agent")
@limiter.limit(config_limit)
async def get_agent_config(request: Request) -> Dict[str, Any]:
    """Get AI agent configuration."""
    try:
        return {
            "dailyTokenBudget": 15000,
            "dailyPlanningTime": "09:15 IST",
            "weeklyPlanningDay": "Monday",
            "tokenAllocations": {
                "swing": 40,
                "options": 35,
                "analysis": 25
            }
        }
    except Exception as e:
        logger.error(f"Agent config retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/config/data-source")
@limiter.limit(config_limit)
async def get_data_source_config(request: Request) -> Dict[str, Any]:
    """Get data source configuration."""
    try:
        return {
            "perplexityApiKey": "[****]",
            "queryTemplates": {
                "news": "Fetch latest news on [SYMBOL]",
                "earnings": "Fetch earnings date for [SYMBOL]",
                "fundamentals": "Fetch current fundamentals for [SYMBOL]"
            },
            "queryVersioning": True
        }
    except Exception as e:
        logger.error(f"Data source config retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/config/database")
@limiter.limit(config_limit)
async def get_database_config(request: Request) -> Dict[str, Any]:
    """Get database configuration."""
    try:
        return {
            "databasePath": "/data/robo-trader.db",
            "backupFrequency": "daily",
            "backupRetention": 7
        }
    except Exception as e:
        logger.error(f"Database config retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/config")
@limiter.limit(config_limit)
async def get_config(request: Request) -> Dict[str, Any]:
    """Get all configuration - matches frontend expectation."""
    try:
        return {
            "scheduler": {
                "portfolioScanFrequency": 60,
                "newsMonitoringTime": "16:00",
                "earningsCheckFrequency": 7,
                "fundamentalRecheck": True,
                "marketHours": {
                    "start": "09:15",
                    "end": "15:30",
                    "timezone": "IST"
                }
            },
            "trading": {
                "environment": "paper_trading",
                "paperCapital": {
                    "swing": 100000,
                    "options": 100000
                },
                "riskSettings": {
                    "maxPositionSize": 5,
                    "maxPortfolioRisk": 10,
                    "stopLossDefault": 2
                },
                "autoApprove": False
            },
            "agent": {
                "dailyTokenBudget": 15000,
                "dailyPlanningTime": "09:15 IST",
                "weeklyPlanningDay": "Monday",
                "tokenAllocations": {
                    "swing": 40,
                    "options": 35,
                    "analysis": 25
                }
            },
            "dataSource": {
                "perplexityApiKey": "[****]",
                "queryTemplates": {
                    "news": "Fetch latest news on [SYMBOL]",
                    "earnings": "Fetch earnings date for [SYMBOL]",
                    "fundamentals": "Fetch current fundamentals for [SYMBOL]"
                },
                "queryVersioning": True
            },
            "database": {
                "databasePath": "/data/robo-trader.db",
                "backupFrequency": "daily",
                "backupRetention": 7
            }
        }
    except Exception as e:
        logger.error(f"Config retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
