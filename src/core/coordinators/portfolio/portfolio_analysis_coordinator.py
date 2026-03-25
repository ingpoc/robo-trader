"""Portfolio Analysis Coordinator - Monitors and triggers portfolio analysis."""

import logging
import asyncio
import traceback
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import Event, EventType
from src.core.database_state.database_state import DatabaseStateManager
from src.core.database_state.configuration_state import ConfigurationState
from src.models.scheduler import QueueName, TaskType

logger = logging.getLogger(__name__)


class PortfolioAnalysisCoordinator(BaseCoordinator):
    """Coordinates portfolio analysis - monitors and queues stocks for Claude analysis."""

    def __init__(
        self,
        config: Any,
        state_manager: DatabaseStateManager,
        config_state: ConfigurationState,
        task_service: Any
    ):
        """Initialize Portfolio Analysis Coordinator.

        Args:
            config: Configuration object
            state_manager: Database state manager for portfolio data
            config_state: Configuration state for analysis history
            task_service: Task service for submitting analysis tasks
        """
        super().__init__(config, "PortfolioAnalysisCoordinator")

        self.state_manager = state_manager
        self.config_state = config_state
        self.task_service = task_service

        # Initialization tracking
        self._initialized = False
        self._initialization_complete = False
        self._initialization_error: Optional[Exception] = None
        self._initialization_error_traceback: Optional[str] = None

        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Configuration
        self._check_interval = 300  # 5 minutes
        self._batch_size = 10  # Top 10 stocks per cycle
        self._min_analysis_interval = 3600  # 1 hour
        self._max_queue_capacity = 20  # Max total tasks in AI Analysis queue

    async def initialize(self) -> None:
        """Initialize portfolio analysis coordinator."""
        try:
            if self._initialized:
                return

            self._initialized = True
            self._log_init_step("Starting Portfolio Analysis Coordinator initialization")

            # Verify dependencies
            self._log_init_step("Verifying state_manager dependency")
            if not self.state_manager:
                raise ValueError("DatabaseStateManager is required")
            self._log_init_step("state_manager verified")

            self._log_init_step("Verifying config_state dependency")
            if not self.config_state:
                raise ValueError("ConfigurationState is required")
            self._log_init_step("config_state verified")

            self._log_init_step("Verifying task_service dependency")
            if not self.task_service:
                raise ValueError("TaskService is required")
            self._log_init_step("task_service verified")

            # Create monitoring background task
            self._log_init_step("Creating monitoring background task")
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._log_init_step("Monitoring task created")

            # Mark initialization complete immediately (monitoring loop will run in background)
            self._initialization_complete = True
            logger.info("Portfolio Analysis Coordinator initialized successfully")

        except Exception as e:
            self._initialized = False
            self._initialization_error = e
            self._initialization_error_traceback = traceback.format_exc()
            self._log_init_step("Portfolio Analysis Coordinator initialization", success=False, error=e)
            raise RuntimeError(f"Portfolio Analysis Coordinator initialization failed: {e}") from e

    def _log_init_step(self, step: str, success: bool = True, error: Optional[Exception] = None) -> None:
        """Log initialization step to logger (outputs to both console and files)."""
        if success:
            msg = f"[INIT] {step} - OK"
            logger.info(msg)
        else:
            msg = f"[INIT FAILED] {step}: {error}"
            logger.error(msg)
            if error:
                logger.error(f"Traceback: {traceback.format_exc()}")

    async def _monitoring_loop(self) -> None:
        """Run the portfolio analysis monitoring loop."""
        retry_delay = 60  # Retry after 60 seconds on error

        while True:
            try:
                # Wait for interval before checking
                await asyncio.sleep(self._check_interval)

                # Run portfolio analysis check
                await self._run_portfolio_analysis_check()

            except asyncio.CancelledError:
                logger.info("Portfolio analysis monitoring loop cancelled")
                break

            except Exception as e:
                logger.error(f"Portfolio analysis monitoring error: {e}", exc_info=True)
                # Continue monitoring despite errors
                await asyncio.sleep(retry_delay)

    async def _run_portfolio_analysis_check(self) -> None:
        """Check portfolio and submit analysis tasks for stocks needing attention."""
        async with self._lock:
            try:
                self._log_info("Running portfolio analysis check")

                # Check queue capacity before proceeding
                current_queue_size = await self._get_current_queue_size()
                if current_queue_size >= self._max_queue_capacity:
                    self._log_info(
                        f"AI Analysis queue at capacity ({current_queue_size}/{self._max_queue_capacity}). "
                        f"Skipping monitoring cycle until tasks are processed."
                    )
                    return

                # Get stocks needing analysis
                stocks_to_analyze = await self._get_stocks_needing_analysis()

                if not stocks_to_analyze:
                    self._log_info("All portfolio stocks have recent analysis")
                    return

                # Calculate how many more tasks we can submit
                remaining_capacity = self._max_queue_capacity - current_queue_size
                stocks_to_analyze = stocks_to_analyze[:remaining_capacity]

                self._log_info(
                    f"Found {len(stocks_to_analyze)} stocks needing analysis "
                    f"(queue capacity: {current_queue_size}/{self._max_queue_capacity})"
                )

                # Submit analysis tasks for selected stocks
                await self._queue_analysis_tasks(stocks_to_analyze)

                # Publish monitoring event
                await self._publish_monitoring_event(stocks_to_analyze)

            except Exception as e:
                logger.error(f"Error checking portfolio for analysis: {e}", exc_info=True)

    async def _get_current_queue_size(self) -> int:
        """Get current number of pending+running tasks in AI Analysis queue.

        Returns:
            Current queue size (pending + running tasks)
        """
        try:
            # Get queue statistics for AI_ANALYSIS queue
            queue_stats = await self.task_service.get_queue_statistics(QueueName.AI_ANALYSIS)

            # Count pending and running tasks
            return queue_stats.pending_count + queue_stats.running_count

        except Exception as e:
            logger.warning(f"Failed to get queue status, assuming queue is empty: {e}")
            return 0  # Assume empty to allow monitoring to continue

    async def _get_stocks_needing_analysis(self) -> List[Dict[str, Any]]:
        """Get stocks needing analysis, prioritized by freshness.

        Priority 1 (Score 10): Never analyzed
        Priority 2 (Score 5): Analysis stale (>1 hour old)

        Returns:
            List of dicts with symbol, priority, and reason
        """
        try:
            # Get portfolio holdings
            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.warning("No portfolio holdings available")
                return []

            # Get symbols currently in AI Analysis queue (to avoid duplicates)
            symbols_in_queue = await self._get_symbols_in_queue()

            # Get analysis history
            analysis_history = await self.config_state.get_analysis_history()
            analyzed_symbols = {}  # symbol -> timestamp

            # Parse analysis history
            for analysis in analysis_history.get("analyses", []):
                symbol = analysis.get("symbol")
                created_at_str = analysis.get("created_at")
                if symbol and created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        # Keep most recent analysis time
                        if symbol not in analyzed_symbols or created_at > analyzed_symbols[symbol]:
                            analyzed_symbols[symbol] = created_at
                    except (ValueError, TypeError):
                        pass

            # Calculate priority for each stock
            stocks_with_priority = []
            now = datetime.now(timezone.utc)
            min_interval = timedelta(seconds=self._min_analysis_interval)

            for holding in portfolio.holdings:
                # Extract symbol from holding dictionary
                symbol = holding.get("symbol")
                if not symbol:
                    continue  # Skip holdings without symbols

                # Skip if symbol already has a pending/running task in queue
                if symbol in symbols_in_queue:
                    logger.debug(f"Skipping {symbol} - already in AI Analysis queue")
                    continue

                # Priority 1: Never analyzed
                if symbol not in analyzed_symbols:
                    stocks_with_priority.append({
                        "symbol": symbol,
                        "priority": 10,
                        "reason": "never_analyzed"
                    })

                # Rule 1: Skip if already analyzed this month (one analysis per month max)
                else:
                    last_analysis = analyzed_symbols[symbol]

                    # Check if analysis was done this month
                    if last_analysis.year == now.year and last_analysis.month == now.month:
                        logger.debug(f"Skipping {symbol} - already analyzed this month on {last_analysis.strftime('%Y-%m-%d')}")
                        continue

                    # Rule 2: Only analyze if data is fresh (check for updated fundamentals, earnings, news)
                    if not await self._has_fresh_data(symbol, last_analysis):
                        logger.debug(f"Skipping {symbol} - no fresh data since last analysis")
                        continue

                    # Priority 2: Analysis is stale and meets both rules
                    age = now - last_analysis
                    if age > min_interval:
                        stocks_with_priority.append({
                            "symbol": symbol,
                            "priority": 5,
                            "reason": "eligible_for_analysis",
                            "age_hours": age.total_seconds() / 3600,
                            "last_analysis": last_analysis.strftime('%Y-%m-%d')
                        })

            # Sort by priority (highest first) and return top batch
            stocks_with_priority.sort(key=lambda x: x["priority"], reverse=True)
            return stocks_with_priority[:self._batch_size]

        except Exception as e:
            logger.error(f"Error getting stocks needing analysis: {e}", exc_info=True)
            return []

    async def _get_symbols_in_queue(self) -> set:
        """Get symbols that currently have pending or running tasks in AI Analysis queue.

        Returns:
            Set of symbols currently in queue
        """
        try:
            # Get pending tasks from AI_ANALYSIS queue
            pending_tasks = await self.task_service.get_pending_tasks(
                queue_name=QueueName.AI_ANALYSIS
            )

            symbols_in_queue = set()
            for task in pending_tasks:
                try:
                    # Extract symbol(s) from task payload (Phase 3: support batch)
                    payload = task.payload
                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    # Check for batch symbols (Phase 3)
                    if "symbols" in payload and isinstance(payload.get("symbols"), list):
                        for symbol in payload.get("symbols", []):
                            if symbol:
                                symbols_in_queue.add(symbol)
                    # Check for single symbol (legacy)
                    elif "symbol" in payload:
                        symbol = payload.get("symbol")
                        if symbol:
                            symbols_in_queue.add(symbol)
                except Exception as e:
                    logger.debug(f"Failed to extract symbol from task {task.task_id}: {e}")
                    continue

            return symbols_in_queue

        except Exception as e:
            logger.warning(f"Failed to get symbols in queue, assuming empty: {e}")
            return set()  # Assume empty to allow monitoring to continue

    async def _queue_analysis_tasks(self, stocks: List[Dict[str, Any]]) -> None:
        """Queue analysis tasks for selected stocks with batch processing (Phase 3).

        Phase 3: Batch 3-5 stocks per task to reduce queue length and API calls.
        Batches are ordered by priority (highest first) and reason.

        Args:
            stocks: List of stocks with priority and reason
        """
        # Phase 3: Batch size = 3 stocks per task (balances efficiency and isolation)
        batch_size = 3

        # Sort by priority (highest first) for consistent batching
        sorted_stocks = sorted(stocks, key=lambda s: s["priority"], reverse=True)

        # Batch stocks together
        for i in range(0, len(sorted_stocks), batch_size):
            batch_stocks = sorted_stocks[i:i + batch_size]
            batch_symbols = [s["symbol"] for s in batch_stocks]

            try:
                # Use highest priority in batch
                priority = max(s["priority"] for s in batch_stocks)

                # Create batch analysis task (Phase 3)
                task = await self.task_service.create_task(
                    queue_name=QueueName.AI_ANALYSIS,
                    task_type=TaskType.STOCK_ANALYSIS,
                    payload={
                        "symbols": batch_symbols  # Phase 3: batch processing
                    },
                    priority=priority
                )

                reasons = ", ".join(set(s["reason"] for s in batch_stocks))
                self._log_info(
                    f"Queued batch task for {len(batch_symbols)} symbols {batch_symbols} "
                    f"(priority={priority}, reasons=[{reasons}], task_id={task.task_id})"
                )

            except Exception as e:
                logger.error(f"Failed to queue batch analysis for {batch_symbols}: {e}", exc_info=True)
                # Continue with next batch on failure

    async def _publish_monitoring_event(self, stocks_analyzed: List[Dict[str, Any]]) -> None:
        """Publish monitoring event for UI updates.

        Args:
            stocks_analyzed: List of stocks queued for analysis
        """
        try:
            priority_distribution = {
                "never_analyzed": len([s for s in stocks_analyzed if s["priority"] == 10]),
                "stale_analysis": len([s for s in stocks_analyzed if s["priority"] == 5])
            }

            event = Event(
                id=f"portfolio_analysis_monitor_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.SYSTEM_STATUS,
                source="PortfolioAnalysisCoordinator",
                timestamp=datetime.now(timezone.utc),
                data={
                    "stocks_queued": [s["symbol"] for s in stocks_analyzed],
                    "total_queued": len(stocks_analyzed),
                    "priority_distribution": priority_distribution
                }
            )

            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Failed to publish monitoring event: {e}")

    async def cleanup(self) -> None:
        """Cleanup portfolio analysis coordinator."""
        if not self._initialized:
            return

        try:
            # Cancel monitoring task
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

            logger.info("Portfolio Analysis Coordinator cleanup complete")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        finally:
            self._initialized = False

    def is_ready(self) -> bool:
        """Check if coordinator is ready.

        Returns:
            True if initialization complete and no errors
        """
        return self._initialization_complete and self._initialization_error is None

    def get_initialization_status(self) -> Tuple[bool, Optional[str]]:
        """Get initialization status.

        Returns:
            Tuple of (success, error_message)
        """
        if self._initialization_error:
            return False, f"{self._initialization_error.__class__.__name__}: {str(self._initialization_error)}"
        return self._initialization_complete, None

    async def _has_fresh_data(self, symbol: str, last_analysis: datetime) -> bool:
        """Check if there's fresh data for the symbol since last analysis.

        Args:
            symbol: Stock symbol to check
            last_analysis: Datetime of last analysis

        Returns:
            True if fresh data exists, False otherwise
        """
        try:
            # Check for fresh fundamentals data
            fresh_fundamentals = await self._has_fresh_fundamentals(symbol, last_analysis)

            # Check for fresh earnings data
            fresh_earnings = await self._has_fresh_earnings(symbol, last_analysis)

            # Check for fresh news data
            fresh_news = await self._has_fresh_news(symbol, last_analysis)

            has_fresh = fresh_fundamentals or fresh_earnings or fresh_news

            if has_fresh:
                logger.debug(f"{symbol} has fresh data - fundamentals:{fresh_fundamentals}, earnings:{fresh_earnings}, news:{fresh_news}")
            else:
                logger.debug(f"{symbol} has no fresh data since {last_analysis.strftime('%Y-%m-%d %H:%M')}")

            return has_fresh

        except Exception as e:
            logger.warning(f"Error checking fresh data for {symbol}: {e}")
            # Default to allowing analysis if we can't check fresh data
            return True

    async def _has_fresh_fundamentals(self, symbol: str, last_analysis: datetime) -> bool:
        """Check if fundamentals data is fresh."""
        try:
            fundamentals = await self.config_state.get_fundamental_analysis(symbol)
            if fundamentals:
                # Check if fundamentals were updated after last analysis
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
            earnings = await self.config_state.get_earnings_reports(symbol)
            if earnings:
                # Check if any earnings were reported after last analysis
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
            news = await self.config_state.get_news_items(symbol)
            if news:
                # Check if any news was published after last analysis
                for news_item in news if isinstance(news, list) else [news]:
                    news_date = news_item.get("published_at") or news_item.get("created_at")
                    if news_date:
                        if isinstance(news_date, str):
                            news_date = datetime.fromisoformat(news_date.replace('Z', '+00:00'))
                        return news_date > last_analysis
            return False
        except Exception:
            return False

    def _log_info(self, message: str) -> None:
        """Log info message."""
        logger.info(f"[PortfolioAnalysisCoordinator] {message}")
