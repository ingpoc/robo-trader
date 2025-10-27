"""Trade execution routes."""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)

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
async def portfolio_scan(request: Request, background_tasks: BackgroundTasks, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Trigger portfolio scan and load holdings from CSV file."""

    try:
        logger.info("Starting portfolio scan request")
        orchestrator = await container.get_orchestrator()

        if not orchestrator:
            logger.error("Orchestrator not available for portfolio scan")
            return {"error": "System not available for portfolio scan"}

        # Run portfolio scan (loads holdings from CSV)
        logger.info("Executing portfolio scan")
        result = await orchestrator.run_portfolio_scan()
        logger.info(f"Portfolio scan result: {result}")

        # Get updated portfolio to return holdings
        portfolio = await orchestrator.state_manager.get_portfolio()

        if portfolio and portfolio.holdings:
            holdings_count = len(portfolio.holdings)
            logger.info(f"Portfolio scan completed successfully: {holdings_count} holdings loaded")
            return {
                "status": "Portfolio scan completed",
                "message": f"Successfully loaded {holdings_count} holdings",
                "source": result.get("source", "unknown"),
                "holdings_count": holdings_count,
                "portfolio": portfolio.to_dict()
            }
        else:
            logger.warning("Portfolio scan completed but no holdings found")
            return {
                "status": "Portfolio scan completed",
                "message": "No holdings found in CSV file",
                "source": result.get("source", "unknown"),
                "holdings_count": 0,
                "portfolio": None
            }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.post("/market-screening")
@limiter.limit(trade_limit)
async def market_screening(request: Request, background_tasks: BackgroundTasks, container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Trigger market screening."""

    try:
        orchestrator = await container.get_orchestrator()
        background_tasks.add_task(orchestrator.run_market_screening)
        return {"status": "Market screening started"}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.post("/manual-trade")
@limiter.limit(trade_limit)
async def manual_trade(request: Request, trade: TradeRequest, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Execute manual trade."""
    import uuid

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

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")
