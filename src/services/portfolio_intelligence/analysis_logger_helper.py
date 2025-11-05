"""
Analysis Logger Helper for Portfolio Intelligence

Handles:
- Analysis step logging
- AI Transparency logging
- WebSocket broadcasting
- Error logging
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PortfolioAnalysisLoggerHelper:
    """Helper for logging portfolio intelligence analysis."""

    def __init__(self, analysis_logger, broadcast_coordinator=None, status_coordinator=None):
        self.analysis_logger = analysis_logger
        self.broadcast_coordinator = broadcast_coordinator
        self.status_coordinator = status_coordinator
        self._active_analyses: Dict[str, Any] = {}

    async def log_analysis_step(
        self,
        step_type: str,
        description: str,
        reasoning: str,
        analysis_id: Optional[str] = None
    ) -> None:
        """Log analysis step to AI Transparency."""
        try:
            if not analysis_id:
                analysis_id = f"portfolio_analysis_{int(datetime.now(timezone.utc).timestamp())}"

            # Create decision log if it doesn't exist
            if analysis_id not in self._active_analyses:
                decision_log = await self.analysis_logger.start_trade_analysis(
                    session_id=f"portfolio_intelligence_{int(datetime.now(timezone.utc).timestamp())}",
                    symbol="PORTFOLIO",  # Portfolio-wide analysis
                    decision_id=analysis_id
                )
                self._active_analyses[analysis_id] = decision_log

            # Log the analysis step
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type=step_type,
                description=description,
                input_data={},
                reasoning=reasoning,
                confidence_score=0.0,
                duration_ms=0
            )
        except Exception as e:
            logger.warning(f"Error logging analysis step: {e}")

    async def log_to_transparency(
        self,
        analysis_id: str,
        agent_name: str,
        symbols: List[str],
        stocks_data: Dict[str, Dict[str, Any]],
        analysis_result: Dict[str, Any]
    ) -> None:
        """Log complete analysis to AI Transparency."""
        try:
            # Final logging step
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="completion",
                description=f"Portfolio intelligence analysis completed for {len(symbols)} stocks",
                input_data={
                    "symbols": symbols,
                    "recommendations_count": len(analysis_result.get("recommendations", [])),
                    "prompt_updates_count": len(analysis_result.get("prompt_updates", []))
                },
                reasoning=f"Analysis complete. Check Claude's response for detailed recommendations and prompt optimizations.",
                confidence_score=0.0,
                duration_ms=analysis_result.get("execution_time_ms", 0)
            )

            # Complete the trade decision to save it to database
            completed_decision = await self.analysis_logger.complete_trade_decision(
                decision_id=analysis_id,
                executed=False,  # Portfolio analysis generates recommendations, not executed trades
                execution_result={
                    "analysis_type": "portfolio_intelligence",
                    "agent_name": agent_name,
                    "symbols_analyzed": len(symbols),
                    "recommendations_generated": len(analysis_result.get("recommendations", [])),
                    "prompt_updates_generated": len(analysis_result.get("prompt_updates", [])),
                    "execution_time_ms": analysis_result.get("execution_time_ms", 0),
                    "claude_response_length": len(analysis_result.get("claude_response", "")),
                    "data_assessment": analysis_result.get("data_assessment", {})
                }
            )

            if completed_decision:
                logger.info(f"Analysis {analysis_id} completed and saved to AI Transparency database")
            else:
                logger.warning(f"Failed to complete analysis decision {analysis_id}")

        except Exception as e:
            logger.warning(f"Error logging to transparency: {e}")

    async def broadcast_analysis_status(
        self,
        status: str,
        message: str,
        symbols_count: int = 0,
        analysis_id: Optional[str] = None,
        recommendations_count: int = 0,
        prompt_updates_count: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Broadcast analysis status via WebSocket."""
        if not self.broadcast_coordinator:
            return

        try:
            # Broadcast portfolio analysis activity update only
            # NOTE: Don't call broadcast_claude_status_update() as it conflicts with
            # the actual Claude SDK status managed by SessionCoordinator
            activity_message = {
                "type": "portfolio_analysis_update",
                "status": status,
                "message": message,
                "analysis_id": analysis_id,
                "symbols_count": symbols_count,
                "recommendations_count": recommendations_count,
                "prompt_updates_count": prompt_updates_count,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await self.broadcast_coordinator.broadcast_to_ui(activity_message)

            # Trigger system health update via status coordinator
            # This ensures the System Health tab shows updated AI Analysis scheduler status
            if self.status_coordinator:
                try:
                    await self.status_coordinator.broadcast_status_change("ai_analysis", status)
                except Exception as e:
                    logger.warning(f"Failed to trigger system health update: {e}")

        except Exception as e:
            logger.warning(f"Failed to broadcast analysis status: {e}")

    async def log_error_to_transparency(
        self,
        analysis_id: str,
        agent_name: str,
        error_message: str
    ) -> None:
        """Log error to AI Transparency."""
        try:
            # Try to log error if analysis_id exists
            if analysis_id in self._active_analyses:
                await self.analysis_logger.log_analysis_step(
                    decision_id=analysis_id,
                    step_type="error",
                    description=f"Analysis failed: {error_message}",
                    input_data={"agent_name": agent_name},
                    reasoning="Error occurred during portfolio intelligence analysis",
                    confidence_score=0.0,
                    duration_ms=0
                )

            logger.error(f"Error in analysis {analysis_id}: {error_message}")
        except Exception as e:
            logger.warning(f"Error logging error to transparency: {e}")
