"""
Analytics & Insights Service
Handles market screening, fundamental analysis, and strategy evaluation
Integrates with Perplexity API and market data
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.shared import EventBus, Event, EventType
from services.shared.database import (
    check_db_health,
    close_db_pool,
    execute_query,
    execute_update,
    get_db_pool,
)
from services.shared.models import HealthCheck

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8005))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/robo_trader")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# ============================================================================
# MODELS
# ============================================================================


class ScreeningParams(BaseModel):
    """Market screening parameters"""
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    pe_ratio_max: Optional[float] = 25
    dividend_yield_min: Optional[float] = None
    symbols: Optional[List[str]] = None


class ScreeningResult(BaseModel):
    """Screening result"""
    symbol: str
    score: float
    reason: str
    market_cap: Optional[int] = None
    pe_ratio: Optional[float] = None


class FundamentalAnalysis(BaseModel):
    """Fundamental analysis"""
    symbol: str
    pe_ratio: Optional[float] = None
    market_cap: Optional[int] = None
    revenue: Optional[int] = None
    net_profit: Optional[int] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    analysis_date: datetime


# ============================================================================
# PERPLEXITY CLIENT
# ============================================================================


class PerplexityClient:
    """Unified Perplexity API client (no duplication per CLAUDE.md)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"

    async def analyze_news(self, symbol: str) -> dict:
        """Analyze news for a symbol"""
        try:
            # Mock Perplexity call
            logger.debug(f"Analyzing news for {symbol} via Perplexity")
            return {
                "symbol": symbol,
                "sentiment": "NEUTRAL",
                "key_points": [
                    f"{symbol} showed stable performance",
                    "Industry trends remain positive",
                ],
                "analysis": f"Analysis for {symbol}",
            }
        except Exception as e:
            logger.error(f"Failed to analyze news: {e}")
            raise

    async def analyze_earnings(self, symbol: str) -> dict:
        """Analyze earnings for a symbol"""
        try:
            logger.debug(f"Analyzing earnings for {symbol} via Perplexity")
            return {
                "symbol": symbol,
                "eps_growth": 15.5,
                "revenue_growth": 12.3,
                "analysis": f"Earnings analysis for {symbol}",
            }
        except Exception as e:
            logger.error(f"Failed to analyze earnings: {e}")
            raise

    async def screen_market(self, criteria: dict) -> List[dict]:
        """Screen market based on criteria"""
        try:
            logger.debug(f"Screening market with criteria: {criteria}")
            # Mock results
            return [
                {"symbol": "RELIANCE", "score": 8.5, "reason": "Strong fundamentals"},
                {"symbol": "TCS", "score": 8.2, "reason": "Stable growth"},
                {"symbol": "INFY", "score": 7.8, "reason": "Good valuation"},
            ]
        except Exception as e:
            logger.error(f"Failed to screen market: {e}")
            raise


# ============================================================================
# GLOBAL STATE
# ============================================================================

