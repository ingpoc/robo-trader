"""
Paper Trading Evening Session API Routes

Routes for evening performance review functionality (PT-004).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, Path
from pydantic import Field, BaseModel

from src.core.di import DependencyContainer
from src.web.dependencies import get_container
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

router = APIRouter(prefix="/api/paper-trading/evening-session", tags=["evening-session"])


# Request/Response Models
class EveningSessionTriggerRequest(BaseModel):
    trigger_source: str = Field(default="MANUAL", description="Source of the trigger")
    review_date: Optional[str] = Field(None, description="Date to review in YYYY-MM-DD format")


class EveningSessionResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


class EveningSessionListResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    total: int
    message: Optional[str] = None


async def _resolve_single_account_id(container: DependencyContainer) -> str:
    """Resolve a single explicit paper-trading account for evening-session read paths."""
    account_manager = await container.get("paper_trading_account_manager")
    accounts = await account_manager.get_all_accounts()
    if not accounts:
        raise TradingError(
            "No paper trading account exists",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
        )

    if len(accounts) > 1:
        account_ids = ", ".join(account.account_id for account in accounts)
        raise TradingError(
            f"Multiple paper accounts exist; explicit account selection is required: {account_ids}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
        )

    return accounts[0].account_id


async def _fetch_current_prices(container: DependencyContainer, account_id: str) -> Dict[str, float]:
    """Fetch current prices for open positions without fabricating marks."""
    store = await container.get("paper_trading_store")
    market_data_service = await container.get("market_data_service")
    open_trades = await store.get_open_trades(account_id)
    symbols = sorted({trade.symbol for trade in open_trades})
    if not symbols:
        return {}

    market_data_map = await market_data_service.get_multiple_market_data(symbols)
    return {
        symbol: market_data.ltp
        for symbol, market_data in market_data_map.items()
        if market_data and market_data.ltp is not None
    }


@router.post("/trigger", response_model=EveningSessionResponse)
async def trigger_evening_session(
    request: EveningSessionTriggerRequest,
    container=Depends(get_container)
):
    """
    Manually trigger an evening performance review session.

    This endpoint allows manual triggering of the evening review process
    which analyzes daily trading performance and generates insights.
    """
    try:
        # Get the evening session coordinator
        coordinator = await container.get("paper_trading_evening_coordinator")

        # Validate review date format
        if request.review_date:
            try:
                datetime.strptime(request.review_date, "%Y-%m-%d")
            except ValueError:
                return EveningSessionResponse(
                    success=False,
                    error="Invalid date format. Use YYYY-MM-DD"
                )

        # Trigger the evening review
        result = await coordinator.run_evening_review(
            trigger_source=request.trigger_source,
            review_date=request.review_date
        )

        return EveningSessionResponse(
            success=True,
            data=result,
            message=f"Evening review completed for {result['review_date']}"
        )

    except TradingError as e:
        return EveningSessionResponse(
            success=False,
            error=str(e)
        )
    except Exception as e:
        return EveningSessionResponse(
            success=False,
            error=f"Failed to trigger evening session: {str(e)}"
        )


@router.get("/reviews", response_model=EveningSessionListResponse)
async def get_evening_reviews(
    limit: int = Query(default=30, ge=1, le=100, description="Maximum number of reviews to return"),
    successful_only: bool = Query(default=False, description="Only return successful reviews"),
    container=Depends(get_container)
):
    """
    Get recent evening performance reviews.

    Returns a list of historical evening performance reviews with their
    metrics, insights, and analysis results.
    """
    try:
        # Get state manager
        state_manager = await container.get("state_manager")
        paper_trading_state = state_manager.paper_trading

        # Fetch reviews
        reviews = await paper_trading_state.get_evening_performance_reviews(
            limit=limit,
            successful_only=successful_only
        )

        return EveningSessionListResponse(
            success=True,
            data=reviews,
            total=len(reviews),
            message=f"Retrieved {len(reviews)} evening reviews"
        )

    except Exception as e:
        return EveningSessionListResponse(
            success=False,
            data=[],
            total=0,
            error=f"Failed to fetch evening reviews: {str(e)}"
        )


@router.get("/reviews/{review_id}", response_model=EveningSessionResponse)
async def get_evening_review(
    review_id: str = Path(..., description="Evening review ID"),
    container=Depends(get_container)
):
    """
    Get a specific evening performance review by ID.

    Retrieves detailed information about a specific evening review
    including all metrics, insights, and analysis.
    """
    try:
        # Get state manager
        state_manager = await container.get("state_manager")
        paper_trading_state = state_manager.paper_trading

        # Get all reviews and find the specific one
        reviews = await paper_trading_state.get_evening_performance_reviews(limit=1000)

        for review in reviews:
            if review.get("review_id") == review_id:
                return EveningSessionResponse(
                    success=True,
                    data=review
                )

        return EveningSessionResponse(
            success=False,
            error=f"Evening review with ID {review_id} not found"
        )

    except Exception as e:
        return EveningSessionResponse(
            success=False,
            error=f"Failed to fetch evening review: {str(e)}"
        )


@router.get("/performance/latest", response_model=EveningSessionResponse)
async def get_latest_performance_metrics(
    container=Depends(get_container)
):
    """
    Get the latest daily performance metrics.

    Returns the most recent performance metrics including P&L,
    win rate, and trading statistics.
    """
    try:
        # Get state manager
        state_manager = await container.get("state_manager")
        paper_trading_state = state_manager.paper_trading

        # Get latest review
        reviews = await paper_trading_state.get_evening_performance_reviews(limit=1)

        if not reviews:
            # No reviews yet, calculate today's metrics
            today = datetime.now().strftime("%Y-%m-%d")
            account_id = await _resolve_single_account_id(container)
            store = await container.get("paper_trading_store")
            current_prices = await _fetch_current_prices(container, account_id)
            metrics = await store.calculate_daily_performance_metrics(
                account_id=account_id,
                review_date=today,
                current_prices=current_prices,
            )

            return EveningSessionResponse(
                success=True,
                data={
                    "review_date": today,
                    "account_id": account_id,
                    "metrics": metrics,
                    "has_review": False
                },
                message="No completed reviews yet, showing current day metrics"
            )

        # Return latest review data
        latest_review = reviews[0]

        return EveningSessionResponse(
            success=True,
            data={
                "review": latest_review,
                "has_review": True
            }
        )

    except Exception as e:
        return EveningSessionResponse(
            success=False,
            error=f"Failed to fetch latest performance: {str(e)}"
        )


@router.get("/insights/recent", response_model=EveningSessionResponse)
async def get_recent_trading_insights(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to look back"),
    container=Depends(get_container)
):
    """
    Get recent trading insights from evening reviews.

    Aggregates trading insights from the last N days of evening reviews
    to provide a consolidated view of recent learnings.
    """
    try:
        # Get state manager
        state_manager = await container.get("state_manager")
        paper_trading_state = state_manager.paper_trading

        # Get recent reviews
        reviews = await paper_trading_state.get_evening_performance_reviews(
            limit=days,
            successful_only=True
        )

        # Aggregate insights
        all_insights = []
        strategy_performance = {}
        total_pnl = 0.0
        total_trades = 0

        for review in reviews:
            # Collect insights
            review_insights = review.get("trading_insights", [])
            if isinstance(review_insights, list):
                all_insights.extend(review_insights)

            # Aggregate strategy performance
            review_strategy_perf = review.get("strategy_performance", {})
            if isinstance(review_strategy_perf, dict):
                for strategy, metrics in review_strategy_perf.items():
                    if strategy not in strategy_performance:
                        strategy_performance[strategy] = {
                            "total_pnl": 0.0,
                            "trades": 0,
                            "win_rate": 0.0
                        }

                    # Note: This is simplified aggregation
                    strategy_performance[strategy]["total_pnl"] += metrics.get("total_pnl", 0)
                    strategy_performance[strategy]["trades"] += metrics.get("trades", 0)

            # Aggregate totals
            total_pnl += review.get("daily_pnl", 0)
            total_trades += len(review.get("trades_reviewed", []))

        # Prepare response
        response_data = {
            "period_days": len(reviews),
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "average_daily_pnl": total_pnl / len(reviews) if reviews else 0,
            "insights": all_insights[:20],  # Limit insights
            "strategy_summary": strategy_performance,
            "review_dates": [r.get("review_date") for r in reviews]
        }

        return EveningSessionResponse(
            success=True,
            data=response_data,
            message=f"Aggregated insights from {len(reviews)} reviews"
        )

    except Exception as e:
        return EveningSessionResponse(
            success=False,
            error=f"Failed to fetch recent insights: {str(e)}"
        )


@router.get("/watchlist", response_model=EveningSessionResponse)
async def get_next_day_watchlist(
    container=Depends(get_container)
):
    """
    Get the next day's watchlist from the latest evening review.

    Returns the watchlist prepared during the most recent evening
    review session for the next trading day.
    """
    try:
        # Get state manager
        state_manager = await container.get("state_manager")
        paper_trading_state = state_manager.paper_trading

        # Get latest review
        reviews = await paper_trading_state.get_evening_performance_reviews(limit=1)

        if not reviews:
            return EveningSessionResponse(
                success=True,
                data={"watchlist": []},
                message="No evening reviews found"
            )

        latest_review = reviews[0]
        watchlist = latest_review.get("next_day_watchlist", [])

        return EveningSessionResponse(
            success=True,
            data={
                "watchlist": watchlist,
                "review_date": latest_review.get("review_date"),
                "generated_at": latest_review.get("created_at")
            }
        )

    except Exception as e:
        return EveningSessionResponse(
            success=False,
            error=f"Failed to fetch watchlist: {str(e)}"
        )


@router.get("/status", response_model=EveningSessionResponse)
async def get_evening_session_status(
    container=Depends(get_container)
):
    """
    Get the status of evening session coordinator.

    Returns information about currently running sessions and
    coordinator health status.
    """
    try:
        # Get coordinator
        coordinator = await container.get("paper_trading_evening_coordinator")

        # Get running sessions
        running_sessions = await coordinator.get_running_sessions()

        # Get automation config
        state_manager = await container.get("state_manager")
        automation_config = await state_manager.paper_trading.get_automation_config()

        return EveningSessionResponse(
            success=True,
            data={
                "coordinator_status": "active",
                "running_sessions": running_sessions,
                "automation_enabled": automation_config.get("evening_review_enabled", False),
                "scheduled_time": automation_config.get("evening_review_time", "16:00"),
                "last_review": None  # Could be populated from latest review
            }
        )

    except Exception as e:
        return EveningSessionResponse(
            success=False,
            error=f"Failed to get session status: {str(e)}"
        )
