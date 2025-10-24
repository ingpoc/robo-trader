"""
API Routes for Claude's Prompt Optimization System

Provides REST endpoints for:
- Viewing active optimized prompts
- Accessing optimization history and trends
- Triggering manual optimizations
- Monitoring prompt performance
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from ..dependencies import get_database, get_current_user, get_container
from ..services.prompt_optimization_service import PromptOptimizationService
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity
from ..core.di import DependencyContainer
from loguru import logger

router = APIRouter(prefix="/api/prompts", tags=["prompt-optimization"])


@router.get("/active/{data_type}")
async def get_active_prompt(
    data_type: str,
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get current active optimized prompt for data type."""

    valid_types = ["earnings", "news", "fundamentals", "metrics"]
    if data_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data type. Must be one of: {valid_types}"
        )

    try:
        database = await container.get("database")
        async with database.connect() as conn:
            cursor = await conn.execute(
                """
                SELECT id, original_prompt, current_prompt, quality_score, optimization_version,
                       claude_feedback, usage_count, avg_quality_rating, last_optimized_at,
                       total_optimizations, success_rate, last_used
                FROM optimized_prompts
                WHERE data_type = ? AND is_active = TRUE
                ORDER BY last_optimized_at DESC
                LIMIT 1
                """,
                (data_type,)
            )
            row = await cursor.fetchone()

            if not row:
                return {
                    "data_type": data_type,
                    "active_prompt": None,
                    "message": "No optimized prompt found"
                }

            return {
                "data_type": data_type,
                "prompt_id": row[0],
                "original_prompt": row[1],
                "current_prompt": row[2],
                "quality_score": row[3],
                "optimization_version": row[4],
                "claude_feedback": row[5],
                "usage_count": row[6],
                "avg_quality_rating": row[7],
                "last_optimized_at": row[8],
                "total_optimizations": row[9],
                "success_rate": row[10],
                "last_used": row[11],
                "is_active": True
            }

    except Exception as e:
        logger.error(f"Failed to get active prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active prompt: {str(e)}")


