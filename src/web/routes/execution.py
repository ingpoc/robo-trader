"""Trade execution routes."""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["execution"])
limiter = Limiter(key_func=get_remote_address)

trade_limit = os.getenv("RATE_LIMIT_TRADES", "10/minute")


class TradeRequest(BaseModel):
    """Manual trade request."""
    symbol: str
    side: str
    quantity: int
    order_type: str = "MARKET"
    price: Optional[float] = None


@router.post("/portfolio-scan")
@limiter.limit(trade_limit)
async def portfolio_scan(request: Request, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Trigger portfolio scan."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        background_tasks.add_task(orchestrator.run_portfolio_scan)
        return {"status": "Portfolio scan started"}
    except Exception as e:
        logger.error(f"Portfolio scan failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/market-screening")
@limiter.limit(trade_limit)
async def market_screening(request: Request, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Trigger market screening."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        background_tasks.add_task(orchestrator.run_market_screening)
        return {"status": "Market screening started"}
    except Exception as e:
        logger.error(f"Market screening failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/manual-trade")
@limiter.limit(trade_limit)
async def manual_trade(request: Request, trade: TradeRequest) -> Dict[str, Any]:
    """Execute manual trade."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()

        # Create intent
        intent = await orchestrator.state_manager.create_intent(trade.symbol)

        # Simulate signal
        from ...core.state import Signal
        signal = Signal(
            symbol=trade.symbol,
            timeframe="manual",
            entry={"type": trade.order_type, "price": trade.price},
            confidence=1.0,
            rationale="Manual trade"
        )
        intent.signal = signal

        # Risk assessment
        from ...agents.risk_manager import risk_assessment_tool
        await risk_assessment_tool({"intent_id": intent.id})

        # Execute if approved
        if intent.risk_decision and intent.risk_decision.decision == "approve":
            await orchestrator.state_manager.execute_intent(intent.id)
            return {"status": "Trade executed", "intent_id": intent.id}
        else:
            return JSONResponse(
                {"error": "Trade rejected by risk manager"},
                status_code=400
            )
    except Exception as e:
        logger.error(f"Manual trade failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)
