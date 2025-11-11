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
from src.models.scheduler import QueueName

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

            # Mark complete only after first successful iteration (happens in monitoring loop)
            logger.info("Portfolio Analysis Coordinator initialized successfully")

        except Exception as e:
            self._initialized = False
            self._initialization_error = e
            self._initialization_error_traceback = traceback.format_exc()
            self._log_init_step("Portfolio Analysis Coordinator initialization", success=False, error=e)
            raise RuntimeError(f"Portfolio Analysis Coordinator initialization failed: {e}") from e

    def _log_init_step(self, step: str, success: bool = True, error: Optional[Exception] = None) -> None:
        """Log initialization step to stdout and logger."""
        if success:
            msg = f"[INIT] {step}"
            print(f"*** {msg} - OK ***")  # Print to stdout
            logger.info(msg)
        else:
            msg = f"[INIT FAILED] {step}"
            print(f"*** {msg}: {error} ***")
            logger.error(f"{msg}: {error}")
            if error:
                tb = traceback.format_exc()
                print(f"*** TRACEBACK: {tb} ***")
                logger.error(f"Traceback: {tb}")

    async def _monitoring_loop(self) -> None:
        """Run the portfolio analysis monitoring loop."""
        retry_delay = 60  # Retry after 60 seconds on error

        while True:
            try:
                # Wait for interval before checking
                await asyncio.sleep(self._check_interval)

                # Run portfolio analysis check
                await self._run_portfolio_analysis_check()

                # Mark initialization complete after first successful iteration
                if not self._initialization_complete:
                    self._log_init_step("First monitoring iteration completed successfully")
                    self._initialization_complete = True

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

                # Priority 2: Analysis is stale
                else:
                    last_analysis = analyzed_symbols[symbol]
                    age = now - last_analysis
                    if age > min_interval:
                        stocks_with_priority.append({
                            "symbol": symbol,
                            "priority": 5,
                            "reason": "stale_analysis",
                            "age_hours": age.total_seconds() / 3600
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
                queue_name=QueueName.AI_ANALYSIS,
                limit=1000  # Get all pending tasks
            )

            symbols_in_queue = set()
            for task in pending_tasks:
                try:
                    # Extract symbols from task payload
                    payload = task.payload
                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    symbols = payload.get("symbols", [])
                    if symbols:
                        symbols_in_queue.add(symbols[0])  # Only one symbol per task
                except Exception as e:
                    logger.debug(f"Failed to extract symbols from task {task.task_id}: {e}")
                    continue

            return symbols_in_queue

        except Exception as e:
            logger.warning(f"Failed to get symbols in queue, assuming empty: {e}")
            return set()  # Assume empty to allow monitoring to continue

    async def _queue_analysis_tasks(self, stocks: List[Dict[str, Any]]) -> None:
        """Queue analysis tasks for selected stocks.

        Args:
            stocks: List of stocks with priority and reason
        """
        for stock in stocks:
            try:
                symbol = stock["symbol"]
                priority = stock["priority"]
                reason = stock["reason"]

                # Create analysis task
                task = await self.task_service.create_task(
                    queue_name=QueueName.AI_ANALYSIS,
                    task_type="RECOMMENDATION_GENERATION",
                    payload={
                        "agent_name": "scan",
                        "symbols": [symbol]
                    },
                    priority=priority
                )

                self._log_info(
                    f"Queued analysis task for {symbol} "
                    f"(priority={priority}, reason={reason}, task_id={task.task_id})"
                )

            except Exception as e:
                logger.error(f"Failed to queue analysis for {stock.get('symbol')}: {e}", exc_info=True)
                # Continue with next stock on failure

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

    def _log_info(self, message: str) -> None:
        """Log info message."""
        logger.info(f"[PortfolioAnalysisCoordinator] {message}")
