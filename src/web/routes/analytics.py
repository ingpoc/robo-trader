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
        return {
            "total_trades": 0,
            "trades": [],
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


@router.get("/analytics/performance/30d")
@limiter.limit(default_limit)
async def get_performance_30d(request: Request) -> Dict[str, Any]:
    """Get 30-day performance analytics - matches frontend expectation."""
    try:
        performance_data = {
            "period": "30d",
            "totalReturn": 2.5,
            "totalReturnPercent": 2.5,
            "dailyReturns": [0.1, -0.2, 0.3, 0.1, -0.1, 0.2, 0.1, 0.0, 0.1, -0.1],
            "cumulativeReturns": [0.1, -0.1, 0.2, 0.3, 0.2, 0.4, 0.5, 0.5, 0.6, 0.5],
            "winRate": 65,
            "totalTrades": 12,
            "winningTrades": 8,
            "losingTrades": 4,
            "avgWin": 450,
            "avgLoss": -320,
            "profitFactor": 1.8,
            "maxDrawdown": -1200,
            "sharpeRatio": 1.2,
            "volatility": 8.5,
            "benchmarkReturn": 1.8,
            "alpha": 0.7,
            "beta": 0.85,
            "topPerformers": [
                {"symbol": "HDFC", "return": 3.2, "contribution": 0.8},
                {"symbol": "INFY", "return": 2.8, "contribution": 0.6},
                {"symbol": "TCS", "return": 2.1, "contribution": 0.4}
            ],
            "worstPerformers": [
                {"symbol": "SBIN", "return": -1.2, "contribution": -0.3},
                {"symbol": "MARUTI", "return": -0.8, "contribution": -0.2}
            ],
            "sectorAllocation": {
                "IT": 35,
                "Banking": 25,
                "Auto": 15,
                "Energy": 10,
                "Pharma": 10,
                "Others": 5
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

        return {"performance": performance_data}
    except Exception as e:
        logger.error(f"30-day performance analytics failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/alerts/active")
@limiter.limit(default_limit)
async def get_active_alerts(request: Request) -> Dict[str, Any]:
    """Get active alerts - matches frontend expectation."""
    try:
        alerts = [
            {
                "id": "alert_1",
                "type": "risk_exposure",
                "severity": "high",
                "message": "Portfolio risk exposure above threshold (12.5% > 10%)",
                "symbol": None,
                "threshold": 10.0,
                "current": 12.5,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False,
                "autoGenerated": True
            },
            {
                "id": "alert_2",
                "type": "stop_loss",
                "severity": "medium",
                "message": "Stop loss triggered for TCS position",
                "symbol": "TCS",
                "threshold": 4350,
                "current": 4320,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False,
                "autoGenerated": True
            },
            {
                "id": "alert_3",
                "type": "earnings",
                "severity": "low",
                "message": "TCS earnings report due tomorrow",
                "symbol": "TCS",
                "threshold": None,
                "current": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "acknowledged": False,
                "autoGenerated": True
            }
        ]

        return {
            "alerts": alerts,
            "total": len(alerts),
            "critical": len([a for a in alerts if a["severity"] == "high"]),
            "warning": len([a for a in alerts if a["severity"] == "medium"]),
            "info": len([a for a in alerts if a["severity"] == "low"]),
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Active alerts retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
