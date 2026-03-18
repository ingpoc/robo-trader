"""API routes for morning trading session management."""

from datetime import datetime, time
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from src.core.di import DependencyContainer as DIContainer
from src.web.dependencies import get_container


router = APIRouter(prefix="/api/paper-trading/morning-session", tags=["morning-session"])


class SessionRequest(BaseModel):
    """Request to trigger morning session manually."""
    trigger_source: Optional[str] = "manual"
    force_run: Optional[bool] = False


class SessionResponse(BaseModel):
    """Response for morning session operations."""
    success: bool
    message: str
    session_id: Optional[str] = None
    session_summary: Optional[Dict[str, Any]] = None


class SessionHistoryResponse(BaseModel):
    """Response for session history."""
    sessions: List[Dict[str, Any]]
    total_count: int
    successful_sessions: int
    success_rate: float


@router.post("/trigger", response_model=SessionResponse)
async def trigger_morning_session(
    request: SessionRequest,
    container: DIContainer = Depends(get_container)
) -> SessionResponse:
    """
    Manually trigger a morning trading session.

    This endpoint allows manual triggering of the morning autonomous trading session
    for testing purposes. The session will run the complete workflow:
    1. Scan pre-market data
    2. Research selected stocks
    3. Generate trade ideas
    4. Apply safeguards
    5. Execute approved trades
    """
    try:
        # Get morning session coordinator
        coordinator = await container.get("morning_session_coordinator")

        # Check if session is already active
        if hasattr(coordinator, '_session_active') and coordinator._session_active:
            if not request.force_run:
                return SessionResponse(
                    success=False,
                    message="Morning session already in progress. Use force_run=true to override."
                )

        # Run morning session
        result = await coordinator.run_morning_session(trigger=request.trigger_source)

        # Prepare response
        session_summary = {
            "session_id": result.session_id,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "duration_seconds": (result.end_time - result.start_time).total_seconds(),
            "pre_market_scanned": result.pre_market_scanned,
            "stocks_researched": result.stocks_researched,
            "trade_ideas_generated": result.trade_ideas_generated,
            "trades_executed": result.trades_executed,
            "total_amount_invested": result.total_amount_invested,
            "decisions_logged": result.decisions_logged,
            "success": result.success,
            "error_message": result.error_message
        }

        return SessionResponse(
            success=result.success,
            message=f"Morning session {'completed successfully' if result.success else 'completed with errors'}",
            session_id=result.session_id,
            session_summary=session_summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger morning session: {str(e)}")


@router.get("/history", response_model=SessionHistoryResponse)
async def get_session_history(
    limit: int = Query(default=30, ge=1, le=100),
    successful_only: bool = Query(default=False),
    container: DIContainer = Depends(get_container)
) -> SessionHistoryResponse:
    """
    Get history of morning trading sessions.

    Returns a list of past morning sessions with their metrics and results.
    """
    try:
        # Get paper trading state manager
        paper_trading_state = await container.get("paper_trading_state")

        # Get session history
        sessions = await paper_trading_state.get_morning_sessions(
            limit=limit,
            successful_only=successful_only
        )

        # Calculate statistics
        successful_sessions = sum(1 for s in sessions if s.get("success", False))
        success_rate = (successful_sessions / len(sessions) * 100) if sessions else 0

        return SessionHistoryResponse(
            sessions=sessions,
            total_count=len(sessions),
            successful_sessions=successful_sessions,
            success_rate=round(success_rate, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session history: {str(e)}")


@router.get("/status")
async def get_session_status(
    container: DIContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Get current morning session status.

    Returns whether a session is currently running and the next scheduled time.
    """
    try:
        # Get morning session coordinator
        coordinator = await container.get("morning_session_coordinator")

        # Get automation config
        paper_trading_state = await container.get("paper_trading_state")
        config = await paper_trading_state.get_automation_config()

        # Check if session is active
        is_active = hasattr(coordinator, '_session_active') and coordinator._session_active

        # Calculate next session time
        now = datetime.now()
        session_time = time.fromisoformat(config.get("morning_session_time", "09:00"))
        next_session = datetime.combine(now.date(), session_time)

        # If next session time has passed, schedule for tomorrow
        if next_session <= now:
            from datetime import timedelta
            next_session += timedelta(days=1)

        return {
            "session_active": is_active,
            "next_scheduled_session": next_session.isoformat(),
            "session_enabled": config.get("morning_session_enabled", False),
            "session_time": config.get("morning_session_time", "09:00"),
            "auto_trade_enabled": config.get("auto_trade_enabled", False),
            "current_time": now.isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session_details(
    session_id: str,
    container: DIContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Get details of a specific morning session.

    Returns complete details of a specific morning session including
    trade ideas, executed trades, and decisions made.
    """
    try:
        # Get paper trading state manager
        paper_trading_state = await container.get("paper_trading_state")

        # Get all sessions and find the one with matching ID
        sessions = await paper_trading_state.get_morning_sessions(limit=1000)
        session = next((s for s in sessions if s["session_id"] == session_id), None)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Add calculated fields
        if session.get("start_time") and session.get("end_time"):
            start = datetime.fromisoformat(session["start_time"])
            end = datetime.fromisoformat(session["end_time"])
            session["duration_seconds"] = (end - start).total_seconds()
            session["duration_minutes"] = round(session["duration_seconds"] / 60, 2)

        # Add success rate if metrics exist
        metrics = session.get("metrics", {})
        if metrics:
            total_ideas = metrics.get("trade_ideas_generated", 0)
            executed = metrics.get("trades_executed", 0)
            session["execution_rate"] = round((executed / total_ideas * 100), 2) if total_ideas > 0 else 0

        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session details: {str(e)}")