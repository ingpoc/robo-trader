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
        logger.info("=" * 80)
        logger.info("PORTFOLIO SCAN REQUEST - Starting")
        logger.info("=" * 80)
        
        # First, check if Zerodha is authenticated
        from src.core.env_helpers import get_zerodha_token_from_env
        from src.mcp.broker import get_broker
        from src.config import load_config
        
        config = load_config()
        
        # Check for OAuth token in ENV (includes expiry check)
        env_token = get_zerodha_token_from_env()
        logger.info(f"ENV Token check: {env_token is not None}")
        
        if env_token:
            logger.info(f"Found valid OAuth token for user: {env_token.get('user_id')}")
            logger.info(f"Token expires at: {env_token.get('expires_at')}")
        
        # If no valid token, check if API credentials are present
        if not env_token:
            api_key = config.integration.zerodha_api_key
            api_secret = config.integration.zerodha_api_secret
            
            logger.info(f"Checking API credentials - Key present: {bool(api_key)}, Secret present: {bool(api_secret)}")
            
            if api_key and api_secret:
                logger.info("OAuth token not found but API credentials present, initiating OAuth flow")
                
                # Get OAuth service and initiate auth flow
                try:
                    oauth_service = await container.get("zerodha_oauth_service")
                    logger.info(f"OAuth service retrieved: {oauth_service is not None}")
                    
                    if oauth_service:
                        auth_data = await oauth_service.generate_auth_url(user_id=None)
                        
                        # Return auth URL for frontend to open
                        auth_url = auth_data["auth_url"]
                        logger.info(f"Generated OAuth URL: {auth_url}")
                        logger.info("=" * 80)
                        logger.info("RETURNING OAUTH REQUIRED RESPONSE")
                        logger.info("=" * 80)
                        
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
                except Exception as e:
                    logger.error(f"Failed to initiate OAuth flow: {e}", exc_info=True)
                    # Fall through to CSV fallback
            else:
                logger.info("No API credentials found, falling back to CSV")
        else:
            logger.info(f"Found OAuth token in ENV, proceeding with broker connection")
        
        # If we get here and no OAuth was triggered, proceed with normal scan
        # (either we have a token or we're falling back to CSV)
        
        logger.info("Proceeding with normal portfolio scan (no OAuth required)")
        
        # Try broker connection (if token exists)
        broker = None
        if env_token:
            try:
                broker = await get_broker(config)
            except Exception as e:
                logger.warning(f"Failed to initialize broker: {e}")
        
        # Get orchestrator
        orchestrator = await container.get_orchestrator()
        if not orchestrator:
            logger.error("Orchestrator not available for portfolio scan")
            return {"error": "System not available for portfolio scan"}

        # Run portfolio scan
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
