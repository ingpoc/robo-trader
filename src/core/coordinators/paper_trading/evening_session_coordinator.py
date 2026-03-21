"""
Evening Session Coordinator (Orchestrator) - PT-004: Evening Performance Review.
Delegates to: EveningPortfolioReviewCoordinator, EveningPerformanceCoordinator, EveningStrategyCoordinator.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType
from ..base_coordinator import BaseCoordinator
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from .evening_portfolio_review_coordinator import EveningPortfolioReviewCoordinator
from .evening_performance_coordinator import EveningPerformanceCoordinator
from .evening_strategy_coordinator import EveningStrategyCoordinator


class EveningSessionCoordinator(BaseCoordinator):
    """Thin orchestrator that delegates to focused sub-coordinators."""

    def __init__(self, config: Config, event_bus: EventBus, container: Any):
        super().__init__(config, event_bus)
        self.container = container
        self._running_sessions: Dict[str, Dict[str, Any]] = {}
        self.portfolio_review = EveningPortfolioReviewCoordinator(config, event_bus, container)
        self.performance = EveningPerformanceCoordinator(config, event_bus, container)
        self.strategy = EveningStrategyCoordinator(config, event_bus)

    async def initialize(self) -> None:
        """Initialize all sub-coordinators."""
        self._log_info("Initializing EveningSessionCoordinator")
        await self.portfolio_review.initialize()
        await self.performance.initialize()
        await self.strategy.initialize()
        self.paper_trading_state = self.portfolio_review.paper_trading_state
        self._initialized = True
        self._log_info("EveningSessionCoordinator initialized successfully")

    async def run_evening_review(
        self, trigger_source: str = "SCHEDULED", review_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the evening performance review session.
        Args:
            trigger_source: Source of the trigger (SCHEDULED, MANUAL)
            review_date: Date to review (defaults to today)
        Returns: Dictionary with review results
        """
        if not self._initialized:
            raise TradingError("EveningSessionCoordinator not initialized",
                               category=ErrorCategory.SYSTEM, severity=ErrorSeverity.CRITICAL)

        session_id = f"evening_review_{uuid.uuid4().hex[:16]}"
        review_date = review_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_time = datetime.now(timezone.utc)
        self._log_info(f"Starting evening review session {session_id} for {review_date}")

        try:
            self._running_sessions[session_id] = {
                "start_time": start_time, "status": "running", "review_date": review_date
            }
            account_id = await self.portfolio_review.resolve_review_account_id()
            self._running_sessions[session_id]["account_id"] = account_id

            # Portfolio data gathering
            current_prices = await self.portfolio_review.fetch_current_prices(account_id)
            metrics = await self.portfolio_review.get_performance_metrics(
                account_id, review_date, current_prices)
            open_positions = await self.portfolio_review.get_open_positions(account_id)
            market_obs = await self.portfolio_review.compile_market_observations()

            # AI analysis and insights
            insights = await self.performance.generate_trading_insights(metrics, open_positions)
            watchlist = await self.performance.prepare_next_day_watchlist(metrics, open_positions)

            # Strategy evaluation and learning
            strategy_analysis = await self.strategy.analyze_strategy_performance(
                metrics.get("strategy_performance", {}))
            learnings = await self.strategy.generate_learning_insights(
                metrics, insights, strategy_analysis)

            # Compile and store results
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            session_data = _build_session_data(
                session_id, account_id, review_date, start_time, end_time,
                duration_ms, trigger_source, metrics, insights,
                strategy_analysis, market_obs, watchlist)
            await self.paper_trading_state.store_evening_performance_review(session_id, session_data)
            await self.performance.update_safeguards(metrics)
            await self._publish_completion(session_id, review_date, metrics)
            self._log_info(f"Evening review {session_id} completed successfully")
            return session_data

        except Exception as e:
            self._log_error(f"Evening review {session_id} failed: {e}", exc_info=True)
            await self._store_failure(session_id, review_date, start_time, trigger_source, str(e))
            raise TradingError(f"Evening review failed: {e}", category=ErrorCategory.SYSTEM,
                               severity=ErrorSeverity.HIGH,
                               context={"session_id": session_id, "review_date": review_date})
        finally:
            self._running_sessions.pop(session_id, None)

    async def _publish_completion(self, session_id, review_date, metrics) -> None:
        await self.event_bus.publish(Event(
            id=str(uuid.uuid4()), type=EventType.EVENING_REVIEW_COMPLETE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"session_id": session_id, "review_date": review_date,
                  "daily_pnl": metrics.get("daily_pnl", 0.0),
                  "trades_count": len(metrics.get("trades_reviewed", [])),
                  "win_rate": metrics.get("win_rate", 0.0)},
            source="evening_session_coordinator"))

    async def _store_failure(self, session_id, review_date, start_time, trigger_source, error) -> None:
        await self.paper_trading_state.store_evening_performance_review(session_id, {
            "review_id": session_id, "review_date": review_date,
            "account_id": self._running_sessions.get(session_id, {}).get("account_id"),
            "start_time": start_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "success": False, "error_message": error, "trigger_source": trigger_source})

    async def get_running_sessions(self) -> List[Dict[str, Any]]:
        """Get list of currently running evening review sessions."""
        return [{"session_id": sid, "start_time": d["start_time"],
                 "status": d["status"], "review_date": d["review_date"]}
                for sid, d in self._running_sessions.items()]

    async def cleanup(self) -> None:
        """Cleanup all sub-coordinators."""
        await self.portfolio_review.cleanup()
        await self.performance.cleanup()
        await self.strategy.cleanup()
        self._running_sessions.clear()
        self._log_info("EveningSessionCoordinator cleanup complete")


def _build_session_data(
    session_id, account_id, review_date, start_time, end_time,
    duration_ms, trigger_source, metrics, insights,
    strategy_analysis, market_obs, watchlist,
) -> Dict[str, Any]:
    """Build the session data dict (module-level helper to keep coordinator lean)."""
    return {
        "review_id": session_id, "account_id": account_id,
        "review_date": review_date, "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(), "success": True, "error_message": None,
        "review_data": {"session_summary": {
            "total_trades": len(metrics.get("trades_reviewed", [])),
            "daily_pnl": metrics.get("daily_pnl", 0.0),
            "daily_pnl_percent": metrics.get("daily_pnl_percent", 0.0),
            "win_rate": metrics.get("win_rate", 0.0),
            "session_duration_minutes": duration_ms / 60000}},
        "trades_reviewed": metrics.get("trades_reviewed", []),
        "daily_pnl": metrics.get("daily_pnl", 0.0),
        "daily_pnl_percent": metrics.get("daily_pnl_percent", 0.0),
        "open_positions_count": metrics.get("open_positions_count", 0),
        "closed_positions_count": metrics.get("closed_positions_count", 0),
        "win_rate": metrics.get("win_rate", 0.0),
        "trading_insights": insights, "strategy_performance": strategy_analysis,
        "market_observations": market_obs, "next_day_watchlist": watchlist,
        "session_context": {"trigger_source": trigger_source,
                            "market_hours": "regular", "session_type": "evening_review"},
        "trigger_source": trigger_source, "total_duration_ms": duration_ms}
