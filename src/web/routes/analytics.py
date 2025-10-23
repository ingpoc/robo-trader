"""Analytics data routes."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])
limiter = Limiter(key_func=get_remote_address)

default_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.get("/analytics/portfolio-deep")
@limiter.limit(default_limit)
async def portfolio_deep_analytics(request: Request) -> Dict[str, Any]:
    """Get deep portfolio analytics."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        analytics = await orchestrator.state_manager.get_portfolio()

        if not analytics:
            return JSONResponse({"error": "No analytics available"}, status_code=404)

        return {
            "portfolio": analytics.to_dict() if hasattr(analytics, 'to_dict') else analytics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/analytics/trades")
@limiter.limit(default_limit)
async def get_trades_analytics(request: Request) -> Dict[str, Any]:
    """Get trades analytics."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        state_manager = orchestrator.state_manager

        trades = await state_manager.get_closed_trades()

        return {
            "total_trades": len(trades) if trades else 0,
            "trades": [t.to_dict() if hasattr(t, 'to_dict') else t for t in (trades or [])],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Trades analytics failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/alerts")
@limiter.limit(default_limit)
async def get_risk_alerts(request: Request, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get risk alerts."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        alerts = [
            {
                "id": "high_risk_alert",
                "severity": "high",
                "type": "risk_exposure",
                "message": "Portfolio risk exposure above threshold",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False
            }
        ]
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Alerts retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/monitor/status")
@limiter.limit(default_limit)
async def get_risk_monitoring_status(
    request: Request,
    user_id: Optional[str] = None,
    portfolio_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get risk monitoring status."""
    if not portfolio_id:
        portfolio_id = "portfolio_123"

    try:
        return {
            "monitoring_active": True,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "risk_score": 2.5,
            "alerts_count": 0,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Monitoring status failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/portfolio/risk-metrics")
@limiter.limit(default_limit)
async def get_portfolio_risk_metrics(
    request: Request,
    portfolio_id: str = "portfolio_123",
    period: str = "1M"
) -> Dict[str, Any]:
    """Get portfolio risk metrics."""
    try:
        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "sharpe_ratio": 1.8,
            "max_drawdown": -8.5,
            "volatility": 12.3,
            "var_95": -15000,
            "beta": 0.85,
            "alpha": 2.1,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Risk metrics failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