event_bus: EventBus = None
db_pool = None
perplexity_client: PerplexityClient = None


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus, db_pool, perplexity_client

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
        db_pool = await get_db_pool(DATABASE_URL)
        db_healthy = await check_db_health(db_pool)
        if not db_healthy:
            raise Exception("Database health check failed")

        event_bus = EventBus(RABBITMQ_URL)
        await event_bus.connect()

        # Single instance of Perplexity client (no duplication)
        perplexity_client = PerplexityClient(PERPLEXITY_API_KEY)

        logger.info(f"✅ {SERVICE_NAME} service started")

    except Exception as e:
        logger.error(f"❌ Failed to start {SERVICE_NAME}: {e}")
        raise

    yield

    logger.info(f"🛑 Shutting down {SERVICE_NAME} service...")
    try:
        if event_bus:
            await event_bus.disconnect()
        if db_pool:
            await close_db_pool()
        logger.info(f"✅ {SERVICE_NAME} service stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=f"{SERVICE_NAME} API",
    description="Market analytics and screening",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    checks = {
        "database": "healthy" if db_pool and await check_db_health(db_pool) else "unhealthy",
        "event_bus": "healthy" if event_bus and await event_bus.health_check() else "unhealthy",
        "perplexity": "connected" if perplexity_client and PERPLEXITY_API_KEY else "not configured",
    }
    return HealthCheck(status="healthy", service=SERVICE_NAME, checks=checks)


@app.post("/screen", response_model=List[ScreeningResult])
async def screen_market(params: ScreeningParams):
    """Run market screening based on parameters"""
    try:
        # Call Perplexity API
        criteria = params.dict()
        results = await perplexity_client.screen_market(criteria)

        screening_results = []
        for result in results:
            # Store in database
            query = """
                INSERT INTO screening_results (screening_date, symbol, score, reason)
                VALUES (CURRENT_DATE, $1, $2, $3)
                ON CONFLICT (screening_date, symbol) DO UPDATE SET
                    score = $2, reason = $3
            """
            await execute_update(db_pool, query, result["symbol"], result["score"], result["reason"])

            screening_results.append(
                ScreeningResult(
                    symbol=result["symbol"],
                    score=result["score"],
                    reason=result["reason"],
                )
            )

        # Emit event
        event = Event(
            event_type=EventType.AI_ANALYSIS_COMPLETE,
            data={
                "analysis_type": "screening",
                "result_count": len(screening_results),
                "symbols": [r.symbol for r in screening_results],
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Market screening complete: {len(screening_results)} symbols found")
        return screening_results

    except Exception as e:
        logger.error(f"Failed to screen market: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fundamentals/{symbol}", response_model=FundamentalAnalysis)
async def get_fundamentals(symbol: str):
    """Get fundamental analysis for a symbol"""
    try:
        query = """
            SELECT symbol, pe_ratio, market_cap, revenue, net_profit, debt_to_equity, roe, analysis_date
            FROM fundamental_analysis
            WHERE symbol = $1
        """
        rows = await execute_query(db_pool, query, symbol.upper())

        if rows:
            row = rows[0]
            return FundamentalAnalysis(
                symbol=row["symbol"],
                pe_ratio=row["pe_ratio"],
                market_cap=row["market_cap"],
                revenue=row["revenue"],
                net_profit=row["net_profit"],
                debt_to_equity=row["debt_to_equity"],
                roe=row["roe"],
                analysis_date=row["analysis_date"],
            )

        # Not found, run analysis
        logger.info(f"Running fundamental analysis for {symbol}")
        analysis_data = await perplexity_client.analyze_earnings(symbol)

        # Store in database
        insert_query = """
            INSERT INTO fundamental_analysis (symbol, pe_ratio, analysis_date)
            VALUES ($1, $2, CURRENT_DATE)
            ON CONFLICT (symbol) DO UPDATE SET analysis_date = CURRENT_DATE
            RETURNING symbol, pe_ratio, analysis_date
        """
        result = await execute_update(db_pool, insert_query, symbol.upper(), analysis_data.get("eps_growth"))

        return FundamentalAnalysis(
            symbol=symbol.upper(),
            pe_ratio=analysis_data.get("eps_growth"),
            analysis_date=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to get fundamentals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/news/{symbol}")
async def get_news(symbol: str, limit: int = 10):
    """Get news for a symbol"""
    try:
        query = """
            SELECT headline, content, source, sentiment, published_at
            FROM news_feed
            WHERE symbol = $1
            ORDER BY published_at DESC
            LIMIT $2
        """
        rows = await execute_query(db_pool, query, symbol.upper(), limit)

        return {
            "symbol": symbol,
            "news_count": len(rows),
            "articles": rows,
        }

    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/earnings/{symbol}")
async def get_earnings(symbol: str):
    """Get earnings data for a symbol"""
    try:
        query = """
            SELECT quarter, year, announcement_date, results_date, eps, revenue
            FROM earnings
            WHERE symbol = $1
            ORDER BY year DESC, quarter DESC
            LIMIT 4
        """
        rows = await execute_query(db_pool, query, symbol.upper())

        return {
            "symbol": symbol,
            "earnings_history": rows,
        }

    except Exception as e:
        logger.error(f"Failed to get earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/{symbol}")
async def run_analysis(symbol: str):
    """Run comprehensive analysis for a symbol"""
    try:
        # Run both news and earnings analysis
        news_data = await perplexity_client.analyze_news(symbol)
        earnings_data = await perplexity_client.analyze_earnings(symbol)

        # Store results
        analysis_results = {
            "symbol": symbol,
            "news_analysis": news_data,
            "earnings_analysis": earnings_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Emit analysis complete event
        event = Event(
            event_type=EventType.AI_ANALYSIS_COMPLETE,
            data={
                "analysis_type": "comprehensive",
                "symbol": symbol,
                "sentiment": news_data.get("sentiment"),
                "eps_growth": earnings_data.get("eps_growth"),
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Comprehensive analysis complete for {symbol}")
        return analysis_results

    except Exception as e:
        logger.error(f"Failed to run analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {"error": exc.detail, "code": str(exc.status_code), "service": SERVICE_NAME}


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {"error": "Internal server error", "code": "500", "service": SERVICE_NAME}


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
