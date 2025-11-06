"""Event handler implementations for background scheduler.

Handles reactive scheduling based on domain events from the event bus.
"""

import logging
from typing import List

from ...core.event_bus import Event
from ...models.scheduler import QueueName, TaskType
from ...services.scheduler.task_service import SchedulerTaskService
from .stores.stock_state_store import StockStateStore

logger = logging.getLogger(__name__)


class EventHandlers:
    """Event handler implementations for background scheduler."""

    def __init__(
        self, task_service: SchedulerTaskService, stock_state_store: StockStateStore
    ):
        """Initialize event handlers.

        Args:
            task_service: SchedulerTaskService for creating tasks
            stock_state_store: StockStateStore for managing stock state
        """
        self.task_service = task_service
        self.stock_state_store = stock_state_store

    async def handle_portfolio_updated(
        self, event: Event, get_portfolio_symbols
    ) -> None:
        """Handle portfolio update events.

        Args:
            event: Portfolio update event
            get_portfolio_symbols: Callable to get portfolio symbols
        """
        logger.info(
            "Portfolio updated, triggering portfolio sync and data fetch sequence"
        )

        # Get all symbols from portfolio
        symbols = await get_portfolio_symbols()

        # Trigger portfolio synchronization
        await self._trigger_portfolio_sync()

        # Trigger sequential data fetching
        await self._trigger_data_fetch_sequence(symbols)

    async def handle_stock_added(self, event: Event) -> None:
        """Handle stock addition events.

        Args:
            event: Stock added event
        """
        symbol = event.data.get("symbol")
        if symbol:
            logger.info(f"Stock {symbol} added, triggering initial data fetch")
            await self._trigger_initial_data_fetch([symbol])

    async def handle_stock_removed(self, event: Event) -> None:
        """Handle stock removal events.

        Args:
            event: Stock removed event
        """
        symbol = event.data.get("symbol")
        if symbol:
            logger.info(f"Stock {symbol} removed, cleaning up state")
            # Clean up stock state if needed

    async def handle_news_fetched(self, event: Event) -> None:
        """Handle news fetch completion.

        Args:
            event: News fetched event
        """
        symbol = event.data.get("symbol")
        if symbol:
            logger.info(f"News fetched for {symbol}, triggering AI analysis")
            await self._trigger_ai_analysis(symbol, "news")

    async def handle_earnings_fetched(self, event: Event) -> None:
        """Handle earnings fetch completion.

        Args:
            event: Earnings fetched event
        """
        symbol = event.data.get("symbol")
        if symbol:
            logger.info(f"Earnings fetched for {symbol}, triggering AI analysis")
            await self._trigger_ai_analysis(symbol, "earnings")

    async def handle_fundamentals_updated(self, event: Event) -> None:
        """Handle fundamentals update completion.

        Args:
            event: Fundamentals updated event
        """
        symbol = event.data.get("symbol")
        if symbol:
            logger.info(f"Fundamentals updated for {symbol}, triggering AI analysis")
            await self._trigger_ai_analysis(symbol, "fundamentals")

    async def handle_market_news(self, event: Event) -> None:
        """Handle significant market news.

        Args:
            event: Market news event
        """
        symbol = event.data.get("symbol")
        impact_score = event.data.get("impact_score", 0)

        if symbol and impact_score > 0.7:
            logger.info(f"High-impact news for {symbol}, flagging for recheck")
            await self.stock_state_store.flag_fundamentals_recheck(symbol)

    async def _trigger_portfolio_sync(self) -> None:
        """Trigger portfolio synchronization tasks."""
        logger.info("Triggering portfolio synchronization")

        # Create portfolio sync tasks
        await self.task_service.create_task(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_type=TaskType.SYNC_ACCOUNT_BALANCES,
            payload={"scheduled": True},
            priority=10,  # High priority
        )

        await self.task_service.create_task(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_type=TaskType.UPDATE_POSITIONS,
            payload={"scheduled": True},
            priority=9,
        )

        await self.task_service.create_task(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_type=TaskType.VALIDATE_PORTFOLIO_RISKS,
            payload={"scheduled": True},
            priority=8,
        )

    async def _trigger_data_fetch_sequence(self, symbols: List[str]) -> None:
        """Trigger sequential data fetching for symbols.

        Args:
            symbols: List of stock symbols
        """
        # Select the 5 oldest stocks for each scheduler type (oldest last_run date first)
        news_stocks = await self.stock_state_store.get_oldest_news_stocks(
            symbols, limit=5
        )
        earnings_stocks = await self.stock_state_store.get_oldest_earnings_stocks(
            symbols, limit=5
        )
        fundamentals_stocks = (
            await self.stock_state_store.get_oldest_fundamentals_stocks(
                symbols, limit=5
            )
        )

        # Create tasks for data fetching with prioritized stocks
        if news_stocks:
            await self.task_service.create_task(
                queue_name=QueueName.DATA_FETCHER,
                task_type=TaskType.NEWS_MONITORING,
                payload={"symbols": news_stocks, "scheduled": True},
                priority=6,
            )

        if earnings_stocks:
            await self.task_service.create_task(
                queue_name=QueueName.DATA_FETCHER,
                task_type=TaskType.EARNINGS_SCHEDULER,
                payload={"symbols": earnings_stocks, "scheduled": True},
                priority=7,
            )

        if fundamentals_stocks:
            await self.task_service.create_task(
                queue_name=QueueName.DATA_FETCHER,
                task_type=TaskType.FUNDAMENTALS_UPDATE,
                payload={"symbols": fundamentals_stocks, "scheduled": True},
                priority=7,
            )

    async def _trigger_initial_data_fetch(self, symbols: List[str]) -> None:
        """Trigger initial data fetch for new symbols.

        Args:
            symbols: List of stock symbols
        """
        await self.task_service.create_task(
            queue_name=QueueName.DATA_FETCHER,
            task_type=TaskType.EARNINGS_SCHEDULER,
            payload={"symbols": symbols, "initial_fetch": True},
            priority=9,
        )

    async def _trigger_ai_analysis(self, symbol: str, trigger_type: str) -> None:
        """Trigger AI analysis for a symbol.

        Args:
            symbol: Stock symbol
            trigger_type: Type of trigger (news, earnings, fundamentals)
        """
        task_type_map = {
            "news": TaskType.CLAUDE_NEWS_ANALYSIS,
            "earnings": TaskType.CLAUDE_EARNINGS_REVIEW,
            "fundamentals": TaskType.CLAUDE_FUNDAMENTAL_ANALYSIS,
        }

        task_type = task_type_map.get(trigger_type, TaskType.CLAUDE_NEWS_ANALYSIS)

        await self.task_service.create_task(
            queue_name=QueueName.AI_ANALYSIS,
            task_type=task_type,
            payload={"symbol": symbol, "trigger": trigger_type, "scheduled": True},
            priority=8,
        )
