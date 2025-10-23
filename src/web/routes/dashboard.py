"""Dashboard and portfolio routes."""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])
limiter = Limiter(key_func=get_remote_address)

dashboard_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.get("/dashboard")
@router.get("/dashboard/")
async def api_dashboard(request: Request) -> Dict[str, Any]:
    """Get dashboard data."""
    from ..app import get_dashboard_data
    return await get_dashboard_data()


@router.get("/portfolio")
@limiter.limit(dashboard_limit)
async def get_portfolio(request: Request) -> Dict[str, Any]:
    """Get portfolio data with lazy bootstrap."""
    from ..app import container

    if not container:
        logger.error("System not initialized")
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        if not orchestrator or not orchestrator.state_manager:
            logger.error("Orchestrator not available")
            return JSONResponse({"error": "System not available"}, status_code=500)

        portfolio = await orchestrator.state_manager.get_portfolio()

        if not portfolio:
            try:
                logger.debug("Triggering portfolio bootstrap")
                await orchestrator.run_portfolio_scan()
                portfolio = await orchestrator.state_manager.get_portfolio()
            except Exception as exc:
                logger.warning(f"Bootstrap failed: {exc}")

        if not portfolio:
            logger.warning("No portfolio data available")
            return JSONResponse({"error": "No portfolio data available"}, status_code=404)

        logger.info("Portfolio retrieved successfully")
        return portfolio.to_dict()

    except Exception as e:
        logger.error(f"Portfolio retrieval failed: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to retrieve portfolio: {str(e)}"}, status_code=500)
