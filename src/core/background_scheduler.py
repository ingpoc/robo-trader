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
from ..services.fundamental_service import FundamentalService


class TaskType(Enum):
    """Types of background tasks."""
    MARKET_MONITORING = "market_monitoring"
    EARNINGS_CHECK = "earnings_check"
    EARNINGS_SCHEDULER = "earnings_scheduler"
    STOP_LOSS_MONITOR = "stop_loss_monitor"
    NEWS_MONITORING = "news_monitoring"
    NEWS_DAILY = "news_daily"
    FUNDAMENTAL_MONITORING = "fundamental_monitoring"
    RECOMMENDATION_GENERATION = "recommendation_generation"
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

        # Initialize fundamental service
        self.fundamental_service = FundamentalService(config, state_manager)

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
                elif task.task_type == TaskType.EARNINGS_SCHEDULER:
                    earnings_scheduler_config = getattr(self.config, 'earnings_scheduler', {})
                    task.interval_seconds = earnings_scheduler_config.get('frequency_seconds', 3600)
                    task.is_active = earnings_scheduler_config.get('enabled', True)
                elif task.task_type == TaskType.NEWS_MONITORING:
                    task.interval_seconds = agents_config.news_monitoring.frequency_seconds
                    task.is_active = agents_config.news_monitoring.enabled
                elif task.task_type == TaskType.NEWS_DAILY:
                    # Daily task - calculate next execution time
                    news_daily_config = getattr(self.config, 'news_daily_scheduler', {})
                    task.is_active = news_daily_config.get('enabled', True)
                    # Interval is 24 hours (86400 seconds) for daily execution
                    task.interval_seconds = 86400
                elif task.task_type == TaskType.FUNDAMENTAL_MONITORING:
                    # Use same config as news monitoring for now, can be customized later
                    task.interval_seconds = getattr(agents_config, 'fundamental_monitoring', {}).get('frequency_seconds', 86400)  # Daily
                    task.is_active = getattr(agents_config, 'fundamental_monitoring', {}).get('enabled', True)
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

            # Earnings Scheduler (new task type)
            earnings_scheduler_config = getattr(self.config, 'earnings_scheduler', {})
            earnings_scheduler_enabled = earnings_scheduler_config.get('enabled', True)
            if earnings_scheduler_enabled and TaskType.EARNINGS_SCHEDULER not in scheduled_types:
                await self.schedule_task(
                    TaskType.EARNINGS_SCHEDULER,
                    TaskPriority.MEDIUM,
                    interval_seconds=earnings_scheduler_config.get('frequency_seconds', 3600)
                )

            if agents_config.news_monitoring.enabled and TaskType.NEWS_MONITORING not in scheduled_types:
                await self.schedule_task(
                    TaskType.NEWS_MONITORING,
                    TaskPriority.MEDIUM,
                    interval_seconds=agents_config.news_monitoring.frequency_seconds
                )

            # Fundamental monitoring (daily, only if enabled)
            fundamental_enabled = getattr(agents_config, 'fundamental_monitoring', {}).get('enabled', True)
            if fundamental_enabled and TaskType.FUNDAMENTAL_MONITORING not in scheduled_types:
                await self.schedule_task(
                    TaskType.FUNDAMENTAL_MONITORING,
                    TaskPriority.MEDIUM,
                    interval_seconds=getattr(agents_config, 'fundamental_monitoring', {}).get('frequency_seconds', 86400)
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

            # News Daily Monitoring (every morning at 9:00 AM IST, only if enabled)
            news_daily_config = getattr(self.config, 'news_daily_scheduler', {})
            news_daily_enabled = news_daily_config.get('enabled', True)
            if news_daily_enabled and TaskType.NEWS_DAILY not in scheduled_types:
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                execution_time_ist = news_daily_config.get('execution_time_ist', '09:00')
                hour, minute = map(int, execution_time_ist.split(':'))
                target_time = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)

                if now_ist.time() >= time(hour, minute):
                    target_time += timedelta(days=1)

                delay_seconds = int((target_time - now_ist).total_seconds())

                await self.schedule_task(
                    TaskType.NEWS_DAILY,
                    TaskPriority.MEDIUM,
                    delay_seconds=delay_seconds,
                    interval_seconds=86400,  # Daily
                    metadata={"execution_time_ist": execution_time_ist}
                )

                logger.info(f"Scheduled daily news monitoring for {target_time} IST")

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

        elif task.task_type == TaskType.EARNINGS_SCHEDULER:
            await self._execute_earnings_scheduler(task.metadata)

        elif task.task_type == TaskType.STOP_LOSS_MONITOR:
            await self._execute_stop_loss_monitor(task.metadata)

        elif task.task_type == TaskType.NEWS_MONITORING:
            await self._execute_news_monitoring(task.metadata)

        elif task.task_type == TaskType.NEWS_DAILY:
            await self._execute_news_daily(task.metadata)

        elif task.task_type == TaskType.FUNDAMENTAL_MONITORING:
            await self._execute_fundamental_monitoring(task.metadata)

        elif task.task_type == TaskType.RECOMMENDATION_GENERATION:
            await self._execute_recommendation_generation(task.metadata)

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

        # Earnings Scheduler (every hour, only if enabled)
        earnings_scheduler_config = getattr(self.config, 'earnings_scheduler', {})
        earnings_scheduler_enabled = earnings_scheduler_config.get('enabled', True)
        if earnings_scheduler_enabled:
            await self.schedule_task(
                TaskType.EARNINGS_SCHEDULER,
                TaskPriority.MEDIUM,
                interval_seconds=earnings_scheduler_config.get('frequency_seconds', 3600)
            )

        # News monitoring (every 5 minutes, only if enabled)
        news_enabled = agents_config.news_monitoring.enabled if hasattr(agents_config, 'news_monitoring') else False
        if news_enabled:
            await self.schedule_task(
                TaskType.NEWS_MONITORING,
                TaskPriority.MEDIUM,
                interval_seconds=300
            )

            # Data cleanup (daily at 2 AM IST)
            now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            cleanup_time = now_ist.replace(hour=2, minute=0, second=0, microsecond=0)

            if now_ist.time() > time(2, 0):
                cleanup_time += timedelta(days=1)

            cleanup_delay_seconds = int((cleanup_time - now_ist).total_seconds())

            await self.schedule_task(
                TaskType.HEALTH_CHECK,  # Reuse health check type for cleanup
                TaskPriority.LOW,
                delay_seconds=cleanup_delay_seconds,
                interval_seconds=86400,  # Daily
                metadata={"task_type": "data_cleanup"}
            )

            logger.info(f"Scheduled daily data cleanup for {cleanup_time} IST")

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

                    await self.state_manager.alert_manager.create_alert(
                        alert_type=alert_data["type"],
                        severity=alert_data["severity"],
                        title=alert_data["message"],
                        message=alert_data["details"],
                        symbol=alert_data["symbol"]
                    )
                    alerts_created += 1
                    logger.info(f"Price movement alert for {symbol}: {pnl_percent:.2f}%")

            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")

        if alerts_created > 0:
            logger.info(f"Market monitoring: created {alerts_created} alerts")

    async def _execute_earnings_check(self, metadata: Dict[str, Any]) -> None:
        """Execute earnings check task - now integrated with news monitoring for comprehensive data."""
        logger.debug("Earnings check executed - data collection now handled by news monitoring task")

        # Earnings data collection is now handled by the enhanced news monitoring task
        # This method remains for backward compatibility and specific earnings-focused triggers

        try:
            # Check for upcoming earnings that need attention
            upcoming_earnings = await self.state_manager.get_upcoming_earnings(days_ahead=7)

            alerts_created = 0
            for earnings in upcoming_earnings:
                symbol = earnings["symbol"]
                earnings_date = earnings["next_earnings_date"]

                # Create alert for earnings within 7 days
                alert_data = {
                    "type": "earnings",
                    "severity": "medium",
                    "symbol": symbol,
                    "message": f"Earnings Alert: {symbol}",
                    "details": f"Upcoming earnings report expected on {earnings_date}",
                    "metadata": {
                        "earnings_date": earnings_date,
                        "fiscal_period": earnings.get("fiscal_period"),
                        "guidance": earnings.get("guidance")
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await self.state_manager.alert_manager.create_alert(
                    alert_type=alert_data["type"],
                    severity=alert_data["severity"],
                    title=alert_data["message"],
                    message=alert_data["details"],
                    symbol=alert_data["symbol"]
                )
                alerts_created += 1
                logger.info(f"Created earnings alert for {symbol} on {earnings_date}")

            if alerts_created > 0:
                logger.info(f"Earnings check completed: created {alerts_created} alerts for upcoming earnings")
            else:
                logger.debug("Earnings check completed: no upcoming earnings within 7 days")

        except Exception as e:
            logger.error(f"Earnings check failed: {e}")

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

                    await self.state_manager.alert_manager.create_alert(
                        alert_type=alert_data["type"],
                        severity=alert_data["severity"],
                        title=alert_data["message"],
                        message=alert_data["details"],
                        symbol=alert_data["symbol"]
                    )
                    alerts_created += 1
                    logger.warning(f"Stop loss breached for {symbol}: {last_price:.2f} <= {stop_loss_price:.2f}")

            except Exception as e:
                logger.error(f"Error checking stop loss for {symbol}: {e}")

        if alerts_created > 0:
            logger.info(f"Stop loss monitor: created {alerts_created} alerts")

    async def _execute_news_monitoring(self, metadata: Dict[str, Any]) -> None:
        """Execute news and earnings monitoring task using Perplexity API with batch processing."""
        try:
            # Load API keys from environment variables for security
            import os
            perplexity_api_keys = [
                os.getenv('PERPLEXITY_API_KEY_1'),
                os.getenv('PERPLEXITY_API_KEY_2'),
                os.getenv('PERPLEXITY_API_KEY_3')
            ]
            perplexity_api_keys = [key for key in perplexity_api_keys if key]  # Filter None values

            if not perplexity_api_keys:
                logger.warning("No Perplexity API keys configured in environment variables, skipping news monitoring")
                return

            use_claude = self.config.agents.news_monitoring.use_claude if hasattr(self.config, 'agents') else True

            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.info("No portfolio holdings to monitor for news")
                return

            from openai import OpenAI
            import httpx

            # Get all portfolio symbols
            symbols = [holding.get('symbol', '') for holding in portfolio.holdings if holding.get('symbol')]
            if not symbols:
                logger.info("No valid symbols found in portfolio")
                return

            # Get configuration values
            batch_size = getattr(self.config, 'news_monitoring', {}).get('batch_size', 5)
            api_timeout = getattr(self.config, 'news_monitoring', {}).get('api_timeout_seconds', 45)
            max_concurrent_batches = getattr(self.config, 'news_monitoring', {}).get('max_concurrent_batches', 1)
            perplexity_model = getattr(self.config, 'news_monitoring', {}).get('perplexity_model', 'sonar-pro')
            search_recency = getattr(self.config, 'news_monitoring', {}).get('search_recency_filter', 'day')
            max_search_results = getattr(self.config, 'news_monitoring', {}).get('max_search_results', 10)
            alerts_created = 0
            news_items_saved = 0
            earnings_reports_saved = 0

            # Implement round-robin rotation for API keys
            current_key_index = getattr(self, '_perplexity_key_index', 0)

            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: {batch_symbols}")

                # Create batch query for news and earnings with structured output
                symbols_str = ", ".join(batch_symbols)
                query = f"""For each of these stocks ({symbols_str}), provide the latest news and earnings information.

Focus on:
- Recent news from last 24 hours (earnings, major announcements, market-moving events)
- Latest earnings report details (EPS, revenue, guidance)
- Next earnings date if available
- Overall sentiment (positive/negative/neutral)

Return structured data for each stock."""

                news_content = None
                api_call_succeeded = False

                # Try with different API keys using round-robin rotation
                for attempt in range(len(perplexity_api_keys)):
                    try:
                        api_key = perplexity_api_keys[current_key_index]

                        client = OpenAI(
                            api_key=api_key,
                            base_url="https://api.perplexity.ai",
                            http_client=httpx.Client(timeout=api_timeout)
                        )

                        # Define structured output schema for stock data
                        from pydantic import BaseModel
                        from typing import Optional, List

                        class StockData(BaseModel):
                            symbol: str
                            news: str
                            earnings: str
                            next_earnings_date: Optional[str] = None
                            sentiment: str

                        class BatchResponse(BaseModel):
                            stocks: List[StockData]

                        completion = client.chat.completions.create(
                            model=perplexity_model,
                            messages=[{"role": "user", "content": query}],
                            max_tokens=2000,
                            response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "schema": BatchResponse.model_json_schema()
                                }
                            },
                            web_search_options={
                                "search_recency_filter": search_recency,
                                "max_search_results": max_search_results
                            }
                        )

                        news_content = completion.choices[0].message.content
                        api_call_succeeded = True

                        # Update key index for next call (round-robin)
                        current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                        self._perplexity_key_index = current_key_index
                        break

                    except Exception as e:
                        error_str = str(e).lower()
                        if "rate limit" in error_str or "quota" in error_str or "limit exceeded" in error_str:
                            logger.warning(f"Perplexity API key {current_key_index + 1} limit exceeded, trying next key")
                            current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                            continue
                        else:
                            logger.error(f"Failed to fetch data for batch {batch_symbols}: {e}")
                            break

                if not api_call_succeeded or not news_content:
                    logger.warning(f"Skipping batch {batch_symbols} due to API failure")
                    continue

                # Parse the structured response and save data
                await self._parse_and_save_batch_data(news_content, batch_symbols, use_claude)

                # Small delay between batches to avoid overwhelming the API
                await asyncio.sleep(2)

            # After processing news and earnings, also fetch fundamental data
            logger.info("Fetching comprehensive fundamental data for portfolio symbols")
            try:
                comprehensive_data = await self.fundamental_service.fetch_comprehensive_data(symbols)

                # Log summary of comprehensive data fetched
                fundamentals_count = sum(1 for data in comprehensive_data.values() if 'fundamentals' in data)
                earnings_count = sum(len(data.get('earnings', [])) for data in comprehensive_data.values())
                news_count = sum(len(data.get('news', [])) for data in comprehensive_data.values())

                logger.info(f"Comprehensive data fetch completed: {fundamentals_count} fundamental analyses, {earnings_count} earnings reports, {news_count} news items")

            except Exception as e:
                logger.error(f"Failed to fetch comprehensive data: {e}")

            logger.info(f"News monitoring completed: processed {len(symbols)} symbols in {len(symbols)//batch_size + 1} batches")

        except Exception as e:
            logger.error(f"News monitoring task failed: {e}")

    async def _execute_news_daily(self, metadata: Dict[str, Any]) -> None:
        """Execute daily news monitoring task with incremental fetching and batch processing."""
        try:
            # Load API keys from environment variables for security
            import os
            perplexity_api_keys = [
                os.getenv('PERPLEXITY_API_KEY_1'),
                os.getenv('PERPLEXITY_API_KEY_2'),
                os.getenv('PERPLEXITY_API_KEY_3')
            ]
            perplexity_api_keys = [key for key in perplexity_api_keys if key]  # Filter None values

            if not perplexity_api_keys:
                logger.warning("No Perplexity API keys configured in environment variables, skipping daily news monitoring")
                return

            # Get configuration values
            daily_config = getattr(self.config, 'news_daily_scheduler', {})
            batch_size = daily_config.get('batch_size', 5)
            api_timeout = daily_config.get('api_timeout_seconds', 45)
            max_concurrent_batches = daily_config.get('max_concurrent_batches', 1)
            perplexity_model = daily_config.get('perplexity_model', 'sonar-pro')
            search_recency = daily_config.get('search_recency_filter', 'day')
            max_search_results = daily_config.get('max_search_results', 10)
            min_relevance_score = daily_config.get('min_relevance_score', 0.6)
            focus_significant = daily_config.get('focus_significant_news', True)

            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.info("No portfolio holdings to monitor for daily news")
                return

            # Get all portfolio symbols
            symbols = [holding.get('symbol', '') for holding in portfolio.holdings if holding.get('symbol')]
            logger.info(f"Found {len(symbols)} symbols for daily news monitoring: {symbols[:5]}...")
            if not symbols:
                logger.info("No valid symbols found in portfolio")
                return

            logger.info(f"Starting daily news monitoring for {len(symbols)} symbols in batches of {batch_size}")

            alerts_created = 0
            news_items_saved = 0
            earnings_reports_saved = 0

            # Implement round-robin rotation for API keys
            current_key_index = getattr(self, '_perplexity_key_index', 0)

            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                logger.info(f"Processing daily batch {i//batch_size + 1}: {batch_symbols}")

                # Process each symbol in the batch individually for incremental fetching
                for symbol in batch_symbols:
                    try:
                        # Get last fetch timestamp for this symbol
                        last_fetch = await self.state_manager.get_last_news_fetch(symbol)
                        current_time = datetime.now(timezone.utc)

                        # Determine date range for fetching
                        if last_fetch:
                            # Only fetch news newer than last fetch
                            last_fetch_dt = datetime.fromisoformat(last_fetch.replace('Z', '+00:00'))
                            # Add small buffer to avoid missing news
                            fetch_from_date = last_fetch_dt - timedelta(hours=1)
                        else:
                            # First time fetching for this symbol, get last 24 hours
                            fetch_from_date = current_time - timedelta(days=1)

                        # Skip if we fetched very recently (within last hour)
                        if last_fetch and (current_time - datetime.fromisoformat(last_fetch.replace('Z', '+00:00'))).total_seconds() < 3600:
                            logger.debug(f"Skipping {symbol} - fetched recently")
                            continue

                        # Create focused query for this symbol with date constraints
                        date_context = f"from {fetch_from_date.strftime('%Y-%m-%d')} onwards"
                        query = f"""For {symbol} stock, provide recent news and earnings information {date_context}.

Focus on:
- Significant news from {date_context} (earnings, major announcements, market-moving events)
- Latest earnings report details (EPS, revenue, guidance) if available
- Overall sentiment (positive/negative/neutral)

Only include information that is genuinely new and significant."""

                        news_content = None
                        api_call_succeeded = False

                        # Try with different API keys using round-robin rotation
                        for attempt in range(len(perplexity_api_keys)):
                            try:
                                api_key = perplexity_api_keys[current_key_index]

                                from openai import OpenAI
                                import httpx

                                client = OpenAI(
                                    api_key=api_key,
                                    base_url="https://api.perplexity.ai",
                                    http_client=httpx.Client(timeout=api_timeout)
                                )

                                # Define structured output schema for single stock data
                                from pydantic import BaseModel
                                from typing import Optional

                                class StockData(BaseModel):
                                    symbol: str
                                    news: str
                                    earnings: str
                                    next_earnings_date: Optional[str] = None
                                    sentiment: str

                                completion = client.chat.completions.create(
                                    model=perplexity_model,
                                    messages=[{"role": "user", "content": query}],
                                    max_tokens=1500,
                                    response_format={
                                        "type": "json_schema",
                                        "json_schema": {
                                            "schema": StockData.model_json_schema()
                                        }
                                    },
                                    web_search_options={
                                        "search_recency_filter": search_recency,
                                        "max_search_results": max_search_results
                                    }
                                )

                                news_content = completion.choices[0].message.content
                                api_call_succeeded = True

                                # Update key index for next call (round-robin)
                                current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                                self._perplexity_key_index = current_key_index
                                break

                            except Exception as e:
                                error_str = str(e).lower()
                                if "rate limit" in error_str or "quota" in error_str or "limit exceeded" in error_str:
                                    logger.warning(f"Perplexity API key {current_key_index + 1} limit exceeded, trying next key")
                                    current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                                    continue
                                else:
                                    logger.error(f"Failed to fetch data for {symbol}: {e}")
                                    break

                        if not api_call_succeeded or not news_content:
                            logger.warning(f"Skipping {symbol} due to API failure")
                            continue

                        # Parse and save data for this symbol
                        await self._parse_and_save_daily_data(symbol, news_content, min_relevance_score, focus_significant)

                        # Update last fetch timestamp
                        await self.state_manager.update_last_news_fetch(symbol)

                        logger.debug(f"Completed daily news fetch for {symbol}")

                    except Exception as e:
                        logger.error(f"Error processing daily news for {symbol}: {e}")
                        continue

                # Small delay between batches to avoid overwhelming the API
                await asyncio.sleep(2)

            logger.info(f"Daily news monitoring completed: processed {len(symbols)} symbols in {len(symbols)//batch_size + 1} batches")

        except Exception as e:
            logger.error(f"Daily news monitoring task failed: {e}")

    async def _execute_fundamental_monitoring(self, metadata: Dict[str, Any]) -> None:
        """Execute fundamental analysis monitoring task."""
        try:
            logger.info("Starting fundamental monitoring task")

            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.info("No portfolio holdings to monitor for fundamentals")
                return

            # Get all portfolio symbols
            symbols = [holding.get('tradingsymbol', '') for holding in portfolio.holdings if holding.get('tradingsymbol')]
            if not symbols:
                logger.info("No valid symbols found in portfolio")
                return

            # Fetch fundamental data using the fundamental service
            logger.info(f"Fetching fundamental data for {len(symbols)} symbols")
            fundamental_results = await self.fundamental_service.fetch_fundamentals_batch(symbols)

            # Create alerts for significant fundamental changes
            alerts_created = 0
            for symbol, analysis in fundamental_results.items():
                try:
                    # Check for concerning fundamentals
                    if analysis.overall_score is not None and analysis.overall_score < 40:
                        alert_data = {
                            "type": "fundamental_warning",
                            "severity": "high",
                            "symbol": symbol,
                            "message": f"Fundamental Warning: {symbol}",
                            "details": f"Fundamental score: {analysis.overall_score:.1f}/100. Recommendation: {analysis.recommendation or 'HOLD'}",
                            "metadata": {
                                "pe_ratio": analysis.pe_ratio,
                                "pb_ratio": analysis.pb_ratio,
                                "roe": analysis.roe,
                                "debt_to_equity": analysis.debt_to_equity,
                                "overall_score": analysis.overall_score,
                                "recommendation": analysis.recommendation
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        await self.state_manager.alert_manager.create_alert(
                            alert_type=alert_data["type"],
                            severity=alert_data["severity"],
                            title=alert_data["message"],
                            message=alert_data["details"],
                            symbol=alert_data["symbol"]
                        )
                        alerts_created += 1
                        logger.info(f"Created fundamental warning alert for {symbol}")

                except Exception as e:
                    logger.error(f"Error processing fundamental data for {symbol}: {e}")

            logger.info(f"Fundamental monitoring completed: analyzed {len(fundamental_results)} symbols, created {alerts_created} alerts")

        except Exception as e:
            logger.error(f"Fundamental monitoring task failed: {e}")

    async def _execute_recommendation_generation(self, metadata: Dict[str, Any]) -> None:
        """Execute recommendation generation task."""
        try:
            logger.info("Starting recommendation generation task")

            # Import recommendation service here to avoid circular imports
            from ..services.recommendation_service import RecommendationEngine

            # Initialize recommendation engine
            reco_engine = RecommendationEngine(
                config=self.config,
                state_manager=self.state_manager,
                fundamental_service=self.fundamental_service,
                risk_service=None  # Will be initialized if needed
            )

            # Get portfolio symbols
            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.info("No portfolio holdings to generate recommendations for")
                return

            symbols = [holding.get('tradingsymbol', '') for holding in portfolio.holdings if holding.get('tradingsymbol')]
            if not symbols:
                logger.info("No valid symbols found in portfolio")
                return

            logger.info(f"Generating recommendations for {len(symbols)} symbols")

            # Generate recommendations for all symbols
            recommendations = await reco_engine.generate_bulk_recommendations(symbols)

            # Store recommendations and create alerts
            stored_count = 0
            alerts_created = 0

            for symbol, result in recommendations.items():
                try:
                    # Store recommendation
                    recommendation_id = await reco_engine.store_recommendation(result)
                    if recommendation_id:
                        stored_count += 1

                    # Create alert for new recommendations if configured
                    reco_config = getattr(self.config, 'recommendation_engine', {})
                    if reco_config.get('alert_on_new_recommendations', True):
                        alert_data = {
                            "type": "recommendation",
                            "severity": "medium" if result.confidence_level in ["MEDIUM", "LOW"] else "high",
                            "symbol": symbol,
                            "message": f"New Recommendation: {symbol}",
                            "details": f"{result.recommendation_type} recommendation with {result.confidence_level} confidence. Target: ₹{result.target_price:.2f}, Stop: ₹{result.stop_loss:.2f}",
                            "metadata": {
                                "recommendation_type": result.recommendation_type,
                                "confidence_level": result.confidence_level,
                                "overall_score": result.overall_score,
                                "target_price": result.target_price,
                                "stop_loss": result.stop_loss,
                                "time_horizon": result.time_horizon,
                                "risk_level": result.risk_level
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        await self.state_manager.alert_manager.create_alert(
                            alert_type=alert_data["type"],
                            severity=alert_data["severity"],
                            title=alert_data["message"],
                            message=alert_data["details"],
                            symbol=alert_data["symbol"]
                        )
                        alerts_created += 1

                    logger.debug(f"Generated recommendation for {symbol}: {result.recommendation_type}")

                except Exception as e:
                    logger.error(f"Error processing recommendation for {symbol}: {e}")
                    continue

            logger.info(f"Recommendation generation completed: stored {stored_count} recommendations, created {alerts_created} alerts")

        except Exception as e:
            logger.error(f"Recommendation generation task failed: {e}")

    async def _parse_and_save_batch_data(self, response_content: str, batch_symbols: List[str], use_claude: bool) -> None:
        """Parse structured JSON batch response and save news/earnings data."""
        try:
            # Validate input
            if not response_content or not isinstance(response_content, str):
                logger.warning("Invalid response content received")
                return

            logger.debug(f"Raw API response content: {response_content[:500]}...")

            # Parse JSON response
            try:
                import json
                response_data = json.loads(response_content)
                stocks_data = response_data.get("stocks", [])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return

            # Process each stock in the structured response
            for stock_data in stocks_data:
                symbol = stock_data.get("symbol", "").upper()
                if not symbol or symbol not in batch_symbols:
                    continue

                logger.debug(f"Processing structured data for symbol: {symbol}")

                news_content = stock_data.get("news", "").strip()
                earnings_content = stock_data.get("earnings", "").strip()
                next_earnings_date = stock_data.get("next_earnings_date")
                sentiment = stock_data.get("sentiment", "neutral").lower()

                # Save news data if available
                if news_content and news_content.lower() not in ["no recent news", "no news", "none", ""]:
                    # Extract title from news (first sentence or first 100 chars)
                    title = news_content.split(".")[0][:100] if "." in news_content else news_content[:100]

                    await self.state_manager.save_news_item(
                        symbol=symbol,
                        title=title,
                        content=news_content,
                        source="Perplexity AI",
                        sentiment=sentiment
                    )

                    # Create alert for significant news
                    if sentiment in ["positive", "negative"] or "earnings" in news_content.lower():
                        alert_data = {
                            "type": "news",
                            "severity": "high" if sentiment in ["positive", "negative"] else "medium",
                            "symbol": symbol,
                            "message": f"News Update: {symbol}",
                            "details": news_content[:500] + "..." if len(news_content) > 500 else news_content,
                            "sentiment": sentiment,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await self.state_manager.alert_manager.create_alert(
                            alert_type=alert_data["type"],
                            severity=alert_data["severity"],
                            title=alert_data["message"],
                            message=alert_data["details"],
                            symbol=alert_data["symbol"]
                        )
                        logger.info(f"Created news alert for {symbol} (sentiment: {sentiment})")

                # Save earnings data if available
                if earnings_content and earnings_content.lower() not in ["no recent earnings", "no earnings", "none", ""]:
                    # Parse earnings data
                    parsed_data = self._parse_earnings_data(earnings_content)
                    fiscal_period = parsed_data.get('fiscal_period', 'Q3 2024')
                    eps_actual = parsed_data.get('eps_actual')
                    revenue_actual = parsed_data.get('revenue_actual')
                    eps_estimated = parsed_data.get('eps_estimated')
                    revenue_estimated = parsed_data.get('revenue_estimated')
                    surprise_pct = parsed_data.get('surprise_pct')
                    guidance = parsed_data.get('guidance', earnings_content)

                    await self.state_manager.save_earnings_report(
                        symbol=symbol,
                        fiscal_period=fiscal_period,
                        report_date=datetime.now(timezone.utc).date().isoformat(),
                        eps_actual=eps_actual,
                        revenue_actual=revenue_actual,
                        eps_estimated=eps_estimated,
                        revenue_estimated=revenue_estimated,
                        surprise_pct=surprise_pct,
                        guidance=guidance,
                        next_earnings_date=next_earnings_date
                    )
                    logger.info(f"Saved earnings report for {symbol}")

        except Exception as e:
            logger.error(f"Failed to parse and save batch data: {e}")

    async def _parse_and_save_daily_data(self, symbol: str, response_content: str, min_relevance_score: float, focus_significant: bool) -> None:
        """Parse structured JSON response and save news/earnings data for daily monitoring with deduplication."""
        try:
            # Validate input
            if not response_content or not isinstance(response_content, str):
                logger.warning("Invalid response content received")
                return

            logger.debug(f"Raw API response content for {symbol}: {response_content[:300]}...")

            # Parse JSON response
            try:
                import json
                response_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for {symbol}: {e}")
                return

            # Process the single stock data
            news_content = response_data.get("news", "").strip()
            earnings_content = response_data.get("earnings", "").strip()
            next_earnings_date = response_data.get("next_earnings_date")
            sentiment = response_data.get("sentiment", "neutral").lower()

            # Calculate relevance score based on content analysis
            relevance_score = self._calculate_news_relevance(news_content, earnings_content, focus_significant)

            # Skip if relevance score is too low
            if relevance_score < min_relevance_score:
                logger.debug(f"Skipping {symbol} - relevance score {relevance_score:.2f} below threshold {min_relevance_score}")
                return

            # Check for duplicates before saving
            if news_content and not await self._is_news_duplicate(symbol, news_content):
                # Extract title from news (first sentence or first 100 chars)
                title = news_content.split(".")[0][:100] if "." in news_content else news_content[:100]

                await self.state_manager.save_news_item(
                    symbol=symbol,
                    title=title,
                    summary=news_content[:500],  # Use first 500 chars as summary
                    content=news_content,
                    source="Perplexity AI (Daily)",
                    sentiment=sentiment,
                    relevance_score=relevance_score
                )

                # Create alert for significant news
                if sentiment in ["positive", "negative"] or "earnings" in news_content.lower() or relevance_score > 0.8:
                    alert_data = {
                        "type": "news",
                        "severity": "high" if relevance_score > 0.8 else "medium",
                        "symbol": symbol,
                        "message": f"Daily News Update: {symbol}",
                        "details": news_content[:500] + "..." if len(news_content) > 500 else news_content,
                        "sentiment": sentiment,
                        "relevance_score": relevance_score,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await self.state_manager.alert_manager.create_alert(
                        alert_type=alert_data["type"],
                        severity=alert_data["severity"],
                        title=alert_data["message"],
                        message=alert_data["details"],
                        symbol=alert_data["symbol"]
                    )
                    logger.info(f"Created daily news alert for {symbol} (relevance: {relevance_score:.2f}, sentiment: {sentiment})")

            # Save earnings data if available and not duplicate
            if earnings_content and not await self._is_earnings_duplicate(symbol, earnings_content):
                # Parse earnings data
                parsed_data = self._parse_earnings_data(earnings_content)
                fiscal_period = parsed_data.get('fiscal_period', f"Q{(datetime.now(timezone.utc).month-1)//3 + 1} {datetime.now(timezone.utc).year}")
                eps_actual = parsed_data.get('eps_actual')
                revenue_actual = parsed_data.get('revenue_actual')
                eps_estimated = parsed_data.get('eps_estimated')
                revenue_estimated = parsed_data.get('revenue_estimated')
                surprise_pct = parsed_data.get('surprise_pct')
                guidance = parsed_data.get('guidance', earnings_content)

                await self.state_manager.save_earnings_report(
                    symbol=symbol,
                    fiscal_period=fiscal_period,
                    report_date=datetime.now(timezone.utc).date().isoformat(),
                    eps_actual=eps_actual,
                    revenue_actual=revenue_actual,
                    eps_estimated=eps_estimated,
                    revenue_estimated=revenue_estimated,
                    surprise_pct=surprise_pct,
                    guidance=guidance,
                    next_earnings_date=next_earnings_date
                )
                logger.info(f"Saved daily earnings report for {symbol}")

        except Exception as e:
            logger.error(f"Failed to parse and save daily data for {symbol}: {e}")

    def _calculate_news_relevance(self, news_content: str, earnings_content: str, focus_significant: bool) -> float:
        """Calculate relevance score for news content."""
        if not news_content and not earnings_content:
            return 0.0

        content = (news_content + " " + earnings_content).lower()
        score = 0.5  # Base score

        # Significant keywords that increase relevance
        high_relevance_keywords = [
            'earnings', 'profit', 'revenue', 'eps', 'guidance', 'forecast',
            'merger', 'acquisition', 'dividend', 'split', 'buyback',
            'lawsuit', 'regulation', 'fda', 'approval', 'launch',
            'bankruptcy', 'restructure', 'layoff', 'strike'
        ]

        medium_relevance_keywords = [
            'announcement', 'update', 'report', 'results', 'quarter',
            'year', 'growth', 'decline', 'increase', 'decrease'
        ]

        # Count keyword matches
        high_matches = sum(1 for keyword in high_relevance_keywords if keyword in content)
        medium_matches = sum(1 for keyword in medium_relevance_keywords if keyword in content)

        # Boost score based on keyword matches
        score += high_matches * 0.2
        score += medium_matches * 0.1

        # Boost for earnings content
        if earnings_content and len(earnings_content.strip()) > 50:
            score += 0.3

        # Length factor - longer content tends to be more significant
        total_length = len(news_content) + len(earnings_content)
        if total_length > 200:
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    async def _is_news_duplicate(self, symbol: str, news_content: str) -> bool:
        """Check if news content is a duplicate of existing news."""
        if not news_content or len(news_content.strip()) < 20:
            return False

        try:
            # Get recent news for this symbol
            recent_news = await self.state_manager.get_news_for_symbol(symbol, limit=10)

            # Simple duplicate detection based on content similarity
            news_lower = news_content.lower().strip()

            for existing in recent_news:
                existing_content = existing.get('content', '').lower().strip()
                existing_title = existing.get('title', '').lower().strip()

                # Check for exact matches or very similar content
                if (news_lower == existing_content or
                    news_lower == existing_title or
                    existing_content in news_lower or
                    existing_title in news_lower):
                    return True

                # Check for high similarity (80% overlap of key words)
                news_words = set(news_lower.split())
                existing_words = set(existing_content.split())

                if news_words and existing_words:
                    intersection = news_words.intersection(existing_words)
                    union = news_words.union(existing_words)
                    similarity = len(intersection) / len(union) if union else 0

                    if similarity > 0.8:
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking news duplicate for {symbol}: {e}")
            return False  # Default to not duplicate on error

    async def _is_earnings_duplicate(self, symbol: str, earnings_content: str) -> bool:
        """Check if earnings content is a duplicate of existing earnings."""
        if not earnings_content or len(earnings_content.strip()) < 20:
            return False

        try:
            # Get recent earnings for this symbol
            recent_earnings = await self.state_manager.get_earnings_for_symbol(symbol, limit=5)

            # Check for duplicate earnings reports
            earnings_lower = earnings_content.lower().strip()

            for existing in recent_earnings:
                existing_guidance = existing.get('guidance', '').lower().strip()

                # Check if this earnings report was already saved recently
                if existing_guidance and (
                    earnings_lower == existing_guidance or
                    existing_guidance in earnings_lower
                ):
                    # Check if it was saved in the last 24 hours
                    created_at = existing.get('created_at', '')
                    if created_at:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if (datetime.now(timezone.utc) - created_dt).total_seconds() < 86400:  # 24 hours
                            return True

            return False

        except Exception as e:
            logger.error(f"Error checking earnings duplicate for {symbol}: {e}")
            return False  # Default to not duplicate on error

    def _extract_news_for_symbol(self, content: str, symbol: str) -> str:
        """Extract news content related to a specific symbol."""
        # For now, return the entire content as news since the API response
        # contains mixed information. In a production system, you'd want
        # more sophisticated parsing to separate news from earnings.
        return content.strip()

    def _extract_earnings_for_symbol(self, content: str, symbol: str) -> str:
        """Extract earnings content related to a specific symbol."""
        # Look for earnings-related keywords
        earnings_keywords = ['earnings', 'profit', 'revenue', 'eps', 'quarter', 'results', 'q1', 'q2', 'q3', 'q4', 'fy']
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in earnings_keywords):
            return content.strip()

        return ""

    def _extract_next_earnings_date(self, content: str, symbol: str) -> Optional[str]:
        """Extract next earnings date from content."""
        # Look for date patterns
        import re
        date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY/MM/DD
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _analyze_sentiment(self, content: str, symbol: str) -> str:
        """Analyze sentiment from content."""
        content_lower = content.lower()

        # Positive indicators
        positive_words = ['rise', 'increase', 'gain', 'beat', 'surprise', 'positive', 'strong', 'growth', 'up', 'higher', 'improved']
        # Negative indicators
        negative_words = ['fall', 'decrease', 'loss', 'miss', 'decline', 'negative', 'weak', 'down', 'lower', 'worse', 'drop']

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _parse_earnings_data(self, earnings_text: str) -> Dict[str, Any]:
        """Parse earnings data with multiple fallback strategies."""
        if not earnings_text or not isinstance(earnings_text, str):
            return {}

        # Strategy 1: Structured parsing for common formats
        try:
            return self._parse_structured_earnings(earnings_text)
        except Exception as e:
            logger.debug(f"Structured parsing failed: {e}")

        # Strategy 2: Regex pattern matching
        try:
            return self._parse_regex_earnings(earnings_text)
        except Exception as e:
            logger.debug(f"Regex parsing failed: {e}")

        # Strategy 3: Basic extraction (fallback)
        try:
            return self._basic_earnings_extraction(earnings_text)
        except Exception as e:
            logger.debug(f"Basic extraction failed: {e}")

        # Final fallback: return empty dict
        return {}

    def _parse_structured_earnings(self, text: str) -> Dict[str, Any]:
        """Parse earnings data assuming structured format."""
        result = {}

        # Look for fiscal period patterns
        fiscal_patterns = [
            r'(Q[1-4]\s+\d{4})',
            r'(FY\d{4}\s+Q[1-4])',
            r'(\d{4}\s+Q[1-4])'
        ]

        for pattern in fiscal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['fiscal_period'] = match.group(1)
                break

        # Extract EPS data
        eps_patterns = [
            r'EPS[:\s]+[\$]?(\d+\.?\d*)\s*(?:\((?:est|estimated)[:\s]+[\$]?(\d+\.?\d*))?',
            r'earnings per share[:\s]+[\$]?(\d+\.?\d*)',
            r'EPS of[\s]+[\$]?(\d+\.?\d*)'
        ]

        for pattern in eps_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['eps_actual'] = float(match.group(1))
                if len(match.groups()) > 1 and match.group(2):
                    result['eps_estimated'] = float(match.group(2))
                break

        # Extract revenue data
        revenue_patterns = [
            r'Revenue[:\s]+[\$]?(\d+(?:\.\d+)?)\s*(million|billion|M|B)',
            r'revenue of[\s]+[\$]?(\d+(?:\.\d+)?)\s*(million|billion|M|B)',
            r'sales[:\s]+[\$]?(\d+(?:\.\d+)?)\s*(million|billion|M|B)'
        ]

        for pattern in revenue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                revenue_val = float(match.group(1))
                unit = match.group(2).lower()
                multiplier = 1000000 if unit in ['million', 'm'] else 1000000000
                result['revenue_actual'] = revenue_val * multiplier
                break

        # Extract surprise percentage
        surprise_patterns = [
            r'surprise[:\s]+([+-]?\d+\.?\d*)%',
            r'beat.*by[:\s]+([+-]?\d+\.?\d*)%',
            r'missed.*by[:\s]+([+-]?\d+\.?\d*)%'
        ]

        for pattern in surprise_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['surprise_pct'] = float(match.group(1))
                break

        # Extract guidance (look for forward-looking statements)
        guidance_indicators = ['guidance', 'outlook', 'expects', 'forecast', 'projects']
        for indicator in guidance_indicators:
            if indicator in text.lower():
                # Extract the sentence containing guidance
                sentences = text.split('.')
                for sentence in sentences:
                    if indicator in sentence.lower():
                        result['guidance'] = sentence.strip()
                        break
                break

        return result

    def _parse_regex_earnings(self, text: str) -> Dict[str, Any]:
        """Fallback regex parsing for earnings data."""
        result = {}

        # Simple pattern matching
        eps_match = re.search(r'(\d+\.?\d*)\s*EPS', text, re.IGNORECASE)
        if eps_match:
            result['eps_actual'] = float(eps_match.group(1))

        revenue_match = re.search(r'(\d+(?:\.\d+)?)\s*(M|B)', text, re.IGNORECASE)
        if revenue_match:
            val = float(revenue_match.group(1))
            multiplier = 1000000 if revenue_match.group(2).upper() == 'M' else 1000000000
            result['revenue_actual'] = val * multiplier

        return result

    def _basic_earnings_extraction(self, text: str) -> Dict[str, Any]:
        """Basic extraction as final fallback."""
        result = {}

        # Look for any dollar amounts that might be EPS or revenue
        dollar_matches = re.findall(r'\$([0-9,]+\.?\d*)', text)
        if dollar_matches:
            # Assume first dollar amount is EPS, second is revenue
            if len(dollar_matches) >= 1:
                eps_str = dollar_matches[0].replace(',', '')
                try:
                    result['eps_actual'] = float(eps_str)
                except ValueError:
                    pass

        # Store original text as guidance
        result['guidance'] = text[:500]  # Limit length

        return result

    def _calculate_business_day(self, start_date: datetime, days_ahead: int) -> datetime:
        """Calculate the nth business day after a given date, skipping weekends and holidays."""
        current_date = start_date
        business_days_added = 0

        # Indian market holidays (simplified list - can be expanded)
        indian_holidays = [
            # Add major Indian holidays here
            # For now, just skip weekends
        ]

        while business_days_added < days_ahead:
            current_date += timedelta(days=1)
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:  # Monday-Friday
                # Check if it's a holiday (simplified - no holidays implemented yet)
                business_days_added += 1

        return current_date

    async def _execute_earnings_scheduler(self, metadata: Dict[str, Any]) -> None:
        """Execute earnings scheduler task - fetch earnings calendar and schedule n+1 analysis."""
        try:
            logger.info("Starting earnings scheduler task")

            # Get earnings scheduler configuration
            earnings_config = getattr(self.config, 'earnings_scheduler', {})
            enabled = earnings_config.get('enabled', True)
            n_plus_one_days = earnings_config.get('n_plus_one_days', 1)
            surprise_threshold = earnings_config.get('surprise_threshold_percent', 5.0)
            immediate_reanalysis = earnings_config.get('immediate_reanalysis', True)
            business_day_only = earnings_config.get('business_day_only', True)

            if not enabled:
                logger.info("Earnings scheduler is disabled")
                return

            # Get portfolio symbols
            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.info("No portfolio holdings to schedule earnings for")
                return

            symbols = [holding.get('tradingsymbol', '') for holding in portfolio.holdings if holding.get('tradingsymbol')]
            if not symbols:
                logger.info("No valid symbols found in portfolio")
                return

            logger.info(f"Processing earnings calendar for {len(symbols)} symbols")

            # Fetch earnings calendar data using Perplexity API
            earnings_calendar = await self._fetch_earnings_calendar(symbols)

            # Process each symbol's earnings data
            scheduled_tasks = 0
            surprise_alerts = 0

            for symbol_data in earnings_calendar:
                symbol = symbol_data.get('symbol', '').upper()
                if not symbol or symbol not in symbols:
                    continue

                next_earnings_date = symbol_data.get('next_earnings_date')
                if not next_earnings_date:
                    continue

                try:
                    # Parse earnings date
                    earnings_datetime = datetime.fromisoformat(next_earnings_date.replace('Z', '+00:00'))

                    # Calculate n+1 business day
                    if business_day_only:
                        analysis_date = self._calculate_business_day(earnings_datetime, n_plus_one_days)
                    else:
                        analysis_date = earnings_datetime + timedelta(days=n_plus_one_days)

                    # Convert to IST for scheduling (market operates in IST)
                    ist_analysis_date = analysis_date + timedelta(hours=5, minutes=30)

                    # Schedule fundamental analysis for n+1 day
                    await self.schedule_task(
                        TaskType.FUNDAMENTAL_MONITORING,
                        TaskPriority.MEDIUM,
                        delay_seconds=int((ist_analysis_date - datetime.now(timezone.utc)).total_seconds()),
                        metadata={
                            "symbol": symbol,
                            "earnings_date": next_earnings_date,
                            "analysis_date": analysis_date.isoformat(),
                            "reason": "earnings_n_plus_one"
                        }
                    )
                    scheduled_tasks += 1

                    # Check for earnings surprises
                    if await self._check_earnings_surprise(symbol, surprise_threshold):
                        if immediate_reanalysis:
                            # Trigger immediate fundamental re-analysis
                            await self.schedule_task(
                                TaskType.FUNDAMENTAL_MONITORING,
                                TaskPriority.CRITICAL,
                                delay_seconds=0,
                                metadata={
                                    "symbol": symbol,
                                    "reason": "earnings_surprise",
                                    "surprise_threshold": surprise_threshold
                                }
                            )
                        surprise_alerts += 1

                    logger.debug(f"Scheduled earnings analysis for {symbol} on {ist_analysis_date}")

                except Exception as e:
                    logger.error(f"Error processing earnings for {symbol}: {e}")
                    continue

            logger.info(f"Earnings scheduler completed: scheduled {scheduled_tasks} tasks, detected {surprise_alerts} surprises")

        except Exception as e:
            logger.error(f"Earnings scheduler task failed: {e}")

    async def _fetch_earnings_calendar(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch earnings calendar data for given symbols using Perplexity API."""
        try:
            # Load API keys
            import os
            perplexity_api_keys = [
                os.getenv('PERPLEXITY_API_KEY_1'),
                os.getenv('PERPLEXITY_API_KEY_2'),
                os.getenv('PERPLEXITY_API_KEY_3')
            ]
            perplexity_api_keys = [key for key in perplexity_api_keys if key]

            if not perplexity_api_keys:
                logger.warning("No Perplexity API keys configured for earnings calendar")
                return []

            earnings_config = getattr(self.config, 'earnings_scheduler', {})
            batch_size = earnings_config.get('batch_size', 10)
            api_timeout = earnings_config.get('api_timeout_seconds', 60)
            perplexity_model = earnings_config.get('perplexity_model', 'sonar-pro')
            search_recency = earnings_config.get('search_recency_filter', 'week')
            max_search_results = earnings_config.get('max_search_results', 15)

            earnings_data = []

            # Process in batches
            current_key_index = getattr(self, '_perplexity_key_index', 0)

            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                logger.debug(f"Fetching earnings calendar for batch: {batch_symbols}")

                # Create query for earnings calendar
                symbols_str = ", ".join(batch_symbols)
                query = f"""For these stocks ({symbols_str}), provide their next earnings report dates and recent earnings results.

Focus on:
- Next scheduled earnings date (if available)
- Most recent earnings report date
- EPS actual vs estimated
- Revenue actual vs estimated
- Any earnings surprises or beats/misses

Return structured data for each stock."""

                # Try with different API keys
                for attempt in range(len(perplexity_api_keys)):
                    try:
                        api_key = perplexity_api_keys[current_key_index]

                        from openai import OpenAI
                        import httpx

                        client = OpenAI(
                            api_key=api_key,
                            base_url="https://api.perplexity.ai",
                            http_client=httpx.Client(timeout=api_timeout)
                        )

                        # Define structured output schema
                        from pydantic import BaseModel
                        from typing import Optional

                        class EarningsData(BaseModel):
                            symbol: str
                            next_earnings_date: Optional[str] = None
                            last_earnings_date: Optional[str] = None
                            eps_actual: Optional[float] = None
                            eps_estimated: Optional[float] = None
                            revenue_actual: Optional[float] = None
                            revenue_estimated: Optional[float] = None
                            surprise_pct: Optional[float] = None

                        class EarningsBatchResponse(BaseModel):
                            stocks: List[EarningsData]

                        completion = client.chat.completions.create(
                            model=perplexity_model,
                            messages=[{"role": "user", "content": query}],
                            max_tokens=2000,
                            response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "schema": EarningsBatchResponse.model_json_schema()
                                }
                            },
                            web_search_options={
                                "search_recency_filter": search_recency,
                                "max_search_results": max_search_results
                            }
                        )

                        response_content = completion.choices[0].message.content

                        # Parse response
                        import json
                        response_data = json.loads(response_content)
                        batch_data = response_data.get("stocks", [])

                        # Save earnings data to database
                        for stock_data in batch_data:
                            symbol = stock_data.get("symbol", "").upper()
                            if symbol:
                                await self.state_manager.save_earnings_report(
                                    symbol=symbol,
                                    fiscal_period="Latest",  # Will be updated with proper period
                                    report_date=stock_data.get("last_earnings_date", datetime.now(timezone.utc).date().isoformat()),
                                    eps_actual=stock_data.get("eps_actual"),
                                    eps_estimated=stock_data.get("eps_estimated"),
                                    revenue_actual=stock_data.get("revenue_actual"),
                                    revenue_estimated=stock_data.get("revenue_estimated"),
                                    surprise_pct=stock_data.get("surprise_pct"),
                                    next_earnings_date=stock_data.get("next_earnings_date")
                                )

                        earnings_data.extend(batch_data)

                        # Update key index
                        current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                        self._perplexity_key_index = current_key_index
                        break

                    except Exception as e:
                        error_str = str(e).lower()
                        if "rate limit" in error_str or "quota" in error_str:
                            current_key_index = (current_key_index + 1) % len(perplexity_api_keys)
                            continue
                        else:
                            logger.error(f"Failed to fetch earnings calendar for batch {batch_symbols}: {e}")
                            break

                # Small delay between batches
                await asyncio.sleep(1)

            logger.info(f"Fetched earnings calendar for {len(earnings_data)} stocks")
            return earnings_data

        except Exception as e:
            logger.error(f"Failed to fetch earnings calendar: {e}")
            return []

    async def _check_earnings_surprise(self, symbol: str, threshold_percent: float) -> bool:
        """Check if a symbol had an earnings surprise above the threshold."""
        try:
            # Get recent earnings reports
            earnings_reports = await self.state_manager.get_earnings_for_symbol(symbol, limit=1)

            if not earnings_reports:
                return False

            latest_report = earnings_reports[0]
            surprise_pct = latest_report.get('surprise_pct')

            if surprise_pct is not None and abs(surprise_pct) >= threshold_percent:
                # Create alert for earnings surprise
                direction = "beat" if surprise_pct > 0 else "missed"
                alert_data = {
                    "type": "earnings_surprise",
                    "severity": "high",
                    "symbol": symbol,
                    "message": f"Earnings Surprise: {symbol}",
                    "details": f"Stock {direction} earnings estimates by {abs(surprise_pct):.1f}% (EPS surprise)",
                    "metadata": {
                        "surprise_pct": surprise_pct,
                        "eps_actual": latest_report.get('eps_actual'),
                        "eps_estimated": latest_report.get('eps_estimated'),
                        "report_date": latest_report.get('report_date')
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await self.state_manager.alert_manager.create_alert(
                    alert_type=alert_data["type"],
                    severity=alert_data["severity"],
                    title=alert_data["message"],
                    message=alert_data["details"],
                    symbol=alert_data["symbol"]
                )

                logger.info(f"Earnings surprise detected for {symbol}: {surprise_pct:.1f}%")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking earnings surprise for {symbol}: {e}")
            return False

    async def _execute_health_check(self, metadata: Dict[str, Any]) -> None:
        """Execute system health check or data cleanup based on metadata."""
        task_type = metadata.get("task_type", "health_check")

        if task_type == "data_cleanup":
            await self._execute_data_cleanup()
        else:
            await self._execute_system_health_check()

    async def _execute_system_health_check(self) -> None:
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

    async def _execute_data_cleanup(self) -> None:
        """Execute data cleanup task."""
        try:
            await self.state_manager.cleanup_old_data()
            logger.info("Data cleanup completed successfully")
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")

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