"""Trading capability routes for mission-critical readiness checks."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.core.di import DependencyContainer
from src.web.dependencies import get_container
from src.web.utils.error_handlers import handle_unexpected_error

router = APIRouter(prefix="/api/paper-trading", tags=["paper-trading-capabilities"])


@router.get("/capabilities")
async def get_trading_capabilities(
    request: Request,
    account_id: Optional[str] = Query(default=None, description="Selected paper trading account ID"),
    container: DependencyContainer = Depends(get_container),
):
    """Return a fail-loud capability snapshot for paper-trading automation."""
    try:
        capability_service = await container.get("trading_capability_service")
        snapshot = await capability_service.get_snapshot(account_id=account_id)
        return snapshot.to_dict()
    except Exception as exc:
        return await handle_unexpected_error(exc, "get_trading_capabilities")
