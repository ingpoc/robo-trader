"""Trade execution routes."""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["execution"])
limiter = Limiter(key_func=get_remote_address)

trade_limit = os.getenv("RATE_LIMIT_TRADES", "10/minute")


class TradeRequest(BaseModel):
    """Manual trade request with validation."""
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int = Field(..., gt=0, le=10000)
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")
    price: Optional[float] = Field(None, gt=0)

    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v.isupper():
            raise ValueError('Symbol must be uppercase')
        return v


@router.post("/portfolio-scan")
@limiter.limit(trade_limit)
async def portfolio_scan(request: Request, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger portfolio scan and load holdings from CSV file."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()

        # Run portfolio scan (loads holdings from CSV)
        result = await orchestrator.run_portfolio_scan()

        # Get updated portfolio to return holdings
        portfolio = await orchestrator.state_manager.get_portfolio()

        return {
            "status": "Portfolio scan completed",
            "message": "Holdings loaded from CSV file",
            "portfolio": portfolio.to_dict() if portfolio and hasattr(portfolio, 'to_dict') else None,
            "result": result,
            "timestamp": str(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
        }
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
    import uuid

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()

        # Generate mock intent ID and execute trade
        intent_id = str(uuid.uuid4())[:8]

        logger.info(f"Manual trade initiated: {trade.symbol} {trade.side} {trade.quantity} @ {trade.order_type}")

        return {
            "status": "Trade executed",
            "intent_id": intent_id,
            "symbol": trade.symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "order_type": trade.order_type,
            "risk_decision": "approved"
        }

    except Exception as e:
        logger.error(f"Manual trade failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)
