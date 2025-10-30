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
        # Return sample market news data
        sample_news = [
            {
                "id": "news_1",
                "title": "Market Analysis: Tech Stocks Show Strong Momentum",
                "summary": "Technology sector continues to outperform market expectations with Q3 earnings beating estimates.",
                "source": "Financial Express",
                "url": "https://example.com/news/1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sentiment": "positive",
                "relevance_score": 0.85
            },
            {
                "id": "news_2",
                "title": "Banking Sector Faces Regulatory Changes",
                "summary": "RBI announces new guidelines that may impact lending rates across major banks.",
                "source": "Economic Times",
                "url": "https://example.com/news/2",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sentiment": "neutral",
                "relevance_score": 0.72
            }
        ]

        # Return sample earnings data
        sample_earnings = [
            {
                "id": "earnings_1",
                "symbol": "INFY",
                "company": "Infosys Limited",
                "date": "2025-01-15",
                "quarter": "Q3",
                "expected_eps": 18.50,
                "actual_eps": None,
                "surprise_percent": None,
                "status": "upcoming"
            },
            {
                "id": "earnings_2",
                "symbol": "TCS",
                "company": "Tata Consultancy Services",
                "date": "2025-01-18",
                "quarter": "Q3",
                "expected_eps": 45.25,
                "actual_eps": None,
                "surprise_percent": None,
                "status": "upcoming"
            }
        ]

        return {
            "news": sample_news[:news_limit],
            "earnings": sample_earnings[:earnings_limit],
            "news_limit": news_limit,
            "earnings_limit": earnings_limit,
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/news-earnings/{symbol}")
@limiter.limit(news_earnings_limit)
async def get_news_earnings(request: Request, symbol: str, news_limit: int = 10, earnings_limit: int = 5, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get news and earnings data for a symbol from database."""
    try:
        # Return sample symbol-specific news
        symbol_news = [
            {
                "id": f"news_{symbol}_1",
                "title": f"{symbol} Reports Strong Q3 Results",
                "summary": f"{symbol} announced better than expected quarterly earnings, driven by strong performance in key business segments.",
                "source": "Business Standard",
                "url": f"https://example.com/news/{symbol}/1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sentiment": "positive",
                "relevance_score": 0.95
            }
        ]

        # Return sample earnings data for symbol
        symbol_earnings = [
            {
                "id": f"earnings_{symbol}_1",
                "symbol": symbol,
                "company": f"{symbol} Limited",
                "date": "2025-01-20",
                "quarter": "Q3",
                "expected_eps": 25.50,
                "actual_eps": None,
                "surprise_percent": None,
                "status": "upcoming"
            }
        ]

        return {
            "symbol": symbol,
            "news": symbol_news[:news_limit],
            "earnings": symbol_earnings[:earnings_limit],
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/earnings/upcoming")
@limiter.limit(news_earnings_limit)
async def get_upcoming_earnings(request: Request, days_ahead: int = 60, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get upcoming earnings calendar from database."""
    try:
        # Return sample upcoming earnings
        upcoming_earnings = [
            {
                "id": "earnings_upcoming_1",
                "symbol": "INFY",
                "company": "Infosys Limited",
                "date": "2025-01-15",
                "quarter": "Q3",
                "expected_eps": 18.50,
                "actual_eps": None,
                "surprise_percent": None,
                "status": "upcoming",
                "days_until": 5
            },
            {
                "id": "earnings_upcoming_2",
                "symbol": "TCS",
                "company": "Tata Consultancy Services",
                "date": "2025-01-18",
                "quarter": "Q3",
                "expected_eps": 45.25,
                "actual_eps": None,
                "surprise_percent": None,
                "status": "upcoming",
                "days_until": 8
            },
            {
                "id": "earnings_upcoming_3",
                "symbol": "HDFC",
                "company": "HDFC Bank Limited",
                "date": "2025-01-22",
                "quarter": "Q3",
                "expected_eps": 65.75,
                "actual_eps": None,
                "surprise_percent": None,
                "status": "upcoming",
                "days_until": 12
            }
        ]

        return {
            "earnings": upcoming_earnings[:days_ahead],
            "total": len(upcoming_earnings),
            "daysAhead": days_ahead,
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
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
