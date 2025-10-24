"""News, earnings, and fundamentals routes."""

import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["news-earnings"])
limiter = Limiter(key_func=get_remote_address)

news_limit = os.getenv("RATE_LIMIT_NEWS", "20/minute")


@router.get("/news-earnings/feed")
@limiter.limit(news_limit)
async def get_news_feed(request: Request) -> Dict[str, Any]:
    """Get news feed articles."""
    try:
        now = datetime.now(timezone.utc)
        return {
            "articles": [
                {
                    "id": "news_1",
                    "symbol": "INFY",
                    "title": "Infosys Q3 earnings beat expectations",
                    "source": "Reuters",
                    "sentiment": "positive",
                    "publishedAt": (now - timedelta(hours=2)).isoformat(),
                    "summary": "Infosys reported better than expected Q3 results with strong margin improvement.",
                    "url": "https://example.com/news/infy-q3"
                },
                {
                    "id": "news_2",
                    "symbol": "TCS",
                    "title": "TCS announces new sustainability initiatives",
                    "source": "Economic Times",
                    "sentiment": "neutral",
                    "publishedAt": (now - timedelta(hours=4)).isoformat(),
                    "summary": "TCS unveiled comprehensive sustainability targets.",
                    "url": "https://example.com/news/tcs-sustainability"
                },
                {
                    "id": "news_3",
                    "symbol": "HDFC",
                    "title": "HDFC Bank credit growth accelerates",
                    "source": "Business Today",
                    "sentiment": "positive",
                    "publishedAt": (now - timedelta(hours=6)).isoformat(),
                    "summary": "HDFC Bank shows strong credit growth in latest quarter.",
                    "url": "https://example.com/news/hdfc-credit"
                }
            ]
        }
    except Exception as e:
        logger.error(f"News feed retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/earnings/calendar")
@limiter.limit(news_limit)
async def get_earnings_calendar(request: Request) -> Dict[str, Any]:
    """Get earnings calendar."""
    try:
        today = datetime.now(timezone.utc).date()
        return {
            "earnings": [
                {
                    "date": "2025-10-25",
                    "symbol": "TCS",
                    "epsEstimate": 7.50,
                    "epsActual": 7.85,
                    "surprise": "+4.67%",
                    "reportTime": "After Market",
                    "status": "reported"
                },
                {
                    "date": "2025-10-26",
                    "symbol": "INFY",
                    "epsEstimate": 18.50,
                    "epsActual": None,
                    "surprise": None,
                    "reportTime": "After Market",
                    "status": "upcoming"
                },
                {
                    "date": "2025-10-27",
                    "symbol": "HDFC",
                    "epsEstimate": 42.30,
                    "epsActual": None,
                    "surprise": None,
                    "reportTime": "Before Market",
                    "status": "upcoming"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Earnings calendar retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/fundamentals/{symbol}")
@limiter.limit(news_limit)
async def get_fundamentals(request: Request, symbol: str) -> Dict[str, Any]:
    """Get fundamental metrics for a stock."""
    try:
        fundamentals_data = {
            "INFY": {
                "revenue": {"current": 27500, "trend": 2.5, "vsSector": 1.2},
                "earnings": {"current": 92.50, "trend": 3.2, "vsSector": 2.1},
                "pe": {"current": 28.5, "trend": -1.2, "vsSector": 25.0},
                "roe": {"current": 16.5, "trend": 0.8, "vsSector": 14.2},
                "debt": {"current": 2.1, "trend": -0.5, "vsSector": 3.5},
                "fairValue": 3450
            },
            "TCS": {
                "revenue": {"current": 65000, "trend": 1.8, "vsSector": 0.9},
                "earnings": {"current": 155.20, "trend": 2.1, "vsSector": 1.8},
                "pe": {"current": 24.2, "trend": -0.8, "vsSector": 22.5},
                "roe": {"current": 18.2, "trend": 1.2, "vsSector": 16.5},
                "debt": {"current": 1.8, "trend": -0.3, "vsSector": 3.2},
                "fairValue": 4150
            },
            "HDFC": {
                "revenue": {"current": 45000, "trend": 3.2, "vsSector": 2.1},
                "earnings": {"current": 168.50, "trend": 4.5, "vsSector": 3.2},
                "pe": {"current": 26.8, "trend": -2.1, "vsSector": 24.0},
                "roe": {"current": 14.8, "trend": 0.6, "vsSector": 13.2},
                "debt": {"current": 2.5, "trend": 0.2, "vsSector": 4.1},
                "fairValue": 2950
            }
        }

        data = fundamentals_data.get(symbol, fundamentals_data["INFY"])
        return {
            "symbol": symbol,
            "fundamentals": data,
            "lastAnalysis": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Fundamentals retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/recommendations")
@limiter.limit(news_limit)
async def get_recommendations(request: Request) -> Dict[str, Any]:
    """Get investment recommendations."""
    try:
        return {
            "recommendations": [
                {
                    "symbol": "HDFC",
                    "action": "BUY",
                    "confidence": 92,
                    "fairValue": 2950,
                    "currentPrice": 2800,
                    "upside": "5.36%",
                    "lastUpdated": datetime.now(timezone.utc).isoformat(),
                    "status": "pending"
                },
                {
                    "symbol": "INFY",
                    "action": "BUY",
                    "confidence": 78,
                    "fairValue": 3450,
                    "currentPrice": 3200,
                    "upside": "7.81%",
                    "lastUpdated": datetime.now(timezone.utc).isoformat(),
                    "status": "pending"
                },
                {
                    "symbol": "TCS",
                    "action": "HOLD",
                    "confidence": 65,
                    "fairValue": 4100,
                    "currentPrice": 4450,
                    "upside": "-8.09%",
                    "lastUpdated": datetime.now(timezone.utc).isoformat(),
                    "status": "approved"
                },
                {
                    "symbol": "LT",
                    "action": "SELL",
                    "confidence": 85,
                    "fairValue": 1800,
                    "currentPrice": 1950,
                    "downside": "7.69%",
                    "lastUpdated": datetime.now(timezone.utc).isoformat(),
                    "status": "rejected",
                    "rejectionReason": "Conflicting with portfolio concentration"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Recommendations retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
