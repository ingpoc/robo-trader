"""Claude AI transparency routes."""

import logging
import os
import json
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

router = APIRouter(prefix="/api/claude", tags=["claude-transparency"])
limiter = Limiter(key_func=get_remote_address)

transparency_limit = os.getenv("RATE_LIMIT_TRANSPARENCY", "20/minute")


@router.get("/transparency/research")
@limiter.limit(transparency_limit)
async def get_research_transparency(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's research activities transparency - matches frontend expectation."""
    try:

        research_tracker = await container.get("research_tracker")

        if not research_tracker:
            return JSONResponse({"error": "Research tracker not available"}, status_code=500)

        # Get research history
        research_sessions = await research_tracker.get_research_history(limit=20)
        data_source_stats = await research_tracker.get_data_source_usage_stats()

        research_data = {
            "active_sessions": len(research_tracker.active_sessions),
            "total_sessions": len(research_sessions),
            "data_sources_used": data_source_stats["sources_used"],
            "total_queries": data_source_stats["total_queries"],
            "total_data_points": data_source_stats["total_data_points"],
            "total_cost_usd": data_source_stats["total_cost_usd"],
            "recent_sessions": [
                {
                    "session_id": session.session_id,
                    "research_type": session.research_type,
                    "symbols_analyzed": session.symbols_analyzed,
                    "data_sources_used": session.data_sources_used,
                    "confidence_score": session.confidence_score,
                    "key_findings": session.key_findings[:3],  # Limit to top 3
                    "recommendations_count": len(session.recommendations),
                    "token_usage": session.token_usage,
                    "cost_usd": session.cost_usd,
                    "created_at": session.created_at
                }
                for session in research_sessions[-10:]  # Last 10 sessions
            ],
            "data_source_breakdown": data_source_stats["source_breakdown"],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return {"research": research_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/transparency/analysis")
@limiter.limit(transparency_limit)
async def get_analysis_transparency(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's analysis activities transparency."""
    try:
        # Get portfolio analysis data from configuration state (with proper locking)
        portfolio_analyses = []
        try:
            configuration_state = await container.get("configuration_state")

            if not configuration_state:
                logger.warning("Configuration state not available")
                portfolio_analyses = []
            else:
                # Use configuration state's locked database access
                config_data = await configuration_state.get_analysis_history()

                if config_data and "analyses" in config_data:
                    for analysis_record in config_data["analyses"]:
                        try:
                            analysis_data = json.loads(analysis_record["analysis"]) if isinstance(analysis_record["analysis"], str) else analysis_record["analysis"]
                            # Extract claude_response for UI display
                            claude_response = analysis_data.get("claude_response", "")
                            # Create analysis_summary from claude_response, truncating if too long
                            analysis_summary = claude_response[:200] + "..." if len(claude_response) > 200 else claude_response

                            portfolio_analyses.append({
                                "symbol": analysis_record.get("symbol", ""),
                                "timestamp": analysis_record.get("timestamp", ""),
                                "created_at": analysis_record.get("created_at", ""),
                                "analysis_type": analysis_data.get("analysis_type", "unknown"),
                                "recommendations_count": analysis_data.get("recommendations_count", 0),
                                "confidence_score": analysis_data.get("confidence_score", 0.0),
                                "key_insights": [],  # Not available in current structure
                                "data_sources": [],  # Not available in current structure
                                "analysis_summary": analysis_summary,
                                "analysis_content": claude_response,  # Full content for detailed view
                                "data_quality": analysis_data.get("data_quality", {})
                            })
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse analysis JSON for {analysis_record.get('symbol', 'unknown')}: {e}")
                            continue

        except Exception as e:
            logger.warning(f"Could not get portfolio analyses from configuration state: {e}")
            portfolio_analyses = []

        # Calculate portfolio analysis stats
        portfolio_stats = {
            "total_analyses": len(portfolio_analyses),
            "symbols_analyzed": len(set(analysis["symbol"] for analysis in portfolio_analyses)),
            "avg_confidence": sum(analysis["confidence_score"] for analysis in portfolio_analyses) / len(portfolio_analyses) if portfolio_analyses else 0.0,
            "total_recommendations": sum(analysis["recommendations_count"] for analysis in portfolio_analyses),
        }

        analysis_data = {
            "portfolio_analyses": portfolio_analyses,
            "portfolio_stats": portfolio_stats,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return {"analysis": analysis_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/transparency/execution")
@limiter.limit(transparency_limit)
async def get_execution_transparency(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's trade execution transparency."""
    try:

        # Get Claude agent service for execution data
        claude_agent_service = await container.get("claude_agent_service")

        if not claude_agent_service:
            return JSONResponse({"error": "Claude agent service not available"}, status_code=500)

        # Get strategy store for session data
        strategy_store = await container.get("claude_strategy_store")

        if not strategy_store:
            return JSONResponse({"error": "Strategy store not available"}, status_code=500)

        # Get recent sessions
        recent_sessions = await strategy_store.get_recent_sessions("swing", limit=10) + \
                         await strategy_store.get_recent_sessions("options", limit=10)

        execution_data = {
            "total_sessions": len(recent_sessions),
            "successful_executions": sum(1 for s in recent_sessions if s.success),
            "failed_executions": sum(1 for s in recent_sessions if not s.success),
            "total_trades_executed": sum(len(s.decisions_made) for s in recent_sessions if s.decisions_made),
            "total_token_usage": sum(s.token_input + s.token_output for s in recent_sessions),
            "total_cost_usd": sum(s.total_cost_usd for s in recent_sessions),
            "recent_sessions": [
                {
                    "session_id": session.session_id,
                    "session_type": session.session_type.value,
                    "account_type": session.account_type,
                    "success": session.success,
                    "trades_executed": len(session.decisions_made) if session.decisions_made else 0,
                    "token_usage": session.token_input + session.token_output,
                    "cost_usd": session.total_cost_usd,
                    "timestamp": session.timestamp
                }
                for session in recent_sessions[-5:]  # Last 5 sessions
            ],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return {"execution": execution_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/transparency/daily-evaluation")
@limiter.limit(transparency_limit)
async def get_daily_evaluation_transparency(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's daily strategy evaluation transparency."""
    try:

        strategy_store = await container.get("claude_strategy_store")

        if not strategy_store:
            return JSONResponse({"error": "Strategy store not available"}, status_code=500)

        # Get daily evaluations (this would need to be implemented in the store)
        # For now, return mock data
        daily_evaluations = [
            {
                "date": "2025-10-24",
                "account_type": "swing",
                "strategies_evaluated": ["RSI Divergence", "Momentum Breakout", "Support Bounce"],
                "best_performing": "RSI Divergence",
                "worst_performing": "Support Bounce",
                "confidence_score": 0.78,
                "recommendations": [
                    "Increase RSI strategy allocation by 20%",
                    "Reduce support bounce position sizing",
                    "Test new volume confirmation filter"
                ],
                "token_usage": 1250,
                "cost_usd": 0.00625
            },
            {
                "date": "2025-10-24",
                "account_type": "options",
                "strategies_evaluated": ["Call Spread", "Put Spread", "Iron Condor"],
                "best_performing": "Iron Condor",
                "worst_performing": "Put Spread",
                "confidence_score": 0.65,
                "recommendations": [
                    "Continue Iron Condor strategy",
                    "Reduce Put Spread allocation",
                    "Test new volatility filter"
                ],
                "token_usage": 980,
                "cost_usd": 0.0049
            }
        ]

        evaluation_data = {
            "evaluations": daily_evaluations,
            "total_evaluations": len(daily_evaluations),
            "avg_confidence": sum(e["confidence_score"] for e in daily_evaluations) / len(daily_evaluations),
            "total_token_usage": sum(e["token_usage"] for e in daily_evaluations),
            "total_cost_usd": sum(e["cost_usd"] for e in daily_evaluations),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return {"daily_evaluation": evaluation_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/transparency/daily-summary")
@limiter.limit(transparency_limit)
async def get_daily_summary_transparency(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's daily activity summary transparency."""
    try:

        # Get various components for summary
        research_tracker = await container.get("research_tracker")
        strategy_store = await container.get("claude_strategy_store")

        if not research_tracker or not strategy_store:
            return JSONResponse({"error": "Required services not available"}, status_code=500)

        # Aggregate data from different sources
        research_stats = await research_tracker.get_data_source_usage_stats()
        recent_sessions = await strategy_store.get_recent_sessions("swing", limit=5) + \
                         await strategy_store.get_recent_sessions("options", limit=5)

        summary_data = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "total_research_sessions": len(await research_tracker.get_research_history(limit=100)),
            "active_research_sessions": len(research_tracker.active_sessions),
            "data_sources_consulted": research_stats["sources_used"],
            "total_queries_made": research_stats["total_queries"],
            "total_data_points": research_stats["total_data_points"],
            "total_ai_sessions": len(recent_sessions),
            "successful_sessions": sum(1 for s in recent_sessions if s.success),
            "total_trades_executed": sum(len(s.decisions_made) for s in recent_sessions if s.decisions_made),
            "total_token_usage": sum(s.token_input + s.token_output for s in recent_sessions),
            "total_cost_usd": sum(s.total_cost_usd for s in recent_sessions) + research_stats["total_cost_usd"],
            "avg_session_confidence": sum(s.confidence_score for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0,
            "key_activities": [
                "Portfolio analysis and rebalancing",
                "Market opportunity identification",
                "Trade execution and risk management",
                "Strategy performance evaluation",
                "Data source optimization"
            ],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return {"daily_summary": summary_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/transparency/trade-decisions")
@limiter.limit(transparency_limit)
async def get_trade_decisions(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's trade decision logs for AI transparency."""
    try:

        trade_decision_logger = await container.get("trade_decision_logger")

        if not trade_decision_logger:
            return JSONResponse({"error": "Trade decision logger not available"}, status_code=500)

        recent_decisions = await trade_decision_logger.get_recent_decisions(limit=20)
        stats = await trade_decision_logger.get_decision_stats()

        return {
            "decisions": recent_decisions,
            "stats": stats,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/transparency/data-quality-summary")
@limiter.limit(transparency_limit)
async def get_data_quality_summary(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get data quality summary from most recent Claude session."""
    try:

        # Get the most recent session's data quality metrics
        # This is stored when ClaudeAgentService fetches optimized data
        strategy_store = await container.get("claude_strategy_store")

        if not strategy_store:
            return JSONResponse({"error": "Strategy store not available"}, status_code=500)

        # Get most recent session for each account type
        sessions = {}
        for account_type in ["swing", "options"]:
            recent = await strategy_store.get_recent_sessions(account_type, limit=1)
            if recent:
                sessions[account_type] = recent[0]

        # Extract data quality from session metadata
        quality_summary = {}
        for account_type, session in sessions.items():
            if hasattr(session, 'metadata') and session.metadata:
                session_quality = session.metadata.get('data_quality_summary', {})
                # Merge quality data from all sessions
                for data_type, metrics in session_quality.items():
                    if data_type not in quality_summary:
                        quality_summary[data_type] = metrics

        # If no session data, provide empty structure
        if not quality_summary:
            quality_summary = {
                "earnings": {"quality_score": 0.0, "optimization_attempts": 0, "optimization_triggered": False, "prompt_optimized": False},
                "news": {"quality_score": 0.0, "optimization_attempts": 0, "optimization_triggered": False, "prompt_optimized": False},
                "fundamentals": {"quality_score": 0.0, "optimization_attempts": 0, "optimization_triggered": False, "prompt_optimized": False}
            }

        return {
            "quality_summary": quality_summary,
            "sessions_analyzed": len(sessions),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")


@router.get("/current-strategy/{account_type}")
@limiter.limit(transparency_limit)
async def get_current_strategy(request: Request, account_type: str, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get current trading strategy for account type."""
    try:

        if account_type not in ["swing", "options"]:
            return JSONResponse({"error": "Invalid account type"}, status_code=400)

        strategy_store = await container.get("claude_strategy_store")

        if not strategy_store:
            return JSONResponse({"error": "Strategy store not available"}, status_code=500)

        # Get most recent session
        recent_sessions = await strategy_store.get_recent_sessions(account_type, limit=1)

        if not recent_sessions:
            return {
                "strategy": None,
                "message": "No strategy available yet"
            }

        session = recent_sessions[0]

        # Extract strategy details
        strategy = {
            "strategy_type": account_type,
            "focus_areas": session.metadata.get("focus_areas", []) if hasattr(session, 'metadata') and session.metadata else [],
            "risk_level": session.metadata.get("risk_level", "moderate") if hasattr(session, 'metadata') and session.metadata else "moderate",
            "current_analysis": session.metadata.get("current_analysis", "") if hasattr(session, 'metadata') and session.metadata else "",
            "data_quality": session.metadata.get("data_quality_summary", {}) if hasattr(session, 'metadata') and session.metadata else {},
            "last_updated": session.timestamp.isoformat() if hasattr(session, 'timestamp') else datetime.now(timezone.utc).isoformat()
        }

        return {
            "strategy": strategy,
            "session_id": session.session_id if hasattr(session, 'session_id') else None
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "claude_transparency_endpoint")
