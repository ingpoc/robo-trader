"""News and earnings routes."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
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

router = APIRouter(prefix="/api", tags=["news-earnings"])
limiter = Limiter(key_func=get_remote_address)

news_earnings_limit = os.getenv("RATE_LIMIT_NEWS_EARNINGS", "20/minute")


@router.get("/news-earnings/")
@limiter.limit(news_earnings_limit)
async def get_news_earnings_general(request: Request, news_limit: int = 10, earnings_limit: int = 5, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get general news and earnings data (portfolio-wide or market overview)."""
    try:
        # Get state manager and fetch real data from database
        state_manager = await container.get_state_manager()
        
        # Try to get portfolio symbols first
        portfolio_symbols = []
        try:
            orchestrator = await container.get_orchestrator()
            if orchestrator and orchestrator.state_manager:
                portfolio_state = await orchestrator.state_manager.get_portfolio()
                if portfolio_state and portfolio_state.holdings:
                    portfolio_symbols = [holding.get("symbol") for holding in portfolio_state.holdings if holding.get("symbol")]
        except Exception as e:
            logger.debug(f"Could not get portfolio symbols for general news/earnings: {e}")
        
        # Fetch recent news (from all portfolio symbols or recent news if no portfolio)
        all_news = []
        if portfolio_symbols:
            # Get news for all portfolio symbols
            for symbol in portfolio_symbols[:10]:  # Limit to first 10 symbols
                symbol_news = await state_manager.get_news_for_symbol(symbol, limit=news_limit)
                all_news.extend(symbol_news)
        else:
            # If no portfolio, try to get most recent news from database
            # Note: This requires a method to get recent news across all symbols
            # For now, return empty and log
            logger.debug("No portfolio symbols found for general news/earnings")
        
        # Sort by published_at DESC and limit
        all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        formatted_news = []
        for news in all_news[:news_limit]:
            formatted_news.append({
                "id": f"news_{news.get('id', 'unknown')}",
                "title": news.get("title", news.get("headline", "")),
                "summary": news.get("summary", ""),
                "source": news.get("source", "Unknown"),
                "sentiment": news.get("sentiment", "neutral").lower(),
                "relevance_score": news.get("relevance_score", 0.5),
                "timestamp": news.get("published_at", datetime.now(timezone.utc).isoformat()),
            })

        # Fetch recent earnings (from all portfolio symbols or recent earnings)
        all_earnings = []
        if portfolio_symbols:
            # Get earnings for all portfolio symbols
            for symbol in portfolio_symbols[:10]:  # Limit to first 10 symbols
                symbol_earnings = await state_manager.get_earnings_for_symbol(symbol, limit=earnings_limit)
                all_earnings.extend(symbol_earnings)
        else:
            logger.debug("No portfolio symbols found for general earnings")
        
        # Sort by report_date DESC and limit
        all_earnings.sort(key=lambda x: x.get("report_date", ""), reverse=True)
        formatted_earnings = []
        for earnings in all_earnings[:earnings_limit]:
            formatted_earnings.append({
                "id": f"earnings_{earnings.get('id', 'unknown')}",
                "symbol": earnings.get("symbol", ""),
                "date": earnings.get("report_date", ""),
                "quarter": earnings.get("fiscal_period", "N/A"),
                "expected_eps": earnings.get("eps_estimated"),
                "actual_eps": earnings.get("eps_actual"),
                "surprise_percent": earnings.get("surprise_pct"),
                "status": "reported" if earnings.get("eps_actual") else "upcoming"
            })

        return {
            "news": formatted_news,
            "earnings": formatted_earnings,
            "news_limit": news_limit,
            "earnings_limit": earnings_limit,
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Error fetching general news/earnings: {e}", exc_info=True)
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/news-earnings/{symbol}")
@limiter.limit(news_earnings_limit)
async def get_news_earnings(request: Request, symbol: str, news_limit: int = 10, earnings_limit: int = 5, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get news and earnings data for a symbol from database."""
    try:
        # Get state manager and fetch real data from database
        state_manager = await container.get_state_manager()
        
        # Fetch news and earnings from database
        symbol_news = await state_manager.get_news_for_symbol(symbol, limit=news_limit)
        symbol_earnings_raw = await state_manager.get_earnings_for_symbol(symbol, limit=earnings_limit)
        
        # Transform earnings data to match frontend expected format
        symbol_earnings = []
        for earnings in symbol_earnings_raw:
            symbol_earnings.append({
                "id": f"earnings_{symbol}_{earnings.get('id', 'unknown')}",
                "symbol": earnings.get("symbol", symbol),
                "fiscal_period": earnings.get("fiscal_period", ""),
                "fiscal_year": earnings.get("fiscal_year"),
                "fiscal_quarter": earnings.get("fiscal_quarter"),
                "report_date": earnings.get("report_date", ""),
                "eps_actual": earnings.get("eps_actual"),
                "eps_estimated": earnings.get("eps_estimated"),
                "revenue_actual": earnings.get("revenue_actual"),
                "revenue_estimated": earnings.get("revenue_estimated"),
                "surprise_pct": earnings.get("surprise_pct"),
                "guidance": earnings.get("guidance"),
                "next_earnings_date": earnings.get("next_earnings_date"),
                "fetched_at": earnings.get("fetched_at", datetime.now(timezone.utc).isoformat()),
                "created_at": earnings.get("created_at", datetime.now(timezone.utc).isoformat())
            })

        # Transform news data to match frontend expected format
        formatted_news = []
        for news in symbol_news:
            formatted_news.append({
                "id": f"news_{symbol}_{news.get('id', 'unknown')}",
                "symbol": news.get("symbol", symbol),
                "title": news.get("headline", news.get("title", "")),  # Database has "title", but check for "headline" for compatibility
                "summary": news.get("summary", news.get("content", "")),  # Database has "summary" field, content is separate
                "content": news.get("content", news.get("summary", "")),  # Full content from database
                "source": news.get("source", "Unknown"),
                "sentiment": news.get("sentiment", "neutral").lower(),
                "relevance_score": news.get("relevance_score", 0.5),
                "published_at": news.get("published_at", datetime.now(timezone.utc).isoformat()),
                "fetched_at": news.get("fetched_at", datetime.now(timezone.utc).isoformat()),
                "citations": news.get("citations"),
                "created_at": news.get("created_at", datetime.now(timezone.utc).isoformat())
            })

        return {
            "symbol": symbol,
            "news": formatted_news[:news_limit],
            "earnings": symbol_earnings[:earnings_limit],
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Error fetching news/earnings for {symbol}: {e}", exc_info=True)
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/earnings/upcoming")
@limiter.limit(news_earnings_limit)
async def get_upcoming_earnings(request: Request, days_ahead: int = 60, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get upcoming earnings calendar from database."""
    try:
        logger.info(f"Fetching upcoming earnings for {days_ahead} days")
        # Get state manager and fetch real data from database
        try:
            state_manager = await container.get_state_manager()
            logger.debug("Got state manager, calling get_upcoming_earnings")
        except Exception as e:
            logger.error(f"Failed to get state manager: {e}", exc_info=True)
            raise
        
        # Fetch upcoming earnings from database
        try:
            upcoming_earnings_raw = await state_manager.get_upcoming_earnings(days_ahead)
            logger.info(f"Retrieved {len(upcoming_earnings_raw)} upcoming earnings from database")
        except Exception as e:
            logger.error(f"Failed to fetch upcoming earnings from database: {e}", exc_info=True)
            raise
        
        # Transform to match frontend expected format
        upcoming_earnings = []
        for earnings in upcoming_earnings_raw:
            try:
                # Calculate days until if next_earnings_date is available
                days_until = None
                next_earnings_date_str = earnings.get("next_earnings_date")
                if next_earnings_date_str:
                    try:
                        # Parse date string (could be ISO format or date only)
                        if 'T' in str(next_earnings_date_str):
                            next_date = datetime.fromisoformat(str(next_earnings_date_str).replace('Z', '+00:00')).date()
                        else:
                            # Date only format (YYYY-MM-DD)
                            next_date = datetime.fromisoformat(str(next_earnings_date_str)).date()
                        
                        today = datetime.now(timezone.utc).date()
                        days_until = (next_date - today).days
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.debug(f"Could not parse next_earnings_date {next_earnings_date_str}: {e}")
                        pass
                
                upcoming_earnings.append({
                    "id": f"earnings_upcoming_{earnings.get('id', 'unknown')}",
                    "symbol": earnings.get("symbol", ""),
                    "company": earnings.get("company", f"{earnings.get('symbol', '')} Limited"),
                    "date": next_earnings_date_str or earnings.get("report_date", ""),
                    "quarter": earnings.get("fiscal_period", "N/A"),
                    "expected_eps": earnings.get("eps_estimated"),
                    "actual_eps": earnings.get("eps_actual"),
                    "surprise_percent": earnings.get("surprise_pct"),
                    "status": "upcoming" if not earnings.get("eps_actual") else "reported",
                    "days_until": days_until
                })
            except Exception as e:
                logger.warning(f"Error processing earnings entry: {e}, skipping", exc_info=True)
                continue

        return {
            "earnings": upcoming_earnings,
            "total": len(upcoming_earnings),
            "daysAhead": days_ahead,
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Error fetching upcoming earnings: {e}", exc_info=True)
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/ai/recommendations")
@limiter.limit(news_earnings_limit)
async def get_ai_recommendations(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get AI-powered stock recommendations from database."""
    try:
        # Get recommendations from database
        state_manager = await container.get_state_manager()
        recommendations = await state_manager.get_recommendations()

        # Transform to expected format
        formatted_recommendations = []
        for rec in recommendations:
            formatted_recommendations.append({
                "id": rec.id,
                "symbol": rec.symbol,
                "action": rec.recommendation_type.upper(),
                "confidence": rec.confidence_score,
                "target_price": rec.target_price,
                "stop_loss": rec.stop_loss,
                "time_horizon": getattr(rec, 'time_horizon', '3-6 months'),
                "thesis": getattr(rec, 'reasoning', 'AI-generated recommendation based on fundamental and technical analysis'),
                "risk_level": getattr(rec, 'risk_level', 'Medium'),
                "sector": getattr(rec, 'sector', 'Unknown'),
                "created_at": rec.created_at.isoformat() if hasattr(rec.created_at, 'isoformat') else rec.created_at
            })

        return {
            "recommendations": formatted_recommendations,
            "total": len(formatted_recommendations),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "modelVersion": "claude-sonnet-4.5",
            "disclaimer": "AI-generated recommendations are for educational purposes only"
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")
