"""Scheduled trigger implementations for background scheduler.

Handles periodic and time-based task scheduling (morning, evening routines, etc.).
Uses EventBus to publish MARKET_OPEN/MARKET_CLOSE events for token-efficient Claude sessions.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, time, timezone

from ...core.event_bus import EventBus, Event, EventType
from ...models.scheduler import QueueName, TaskType
from ...services.scheduler.task_service import SchedulerTaskService
from .monitors.monthly_reset_monitor import MonthlyResetMonitor

logger = logging.getLogger(__name__)


class Triggers:
    """Scheduled trigger implementations for background scheduler."""

    def __init__(
        self,
        task_service: SchedulerTaskService,
        monthly_reset_monitor: MonthlyResetMonitor,
        market_open_time: time,
        market_close_time: time,
        event_bus: Optional[EventBus] = None
    ):
        """Initialize trigger handlers.

        Args:
            task_service: SchedulerTaskService for creating tasks
            monthly_reset_monitor: MonthlyResetMonitor for monthly resets
            market_open_time: Market open time
            market_close_time: Market close time
            event_bus: EventBus for publishing market events
        """
        self.task_service = task_service
        self.monthly_reset_monitor = monthly_reset_monitor
        self.market_open_time = market_open_time
        self.market_close_time = market_close_time
        self.event_bus = event_bus

    async def run_morning_routine(self, get_portfolio_symbols) -> None:
        """Run morning market open routine.

        Publishes MARKET_OPEN event for ClaudeAgentService to handle.
        This is more token-efficient than creating task queue entries.

        Args:
            get_portfolio_symbols: Callable to get portfolio symbols
        """
        logger.info("Running morning routine - publishing MARKET_OPEN event")

        # Trigger portfolio synchronization first
        await self._trigger_portfolio_sync()

        # Publish MARKET_OPEN event for ClaudeAgentService
        if self.event_bus:
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.MARKET_OPEN,
                source="triggers",
                data={"scheduled": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
            logger.info("MARKET_OPEN event published - ClaudeAgentService will handle morning prep")
        else:
            logger.warning("EventBus not available - cannot publish MARKET_OPEN event")

    async def run_evening_routine(self) -> None:
        """Run evening market close routine.

        Publishes MARKET_CLOSE event for ClaudeAgentService to handle.
        This is more token-efficient than creating task queue entries.
        """
        logger.info("Running evening routine - publishing MARKET_CLOSE event")

        # Publish MARKET_CLOSE event for ClaudeAgentService
        if self.event_bus:
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.MARKET_CLOSE,
                source="triggers",
                data={"scheduled": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
            logger.info("MARKET_CLOSE event published - ClaudeAgentService will handle evening review")
        else:
            logger.warning("EventBus not available - cannot publish MARKET_CLOSE event")

        # Check for monthly reset
        await self.check_monthly_reset()

    async def schedule_daily_routines(self) -> None:
        """Schedule daily market routines.

        Skip running routines during startup to avoid database conflicts.
        Routines will be triggered by scheduled timers or manual triggers.
        """
        logger.info("Daily routines scheduling initialized (routines will run on schedule)")

    async def check_monthly_reset(self) -> None:
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

    def is_market_open_time(self, current_time: time) -> bool:
        """Check if current time is market open.

        Args:
            current_time: Time to check

        Returns:
            True if within market open hour
        """
        return self.market_open_time <= current_time <= self.market_open_time.replace(
            hour=self.market_open_time.hour + 1
        )

    def is_market_close_time(self, current_time: time) -> bool:
        """Check if current time is market close.

        Args:
            current_time: Time to check

        Returns:
            True if within market close hour
        """
        return self.market_close_time.replace(
            hour=self.market_close_time.hour - 1
        ) <= current_time <= self.market_close_time

    @staticmethod
    def is_weekday(dt: datetime) -> bool:
        """Check if given datetime is a weekday (Monday-Friday).

        Args:
            dt: Datetime to check

        Returns:
            True if weekday (Monday=0 through Friday=4)
        """
        return dt.weekday() < 5  # 0=Monday, 4=Friday

    async def _trigger_portfolio_sync(self) -> None:
        """Trigger portfolio synchronization tasks."""
        logger.info("Triggering portfolio synchronization")

        # Create portfolio sync tasks
        await self.task_service.create_task(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_type=TaskType.SYNC_ACCOUNT_BALANCES,
            payload={"scheduled": True},
            priority=10  # High priority
        )

        await self.task_service.create_task(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_type=TaskType.UPDATE_POSITIONS,
            payload={"scheduled": True},
            priority=9
        )

        await self.task_service.create_task(
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_type=TaskType.VALIDATE_PORTFOLIO_RISKS,
            payload={"scheduled": True},
            priority=8
        )
