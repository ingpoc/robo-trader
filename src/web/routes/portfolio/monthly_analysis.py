"""API routes for monthly portfolio analysis."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from loguru import logger

# Import dependencies with error handling
try:
    from src.web.dependencies import get_di_container
except ImportError:
    # Fallback for testing
    def get_di_container():
        return None

try:
    from src.core.di import DIContainer
except ImportError:
    # Fallback for testing
    DIContainer = type

from src.core.errors import TradingError


router = APIRouter(prefix="/api/portfolio/monthly-analysis", tags=["monthly-analysis"])


# Request/Response Models
class AnalysisRequest(BaseModel):
    """Request to trigger monthly analysis."""
    analysis_date: Optional[str] = Field(None, description="Analysis date in YYYY-MM-DD format")
    force: bool = Field(False, description="Force analysis even if already done for the month")


class AnalysisResponse(BaseModel):
    """Response for monthly analysis."""
    status: str
    analysis_id: Optional[str] = None
    month: Optional[str] = None
    message: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None


class AnalysisRecord(BaseModel):
    """Single analysis record."""
    id: int
    analysis_date: str
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    recommendation: str
    reasoning: str
    confidence_score: float
    price_at_analysis: Optional[float] = None
    next_review_date: Optional[str] = None
    created_at: str


class MonthlySummary(BaseModel):
    """Monthly analysis summary."""
    id: int
    analysis_month: str
    total_stocks_analyzed: int
    keep_recommendations: int
    sell_recommendations: int
    portfolio_value_at_analysis: Optional[float] = None
    analysis_duration_seconds: Optional[float] = None
    perplexity_api_calls: int = 0
    claude_analysis_tokens: int = 0
    created_at: str


@router.post("/trigger", response_model=AnalysisResponse)
async def trigger_monthly_analysis(
    request: AnalysisRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Trigger monthly portfolio analysis.

    Analyzes all stocks in the user's real portfolio and provides KEEP/SELL recommendations.
    """
    try:
        # Get coordinator
        coordinator = await container.get("monthly_portfolio_analysis_coordinator")
        if not coordinator:
            raise HTTPException(status_code=503, detail="Monthly analysis coordinator not available")

        # Trigger analysis
        result = await coordinator.trigger_monthly_analysis(
            analysis_date=request.analysis_date,
            force=request.force
        )

        return AnalysisResponse(**result)

    except TradingError as e:
        logger.error(f"Trading error in monthly analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in monthly analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history", response_model=List[AnalysisRecord])
async def get_analysis_history(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
    container: DIContainer = Depends(get_di_container)
):
    """
    Get portfolio analysis history.

    Returns analysis records for all stocks or a specific symbol.
    """
    try:
        # Get coordinator
        coordinator = await container.get("monthly_portfolio_analysis_coordinator")
        if not coordinator:
            raise HTTPException(status_code=503, detail="Monthly analysis coordinator not available")

        # Get analysis history
        analyses = await coordinator.get_analysis_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return [AnalysisRecord(**analysis) for analysis in analyses]

    except Exception as e:
        logger.error(f"Error fetching analysis history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis history")


@router.get("/history/{symbol}", response_model=List[AnalysisRecord])
async def get_symbol_analysis_history(
    symbol: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    container: DIContainer = Depends(get_di_container)
):
    """
    Get analysis history for a specific symbol.

    Returns all historical analyses for the given stock symbol.
    """
    try:
        # Get coordinator
        coordinator = await container.get("monthly_portfolio_analysis_coordinator")
        if not coordinator:
            raise HTTPException(status_code=503, detail="Monthly analysis coordinator not available")

        # Get analysis history for symbol
        analyses = await coordinator.get_analysis_history(symbol=symbol, limit=limit)

        return [AnalysisRecord(**analysis) for analysis in analyses]

    except Exception as e:
        logger.error(f"Error fetching analysis history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch analysis history for {symbol}")


