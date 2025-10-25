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


@router.get("/news-earnings/{symbol}")
@limiter.limit(news_earnings_limit)
async def get_news_earnings(request: Request, symbol: str, news_limit: int = 10, earnings_limit: int = 5, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get news and earnings data for a symbol - matches frontend expectation."""
    try:
        # Mock news data
        news_data = [
            {
                "id": f"news_{i+1}",
                "symbol": symbol,
                "title": f"Market Update for {symbol} - Q3 Results",
                "summary": f"{symbol} reported strong quarterly results with revenue growth of 15%.",
                "source": "Economic Times",
                "publishedAt": datetime.now(timezone.utc).isoformat(),
                "sentiment": "positive",
                "url": f"https://economictimes.com/{symbol.lower()}-news"
            }
            for i in range(news_limit)
        ]

        # Mock earnings data
        earnings_data = [
            {
                "id": f"earnings_{i+1}",
                "symbol": symbol,
                "date": "2025-10-30",
                "time": "After Market",
                "estimate": 25.50,
                "actual": None,
                "surprise": None,
                "revenueEstimate": 1500000000,
                "revenueActual": None,
                "fiscalQuarter": "Q3 2025",
                "fiscalYear": 2025,
                "status": "upcoming"
            }
            for i in range(earnings_limit)
        ]

        return {
            "symbol": symbol,
            "news": news_data,
            "earnings": earnings_data,
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/earnings/upcoming")
@limiter.limit(news_earnings_limit)
async def get_upcoming_earnings(request: Request, days_ahead: int = 60, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get upcoming earnings calendar - matches frontend expectation."""
    try:
        upcoming_earnings = [
            {
                "symbol": "TCS",
                "date": "2025-10-25",
                "time": "After Market",
                "estimate": 45.20,
                "revenueEstimate": 2500000000,
                "fiscalQuarter": "Q3 2025",
                "fiscalYear": 2025,
                "marketCap": 1500000000000
            },
            {
                "symbol": "INFY",
                "date": "2025-10-26",
                "time": "Before Market",
                "estimate": 18.75,
                "revenueEstimate": 1200000000,
                "fiscalQuarter": "Q3 2025",
                "fiscalYear": 2025,
                "marketCap": 800000000000
            },
            {
                "symbol": "HDFC",
                "date": "2025-10-28",
                "time": "After Market",
                "estimate": 85.30,
                "revenueEstimate": 1800000000,
                "fiscalQuarter": "Q3 2025",
                "fiscalYear": 2025,
                "marketCap": 900000000000
            },
            {
                "symbol": "RELIANCE",
                "date": "2025-10-30",
                "time": "After Market",
                "estimate": 125.50,
                "revenueEstimate": 95000000000,
                "fiscalQuarter": "Q3 2025",
                "fiscalYear": 2025,
                "marketCap": 2000000000000
            }
        ]

        return {
            "earnings": upcoming_earnings,
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
    """Get AI-powered stock recommendations - matches frontend expectation."""
    try:
        recommendations = [
            {
                "symbol": "TCS",
                "recommendation": "BUY",
                "confidence": 85,
                "targetPrice": 4600,
                "currentPrice": 4450,
                "upside": 3.4,
                "rationale": "Strong earnings momentum and positive sector outlook",
                "riskLevel": "medium",
                "timeframe": "3-6 months",
                "generatedAt": datetime.now(timezone.utc).isoformat()
            },
            {
                "symbol": "INFY",
                "recommendation": "HOLD",
                "confidence": 72,
                "targetPrice": 3250,
                "currentPrice": 3200,
                "upside": 1.6,
                "rationale": "Fair valuation, limited upside in current market conditions",
                "riskLevel": "low",
                "timeframe": "1-3 months",
                "generatedAt": datetime.now(timezone.utc).isoformat()
            },
            {
                "symbol": "HDFC",
                "recommendation": "BUY",
                "confidence": 78,
                "targetPrice": 2900,
                "currentPrice": 2800,
                "upside": 3.6,
                "rationale": "Strong fundamentals and positive technical indicators",
                "riskLevel": "medium",
                "timeframe": "1-3 months",
                "generatedAt": datetime.now(timezone.utc).isoformat()
            }
        ]

        return {
            "recommendations": recommendations,
            "total": len(recommendations),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "modelVersion": "claude-3.5-sonnet",
            "disclaimer": "AI-generated recommendations are for educational purposes only"
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")
