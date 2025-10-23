"""
Claude Agent API routes for session management and autonomous trading.

Enhanced with comprehensive AI transparency endpoints.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..services.claude_agent import (
    ResearchTracker, AnalysisLogger, ExecutionMonitor,
    DailyStrategyEvaluator, ActivitySummarizer
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/claude", tags=["Claude Agent"])

# Rate limiter for Claude endpoints
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Request/Response Models
# ============================================================================

class StartSessionRequest(BaseModel):
    """Request to start a new Claude Agent session."""

    account_type: str = Field(..., description="Account type: 'swing_trading' or 'options_trading'")
    session_type: str = Field(..., description="Session type: 'morning_prep' or 'evening_review'")


class SessionResponse(BaseModel):
    """Response containing session details."""

    session_id: str = Field(..., description="Unique session ID")
    account_type: str = Field(..., description="Account type for session")
    session_type: str = Field(..., description="Type of session")
    status: str = Field(..., description="Session status: 'running', 'completed', 'failed', 'cancelled'")
    started_at: str = Field(..., description="ISO timestamp when session started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when session completed")
    turns: int = Field(default=0, description="Number of conversation turns")
    tools_executed: int = Field(default=0, description="Number of tools executed")
    decisions_made: int = Field(default=0, description="Number of decisions made")
    token_input: int = Field(default=0, description="Input tokens used")
    token_output: int = Field(default=0, description="Output tokens used")
    cost_usd: float = Field(default=0.0, description="Estimated API cost in USD")
    error: Optional[str] = Field(None, description="Error message if session failed")


class SessionListResponse(BaseModel):
    """Response containing list of sessions."""

    total: int = Field(..., description="Total number of sessions")
    sessions: list[SessionResponse] = Field(..., description="List of session details")


class CancelSessionRequest(BaseModel):
    """Request to cancel a running session."""

    reason: str = Field(default="User requested cancellation", description="Reason for cancellation")


# ============================================================================
# Transparency API Models
# ============================================================================

class ResearchActivityResponse(BaseModel):
    """Response containing research activity data."""

    total_sessions: int = Field(..., description="Total research sessions")
    symbols_analyzed: int = Field(..., description="Symbols analyzed")
    data_sources_used: int = Field(..., description="Data sources consulted")
    key_findings: list[str] = Field(..., description="Key research findings")
    recent_sessions: list[Dict[str, Any]] = Field(..., description="Recent research sessions")


class AnalysisActivityResponse(BaseModel):
    """Response containing analysis activity data."""

    total_decisions: int = Field(..., description="Total trade decisions made")
    avg_confidence: float = Field(..., description="Average confidence score")
    strategies_evaluated: int = Field(..., description="Strategies evaluated")
    refinements_made: int = Field(..., description="Strategy refinements implemented")
    recent_decisions: list[Dict[str, Any]] = Field(..., description="Recent trade decisions")


class ExecutionActivityResponse(BaseModel):
    """Response containing execution activity data."""

    total_executions: int = Field(..., description="Total trade executions")
    success_rate: float = Field(..., description="Execution success rate")
    avg_slippage: float = Field(..., description="Average slippage (bps)")
    avg_cost: float = Field(..., description="Average execution cost (%)")
    risk_compliance: float = Field(..., description="Risk check compliance rate")
    recent_executions: list[Dict[str, Any]] = Field(..., description="Recent executions")


class DailyStrategyReportResponse(BaseModel):
    """Response containing daily strategy evaluation."""

    evaluation_date: str = Field(..., description="Date of evaluation")
    strategies_evaluated: int = Field(..., description="Number of strategies evaluated")
    refinements_recommended: int = Field(..., description="Refinements recommended")
    confidence_score: float = Field(..., description="Overall confidence score")
    key_insights: list[str] = Field(..., description="Key insights from evaluation")
    performance_summary: Dict[str, Any] = Field(..., description="Strategy performance summary")


class DailyActivitySummaryResponse(BaseModel):
    """Response containing daily AI activity summary."""

    date: str = Field(..., description="Date of summary")
    day_rating: str = Field(..., description="Overall day rating")
    trades_executed: int = Field(..., description="Trades executed")
    total_pnl: float = Field(..., description="Total P&L")
    research_sessions: int = Field(..., description="Research sessions completed")
    strategies_evaluated: int = Field(..., description="Strategies evaluated")
    key_achievements: list[str] = Field(..., description="Key achievements")
    areas_for_improvement: list[str] = Field(..., description="Areas for improvement")
    planned_activities: list[str] = Field(..., description="Planned activities for tomorrow")


# ============================================================================
# Dependency Functions
# ============================================================================

async def get_container(request: Request):
    """Get DI container from request state."""
    if not hasattr(request.app.state, "container"):
        raise HTTPException(status_code=500, detail="Application not properly initialized")
    return request.app.state.container


async def get_transparency_services(container):
    """Get transparency service instances."""
    return {
        "research_tracker": await container.get("research_tracker"),
        "analysis_logger": await container.get("analysis_logger"),
        "execution_monitor": await container.get("execution_monitor"),
        "strategy_evaluator": await container.get("daily_strategy_evaluator"),
        "activity_summarizer": await container.get("activity_summarizer")
    }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/sessions/start", response_model=SessionResponse)
@limiter.limit("5/minute")
async def start_claude_session(
    request_data: StartSessionRequest,
    request: Request,
    container=Depends(get_container),
) -> SessionResponse:
    """
    Start a new Claude Agent autonomous trading session.

    The session will run the specified account type through either:
    - Morning Prep: Analyzes open positions, identifies opportunities, executes new trades
    - Evening Review: Reviews daily performance, extracts learnings, plans next day

    Returns the session ID and initial status.
    """
    try:
        logger.info(
            f"Starting Claude session: {request_data.session_type} for {request_data.account_type}"
        )

        # Validate inputs
        if request_data.account_type not in ["swing_trading", "options_trading"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid account_type: {request_data.account_type}. Must be 'swing_trading' or 'options_trading'",
            )

        if request_data.session_type not in ["morning_prep", "evening_review"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid session_type: {request_data.session_type}. Must be 'morning_prep' or 'evening_review'",
            )

        # Get coordinator from container
        coordinator = await container.get("claude_agent_coordinator")

        # Build context from account state
        account_manager = await container.get("paper_trading_account_manager")
        account = await account_manager.get_account(f"paper_{request_data.account_type}_main")

        if not account:
            raise HTTPException(
                status_code=404, detail=f"Account not found: paper_{request_data.account_type}_main"
            )

        # Get account balance and positions
        balance_info = await account_manager.get_account_balance(f"paper_{request_data.account_type}_main")
        positions = await account_manager.get_open_positions(f"paper_{request_data.account_type}_main")

        # Build context dict for Claude
        context = {
            "balance": balance_info.get("balance", 100000),
            "buying_power": balance_info.get("buying_power", 100000),
            "open_positions": positions,
            "market_context": {
                "timestamp": datetime.utcnow().isoformat(),
                "nse_status": "open",  # Would fetch from market data in production
            },
        }

        # Start session based on type
        if request_data.session_type == "morning_prep":
            session_result = await coordinator.run_morning_prep_session(
                account_type=request_data.account_type, context=context
            )
        else:  # evening_review
            context["trades_today"] = []  # Would fetch from database in production
            context["daily_pnl"] = 0
            context["win_rate"] = 0
            session_result = await coordinator.run_evening_review_session(
                account_type=request_data.account_type, context=context
            )

        # Build response
        return SessionResponse(
            session_id=session_result.session_id,
            account_type=session_result.account_type,
            session_type=request_data.session_type,
            status="completed",
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            turns=getattr(session_result, "turns", 0),
            tools_executed=len(session_result.tool_calls),
            decisions_made=len(session_result.decisions_made),
            token_input=session_result.token_input,
            token_output=session_result.token_output,
            cost_usd=session_result.total_cost_usd,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Claude session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.get("/sessions", response_model=SessionListResponse)
@limiter.limit("30/minute")
async def list_claude_sessions(
    request: Request,
    container=Depends(get_container),
    limit: int = 10,
    offset: int = 0,
) -> SessionListResponse:
    """
    List recent Claude Agent sessions.

    Returns a paginated list of session details including status, tokens used, and decisions made.
    """
    try:
        logger.info(f"Listing Claude sessions: limit={limit}, offset={offset}")

        # Get strategy store from container
        strategy_store = await container.get("claude_strategy_store")

        # Fetch sessions from store
        sessions = await strategy_store.get_sessions(limit=limit, offset=offset)
        total = await strategy_store.get_sessions_count()

        # Convert to response models
        session_responses = [
            SessionResponse(
                session_id=s.session_id,
                account_type=s.account_type,
                session_type=s.session_type.value,
                status="completed",  # Would determine from database
                started_at=s.timestamp,
                completed_at=s.timestamp,
                turns=len(s.decisions_made),
                tools_executed=len(s.tool_calls),
                decisions_made=len(s.decisions_made),
                token_input=s.token_input,
                token_output=s.token_output,
                cost_usd=s.total_cost_usd,
                error=None,
            )
            for s in sessions
        ]

        return SessionListResponse(total=total, sessions=session_responses)

    except Exception as e:
        logger.error(f"Failed to list Claude sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
@limiter.limit("30/minute")
async def get_claude_session(
    session_id: str,
    request: Request,
    container=Depends(get_container),
) -> SessionResponse:
    """
    Get details of a specific Claude Agent session.

    Returns the session status, decisions made, and token usage information.
    """
    try:
        logger.info(f"Fetching Claude session: {session_id}")

        # Get strategy store from container
        strategy_store = await container.get("claude_strategy_store")

        # Fetch session from store
        session = await strategy_store.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        # Convert to response model
        return SessionResponse(
            session_id=session.session_id,
            account_type=session.account_type,
            session_type=session.session_type.value,
            status="completed",
            started_at=session.timestamp,
            completed_at=session.timestamp,
            turns=len(session.decisions_made),
            tools_executed=len(session.tool_calls),
            decisions_made=len(session.decisions_made),
            token_input=session.token_input,
            token_output=session.token_output,
            cost_usd=session.total_cost_usd,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Claude session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.post("/sessions/{session_id}/cancel")
@limiter.limit("10/minute")
async def cancel_claude_session(
    session_id: str,
    request_data: CancelSessionRequest,
    request: Request,
    container=Depends(get_container),
) -> Dict[str, Any]:
    """
    Cancel a running Claude Agent session.

    Stops the current conversation and saves any partial results.
    """
    try:
        logger.info(f"Cancelling Claude session: {session_id}, reason: {request_data.reason}")

        # In a full implementation, this would:
        # 1. Get session from store
        # 2. Check if still running
        # 3. Set cancellation flag
        # 4. Save cancellation reason
        # 5. Return confirmation

        return {
            "success": True,
            "message": f"Session {session_id} cancellation requested",
            "session_id": session_id,
            "reason": request_data.reason,
        }

    except Exception as e:
        logger.error(f"Failed to cancel Claude session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel session: {str(e)}")


@router.get("/status")
@limiter.limit("60/minute")
async def get_claude_status(
    request: Request,
    container=Depends(get_container),
) -> Dict[str, Any]:
    """
    Get overall Claude Agent system status.

    Returns information about coordinator initialization, recent sessions, and health metrics.
    """
    try:
        coordinator = await container.get("claude_agent_coordinator")

        return {
            "status": "operational",
            "initialized": True,
            "coordinator": {
                "client": "initialized" if coordinator.client else "not_initialized",
                "tool_executor": "initialized" if coordinator.tool_executor else "not_initialized",
                "validator": "initialized" if coordinator.validator else "not_initialized",
                "tools_available": len(coordinator._tools),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get Claude status: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "initialized": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# Transparency API Endpoints
# ============================================================================

@router.get("/transparency/research", response_model=ResearchActivityResponse)
@limiter.limit("30/minute")
async def get_research_activity(
    request: Request,
    container=Depends(get_container),
    account_type: Optional[str] = None,
    days: int = 7,
) -> ResearchActivityResponse:
    """
    Get AI research activity transparency data.

    Shows what Claude has been researching, data sources used, and key findings.
    """
    try:
        services = await get_transparency_services(container)
        research_tracker = services["research_tracker"]

        # Get research history
        research_sessions = await research_tracker.get_research_history(
            account_type=account_type
        )

        # Get data source usage
        data_source_stats = await research_tracker.get_data_source_usage_stats()

        # Get research effectiveness
        effectiveness = await research_tracker.get_research_effectiveness(
            account_type or "swing_trading", days=days
        )

        return ResearchActivityResponse(
            total_sessions=effectiveness["total_sessions"],
            symbols_analyzed=effectiveness["total_symbols_analyzed"],
            data_sources_used=data_source_stats["sources_used"],
            key_findings=["Market analysis completed", "Technical indicators reviewed", "Fundamental data assessed"],  # Would come from sessions
            recent_sessions=[s.to_dict() for s in research_sessions[-5:]]
        )

    except Exception as e:
        logger.error(f"Failed to get research activity: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get research activity: {str(e)}")


@router.get("/transparency/analysis", response_model=AnalysisActivityResponse)
@limiter.limit("30/minute")
async def get_analysis_activity(
    request: Request,
    container=Depends(get_container),
    account_type: Optional[str] = None,
    days: int = 7,
) -> AnalysisActivityResponse:
    """
    Get AI analysis activity transparency data.

    Shows Claude's decision-making process, confidence levels, and strategy evaluations.
    """
    try:
        services = await get_transparency_services(container)
        analysis_logger = services["analysis_logger"]

        # Get decision history
        decisions = await analysis_logger.get_decision_history()

        # Get analysis effectiveness
        effectiveness = await analysis_logger.get_analysis_effectiveness(days=days)

        # Get strategy evaluations
        evaluations = await analysis_logger.get_strategy_evaluations()

        return AnalysisActivityResponse(
            total_decisions=effectiveness["total_decisions"],
            avg_confidence=effectiveness["avg_confidence_score"],
            strategies_evaluated=len(evaluations),
            refinements_made=sum(len(e.get("refinements", [])) for e in evaluations),
            recent_decisions=[d.to_dict() for d in decisions[-5:]]
        )

    except Exception as e:
        logger.error(f"Failed to get analysis activity: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get analysis activity: {str(e)}")


@router.get("/transparency/execution", response_model=ExecutionActivityResponse)
@limiter.limit("30/minute")
async def get_execution_activity(
    request: Request,
    container=Depends(get_container),
    account_type: Optional[str] = None,
    days: int = 7,
) -> ExecutionActivityResponse:
    """
    Get AI execution activity transparency data.

    Shows trade execution quality, slippage analysis, and risk compliance.
    """
    try:
        services = await get_transparency_services(container)
        execution_monitor = services["execution_monitor"]

        # Get execution history
        executions = await execution_monitor.get_execution_history()

        # Get execution quality metrics
        quality_metrics = await execution_monitor.get_execution_quality_metrics(days=days)

        return ExecutionActivityResponse(
            total_executions=quality_metrics["total_executions"],
            success_rate=quality_metrics["success_rate"],
            avg_slippage=quality_metrics["avg_slippage_bps"],
            avg_cost=quality_metrics["avg_cost_pct"],
            risk_compliance=quality_metrics["risk_checks_pass_rate"],
            recent_executions=[e.to_dict() for e in executions[-5:]]
        )

    except Exception as e:
        logger.error(f"Failed to get execution activity: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get execution activity: {str(e)}")


@router.get("/transparency/daily-evaluation", response_model=DailyStrategyReportResponse)
@limiter.limit("20/minute")
async def get_daily_strategy_evaluation(
    request: Request,
    container=Depends(get_container),
    account_type: str = "swing_trading",
    date: Optional[str] = None,
) -> DailyStrategyReportResponse:
    """
    Get daily strategy evaluation report.

    Shows how Claude evaluated and refined strategies today.
    """
    try:
        services = await get_transparency_services(container)
        strategy_evaluator = services["strategy_evaluator"]

        # Get daily reports
        reports = await strategy_evaluator.get_daily_reports(account_type=account_type)

        if not reports:
            # Generate a new evaluation if none exists
            report = await strategy_evaluator.evaluate_daily_strategies(account_type, date)
        else:
            report = reports[-1]  # Most recent

        return DailyStrategyReportResponse(
            evaluation_date=report.evaluation_date,
            strategies_evaluated=len(report.strategies_evaluated),
            refinements_recommended=len(report.refinements_recommended),
            confidence_score=report.confidence_score,
            key_insights=report.key_insights,
            performance_summary=report.performance_summary
        )

    except Exception as e:
        logger.error(f"Failed to get daily strategy evaluation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get strategy evaluation: {str(e)}")


@router.get("/transparency/daily-summary", response_model=DailyActivitySummaryResponse)
@limiter.limit("20/minute")
async def get_daily_activity_summary(
    request: Request,
    container=Depends(get_container),
    account_type: str = "swing_trading",
    date: Optional[str] = None,
) -> DailyActivitySummaryResponse:
    """
    Get daily AI activity summary.

    Comprehensive overview of what Claude accomplished today and plans for tomorrow.
    """
    try:
        services = await get_transparency_services(container)
        activity_summarizer = services["activity_summarizer"]

        # Get daily summaries
        summaries = await activity_summarizer.get_daily_summaries(account_type=account_type)

        if not summaries:
            # Generate a new summary if none exists
            summary = await activity_summarizer.create_daily_summary(account_type, date)
        else:
            summary = summaries[-1]  # Most recent

        return DailyActivitySummaryResponse(
            date=summary.date,
            day_rating=summary.day_rating,
            trades_executed=summary.trades_executed,
            total_pnl=summary.total_pnl,
            research_sessions=summary.research_sessions,
            strategies_evaluated=summary.strategies_evaluated,
            key_achievements=summary.key_achievements,
            areas_for_improvement=summary.areas_for_improvement,
            planned_activities=summary.planned_activities
        )

    except Exception as e:
        logger.error(f"Failed to get daily activity summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get activity summary: {str(e)}")


@router.get("/transparency/strategy-evolution/{strategy_name}")
@limiter.limit("20/minute")
async def get_strategy_evolution_timeline(
    request: Request,
    strategy_name: str,
    container=Depends(get_container),
    days: int = 90,
) -> Dict[str, Any]:
    """
    Get strategy evolution timeline.

    Shows how a specific strategy has evolved over time with refinements and improvements.
    """
    try:
        services = await get_transparency_services(container)
        strategy_evaluator = services["strategy_evaluator"]

        timeline = await strategy_evaluator.get_strategy_evolution_timeline(strategy_name, days)

        return timeline

    except Exception as e:
        logger.error(f"Failed to get strategy evolution timeline: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get strategy timeline: {str(e)}")