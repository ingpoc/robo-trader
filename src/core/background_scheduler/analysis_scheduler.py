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

            # Create tasks for stocks needing analysis
            task_service = await self.container.get("task_service")
            stocks_queued = []
            stocks_skipped = []

            for symbol in stocks_needing_analysis:
                # Check if already queued (deduplication)
                if await self._is_already_queued(task_service, symbol):
                    logger.debug(f"Skipping {symbol} - already in AI_ANALYSIS queue")
                    stocks_skipped.append(symbol)
                    continue

                # Queue comprehensive analysis task
                try:
                    await task_service.create_task(
                        queue_name=QueueName.AI_ANALYSIS,
                        task_type=TaskType.COMPREHENSIVE_STOCK_ANALYSIS,
                        payload={"symbol": symbol},
                        priority=7
                    )
                    stocks_queued.append(symbol)
                    logger.info(f"Queued comprehensive analysis for {symbol}")
                except Exception as e:
                    logger.error(f"Failed to queue analysis for {symbol}: {e}")
                    stocks_skipped.append(symbol)

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

            # Check if any task is for this symbol with COMPREHENSIVE_STOCK_ANALYSIS type
            for task in pending_tasks:
                if (task.task_type == TaskType.COMPREHENSIVE_STOCK_ANALYSIS and
                    task.payload.get("symbol") == symbol):
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