@router.get("/optimization-history/{data_type}")
async def get_optimization_history(
    data_type: str,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get optimization history for a data type."""

    valid_types = ["earnings", "news", "fundamentals", "metrics"]
    if data_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data type. Must be one of: {valid_types}"
        )

    try:
        prompt_service = await container.get(PromptOptimizationService)
        history = await prompt_service.get_prompt_history(data_type, days)

        # Limit results
        limited_history = history[:limit]

        return {
            "data_type": data_type,
            "history": limited_history,
            "total_count": len(history),
            "period_days": days
        }

    except Exception as e:
        logger.error(f"Failed to get optimization history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimization history: {str(e)}")


@router.get("/attempts/{prompt_id}")
async def get_prompt_attempts(
    prompt_id: str,
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed optimization attempts for a specific prompt."""

    try:
        database = await container.get("database")

        # Get main prompt info
        async with database.connect() as conn:
            cursor = await conn.execute(
                "SELECT data_type, original_prompt FROM optimized_prompts WHERE id = ?",
                (prompt_id,)
            )
            prompt_row = await cursor.fetchone()

            if not prompt_row:
                raise HTTPException(status_code=404, detail="Prompt not found")

            # Get optimization attempts
            cursor = await conn.execute(
                """
                SELECT attempt_number, prompt_text, data_received, quality_score,
                       claude_analysis, missing_elements, redundant_elements,
                       optimization_time_ms, tokens_used, created_at
                FROM prompt_optimization_attempts
                WHERE prompt_id = ?
                ORDER BY attempt_number
                """,
                (prompt_id,)
            )
            attempt_rows = await cursor.fetchall()

            attempts = []
            for row in attempt_rows:
                attempts.append({
                    "attempt_number": row[0],
                    "prompt_text": row[1],
                    "data_received": row[2][:1000] + "..." if len(row[2]) > 1000 else row[2],
                    "quality_score": row[3],
                    "claude_analysis": row[4],
                    "missing_elements": _parse_json_field(row[5]),
                    "redundant_elements": _parse_json_field(row[6]),
                    "optimization_time_ms": row[7],
                    "tokens_used": row[8],
                    "created_at": row[9]
                })

            return {
                "prompt_id": prompt_id,
                "data_type": prompt_row[0],
                "original_prompt": prompt_row[1],
                "attempts": attempts,
                "total_attempts": len(attempts)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt attempts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt attempts: {str(e)}")


@router.get("/quality-trends")
async def get_quality_trends(
    days: int = Query(default=30, ge=1, le=365),
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get quality trends for all data types over time."""

    try:
        prompt_service = await container.get(PromptOptimizationService)
        trends = await prompt_service.get_quality_trends(days)

        return {
            "trends": trends,
            "period_days": days,
            "data_types": list(trends.keys())
        }

    except Exception as e:
        logger.error(f"Failed to get quality trends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quality trends: {str(e)}")


@router.get("/session-prompts/{session_id}")
async def get_session_prompt_usage(
    session_id: str,
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get all prompts used in a specific Claude session."""

    try:
        database = await container.get("database")

        async with database.connect() as conn:
            cursor = await conn.execute(
                """
                SELECT sp.id, sp.data_type, sp.quality_achieved, sp.symbols_analyzed,
                       sp.trading_decisions_influenced, sp.created_at,
                       op.current_prompt, op.quality_score as baseline_quality,
                       op.claude_feedback
                FROM session_prompt_usage sp
                LEFT JOIN optimized_prompts op ON sp.prompt_id = op.id
                WHERE sp.session_id = ?
                ORDER BY sp.created_at
                """,
                (session_id,)
            )
            rows = await cursor.fetchall()

            session_prompts = []
            for row in rows:
                session_prompts.append({
                    "usage_id": row[0],
                    "data_type": row[1],
                    "quality_achieved": row[2],
                    "symbols_analyzed": _parse_json_field(row[3]),
                    "trading_decisions_influenced": row[4],
                    "created_at": row[5],
                    "prompt_used": row[6],
                    "baseline_quality": row[7],
                    "claude_feedback": row[8]
                })

            return {
                "session_id": session_id,
                "prompts_used": session_prompts,
                "total_prompts": len(session_prompts)
            }

    except Exception as e:
        logger.error(f"Failed to get session prompt usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session prompt usage: {str(e)}")


@router.post("/trigger-optimization")
async def trigger_manual_optimization(
    data_type: str,
    symbols: List[str],
    force_optimization: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger prompt optimization for testing/improvement."""

    valid_types = ["earnings", "news", "fundamentals", "metrics"]
    if data_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data type. Must be one of: {valid_types}"
        )

    if not symbols:
        raise HTTPException(status_code=400, detail="Symbols list cannot be empty")

    try:
        prompt_service = await container.get(PromptOptimizationService)

        # Create a test session ID
        test_session_id = f"manual_optimization_{datetime.utcnow().isoformat()}"

        # Trigger optimization in background
        background_tasks.add_task(
            _run_optimization_task,
            prompt_service,
            data_type,
            symbols,
            test_session_id,
            force_optimization
        )

        return {
            "status": "started",
            "data_type": data_type,
            "session_id": test_session_id,
            "symbols": symbols,
            "message": "Optimization started in background"
        }

    except Exception as e:
        logger.error(f"Manual optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Manual optimization failed: {str(e)}")


@router.get("/optimization-status/{session_id}")
async def get_optimization_status(
    session_id: str,
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get status of an optimization session."""

    try:
        database = await container.get("database")

        async with database.connect() as conn:
            cursor = await conn.execute(
                """
                SELECT COUNT(*) as total_prompts,
                       AVG(quality_achieved) as avg_quality,
                       MAX(created_at) as last_update
                FROM session_prompt_usage
                WHERE session_id = ?
                """,
                (session_id,)
            )
            row = await cursor.fetchone()

            if not row or row[0] == 0:
                return {
                    "session_id": session_id,
                    "status": "not_found",
                    "message": "No optimization activity found for this session"
                }

            return {
                "session_id": session_id,
                "status": "completed",
                "total_prompts": row[0],
                "avg_quality": round(row[1], 2) if row[1] else 0.0,
                "last_update": row[2]
            }

    except Exception as e:
        logger.error(f"Failed to get optimization status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimization status: {str(e)}")


@router.get("/performance-summary")
async def get_performance_summary(
    days: int = Query(default=30, ge=1, le=365),
    container: DependencyContainer = Depends(get_container),
    current_user: dict = Depends(get_current_user)
):
    """Get overall performance summary of prompt optimization."""

    try:
        database = await container.get("database")
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with database.connect() as conn:
            # Overall stats
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(DISTINCT id) as total_prompts,
                    AVG(quality_score) as avg_quality,
                    MAX(quality_score) as best_quality,
                    MIN(quality_score) as worst_quality,
                    SUM(usage_count) as total_usage,
                    AVG(avg_quality_rating) as avg_user_rating
                FROM optimized_prompts
                WHERE created_at >= ?
                """,
                (cutoff_date,)
            )
            overall_row = await cursor.fetchone()

            # Per data type stats
            cursor = await conn.execute(
                """
                SELECT data_type,
                       COUNT(*) as prompt_count,
                       AVG(quality_score) as avg_quality,
                       SUM(usage_count) as total_usage,
                       AVG(avg_quality_rating) as avg_rating
                FROM optimized_prompts
                WHERE created_at >= ?
                GROUP BY data_type
                ORDER BY avg_quality DESC
                """,
                (cutoff_date,)
            )
            type_rows = await cursor.fetchall()

            return {
                "period_days": days,
                "overall": {
                    "total_prompts": overall_row[0] or 0,
                    "avg_quality": round(overall_row[1] or 0, 2),
                    "best_quality": round(overall_row[2] or 0, 2),
                    "worst_quality": round(overall_row[3] or 0, 2),
                    "total_usage": overall_row[4] or 0,
                    "avg_user_rating": round(overall_row[5] or 0, 2)
                },
                "by_data_type": [
                    {
                        "data_type": row[0],
                        "prompt_count": row[1],
                        "avg_quality": round(row[2], 2),
                        "total_usage": row[3],
                        "avg_rating": round(row[4], 2)
                    }
                    for row in type_rows
                ]
            }

    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")


def _parse_json_field(field: Any) -> Any:
    """Parse JSON field safely."""
    if field is None:
        return []
    try:
        if isinstance(field, str):
            return json.loads(field)
        return field
    except (json.JSONDecodeError, TypeError):
        return []


async def _run_optimization_task(
    prompt_service: PromptOptimizationService,
    data_type: str,
    symbols: List[str],
    session_id: str,
    force_optimization: bool
) -> None:
    """Background task to run optimization."""
    try:
        data, quality_score, final_prompt, optimization_metadata = await prompt_service.get_optimized_data(
            data_type=data_type,
            symbols=symbols,
            session_id=session_id,
            force_optimization=force_optimization
        )

        logger.info(
            f"Background optimization completed for {data_type}: "
            f"quality {quality_score}/10, attempts {len(optimization_metadata['attempts'])}"
        )

    except Exception as e:
        logger.error(f"Background optimization failed: {e}")