@router.get("/summaries", response_model=List[MonthlySummary])
async def get_monthly_summaries(
    months: int = Query(12, ge=1, le=60, description="Number of months to fetch"),
    container: DIContainer = Depends(get_di_container)
):
    """
    Get monthly analysis summaries.

    Returns summary statistics for each month's analysis.
    """
    try:
        # Get coordinator
        coordinator = await container.get("monthly_portfolio_analysis_coordinator")
        if not coordinator:
            raise HTTPException(status_code=503, detail="Monthly analysis coordinator not available")

        # Get monthly summaries
        summaries = await coordinator.get_monthly_summaries(months=months)

        return [MonthlySummary(**summary) for summary in summaries]

    except Exception as e:
        logger.error(f"Error fetching monthly summaries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch monthly summaries")


@router.get("/statistics")
async def get_analysis_statistics(
    months: int = Query(12, ge=1, le=60, description="Number of months for statistics"),
    container: DIContainer = Depends(get_di_container)
):
    """
    Get analysis statistics.

    Returns aggregate statistics for portfolio analysis over time.
    """
    try:
        # Get coordinator
        coordinator = await container.get("monthly_portfolio_analysis_coordinator")
        if not coordinator:
            raise HTTPException(status_code=503, detail="Monthly analysis coordinator not available")

        # Get statistics
        stats = await coordinator.get_analysis_statistics(months=months)

        return {
            "status": "success",
            "statistics": stats,
            "period_months": months
        }

    except Exception as e:
        logger.error(f"Error fetching analysis statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis statistics")


@router.get("/latest/{symbol}")
async def get_latest_analysis(
    symbol: str,
    container: DIContainer = Depends(get_di_container)
):
    """
    Get the latest analysis for a symbol.

    Returns the most recent KEEP/SELL recommendation for the stock.
    """
    try:
        # Get portfolio analysis state
        portfolio_analysis_state = await container.get("portfolio_monthly_analysis_state")
        if not portfolio_analysis_state:
            raise HTTPException(status_code=503, detail="Portfolio analysis state not available")

        # Get latest analysis
        analysis = await portfolio_analysis_state.get_latest_analysis_for_symbol(symbol)

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis found for symbol {symbol}"
            )

        return {
            "status": "success",
            "analysis": AnalysisRecord(**analysis)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest analysis for {symbol}")


@router.get("/recommendations")
async def get_current_recommendations(
    container: DIContainer = Depends(get_di_container)
):
    """
    Get current portfolio recommendations.

    Returns the latest KEEP/SELL recommendation for each stock in the portfolio.
    """
    try:
        # Get coordinator
        coordinator = await container.get("monthly_portfolio_analysis_coordinator")
        if not coordinator:
            raise HTTPException(status_code=503, detail="Monthly analysis coordinator not available")

        # Get all analyses
        analyses = await coordinator.get_analysis_history(limit=1000)

        # Group by symbol and get latest
        latest_by_symbol = {}
        for analysis in analyses:
            symbol = analysis["symbol"]
            if symbol not in latest_by_symbol or analysis["analysis_date"] > latest_by_symbol[symbol]["analysis_date"]:
                latest_by_symbol[symbol] = analysis

        # Format response
        recommendations = []
        for symbol, analysis in latest_by_symbol.items():
            recommendations.append({
                "symbol": symbol,
                "company_name": analysis.get("company_name"),
                "recommendation": analysis["recommendation"],
                "confidence_score": analysis["confidence_score"],
                "reasoning": analysis["reasoning"][:200] + "..." if len(analysis["reasoning"]) > 200 else analysis["reasoning"],
                "analysis_date": analysis["analysis_date"],
                "price_at_analysis": analysis.get("price_at_analysis")
            })

        # Sort by recommendation and confidence
        recommendations.sort(key=lambda x: (x["recommendation"], -x["confidence_score"]))

        return {
            "status": "success",
            "total_stocks": len(recommendations),
            "keep_recommendations": len([r for r in recommendations if r["recommendation"] == "KEEP"]),
            "sell_recommendations": len([r for r in recommendations if r["recommendation"] == "SELL"]),
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"Error fetching current recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch current recommendations")