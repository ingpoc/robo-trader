"""
Background Scheduler Facade.

Coordinates all background scheduler components with unified public API.
"""

import asyncio
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Any, Callable

from loguru import logger

from .models import TaskType, TaskPriority, BackgroundTask
from .core import TaskScheduler
from .stores import TaskStore
from .clients import PerplexityClient, APIKeyRotator
from .processors import EarningsProcessor, NewsProcessor, FundamentalAnalyzer
from .monitors import MarketMonitor, RiskMonitor, HealthMonitor
from .config import TaskConfigManager
from .events import EventHandler
from .executors import FundamentalExecutor


class BackgroundScheduler:
    """Facade coordinating all background scheduling components."""

    def __init__(self, config, state_manager, orchestrator=None):
        """Initialize Background Scheduler.

        Args:
            config: Configuration object
            state_manager: Database state manager
            orchestrator: Optional orchestrator for callbacks
        """
        self.config = config
        self.state_manager = state_manager
        self.orchestrator = orchestrator

        self.task_scheduler = TaskScheduler(
            config.state_dir,
            max_concurrent_tasks=3,
            task_timeout_seconds=300
        )

        self.config_manager = TaskConfigManager()
        self.event_handler = EventHandler()

        self.perplexity_client = PerplexityClient()
        self.earnings_processor = EarningsProcessor()
        self.news_processor = NewsProcessor()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.fundamental_executor = None

        self.market_monitor = MarketMonitor()
        self.risk_monitor = RiskMonitor(state_manager, None)
        self.health_monitor = HealthMonitor()
        self.health_monitor.set_state_manager(state_manager)

        self.is_running = False
        self.market_open = False
        self.last_market_check = datetime.now(timezone.utc)

        self._callback_registry = {
            '_run_portfolio_scan': None,
            '_run_market_screening': None,
            '_ai_planner_create_plan': None,
            '_orchestrator_get_claude_status': None
        }

        self._setup_component_handlers()
        self._setup_event_handlers()

    def _setup_component_handlers(self) -> None:
        """Setup handlers between components."""
        self.task_scheduler.set_task_logic_handler(self._execute_task_logic)
        self.task_scheduler.set_task_failure_handler(self._handle_task_failure)

        self.market_monitor.set_market_open_callback(self._on_market_open)
        self.market_monitor.set_market_close_callback(self._on_market_close)

        if self._callback_registry['_orchestrator_get_claude_status']:
            self.health_monitor.set_claude_status_callback(
                self._callback_registry['_orchestrator_get_claude_status']
            )

    def _setup_event_handlers(self) -> None:
        """Setup event handler registrations."""
        self.event_handler.register_handler("market_open", self._handle_market_open_event)
        self.event_handler.register_handler("market_close", self._handle_market_close_event)
        self.event_handler.register_handler("earnings_announced", self._handle_earnings_event)
        self.event_handler.register_handler("stop_loss_triggered", self._handle_stop_loss_event)
        self.event_handler.register_handler("news_alert", self._handle_news_event)
        self.event_handler.register_handler("price_movement", self._handle_price_movement_event)

    def register_callback(self, callback_name: str, callback: Callable) -> None:
        """Register callback for task execution.

        Args:
            callback_name: Name of callback
            callback: Async callable
        """
        if callback_name in self._callback_registry:
            self._callback_registry[callback_name] = callback
            if callback_name == '_orchestrator_get_claude_status':
                self.health_monitor.set_claude_status_callback(callback)
        else:
            logger.warning(f"Unknown callback: {callback_name}")

    # Public API Methods

    async def start(self) -> List[asyncio.Task]:
        """Start the background scheduler.

        Returns:
            List of background tasks
        """
        if self.is_running:
            return []

        logger.info("Starting Background Scheduler")
        self.is_running = True

        await self.task_scheduler.load_tasks()
        await self._schedule_default_tasks()

        scheduling_task = asyncio.create_task(self._scheduling_loop())
        monitoring_task = asyncio.create_task(self._market_monitoring_loop())

        logger.info("Background Scheduler started successfully")
        return [scheduling_task, monitoring_task]

    async def stop(self) -> None:
        """Stop the background scheduler."""
        logger.info("Stopping Background Scheduler")
        self.is_running = False
        await self.task_scheduler.cancel_all_running_tasks()
        logger.info("Background Scheduler stopped")

    async def schedule_task(
        self,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: int = 0,
        interval_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule a new background task.

        Args:
            task_type: Type of task to schedule
            priority: Priority level
            delay_seconds: Delay before first execution
            interval_seconds: Repeat interval in seconds
            metadata: Task metadata

        Returns:
            Task ID
        """
        return await self.task_scheduler.schedule_task(
            task_type, priority, delay_seconds, interval_seconds, metadata
        )

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if cancelled, False if not found
        """
        return await self.task_scheduler.cancel_task(task_id)

    async def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger an event.

        Args:
            event_type: Type of event
            event_data: Event data
        """
        await self.event_handler.trigger_event(event_type, event_data)

    async def reload_config(self, new_config) -> None:
        """Reload configuration.

        Args:
            new_config: New configuration object
        """
        self.config = new_config
        await self.config_manager.reload_config(new_config, self.task_scheduler)

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status.

        Returns:
            Status dictionary
        """
        active_tasks = [task for task in self.task_scheduler.tasks.values() if task.is_active]
        running_count = len(self.task_scheduler.running_tasks)

        return {
            "is_running": self.is_running,
            "market_open": self.market_open,
            "active_tasks": len(active_tasks),
            "running_tasks": running_count,
            "queued_tasks": len(active_tasks) - running_count,
            "last_market_check": self.last_market_check.isoformat(),
            "tasks_by_type": self.task_scheduler.count_tasks_by_type(),
            "tasks_by_priority": self.task_scheduler.count_tasks_by_priority()
        }

    # Internal Loops

    async def _scheduling_loop(self) -> None:
        """Main scheduling loop."""
        while self.is_running:
            try:
                await self.task_scheduler.execute_due_tasks()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}")
                await asyncio.sleep(30)

    async def _market_monitoring_loop(self) -> None:
        """Market monitoring loop."""
        while self.is_running:
            try:
                status = await self.market_monitor.check_market_status()
                self.market_open = status.get("market_open", False)
                self.last_market_check = datetime.now(timezone.utc)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in market monitoring: {e}")
                await asyncio.sleep(300)

    # Task Execution

    async def _execute_task_logic(self, task: BackgroundTask) -> None:
        """Execute task logic based on type."""
        task_type = task.task_type

        if task_type == TaskType.MARKET_MONITORING and self.market_open:
            logger.info("Executing market monitoring task")
        elif task_type == TaskType.STOP_LOSS_MONITOR:
            portfolio = await self.state_manager.get_portfolio()
            await self.risk_monitor.check_stop_loss(portfolio, self.config.risk.stop_loss_percent)
        elif task_type == TaskType.HEALTH_CHECK:
            await self.health_monitor.execute_system_health_check()
        elif task_type == TaskType.EARNINGS_FUNDAMENTALS:
            if self.fundamental_executor:
                await self.fundamental_executor.execute_earnings_fundamentals([], task.metadata)
        elif task_type == TaskType.MARKET_NEWS_ANALYSIS:
            if self.fundamental_executor:
                await self.fundamental_executor.execute_market_news_analysis([], task.metadata)
        elif task_type == TaskType.DEEP_FUNDAMENTAL_ANALYSIS:
            if self.fundamental_executor:
                await self.fundamental_executor.execute_deep_fundamental_analysis([], task.metadata)

    async def _handle_task_failure(self, task: BackgroundTask, error: str) -> None:
        """Handle task failure.

        Args:
            task: Failed task
            error: Error message
        """
        task.retry_count += 1

        if task.retry_count < task.max_retries:
            task.execute_at = datetime.now(timezone.utc) + timedelta(seconds=60 * task.retry_count)
            await TaskStore.save_task(self.task_scheduler.state_dir, self.task_scheduler.tasks)
            logger.warning(f"Task {task.task_id} failed, scheduled for retry {task.retry_count}/{task.max_retries}")
        else:
            task.is_active = False
            await TaskStore.save_task(self.task_scheduler.state_dir, self.task_scheduler.tasks)
            logger.error(f"Task {task.task_id} failed after {task.max_retries} retries")

    # Event Handlers

    async def _handle_market_open_event(self, event_data: Dict) -> None:
        """Handle market open event."""
        logger.info("Market opened")
        self.market_open = True

    async def _handle_market_close_event(self, event_data: Dict) -> None:
        """Handle market close event."""
        logger.info("Market closed")
        self.market_open = False

    async def _handle_earnings_event(self, event_data: Dict) -> None:
        """Handle earnings announcement event."""
        logger.info(f"Earnings event: {event_data}")

    async def _handle_stop_loss_event(self, event_data: Dict) -> None:
        """Handle stop loss triggered event."""
        logger.info(f"Stop loss event: {event_data}")

    async def _handle_news_event(self, event_data: Dict) -> None:
        """Handle news alert event."""
        logger.info(f"News event: {event_data}")

    async def _handle_price_movement_event(self, event_data: Dict) -> None:
        """Handle price movement event."""
        logger.info(f"Price movement event: {event_data}")

    async def _on_market_open(self) -> None:
        """Callback when market opens."""
        await self.trigger_event("market_open", {})

    async def _on_market_close(self) -> None:
        """Callback when market closes."""
        await self.trigger_event("market_close", {})

    # Scheduling

    async def _schedule_default_tasks(self) -> None:
        """Schedule default tasks based on configuration."""
        agents_config = getattr(self.config, 'agents', None)
        if not agents_config:
            logger.warning("No agents configuration found")
            return

        base_delay = 0

        if agents_config.health_check.enabled:
            await self.schedule_task(
                TaskType.HEALTH_CHECK,
                TaskPriority.LOW,
                delay_seconds=base_delay,
                interval_seconds=300
            )

        if agents_config.market_monitoring.enabled:
            await self.schedule_task(
                TaskType.MARKET_MONITORING,
                TaskPriority.MEDIUM,
                delay_seconds=base_delay + 60,
                interval_seconds=30
            )

        if agents_config.stop_loss_monitor.enabled:
            await self.schedule_task(
                TaskType.STOP_LOSS_MONITOR,
                TaskPriority.HIGH,
                delay_seconds=base_delay + 90,
                interval_seconds=15
            )

        logger.info("Default tasks scheduled")
