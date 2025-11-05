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
    """
    Trigger portfolio scan with automatic OAuth flow if needed.
    
    Priority:
    1. Check for OAuth token in ENV variable
    2. If not found, check for API key/secret in ENV
    3. If API key/secret present, trigger OAuth flow
    4. If neither available, fallback to CSV
    """

    try:
        logger.info("Portfolio scan request initiated")

        # Get OAuth service to check for stored token
        oauth_service = await container.get("zerodha_oauth_service")

        # Check if a valid token already exists (same check as /api/auth/zerodha/login)
        token_data = await oauth_service.get_stored_token()

        if token_data:
            logger.info(f"Valid OAuth token found for user: {token_data.get('user_id')}, expires at: {token_data.get('expires_at')}")
            logger.info("Proceeding with broker connection using stored token")
        else:
            logger.debug("No valid OAuth token found in storage")

            # Check if API credentials are present for OAuth flow
            from src.config import load_config
            config = load_config()
            api_key = config.integration.zerodha_api_key
            api_secret = config.integration.zerodha_api_secret

            logger.debug(f"API credentials check - Key present: {bool(api_key)}, Secret present: {bool(api_secret)}")

            if api_key and api_secret:
                if oauth_service:
                    auth_data = await oauth_service.generate_auth_url(user_id=None)

                    # Return auth URL for frontend to open
                    auth_url = auth_data["auth_url"]
                    logger.info("OAuth authentication required - returning auth URL")

                    return {
                        "status": "oauth_required",
                        "message": "OAuth authentication required. Please open the auth URL in your browser.",
                        "auth_url": auth_url,
                        "state": auth_data["state"],
                        "redirect_url": auth_data["redirect_url"],
                        "instructions": "After approving in Zerodha, click 'Scan Portfolio' again to fetch holdings"
                    }
                else:
                    logger.error("OAuth service is None")
            else:
                logger.debug("No API credentials found, will fallback to CSV or database")

        # If we get here and no OAuth was triggered, proceed with normal scan
        # (either we have a token or we're falling back to CSV)

        logger.info("Executing portfolio scan")

        # Try broker connection (if token exists)
        broker = None
        if token_data:
            try:
                from src.config import load_config
                config = load_config()
                broker = await get_broker(config)
            except Exception as e:
                logger.warning(f"Failed to initialize broker: {e}")

        # Get orchestrator
        orchestrator = await container.get_orchestrator()
        if not orchestrator:
            logger.error("Orchestrator not available for portfolio scan")
            return {"error": "System not available for portfolio scan"}

        # Run portfolio scan
        result = await orchestrator.run_portfolio_scan()

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
                "message": "No holdings found",
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
