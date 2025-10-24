"""Background scheduler with event-driven architecture."""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, time

from ...core.event_bus import EventBus, Event, EventType
from ...services.scheduler.task_service import SchedulerTaskService
from ...models.scheduler import QueueName, TaskType
from .stores.task_store import TaskStore
from .stores.stock_state_store import StockStateStore
from .stores.strategy_log_store import StrategyLogStore
from .monitors.monthly_reset_monitor import MonthlyResetMonitor

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Event-driven background scheduler with database storage."""

    def __init__(self, task_service: SchedulerTaskService, event_bus: EventBus, db_connection, config=None):
        """Initialize event-driven background scheduler."""
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

        # Schedule configuration
        self.market_open_time = time(9, 30)  # 9:30 AM EST
        self.market_close_time = time(16, 0)  # 4:00 PM EST

        # Register event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for reactive scheduling."""
        # Portfolio events trigger data fetching
        self.event_bus.subscribe(EventType.PORTFOLIO_POSITION_CHANGE, self._handle_portfolio_updated)
        # Note: STOCK_ADDED and STOCK_REMOVED events don't exist in current EventType enum
        # self.event_bus.subscribe(EventType.STOCK_ADDED, self._handle_stock_added)
        # self.event_bus.subscribe(EventType.STOCK_REMOVED, self._handle_stock_removed)

        # Data fetch completion triggers AI analysis - these events don't exist yet
        # self.event_bus.subscribe(EventType.NEWS_FETCHED, self._handle_news_fetched)
        # self.event_bus.subscribe(EventType.EARNINGS_FETCHED, self._handle_earnings_fetched)
        # self.event_bus.subscribe(EventType.FUNDAMENTALS_UPDATED, self._handle_fundamentals_updated)

        # Market events trigger re-analysis
        self.event_bus.subscribe(EventType.MARKET_NEWS, self._handle_market_news)

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

    async def _handle_portfolio_updated(self, event: Event) -> None:
        """Handle portfolio update events."""
        logger.info("Portfolio updated, triggering data fetch sequence")

        # Get all symbols from portfolio
        symbols = await self._get_portfolio_symbols()

        # Trigger sequential data fetching
        await self._trigger_data_fetch_sequence(symbols)

    async def _handle_stock_added(self, event: Event) -> None:
        """Handle stock addition events."""
        symbol = event.data.get('symbol')
        if symbol:
            logger.info(f"Stock {symbol} added, triggering initial data fetch")
            await self._trigger_initial_data_fetch([symbol])

    async def _handle_stock_removed(self, event: Event) -> None:
        """Handle stock removal events."""
        symbol = event.data.get('symbol')
        if symbol:
            logger.info(f"Stock {symbol} removed, cleaning up state")
            # Clean up stock state if needed

    async def _handle_news_fetched(self, event: Event) -> None:
        """Handle news fetch completion."""
        symbol = event.data.get('symbol')
        if symbol:
            logger.info(f"News fetched for {symbol}, triggering AI analysis")
            await self._trigger_ai_analysis(symbol, "news")

    async def _handle_earnings_fetched(self, event: Event) -> None:
        """Handle earnings fetch completion."""
        symbol = event.data.get('symbol')
        if symbol:
            logger.info(f"Earnings fetched for {symbol}, triggering AI analysis")
            await self._trigger_ai_analysis(symbol, "earnings")

    async def _handle_fundamentals_updated(self, event: Event) -> None:
        """Handle fundamentals update completion."""
        symbol = event.data.get('symbol')
        if symbol:
            logger.info(f"Fundamentals updated for {symbol}, triggering AI analysis")
            await self._trigger_ai_analysis(symbol, "fundamentals")

    async def _handle_market_news(self, event: Event) -> None:
        """Handle significant market news."""
        symbol = event.data.get('symbol')
        impact_score = event.data.get('impact_score', 0)

        if symbol and impact_score > 0.7:
            logger.info(f"High-impact news for {symbol}, flagging for recheck")
            await self.stock_state_store.flag_fundamentals_recheck(symbol)

    async def _trigger_data_fetch_sequence(self, symbols: list) -> None:
        """Trigger sequential data fetching for symbols."""
        # Check which symbols need data fetching based on per-stock state
        news_needed = await self.stock_state_store.get_stocks_needing_news(symbols)
        earnings_needed = await self.stock_state_store.get_stocks_needing_earnings(symbols)
        fundamentals_needed = []

        # Check for fundamentals recheck flags
        for symbol in symbols:
            if await self.stock_state_store.needs_fundamentals_check(symbol):
                fundamentals_needed.append(symbol)

        # Create tasks for data fetching
        if news_needed:
            await self.task_service.create_task(
                queue_name=QueueName.DATA_FETCHER,
                task_type=TaskType.NEWS_MONITORING,
                payload={"symbols": news_needed, "scheduled": True},
                priority=6
            )

        if earnings_needed:
            await self.task_service.create_task(
                queue_name=QueueName.DATA_FETCHER,
                task_type=TaskType.EARNINGS_SCHEDULER,
                payload={"symbols": earnings_needed, "scheduled": True},
                priority=7
            )

        if fundamentals_needed:
            await self.task_service.create_task(
                queue_name=QueueName.DATA_FETCHER,
                task_type=TaskType.FUNDAMENTALS_CHECKER,
                payload={"symbols": fundamentals_needed, "scheduled": True},
                priority=7
            )

    async def _trigger_initial_data_fetch(self, symbols: list) -> None:
        """Trigger initial data fetch for new symbols."""
        await self.task_service.create_task(
            queue_name=QueueName.DATA_FETCHER,
            task_type=TaskType.EARNINGS_SCHEDULER,
            payload={"symbols": symbols, "initial_fetch": True},
            priority=9
        )

    async def _trigger_ai_analysis(self, symbol: str, trigger_type: str) -> None:
        """Trigger AI analysis for a symbol."""
        task_type_map = {
            "news": TaskType.CLAUDE_NEWS_ANALYSIS,
            "earnings": TaskType.CLAUDE_EARNINGS_REVIEW,
            "fundamentals": TaskType.CLAUDE_FUNDAMENTAL_ANALYSIS
        }

        task_type = task_type_map.get(trigger_type, TaskType.CLAUDE_NEWS_ANALYSIS)

        await self.task_service.create_task(
            queue_name=QueueName.AI_ANALYSIS,
            task_type=task_type,
            payload={"symbol": symbol, "trigger": trigger_type, "scheduled": True},
            priority=8
        )

    async def _schedule_daily_routines(self) -> None:
        """Schedule daily market routines."""
        now = datetime.utcnow()
        current_time = now.time()

        # Morning routine
        if self._is_market_open_time(current_time) and self._is_weekday(now):
            await self._run_morning_routine()

        # Evening routine
        elif self._is_market_close_time(current_time) and self._is_weekday(now):
            await self._run_evening_routine()

    async def _run_morning_routine(self) -> None:
        """Run morning market open routine."""
        logger.info("Running morning routine")

        # Get all portfolio symbols
        symbols = await self._get_portfolio_symbols()

        # Trigger morning analysis
        await self.task_service.create_task(
            queue_name=QueueName.AI_ANALYSIS,
            task_type=TaskType.CLAUDE_MORNING_PREP,
            payload={"symbols": symbols, "scheduled": True},
            priority=9
        )

    async def _run_evening_routine(self) -> None:
        """Run evening market close routine."""
        logger.info("Running evening routine")

        # Trigger evening review
        await self.task_service.create_task(
            queue_name=QueueName.AI_ANALYSIS,
            task_type=TaskType.CLAUDE_EVENING_REVIEW,
            payload={"scheduled": True},
            priority=8
        )

        # Check for monthly reset
        await self._check_monthly_reset()

    async def _get_portfolio_symbols(self) -> list:
        """Get all symbols from portfolio."""
        # This would query the portfolio service
        # For now, return empty list - would be implemented based on portfolio service
        return []

    def _is_market_open_time(self, current_time: time) -> bool:
        """Check if current time is market open."""
        return self.market_open_time <= current_time <= self.market_open_time.replace(hour=self.market_open_time.hour + 1)

    def _is_market_close_time(self, current_time: time) -> bool:
        """Check if current time is market close."""
        return self.market_close_time.replace(hour=self.market_close_time.hour - 1) <= current_time <= self.market_close_time

    def _is_weekday(self, dt: datetime) -> bool:
        """Check if given datetime is a weekday (Monday-Friday)."""
        return dt.weekday() < 5  # 0=Monday, 4=Friday

    async def _check_monthly_reset(self) -> None:
        """Check and execute monthly performance reset if needed."""
        try:
            # Get paper trading account manager from container
            from ...core.di import get_container
            container = await get_container()
            if not container:
                logger.warning("Container not available for monthly reset check")
                return

            account_manager = await container.get("paper_trading_account_manager")
            if not account_manager:
                logger.warning("Paper trading account manager not available for monthly reset")
                return

            # Get current balances and closed trades for both account types
            swing_balance = await account_manager.get_balance("swing")
            options_balance = await account_manager.get_balance("options")

            swing_trades = await account_manager.get_closed_trades("swing")
            options_trades = await account_manager.get_closed_trades("options")

            # Check for monthly reset (framework exists, needs activation)
            initial_balance = 100000  # ₹1,00,000

            # Check swing account reset
            swing_reset = await self.monthly_reset_monitor.check_and_execute_reset(
                account_manager, swing_balance, initial_balance, swing_trades, "swing"
            )

            # Check options account reset
            options_reset = await self.monthly_reset_monitor.check_and_execute_reset(
                account_manager, options_balance, initial_balance, options_trades, "options"
            )

            if swing_reset or options_reset:
                logger.info("Monthly performance reset executed")
                # Could emit event here for UI notification

        except Exception as e:
            logger.error(f"Error during monthly reset check: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "event_driven": True,
            "market_open_time": self.market_open_time.isoformat(),
            "market_close_time": self.market_close_time.isoformat()
        }

    async def trigger_manual_execution(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Manually trigger event-based execution."""
        event = Event(
            event_type=EventType(event_type),
            data=event_data,
            source="manual_trigger"
        )
        await self.event_bus.publish(event)