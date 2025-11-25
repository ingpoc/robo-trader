"""Smart periodic analysis scheduler for comprehensive stock analysis.

Replaces event-driven AI task creation with a periodic scheduler that:
1. Checks which stocks need analysis (no analysis in 24 hours OR never analyzed)
2. Deduplicates against existing pending tasks in AI_ANALYSIS queue
3. Creates ONE comprehensive analysis task per stock (not 4+ separate tasks)
4. Prioritizes: unanalyzed stocks > oldest analysis > skip

This prevents queue bloat (4,731 → 10-20 pending tasks max) and reduces Claude API costs.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from src.core.event_bus import EventHandler, Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.models.scheduler import QueueName, TaskType

if TYPE_CHECKING:
    from src.core.di import DependencyContainer

logger = logging.getLogger(__name__)


class AnalysisScheduler(EventHandler):
    """Periodic scheduler for comprehensive stock analysis.

    Runs every 5 minutes to check which stocks need analysis and queue
    comprehensive analysis tasks (news + earnings + fundamentals in one session).
    """

    def __init__(
        self,
        container: "DependencyContainer",
        check_interval_minutes: int = 5,
        analysis_threshold_hours: int = 24
    ):
        """Initialize analysis scheduler.

        Args:
            container: Dependency injection container
            check_interval_minutes: How often to check for stocks needing analysis (default 5 min)
            analysis_threshold_hours: Minimum hours since last analysis (default 24 hours)
        """
        self.container = container
        self.check_interval_minutes = check_interval_minutes
        self.analysis_threshold_hours = analysis_threshold_hours
        self._max_queue_capacity = 20  # Max tasks in AI_ANALYSIS queue (aligned with PortfolioAnalysisCoordinator)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize scheduler and start background loop."""
        if self._initialized:
            return

        self._initialized = True
        logger.info(
            f"Initializing AnalysisScheduler "
            f"(check every {self.check_interval_minutes} min, threshold {self.analysis_threshold_hours}h)"
        )

    async def start(self) -> None:
        """Start the scheduler background loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler_loop())
        logger.info("AnalysisScheduler started")

    async def stop(self) -> None:
        """Stop the scheduler background loop."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("AnalysisScheduler stopped")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.stop()
        self._initialized = False

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events (for EventHandler interface)."""
        # AnalysisScheduler doesn't subscribe to events currently
        pass

    async def run_scheduling_cycle(self) -> Dict[str, Any]:
        """Execute one scheduling cycle - check stocks and queue analysis.

        Returns:
            Dict with results: {
                "stocks_queued": [...symbols...],
                "stocks_skipped": [...symbols...],
                "cycle_time_seconds": 0.5,
            }
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Get portfolio symbols
            state_manager = await self.container.get_state_manager()
            portfolio_state = await state_manager.portfolio.get_portfolio()

            if not portfolio_state or not portfolio_state.holdings:
                logger.debug("No portfolio holdings - skipping analysis cycle")
                return {
                    "stocks_queued": [],
                    "stocks_skipped": [],
                    "cycle_time_seconds": 0.0
                }

            # Check queue capacity before proceeding (Phase 2: Align with PortfolioAnalysisCoordinator)
            task_service = await self.container.get("task_service")
            queue_stats = await task_service.get_queue_statistics(QueueName.AI_ANALYSIS)
            current_queue_size = (queue_stats.pending_count + queue_stats.running_count)

            if current_queue_size >= self._max_queue_capacity:
                logger.info(
                    f"AI Analysis queue at capacity ({current_queue_size}/{self._max_queue_capacity}). "
                    f"Skipping scheduling cycle until tasks are processed."
                )
                return {
                    "stocks_queued": [],
                    "stocks_skipped": [],
                    "cycle_time_seconds": 0.0
                }

            # Extract symbols
            symbols = [
                h['symbol'] if isinstance(h, dict) else h.symbol
                for h in portfolio_state.holdings
            ]
            logger.debug(f"Checking {len(symbols)} portfolio stocks for analysis")

            # Get stocks needing analysis
            analysis_state = await self.container.get_state_manager()
            stocks_needing_analysis = await analysis_state.analysis.get_stocks_needing_analysis(
                symbols,
                hours=self.analysis_threshold_hours
            )
            logger.debug(f"Stocks needing analysis: {stocks_needing_analysis}")

            # Create batch tasks for stocks needing analysis (Phase 3: batch processing)
            stocks_queued = []
            stocks_skipped = []

            # Phase 3: Filter symbols based on analysis rules
            symbols_to_queue = []
            for symbol in stocks_needing_analysis:
                if await self._is_already_queued(task_service, symbol):
                    logger.debug(f"Skipping {symbol} - already in AI_ANALYSIS queue")
                    stocks_skipped.append(symbol)
                elif await self._already_analyzed_this_month(symbol):
                    logger.debug(f"Skipping {symbol} - already analyzed this month")
                    stocks_skipped.append(symbol)
                elif not await self._has_fresh_data(symbol):
                    logger.debug(f"Skipping {symbol} - no fresh data available")
                    stocks_skipped.append(symbol)
                else:
                    symbols_to_queue.append(symbol)

            # Phase 3: Batch size = 3 stocks per task (balances efficiency and isolation)
            batch_size = 3
            for i in range(0, len(symbols_to_queue), batch_size):
                batch_symbols = symbols_to_queue[i:i + batch_size]

                # Queue batch analysis task
                try:
                    await task_service.create_task(
                        queue_name=QueueName.AI_ANALYSIS,
                        task_type=TaskType.STOCK_ANALYSIS,
                        payload={"symbols": batch_symbols},  # Phase 3: batch processing
                        priority=7
                    )
                    stocks_queued.extend(batch_symbols)
                    logger.info(f"Queued batch analysis for {len(batch_symbols)} symbols: {batch_symbols}")
                except Exception as e:
                    logger.error(f"Failed to queue batch analysis for {batch_symbols}: {e}")
                    stocks_skipped.extend(batch_symbols)

            # Calculate cycle time
            cycle_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return {
                "stocks_queued": stocks_queued,
                "stocks_skipped": stocks_skipped,
                "cycle_time_seconds": round(cycle_time, 2),
                "total_checked": len(symbols),
            }

        except TradingError as e:
            logger.error(f"Trading error in scheduling cycle: {e.context.code}")
            return {
                "stocks_queued": [],
                "stocks_skipped": [],
                "error": str(e),
                "cycle_time_seconds": 0.0
            }
        except Exception as e:
            logger.exception(f"Unexpected error in scheduling cycle: {e}")
            return {
                "stocks_queued": [],
                "stocks_skipped": [],
                "error": str(e),
                "cycle_time_seconds": 0.0
            }

    async def _is_already_queued(self, task_service, symbol: str) -> bool:
        """Check if stock has pending comprehensive analysis task.

        Args:
            task_service: Task service instance
            symbol: Stock symbol

        Returns:
            True if stock already has pending task in AI_ANALYSIS queue
        """
        try:
            # Get pending tasks from AI_ANALYSIS queue
            pending_tasks = await task_service.get_pending_tasks(QueueName.AI_ANALYSIS)

            # Check if any task is for this symbol with STOCK_ANALYSIS type (Phase 3: support batch)
            for task in pending_tasks:
                if task.task_type == TaskType.STOCK_ANALYSIS:
                    payload = task.payload or {}
                    # Check for single symbol (legacy)
                    if payload.get("symbol") == symbol:
                        return True
                    # Check for batch symbols (Phase 3)
                    if "symbols" in payload and isinstance(payload.get("symbols"), list):
                        if symbol in payload.get("symbols", []):
                            return True

            return False
        except Exception as e:
            logger.warning(f"Failed to check pending tasks for {symbol}: {e}")
            # Err on side of caution - assume not queued if we can't check
            return False

    async def _run_scheduler_loop(self) -> None:
        """Background loop that runs scheduling cycles periodically."""
        logger.info(f"Starting analysis scheduler loop (interval: {self.check_interval_minutes} min)")

        while self._running:
            try:
                # Run one scheduling cycle
                result = await self.run_scheduling_cycle()

                # Log results
                queued = len(result.get("stocks_queued", []))
                skipped = len(result.get("stocks_skipped", []))
                cycle_time = result.get("cycle_time_seconds", 0)

                if queued > 0:
                    logger.info(
                        f"Analysis cycle complete: {queued} queued, {skipped} skipped "
                        f"({cycle_time}s)"
                    )
                else:
                    logger.debug(
                        f"Analysis cycle complete: 0 queued, {skipped} skipped "
                        f"({cycle_time}s)"
                    )

                # Emit event if tasks were queued
                if queued > 0:
                    event_bus = await self.container.get("event_bus")
                    if event_bus:
                        await event_bus.publish(Event(
                            id=f"analysis_scheduled_{datetime.now(timezone.utc).timestamp()}",
                            type=EventType.FEATURE_UPDATED,  # Generic feature update
                            source="AnalysisScheduler",
                            timestamp=datetime.now(timezone.utc),
                            data={
                                "action": "analysis_scheduled",
                                "stocks_queued": result.get("stocks_queued", []),
                                "count": queued
                            }
                        ))

            except asyncio.CancelledError:
                logger.debug("Analysis scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in analysis scheduler loop: {e}", exc_info=True)

            # Wait for next cycle
            try:
                await asyncio.sleep(self.check_interval_minutes * 60)
            except asyncio.CancelledError:
                break

        logger.info("Analysis scheduler loop stopped")

    async def _already_analyzed_this_month(self, symbol: str) -> bool:
        """Check if symbol was already analyzed this month."""
        try:
            analysis_state = await self.container.get_state_manager()
            analysis_history = await analysis_state.config_state.get_analysis_history()

            now = datetime.now(timezone.utc)

            for analysis in analysis_history.get("analyses", []):
                if analysis.get("symbol") == symbol:
                    created_at_str = analysis.get("created_at")
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            # Check if analysis was done this month
                            if created_at.year == now.year and created_at.month == now.month:
                                return True
                        except (ValueError, TypeError):
                            pass

            return False
        except Exception as e:
            logger.warning(f"Error checking monthly analysis for {symbol}: {e}")
            return False

    async def _has_fresh_data(self, symbol: str) -> bool:
        """Check if there's fresh data for the symbol since last analysis."""
        try:
            analysis_state = await self.container.get_state_manager()

            # Get last analysis time
            analysis_history = await analysis_state.config_state.get_analysis_history()
            last_analysis = None

            for analysis in analysis_history.get("analyses", []):
                if analysis.get("symbol") == symbol:
                    created_at_str = analysis.get("created_at")
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            if not last_analysis or created_at > last_analysis:
                                last_analysis = created_at
                        except (ValueError, TypeError):
                            pass

            if not last_analysis:
                # Never analyzed, always has fresh data
                return True

            # Check for fresh fundamentals, earnings, and news
            fresh_fundamentals = await self._has_fresh_fundamentals(symbol, last_analysis)
            fresh_earnings = await self._has_fresh_earnings(symbol, last_analysis)
            fresh_news = await self._has_fresh_news(symbol, last_analysis)

            return fresh_fundamentals or fresh_earnings or fresh_news

        except Exception as e:
            logger.warning(f"Error checking fresh data for {symbol}: {e}")
            # Default to allowing analysis if we can't check fresh data
            return True

    async def _has_fresh_fundamentals(self, symbol: str, last_analysis: datetime) -> bool:
        """Check if fundamentals data is fresh."""
        try:
            analysis_state = await self.container.get_state_manager()
            fundamentals = await analysis_state.config_state.get_fundamental_analysis(symbol)
            if fundamentals:
                last_update = fundamentals.get("updated_at") or fundamentals.get("created_at")
                if last_update:
                    if isinstance(last_update, str):
                        last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    return last_update > last_analysis
            return False
        except Exception:
            return False

    async def _has_fresh_earnings(self, symbol: str, last_analysis: datetime) -> bool:
        """Check if earnings data is fresh."""
        try:
            analysis_state = await self.container.get_state_manager()
            earnings = await analysis_state.config_state.get_earnings_reports(symbol)
            if earnings:
                for earnings_report in earnings if isinstance(earnings, list) else [earnings]:
                    report_date = earnings_report.get("report_date") or earnings_report.get("created_at")
                    if report_date:
                        if isinstance(report_date, str):
                            report_date = datetime.fromisoformat(report_date.replace('Z', '+00:00'))
                        return report_date > last_analysis
            return False
        except Exception:
            return False

    async def _has_fresh_news(self, symbol: str, last_analysis: datetime) -> bool:
        """Check if news data is fresh."""
        try:
            analysis_state = await self.container.get_state_manager()
            news = await analysis_state.config_state.get_news_items(symbol)
            if news:
                for news_item in news if isinstance(news, list) else [news]:
                    news_date = news_item.get("published_at") or news_item.get("created_at")
                    if news_date:
                        if isinstance(news_date, str):
                            news_date = datetime.fromisoformat(news_date.replace('Z', '+00:00'))
                        return news_date > last_analysis
            return False
        except Exception:
            return False
