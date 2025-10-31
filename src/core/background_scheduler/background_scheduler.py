"""Background scheduler with event-driven architecture.

Facade that coordinates event handlers and triggers for reactive task scheduling.
Maintains core scheduler lifecycle (start, stop) and execution tracking.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time, timezone

from ...core.event_bus import EventBus, Event, EventType
from ...services.scheduler.task_service import SchedulerTaskService
from .stores.task_store import TaskStore
from .stores.stock_state_store import StockStateStore
from .stores.strategy_log_store import StrategyLogStore
from .monitors.monthly_reset_monitor import MonthlyResetMonitor
from .event_handlers import EventHandlers
from .triggers import Triggers

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Event-driven background scheduler facade.

    Manages scheduler lifecycle, event subscription, and delegates event handling
    and trigger logic to specialized modules.
    """

    def __init__(self, task_service: SchedulerTaskService, event_bus: EventBus, db_connection, config=None, execution_tracker=None):
        """Initialize event-driven background scheduler.

        Args:
            task_service: SchedulerTaskService for task creation
            event_bus: EventBus for event subscription
            db_connection: Database connection for stores
            config: Configuration object
            execution_tracker: ExecutionTracker for recording executions
        """
        self.task_service = task_service
        self.event_bus = event_bus
        self.db = db_connection
        self.config = config

        # Database stores
        self.task_store = TaskStore(db_connection)
        self.stock_state_store = StockStateStore(db_connection)
        self.strategy_log_store = StrategyLogStore(db_connection)

        # Monitors
        self.monthly_reset_monitor = MonthlyResetMonitor(self.config)

        # Execution state
        self._running = False
        self._event_listener_task: Optional[asyncio.Task] = None

        # Execution tracker (injected from DI)
        self.execution_tracker = execution_tracker

        # Schedule configuration
        self.market_open_time = time(9, 30)  # 9:30 AM EST
        self.market_close_time = time(16, 0)  # 4:00 PM EST

        # Initialize modular handlers and triggers
        self.event_handlers = EventHandlers(task_service, self.stock_state_store)
        self.triggers = Triggers(
            task_service,
            self.monthly_reset_monitor,
            self.market_open_time,
            self.market_close_time
        )

        # Register event handlers
        self._setup_event_handlers()

    async def record_execution(self, task_name: str, task_id: str = "", execution_type: str = "scheduled", user: str = "system", symbols: list = None, status: str = "completed", error_message: str = None, execution_time: float = None) -> None:
        """Record any execution (manual or scheduled) for tracking."""
        if self.execution_tracker:
            await self.execution_tracker.record_execution(
                task_name=task_name,
                task_id=task_id,
                execution_type=execution_type,
                user=user,
                symbols=symbols,
                status=status,
                error_message=error_message,
                execution_time=execution_time
            )
        else:
            # Fallback to old internal tracking if tracker not available
            logger.warning("Execution tracker not available, using fallback tracking")
            execution_record = {
                "task_name": task_name,
                "task_id": task_id,
                "execution_type": execution_type,
                "user": user,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbols": symbols or [],
                "symbol_count": len(symbols) if symbols else 0,
                "status": status,
                "error_message": error_message,
                "execution_time_seconds": execution_time
            }

            if not hasattr(self, 'execution_history'):
                self.execution_history = []
                self.max_execution_history = 10

            self.execution_history.insert(0, execution_record)
            if len(self.execution_history) > self.max_execution_history:
                self.execution_history = self.execution_history[:self.max_execution_history]

    async def record_manual_execution(self, task_name: str, task_id: str, user: str = "user") -> None:
        """Record a manual execution for tracking."""
        await self.record_execution(task_name, task_id, "manual", user)

    async def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get execution history from the tracker."""
        if self.execution_tracker:
            return await self.execution_tracker.get_execution_history(limit)
        else:
            # Fallback to internal history
            return getattr(self, 'execution_history', [])[:limit]

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for reactive scheduling."""
        # Portfolio events trigger data fetching
        self.event_bus.subscribe(
            EventType.PORTFOLIO_POSITION_CHANGE,
            lambda event: self._create_async_handler(
                self.event_handlers.handle_portfolio_updated, event, self._get_portfolio_symbols
            )
        )

        # Market events trigger re-analysis
        self.event_bus.subscribe(
            EventType.MARKET_NEWS,
            lambda event: self._create_async_handler(self.event_handlers.handle_market_news, event)
        )

    async def start(self) -> None:
        """Start the event-driven background scheduler."""
        if self._running:
            return

        logger.info("Starting event-driven background scheduler...")
        self._running = True

        # Initialize stores
        await self.stock_state_store.initialize()
        await self.strategy_log_store.initialize()

        # Initialize monitors
        await self.monthly_reset_monitor.initialize()

        # Start event listener
        self._event_listener_task = asyncio.create_task(self._event_listener())

        # Schedule daily routines
        await self._schedule_daily_routines()

        logger.info("Event-driven background scheduler started")

    async def stop(self) -> None:
        """Stop the event-driven background scheduler."""
        if not self._running:
            return

        logger.info("Stopping event-driven background scheduler...")
        self._running = False

        # Cancel event listener
        if self._event_listener_task and not self._event_listener_task.done():
            self._event_listener_task.cancel()
            try:
                await self._event_listener_task
            except asyncio.CancelledError:
                pass

        logger.info("Event-driven background scheduler stopped")

    async def _event_listener(self) -> None:
        """Main event listener loop."""
        logger.info("Event listener started")

        while self._running:
            try:
                # Process events (this would be handled by event bus polling)
                await asyncio.sleep(1)  # Keep alive
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                await asyncio.sleep(5)

    def _create_async_handler(self, handler, event: Event, *args):
        """Create async handler wrapper for event subscription.

        Args:
            handler: Async handler function
            event: Event to pass to handler
            *args: Additional arguments for handler
        """
        return asyncio.create_task(handler(event, *args) if args else handler(event))

    async def _schedule_daily_routines(self) -> None:
        """Schedule daily market routines."""
        await self.triggers.schedule_daily_routines()

    async def _run_morning_routine(self) -> None:
        """Run morning market open routine."""
        await self.triggers.run_morning_routine(self._get_portfolio_symbols)

    async def _run_evening_routine(self) -> None:
        """Run evening market close routine."""
        await self.triggers.run_evening_routine()

    async def _get_portfolio_symbols(self) -> list:
        """Get all symbols from portfolio."""
        # This would query the portfolio service
        # For now, return empty list - would be implemented based on portfolio service
        return []

    def is_market_open_time(self, current_time: time) -> bool:
        """Check if current time is market open.

        Args:
            current_time: Time to check

        Returns:
            True if within market open hour
        """
        return self.triggers.is_market_open_time(current_time)

    def is_market_close_time(self, current_time: time) -> bool:
        """Check if current time is market close.

        Args:
            current_time: Time to check

        Returns:
            True if within market close hour
        """
        return self.triggers.is_market_close_time(current_time)

    @staticmethod
    def is_weekday(dt: datetime) -> bool:
        """Check if given datetime is a weekday (Monday-Friday).

        Args:
            dt: Datetime to check

        Returns:
            True if weekday (Monday=0 through Friday=4)
        """
        return Triggers.is_weekday(dt)

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "event_driven": True,
            "market_open_time": self.market_open_time.isoformat(),
            "market_close_time": self.market_close_time.isoformat()
        }

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get detailed scheduler status for system health monitoring."""
        try:
            # Calculate uptime
            uptime_seconds = 0
            if hasattr(self, '_start_time') and self._start_time:
                uptime_seconds = int((datetime.now(timezone.utc) - self._start_time).total_seconds())

            # Get execution history from tracker (get more to calculate stats)
            execution_history = await self.get_execution_history(100)  # Get more for accurate stats
            total_executions = len(execution_history)

            # Calculate processed/failed counts from execution history
            tasks_processed = 0
            tasks_failed = 0

            # Count completed and failed executions
            for execution in execution_history:
                if isinstance(execution, dict):
                    status = execution.get("status", "").lower()
                    if status == "completed":
                        tasks_processed += 1
                    elif status == "failed":
                        tasks_failed += 1

            # Get last run time (most recent execution)
            last_run_time = ""
            if execution_history and len(execution_history) > 0:
                first_execution = execution_history[0]
                if isinstance(first_execution, dict):
                    last_run_time = first_execution.get("timestamp", datetime.now(timezone.utc).isoformat())
                else:
                    last_run_time = datetime.now(timezone.utc).isoformat()
            else:
                last_run_time = datetime.now(timezone.utc).isoformat()

            # Return only the 10 most recent executions for display
            recent_executions = execution_history[:10] if execution_history else []

            return {
                "running": self._running,
                "event_driven": True,
                "last_run_time": last_run_time,
                "uptime_seconds": uptime_seconds,
                "tasks_processed": tasks_processed,
                "tasks_failed": tasks_failed,
                "execution_history": recent_executions,
                "total_executions": total_executions,
                "market_open_time": self.market_open_time.isoformat(),
                "market_close_time": self.market_close_time.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            # Fallback to internal history on error
            fallback_history = getattr(self, 'execution_history', [])
            return {
                "running": self._running,
                "event_driven": True,
                "last_run_time": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": 0,
                "tasks_processed": 0,
                "tasks_failed": 0,
                "execution_history": fallback_history,
                "total_executions": len(fallback_history),
                "error": str(e)
            }

    async def trigger_manual_execution(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Manually trigger event-based execution."""
        event = Event(
            event_type=EventType(event_type),
            data=event_data,
            source="manual_trigger"
        )
        await self.event_bus.publish(event)