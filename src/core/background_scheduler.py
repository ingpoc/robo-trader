"""
Background Scheduler for Robo Trader

Manages autonomous background tasks including:
- Market monitoring during trading hours
- Earnings announcement tracking
- Stop loss monitoring
- News event detection
- Periodic health checks
- Autonomous task execution
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from loguru import logger
from ..config import Config
from ..core.database_state import DatabaseStateManager


class TaskType(Enum):
    """Types of background tasks."""
    MARKET_MONITORING = "market_monitoring"
    EARNINGS_CHECK = "earnings_check"
    STOP_LOSS_MONITOR = "stop_loss_monitor"
    NEWS_MONITORING = "news_monitoring"
    HEALTH_CHECK = "health_check"
    PORTFOLIO_SCAN = "portfolio_scan"
    MARKET_SCREENING = "market_screening"
    AI_PLANNING = "ai_planning"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = "critical"  # Execute immediately
    HIGH = "high"         # Execute within minutes
    MEDIUM = "medium"     # Execute within hours
    LOW = "low"          # Execute when convenient


@dataclass
class BackgroundTask:
    """Represents a scheduled background task."""
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    execute_at: datetime
    interval_seconds: Optional[int] = None  # For recurring tasks
    max_retries: int = 3
    retry_count: int = 0
    last_executed: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['priority'] = self.priority.value
        data['execute_at'] = self.execute_at.isoformat()
        if self.last_executed:
            data['last_executed'] = self.last_executed.isoformat()
        if self.next_execution:
            data['next_execution'] = self.next_execution.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackgroundTask":
        data_copy = data.copy()
        data_copy['task_type'] = TaskType(data['task_type'])
        data_copy['priority'] = TaskPriority(data['priority'])
        data_copy['execute_at'] = datetime.fromisoformat(data['execute_at'])
        if 'last_executed' in data and data['last_executed']:
            data_copy['last_executed'] = datetime.fromisoformat(data['last_executed'])
        if 'next_execution' in data and data['next_execution']:
            data_copy['next_execution'] = datetime.fromisoformat(data['next_execution'])
        return cls(**data_copy)


class BackgroundScheduler:
    """
    Autonomous background task scheduler for Robo Trader.

    Features:
    - Market hours awareness
    - Priority-based task execution
    - Event-driven task triggering
    - Health monitoring and recovery
    - Real-time status reporting
    """

    def __init__(self, config: Config, state_manager: DatabaseStateManager, orchestrator=None):
        self.config = config
        self.state_manager = state_manager
        self.orchestrator = orchestrator

        # Callback functions to avoid circular imports
        self._run_portfolio_scan = None
        self._run_market_screening = None
        self._ai_planner_create_plan = None
        self._orchestrator_get_claude_status = None
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.market_open = False
        self.last_market_check = datetime.now(timezone.utc)

        # Market hours (IST: 9:15 AM - 3:30 PM)
        self.market_open_time = time(9, 15)
        self.market_close_time = time(15, 30)

        # Task execution limits
        self.max_concurrent_tasks = 3
        self.task_timeout_seconds = 300  # 5 minutes

    async def start(self) -> List[asyncio.Task]:
        """Start the background scheduler and return background tasks."""
        if self.is_running:
            return []

        logger.info("Starting Background Scheduler")
        self.is_running = True

        # Load existing tasks
        await self._load_tasks()

        # Schedule default tasks
        await self._schedule_default_tasks()

        # Start main scheduling loop and track the task
        scheduling_task = asyncio.create_task(self._scheduling_loop())

        # Start market monitoring and track the task
        monitoring_task = asyncio.create_task(self._market_monitoring_loop())

        logger.info("Background Scheduler started successfully")

        # Return tasks for lifecycle management
        return [scheduling_task, monitoring_task]

    async def stop(self) -> None:
        """Stop the background scheduler."""
        logger.info("Stopping Background Scheduler")
        self.is_running = False

        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()

        self.running_tasks.clear()
        logger.info("Background Scheduler stopped")

    async def schedule_task(
        self,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: int = 0,
        interval_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule a new background task."""
        task_id = f"{task_type.value}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        execute_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            execute_at=execute_at,
            interval_seconds=interval_seconds,
            metadata=metadata or {}
        )

        self.tasks[task_id] = task
        await self._save_task(task)

        logger.info(f"Scheduled task: {task_id} ({task_type.value}) for {execute_at}")
        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.is_active = False
            await self._save_task(task)

            # Cancel running task if exists
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]

            logger.info(f"Cancelled task: {task_id}")
            return True

        return False

    async def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger event-driven tasks based on market events."""
        logger.info(f"Event triggered: {event_type} - {event_data}")

        if event_type == "earnings_announced":
            await self._handle_earnings_event(event_data)
        elif event_type == "stop_loss_triggered":
            await self._handle_stop_loss_event(event_data)
        elif event_type == "price_movement":
            await self._handle_price_movement_event(event_data)
        elif event_type == "news_alert":
            await self._handle_news_event(event_data)
        elif event_type == "market_open":
            await self._handle_market_open_event()
        elif event_type == "market_close":
            await self._handle_market_close_event()

    async def reload_config(self, new_config: Config) -> None:
        """Reload configuration and update task frequencies."""
        self.config = new_config

        if hasattr(new_config, 'agents'):
            agents_config = new_config.agents

            # Track which task types are currently scheduled
            scheduled_types = {task.task_type for task in self.tasks.values()}

            # Update existing tasks
            for task_id, task in self.tasks.items():
                if task.task_type == TaskType.MARKET_MONITORING:
                    task.interval_seconds = agents_config.market_monitoring.frequency_seconds
                    task.is_active = agents_config.market_monitoring.enabled
                elif task.task_type == TaskType.STOP_LOSS_MONITOR:
                    task.interval_seconds = agents_config.stop_loss_monitor.frequency_seconds
                    task.is_active = agents_config.stop_loss_monitor.enabled
                elif task.task_type == TaskType.EARNINGS_CHECK:
                    task.interval_seconds = agents_config.earnings_check.frequency_seconds
                    task.is_active = agents_config.earnings_check.enabled
                elif task.task_type == TaskType.NEWS_MONITORING:
                    task.interval_seconds = agents_config.news_monitoring.frequency_seconds
                    task.is_active = agents_config.news_monitoring.enabled
                elif task.task_type == TaskType.HEALTH_CHECK:
                    task.interval_seconds = agents_config.health_check.frequency_seconds
                    task.is_active = agents_config.health_check.enabled
                elif task.task_type == TaskType.AI_PLANNING:
                    task.interval_seconds = agents_config.ai_daily_planning.frequency_seconds
                    task.is_active = agents_config.ai_daily_planning.enabled
                elif task.task_type == TaskType.PORTFOLIO_SCAN:
                    task.interval_seconds = agents_config.portfolio_scan.frequency_seconds
                    task.is_active = agents_config.portfolio_scan.enabled
                elif task.task_type == TaskType.MARKET_SCREENING:
                    task.interval_seconds = agents_config.market_screening.frequency_seconds
                    task.is_active = agents_config.market_screening.enabled

                await self._save_task(task)

            # Schedule any newly enabled tasks that weren't previously scheduled
            if agents_config.market_monitoring.enabled and TaskType.MARKET_MONITORING not in scheduled_types:
                await self.schedule_task(
                    TaskType.MARKET_MONITORING,
                    TaskPriority.MEDIUM,
                    delay_seconds=60,
                    interval_seconds=agents_config.market_monitoring.frequency_seconds
                )

            if agents_config.stop_loss_monitor.enabled and TaskType.STOP_LOSS_MONITOR not in scheduled_types:
                await self.schedule_task(
                    TaskType.STOP_LOSS_MONITOR,
                    TaskPriority.HIGH,
                    delay_seconds=30,
                    interval_seconds=agents_config.stop_loss_monitor.frequency_seconds
                )

            if agents_config.earnings_check.enabled and TaskType.EARNINGS_CHECK not in scheduled_types:
                await self.schedule_task(
                    TaskType.EARNINGS_CHECK,
                    TaskPriority.MEDIUM,
                    interval_seconds=agents_config.earnings_check.frequency_seconds
                )

            if agents_config.news_monitoring.enabled and TaskType.NEWS_MONITORING not in scheduled_types:
                await self.schedule_task(
                    TaskType.NEWS_MONITORING,
                    TaskPriority.MEDIUM,
                    interval_seconds=agents_config.news_monitoring.frequency_seconds
                )

            if agents_config.health_check.enabled and TaskType.HEALTH_CHECK not in scheduled_types:
                await self.schedule_task(
                    TaskType.HEALTH_CHECK,
                    TaskPriority.LOW,
                    interval_seconds=agents_config.health_check.frequency_seconds
                )

            if agents_config.ai_daily_planning.enabled and TaskType.AI_PLANNING not in scheduled_types:
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                target_time = now_ist.replace(hour=8, minute=30, second=0, microsecond=0)

                if now_ist.time() > time(8, 30):
                    target_time += timedelta(days=1)

                delay_seconds = int((target_time - now_ist).total_seconds())

                await self.schedule_task(
                    TaskType.AI_PLANNING,
                    TaskPriority.HIGH,
                    delay_seconds=delay_seconds,
                    interval_seconds=agents_config.ai_daily_planning.frequency_seconds,
                    metadata={"planning_type": "daily"}
                )

                logger.info(f"Scheduled newly enabled AI planning for {target_time} IST")

        logger.info("Scheduler config reloaded successfully")

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status for monitoring."""
        active_tasks = [task for task in self.tasks.values() if task.is_active]
        running_count = len(self.running_tasks)

        return {
            "is_running": self.is_running,
            "market_open": self.market_open,
            "active_tasks": len(active_tasks),
            "running_tasks": running_count,
            "queued_tasks": len(active_tasks) - running_count,
            "last_market_check": self.last_market_check.isoformat(),
            "tasks_by_type": self._count_tasks_by_type(),
            "tasks_by_priority": self._count_tasks_by_priority()
        }

    def _count_tasks_by_type(self) -> Dict[str, int]:
        """Count active tasks by type."""
        counts = {}
        for task in self.tasks.values():
            if task.is_active:
                task_type = task.task_type.value
                counts[task_type] = counts.get(task_type, 0) + 1
        return counts

    def _count_tasks_by_priority(self) -> Dict[str, int]:
        """Count active tasks by priority."""
        counts = {}
        for task in self.tasks.values():
            if task.is_active:
                priority = task.priority.value
                counts[priority] = counts.get(priority, 0) + 1
        return counts

    async def _scheduling_loop(self) -> None:
        """Main scheduling loop that executes due tasks."""
        while self.is_running:
            try:
                await self._execute_due_tasks()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _market_monitoring_loop(self) -> None:
        """Monitor market hours and trigger appropriate tasks."""
        while self.is_running:
            try:
                await self._check_market_status()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in market monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _execute_due_tasks(self) -> None:
        """Execute tasks that are due."""
        now = datetime.now(timezone.utc)
        due_tasks = []

        # Find due tasks
        for task in self.tasks.values():
            if (task.is_active and
                task.execute_at <= now and
                task.task_id not in self.running_tasks):

                # Check concurrent task limit
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    # Only execute critical tasks when at limit
                    if task.priority != TaskPriority.CRITICAL:
                        continue

                due_tasks.append(task)

        # Sort by priority (critical first)
        due_tasks.sort(key=lambda t: t.priority.value == 'critical', reverse=True)

        # Execute due tasks
        for task in due_tasks[:self.max_concurrent_tasks - len(self.running_tasks)]:
            await self._execute_task(task)

    async def _execute_task(self, task: BackgroundTask) -> None:
        """Execute a single task."""
        if task.task_id in self.running_tasks:
            return  # Already running

        # Create execution task
        execution_task = asyncio.create_task(self._run_task_with_timeout(task))
        self.running_tasks[task.task_id] = execution_task

        # Update task status
        task.last_executed = datetime.now(timezone.utc)
        if task.interval_seconds and task.is_active:
            task.next_execution = task.last_executed + timedelta(seconds=task.interval_seconds)
            task.execute_at = task.next_execution

        await self._save_task(task)

        logger.info(f"Started execution of task: {task.task_id} ({task.task_type.value})")

    async def _run_task_with_timeout(self, task: BackgroundTask) -> None:
        """Run a task with timeout handling."""
        execution_task = None
        try:
            task_coro = self._execute_task_logic(task)
            execution_task = asyncio.create_task(task_coro)

            await asyncio.wait_for(execution_task, timeout=self.task_timeout_seconds)

            logger.info(f"Completed task: {task.task_id}")

        except asyncio.TimeoutError:
            if execution_task and not execution_task.done():
                execution_task.cancel()
                try:
                    await asyncio.wait_for(execution_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            logger.error(f"Task timeout: {task.task_id}")
            await self._handle_task_failure(task, "timeout")

        except Exception as e:
            logger.error(f"Task execution error: {task.task_id} - {e}")
            await self._handle_task_failure(task, str(e))

        finally:
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]

    async def _execute_task_logic(self, task: BackgroundTask) -> None:
        """Execute the actual task logic."""
        if task.task_type == TaskType.MARKET_MONITORING:
            await self._execute_market_monitoring(task.metadata)

        elif task.task_type == TaskType.EARNINGS_CHECK:
            await self._execute_earnings_check(task.metadata)

        elif task.task_type == TaskType.STOP_LOSS_MONITOR:
            await self._execute_stop_loss_monitor(task.metadata)

        elif task.task_type == TaskType.NEWS_MONITORING:
            await self._execute_news_monitoring(task.metadata)

        elif task.task_type == TaskType.HEALTH_CHECK:
            await self._execute_health_check(task.metadata)

        elif task.task_type == TaskType.PORTFOLIO_SCAN:
            if self._run_portfolio_scan:
                await self._run_portfolio_scan()
            else:
                logger.warning("Portfolio scan callback not set")

        elif task.task_type == TaskType.MARKET_SCREENING:
            if self._run_market_screening:
                await self._run_market_screening()
            else:
                logger.warning("Market screening callback not set")

        elif task.task_type == TaskType.AI_PLANNING:
            if self._ai_planner_create_plan:
                await self._ai_planner_create_plan()
            else:
                logger.warning("AI planning callback not set")

        else:
            logger.warning(f"Unknown task type: {task.task_type}")

    async def _handle_task_failure(self, task: BackgroundTask, error: str) -> None:
        """Handle task execution failure."""
        task.retry_count += 1

        if task.retry_count < task.max_retries:
            # Schedule retry with exponential backoff
            retry_delay = 60 * (2 ** task.retry_count)  # 1min, 2min, 4min
            task.execute_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
            logger.info(f"Scheduling retry {task.retry_count}/{task.max_retries} for task: {task.task_id}")
        else:
            # Mark task as failed
            task.is_active = False
            logger.error(f"Task failed permanently: {task.task_id} after {task.max_retries} retries")

        await self._save_task(task)

    async def _check_market_status(self) -> None:
        """Check if market is open and update status."""
        now = datetime.now(timezone.utc)
        ist_time = now + timedelta(hours=5, minutes=30)  # Convert to IST
        current_time = ist_time.time()

        was_open = self.market_open
        self.market_open = (
            ist_time.weekday() < 5 and  # Monday-Friday
            self.market_open_time <= current_time <= self.market_close_time
        )

        self.last_market_check = now

        # Trigger market open/close events
        if self.market_open and not was_open:
            await self.trigger_event("market_open", {})
        elif not self.market_open and was_open:
            await self.trigger_event("market_close", {})

    async def _schedule_default_tasks(self) -> None:
        """Schedule default background tasks based on configuration."""
        # Get agent configurations
        agents_config = getattr(self.config, 'agents', None)
        if not agents_config:
            logger.warning("No agents configuration found, using defaults")
            return

        # Health check every 5 minutes (only if enabled)
        health_enabled = agents_config.health_check.enabled if hasattr(agents_config, 'health_check') else True
        if health_enabled:
            await self.schedule_task(
                TaskType.HEALTH_CHECK,
                TaskPriority.LOW,
                interval_seconds=300
            )

        # Market monitoring during market hours (every 30 seconds, only if enabled)
        market_monitoring_enabled = agents_config.market_monitoring.enabled if hasattr(agents_config, 'market_monitoring') else False
        if market_monitoring_enabled:
            await self.schedule_task(
                TaskType.MARKET_MONITORING,
                TaskPriority.MEDIUM,
                delay_seconds=60,
                interval_seconds=30
            )

        # Stop loss monitoring (every 15 seconds during market hours, only if enabled)
        stop_loss_enabled = agents_config.stop_loss_monitor.enabled if hasattr(agents_config, 'stop_loss_monitor') else False
        if stop_loss_enabled:
            await self.schedule_task(
                TaskType.STOP_LOSS_MONITOR,
                TaskPriority.HIGH,
                delay_seconds=30,
                interval_seconds=15
            )

        # Earnings check (every 15 minutes, only if enabled)
        earnings_enabled = agents_config.earnings_check.enabled if hasattr(agents_config, 'earnings_check') else False
        if earnings_enabled:
            await self.schedule_task(
                TaskType.EARNINGS_CHECK,
                TaskPriority.MEDIUM,
                interval_seconds=900
            )

        # News monitoring (every 5 minutes, only if enabled)
        news_enabled = agents_config.news_monitoring.enabled if hasattr(agents_config, 'news_monitoring') else False
        if news_enabled:
            await self.schedule_task(
                TaskType.NEWS_MONITORING,
                TaskPriority.MEDIUM,
                interval_seconds=300
            )

        # AI Daily Planning (every morning at 8:30 AM IST, only if enabled)
        ai_planning_enabled = agents_config.ai_daily_planning.enabled if hasattr(agents_config, 'ai_daily_planning') else False
        if ai_planning_enabled:
            now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            target_time = now_ist.replace(hour=8, minute=30, second=0, microsecond=0)

            if now_ist.time() > time(8, 30):
                target_time += timedelta(days=1)

            delay_seconds = int((target_time - now_ist).total_seconds())

            await self.schedule_task(
                TaskType.AI_PLANNING,
                TaskPriority.HIGH,
                delay_seconds=delay_seconds,
                interval_seconds=86400,
                metadata={"planning_type": "daily"}
            )

            logger.info(f"Scheduled daily AI planning for {target_time} IST")

    # Event handlers
    async def _handle_earnings_event(self, event_data: Dict[str, Any]) -> None:
        """Handle earnings announcement event."""
        symbol = event_data.get("symbol", "")
        if symbol:
            # Schedule immediate earnings analysis
            await self.schedule_task(
                TaskType.EARNINGS_CHECK,
                TaskPriority.CRITICAL,
                delay_seconds=0,
                metadata={"symbol": symbol, "reason": "earnings_announced"}
            )

    async def _handle_stop_loss_event(self, event_data: Dict[str, Any]) -> None:
        """Handle stop loss trigger event."""
        symbol = event_data.get("symbol", "")
        if symbol:
            # Schedule immediate analysis
            await self.schedule_task(
                TaskType.STOP_LOSS_MONITOR,
                TaskPriority.CRITICAL,
                delay_seconds=0,
                metadata={"symbol": symbol, "reason": "stop_loss_triggered"}
            )

    async def _handle_price_movement_event(self, event_data: Dict[str, Any]) -> None:
        """Handle significant price movement event."""
        symbol = event_data.get("symbol", "")
        change_pct = event_data.get("change_pct", 0)

        if symbol and abs(change_pct) > 3:  # >3% movement
            await self.schedule_task(
                TaskType.MARKET_MONITORING,
                TaskPriority.HIGH,
                delay_seconds=30,  # Wait 30 seconds to confirm
                metadata={"symbol": symbol, "change_pct": change_pct}
            )

    async def _handle_news_event(self, event_data: Dict[str, Any]) -> None:
        """Handle news alert event."""
        symbols = event_data.get("symbols", [])
        for symbol in symbols:
            await self.schedule_task(
                TaskType.NEWS_MONITORING,
                TaskPriority.HIGH,
                delay_seconds=0,
                metadata={"symbol": symbol, "news": event_data}
            )

    async def _handle_market_open_event(self) -> None:
        """Handle market open event."""
        logger.info("Market opened - activating monitoring tasks")

        # Ensure monitoring tasks are active
        for task in self.tasks.values():
            if task.task_type in [TaskType.MARKET_MONITORING, TaskType.STOP_LOSS_MONITOR]:
                task.is_active = True
                await self._save_task(task)

    async def _handle_market_close_event(self) -> None:
        """Handle market close event."""
        logger.info("Market closed - deactivating monitoring tasks")

        # Deactivate high-frequency monitoring
        for task in self.tasks.values():
            if task.task_type in [TaskType.MARKET_MONITORING, TaskType.STOP_LOSS_MONITOR]:
                task.is_active = False
                await self._save_task(task)

    # Task execution implementations
    async def _execute_market_monitoring(self, metadata: Dict[str, Any]) -> None:
        """Execute market monitoring task - detect significant price movements."""
        portfolio = await self.state_manager.get_portfolio()
        if not portfolio or not portfolio.holdings:
            return

        alerts_created = 0
        threshold_percent = 3.0  # Alert on >3% movement

        for holding in portfolio.holdings:
            try:
                symbol = holding.get('tradingsymbol', '')
                if not symbol:
                    continue

                pnl_percent = holding.get('pnl_percent', 0)
                last_price = holding.get('last_price', 0)
                avg_price = holding.get('average_price', 0)

                if abs(pnl_percent) >= threshold_percent:
                    direction = "up" if pnl_percent > 0 else "down"
                    alert_type = "profit_opportunity" if pnl_percent > 0 else "loss_warning"
                    severity = "high" if abs(pnl_percent) > 5 else "medium"

                    alert_data = {
                        "type": "price_movement",
                        "severity": severity,
                        "symbol": symbol,
                        "message": f"Significant Price Movement: {symbol}",
                        "details": f"Stock moved {direction} {abs(pnl_percent):.2f}% (₹{avg_price:.2f} → ₹{last_price:.2f})",
                        "metadata": {
                            "pnl_percent": pnl_percent,
                            "current_price": last_price,
                            "avg_price": avg_price,
                            "direction": direction,
                            "alert_type": alert_type
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await self.state_manager.add_alert(alert_data)
                    alerts_created += 1
                    logger.info(f"Price movement alert for {symbol}: {pnl_percent:.2f}%")

            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")

        if alerts_created > 0:
            logger.info(f"Market monitoring: created {alerts_created} alerts")

    async def _execute_earnings_check(self, metadata: Dict[str, Any]) -> None:
        """Execute earnings check task - placeholder for earnings calendar integration."""
        logger.debug("Earnings check executed (no external API integrated yet)")

        # This is a placeholder for future earnings calendar API integration
        # Potential data sources:
        # - NSE earnings calendar
        # - BSE earnings announcements
        # - Financial data providers (Alpha Vantage, Polygon, etc.)
        #
        # Implementation would:
        # 1. Fetch earnings calendar for portfolio symbols
        # 2. Check for earnings in next 7 days
        # 3. Create alerts for upcoming earnings
        # 4. Flag positions that might be affected

        # For now, just log that the check ran
        portfolio = await self.state_manager.get_portfolio()
        if portfolio and portfolio.holdings:
            logger.debug(f"Checked {len(portfolio.holdings)} holdings for earnings (API integration pending)")

    async def _execute_stop_loss_monitor(self, metadata: Dict[str, Any]) -> None:
        """Execute stop loss monitoring task."""
        portfolio = await self.state_manager.get_portfolio()
        if not portfolio or not portfolio.holdings:
            return

        stop_loss_percent = self.config.risk.stop_loss_percent
        alerts_created = 0

        for holding in portfolio.holdings:
            try:
                symbol = holding.get('tradingsymbol', '')
                if not symbol:
                    continue

                avg_price = holding.get('average_price', 0)
                last_price = holding.get('last_price', 0)
                quantity = holding.get('quantity', 0)
                pnl_percent = holding.get('pnl_percent', 0)

                if avg_price <= 0 or last_price <= 0:
                    continue

                stop_loss_price = avg_price * (1 - stop_loss_percent / 100)
                stop_loss_breached = last_price <= stop_loss_price

                if stop_loss_breached and pnl_percent < 0:
                    potential_loss = abs(pnl_percent)
                    alert_data = {
                        "type": "stop_loss",
                        "severity": "high" if potential_loss > 5 else "medium",
                        "symbol": symbol,
                        "message": f"Stop Loss Alert: {symbol}",
                        "details": f"Price ₹{last_price:.2f} breached stop loss at ₹{stop_loss_price:.2f} (target: {stop_loss_percent}% from ₹{avg_price:.2f}). Current loss: {pnl_percent:.2f}%",
                        "metadata": {
                            "current_price": last_price,
                            "stop_loss_price": stop_loss_price,
                            "avg_price": avg_price,
                            "quantity": quantity,
                            "pnl_percent": pnl_percent,
                            "action_required": "Consider exiting position"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await self.state_manager.add_alert(alert_data)
                    alerts_created += 1
                    logger.warning(f"Stop loss breached for {symbol}: {last_price:.2f} <= {stop_loss_price:.2f}")

            except Exception as e:
                logger.error(f"Error checking stop loss for {symbol}: {e}")

        if alerts_created > 0:
            logger.info(f"Stop loss monitor: created {alerts_created} alerts")

    async def _execute_news_monitoring(self, metadata: Dict[str, Any]) -> None:
        """Execute news monitoring task using Perplexity API with automatic failover."""
        try:
            perplexity_api_keys = self.config.integration.perplexity_api_keys
            if not perplexity_api_keys:
                logger.warning("No Perplexity API keys configured, skipping news monitoring")
                return

            use_claude = self.config.agents.news_monitoring.use_claude if hasattr(self.config, 'agents') else True

            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.info("No portfolio holdings to monitor for news")
                return

            from openai import OpenAI
            import httpx

            alerts_created = 0
            current_key_index = 0

            for holding in portfolio.holdings[:10]:
                symbol = holding.get('tradingsymbol', '')
                if not symbol:
                    continue

                news_content = None
                citations = []
                api_call_succeeded = False

                for attempt in range(len(perplexity_api_keys)):
                    try:
                        api_key = perplexity_api_keys[current_key_index]

                        client = OpenAI(
                            api_key=api_key,
                            base_url="https://api.perplexity.ai",
                            http_client=httpx.Client(timeout=30.0)
                        )

                        query = f"Latest news about {symbol} stock in the last 24 hours, focusing on earnings, major announcements, and market-moving events"

                        completion = client.chat.completions.create(
                            model="sonar-pro",
                            messages=[{"role": "user", "content": query}],
                            web_search_options={
                                "search_recency_filter": "day",
                                "max_search_results": 5
                            }
                        )

                        news_content = completion.choices[0].message.content
                        citations = getattr(completion, 'citations', [])
                        api_call_succeeded = True
                        break

                    except Exception as e:
                        error_str = str(e).lower()
                        if "rate limit" in error_str or "quota" in error_str or "limit exceeded" in error_str:
                            logger.warning(f"Perplexity API key {current_key_index + 1} limit exceeded, switching to next key")
                            current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                            continue
                        else:
                            logger.error(f"Failed to fetch news for {symbol}: {e}")
                            break

                if not api_call_succeeded or not news_content:
                    continue

                if "no recent news" in news_content.lower() or "no significant news" in news_content.lower():
                    continue

                sentiment = "neutral"
                alert_priority = "medium"

                if use_claude and self.orchestrator and self.orchestrator.claude_client:
                    sentiment_prompt = f"""Analyze this news summary for {symbol} and provide:
1. Sentiment (positive/negative/neutral)
2. Priority (critical/high/medium/low) based on market impact
3. Brief assessment (1-2 sentences)

News: {news_content}

Respond in format:
Sentiment: <sentiment>
Priority: <priority>
Assessment: <assessment>"""

                    try:
                        sentiment_response = await self.orchestrator.claude_client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=200,
                            messages=[{"role": "user", "content": sentiment_prompt}]
                        )

                        analysis = sentiment_response.content[0].text
                        if "Sentiment:" in analysis:
                            sentiment = analysis.split("Sentiment:")[1].split("\n")[0].strip().lower()
                        if "Priority:" in analysis:
                            alert_priority = analysis.split("Priority:")[1].split("\n")[0].strip().lower()

                    except Exception as e:
                        logger.warning(f"Claude sentiment analysis failed for {symbol}: {e}")

                alert_data = {
                    "type": "news",
                    "severity": alert_priority,
                    "symbol": symbol,
                    "message": f"News Update: {symbol}",
                    "details": news_content,
                    "sentiment": sentiment,
                    "citations": citations[:3] if citations else [],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await self.state_manager.add_alert(alert_data)
                alerts_created += 1
                logger.info(f"Created news alert for {symbol} (sentiment: {sentiment}, priority: {alert_priority})")

            if alerts_created > 0:
                logger.info(f"News monitoring completed: created {alerts_created} alerts")
            else:
                logger.info("News monitoring completed: no significant news found")

        except Exception as e:
            logger.error(f"News monitoring task failed: {e}")

    async def _execute_health_check(self, metadata: Dict[str, Any]) -> None:
        """Execute system health check."""
        # Check API connectivity, database health, etc.
        try:
            # Test Claude API
            if self._orchestrator_get_claude_status:
                claude_status = await self._orchestrator_get_claude_status()
            else:
                logger.warning("Claude status callback not set")

            # Test broker connection
            # Test database connectivity

            logger.info("Health check completed successfully")
        except Exception as e:
            logger.error(f"Health check failed: {e}")

    # Persistence methods
    async def _load_tasks(self) -> None:
        """Load tasks from persistent storage."""
        try:
            import aiofiles
            tasks_file = self.config.state_dir / "scheduler_tasks.json"
            if tasks_file.exists():
                async with aiofiles.open(tasks_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    tasks_data = json.loads(content)

                for task_data in tasks_data:
                    task = BackgroundTask(
                        task_id=task_data["task_id"],
                        task_type=TaskType(task_data["task_type"]),
                        priority=TaskPriority(task_data["priority"]),
                        execute_at=datetime.fromisoformat(task_data["execute_at"]),
                        interval_seconds=task_data.get("interval_seconds"),
                        metadata=task_data.get("metadata", {}),
                        is_active=task_data.get("is_active", True),
                        retry_count=task_data.get("retry_count", 0),
                        max_retries=task_data.get("max_retries", 3)
                    )
                    if task_data.get("last_executed"):
                        task.last_executed = datetime.fromisoformat(task_data["last_executed"])
                    if task_data.get("next_execution"):
                        task.next_execution = datetime.fromisoformat(task_data["next_execution"])

                    self.tasks[task.task_id] = task

                logger.info(f"Loaded {len(self.tasks)} tasks from storage")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

    async def _save_task(self, task: BackgroundTask) -> None:
        """Save task to persistent storage."""
        try:
            import aiofiles
            tasks_file = self.config.state_dir / "scheduler_tasks.json"

            # Load all tasks
            all_tasks = list(self.tasks.values())

            # Serialize to JSON
            tasks_data = []
            for t in all_tasks:
                task_dict = {
                    "task_id": t.task_id,
                    "task_type": t.task_type.value,
                    "priority": t.priority.value,
                    "execute_at": t.execute_at.isoformat(),
                    "interval_seconds": t.interval_seconds,
                    "metadata": t.metadata,
                    "is_active": t.is_active,
                    "retry_count": t.retry_count,
                    "max_retries": t.max_retries
                }
                if t.last_executed:
                    task_dict["last_executed"] = t.last_executed.isoformat()
                if t.next_execution:
                    task_dict["next_execution"] = t.next_execution.isoformat()

                tasks_data.append(task_dict)

            # Write to file asynchronously
            async with aiofiles.open(tasks_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(tasks_data, indent=2, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Failed to save task {task.task_id}: {e}")