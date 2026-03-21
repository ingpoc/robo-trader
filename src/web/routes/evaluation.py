"""Evaluation API routes for replay, divergence, and shadow-live reporting."""

import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.core.di import DependencyContainer
from src.web.dependencies import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/divergence")
async def get_divergence_report(
    request: Request,
    days: int = 30,
    container: DependencyContainer = Depends(get_container),
):
    """Get divergence report: research signals vs actual execution."""
    try:
        from src.services.evaluation.divergence_tracker import DivergenceTracker

        ledger_store = await container.get("research_ledger_store")
        lifecycle_store = await container.get("trade_lifecycle_store")
        tracker = DivergenceTracker(lifecycle_store, ledger_store)
        report = await tracker.get_divergence_report(days=days)
        return {"success": True, "data": report}
    except Exception as e:
        logger.error(f"Failed to get divergence report: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.get("/shadow")
async def get_shadow_report(
    request: Request,
    days: int = 7,
    container: DependencyContainer = Depends(get_container),
):
    """Get shadow-live mode performance report."""
    try:
        from src.services.evaluation.shadow_live import ShadowLiveService

        ledger_store = await container.get("research_ledger_store")
        lifecycle_store = await container.get("trade_lifecycle_store")
        shadow = ShadowLiveService(ledger_store, lifecycle_store)
        report = await shadow.get_shadow_report(days=days)
        return {"success": True, "data": report}
    except Exception as e:
        logger.error(f"Failed to get shadow report: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.get("/research-ledger")
async def get_research_ledger(
    request: Request,
    symbol: str = None,
    action: str = None,
    limit: int = 50,
    container: DependencyContainer = Depends(get_container),
):
    """Get research ledger entries (structured feature extraction results)."""
    try:
        ledger_store = await container.get("research_ledger_store")
        if symbol:
            entries = await ledger_store.get_history(symbol, limit=limit)
        elif action and action.upper() == "BUY":
            entries = await ledger_store.get_buy_candidates(limit=limit)
        else:
            entries = await ledger_store.get_all_latest(limit=limit)
        return {"success": True, "data": entries}
    except Exception as e:
        logger.error(f"Failed to get research ledger: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )
