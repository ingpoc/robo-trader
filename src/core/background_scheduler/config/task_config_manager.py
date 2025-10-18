"""
Task configuration management.

Handles configuration reloading and task synchronization based on config changes.
"""

from datetime import datetime, timezone, timedelta, time
from typing import Dict, Any, Optional, Set

from loguru import logger

from ..models import TaskType, TaskPriority


class TaskConfigManager:
    """Manages task configuration and updates."""

    def __init__(self):
        """Initialize config manager."""
        self._config = None

    async def reload_config(self, new_config: Any, task_scheduler: Any) -> None:
        """Reload configuration and update task frequencies.

        Args:
            new_config: New configuration object
            task_scheduler: TaskScheduler instance to update tasks
        """
        self._config = new_config
        logger.info("Starting config reload")

        if not hasattr(new_config, 'agents'):
            logger.warning("No agents configuration found")
            return

        agents_config = new_config.agents

        await self._update_existing_tasks(agents_config, task_scheduler)
        await self._schedule_new_tasks(agents_config, task_scheduler)

        logger.info("Scheduler config reloaded successfully")

    async def _update_existing_tasks(self, agents_config: Any, task_scheduler: Any) -> None:
        """Update frequencies and status of existing tasks.

        Args:
            agents_config: Agents configuration
            task_scheduler: TaskScheduler instance
        """
        task_config_map = self._get_task_config_map(agents_config)

        for task_id, task in list(task_scheduler.tasks.items()):
            if task.task_type in task_config_map:
                config = task_config_map[task.task_type]
                task.interval_seconds = config.get('interval_seconds')
                task.is_active = config.get('enabled', True)

                from ..stores.task_store import TaskStore
                await TaskStore.save_task(task_scheduler.state_dir, task_scheduler.tasks)

    async def _schedule_new_tasks(self, agents_config: Any, task_scheduler: Any) -> None:
        """Schedule newly enabled tasks that aren't yet scheduled.

        Args:
            agents_config: Agents configuration
            task_scheduler: TaskScheduler instance
        """
        scheduled_types = {task.task_type for task in task_scheduler.tasks.values()}

        if (agents_config.market_monitoring.enabled and
                TaskType.MARKET_MONITORING not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.MARKET_MONITORING,
                TaskPriority.MEDIUM,
                delay_seconds=60,
                interval_seconds=agents_config.market_monitoring.frequency_seconds
            )

        if (agents_config.stop_loss_monitor.enabled and
                TaskType.STOP_LOSS_MONITOR not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.STOP_LOSS_MONITOR,
                TaskPriority.HIGH,
                delay_seconds=30,
                interval_seconds=agents_config.stop_loss_monitor.frequency_seconds
            )

        if (agents_config.earnings_check.enabled and
                TaskType.EARNINGS_CHECK not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.EARNINGS_CHECK,
                TaskPriority.MEDIUM,
                interval_seconds=agents_config.earnings_check.frequency_seconds
            )

        earnings_scheduler_config = getattr(self._config, 'earnings_scheduler', {})
        if (earnings_scheduler_config.get('enabled', True) and
                TaskType.EARNINGS_SCHEDULER not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.EARNINGS_SCHEDULER,
                TaskPriority.MEDIUM,
                interval_seconds=earnings_scheduler_config.get('frequency_seconds', 3600)
            )

        if (agents_config.news_monitoring.enabled and
                TaskType.NEWS_MONITORING not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.NEWS_MONITORING,
                TaskPriority.MEDIUM,
                interval_seconds=agents_config.news_monitoring.frequency_seconds
            )

        fundamental_config = getattr(agents_config, 'fundamental_monitoring', {})
        if (fundamental_config.get('enabled', True) and
                TaskType.FUNDAMENTAL_MONITORING not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.FUNDAMENTAL_MONITORING,
                TaskPriority.MEDIUM,
                interval_seconds=fundamental_config.get('frequency_seconds', 86400)
            )

        if (agents_config.health_check.enabled and
                TaskType.HEALTH_CHECK not in scheduled_types):
            await task_scheduler.schedule_task(
                TaskType.HEALTH_CHECK,
                TaskPriority.LOW,
                interval_seconds=agents_config.health_check.frequency_seconds
            )

        if (agents_config.ai_daily_planning.enabled and
                TaskType.AI_PLANNING not in scheduled_types):
            await self._schedule_time_based_task(
                TaskType.AI_PLANNING,
                task_scheduler,
                hour=8,
                minute=30,
                priority=TaskPriority.HIGH,
                interval_seconds=agents_config.ai_daily_planning.frequency_seconds,
                metadata={"planning_type": "daily"}
            )

        news_daily_config = getattr(self._config, 'news_daily_scheduler', {})
        if (news_daily_config.get('enabled', True) and
                TaskType.NEWS_DAILY not in scheduled_types):
            execution_time_ist = news_daily_config.get('execution_time_ist', '09:00')
            hour, minute = map(int, execution_time_ist.split(':'))

            await self._schedule_time_based_task(
                TaskType.NEWS_DAILY,
                task_scheduler,
                hour=hour,
                minute=minute,
                priority=TaskPriority.MEDIUM,
                interval_seconds=86400,
                metadata={"execution_time_ist": execution_time_ist}
            )

    async def _schedule_time_based_task(
        self,
        task_type: TaskType,
        task_scheduler: Any,
        hour: int,
        minute: int,
        priority: TaskPriority = TaskPriority.MEDIUM,
        interval_seconds: int = 86400,
        metadata: Optional[Dict] = None
    ) -> None:
        """Schedule a task for a specific time of day (IST).

        Args:
            task_type: Type of task to schedule
            task_scheduler: TaskScheduler instance
            hour: Hour in IST (0-23)
            minute: Minute in IST (0-59)
            priority: Task priority
            interval_seconds: Repeat interval
            metadata: Task metadata
        """
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        target_time = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if now_ist.time() >= time(hour, minute):
            target_time += timedelta(days=1)

        delay_seconds = int((target_time - now_ist).total_seconds())

        await task_scheduler.schedule_task(
            task_type,
            priority,
            delay_seconds=delay_seconds,
            interval_seconds=interval_seconds,
            metadata=metadata
        )

        logger.info(f"Scheduled {task_type.value} for {target_time} IST")

    @staticmethod
    def _get_task_config_map(agents_config: Any) -> Dict[TaskType, Dict[str, Any]]:
        """Get mapping of task types to their configuration.

        Args:
            agents_config: Agents configuration

        Returns:
            Dictionary mapping TaskType to config dict
        """
        return {
            TaskType.MARKET_MONITORING: {
                "interval_seconds": agents_config.market_monitoring.frequency_seconds,
                "enabled": agents_config.market_monitoring.enabled
            },
            TaskType.STOP_LOSS_MONITOR: {
                "interval_seconds": agents_config.stop_loss_monitor.frequency_seconds,
                "enabled": agents_config.stop_loss_monitor.enabled
            },
            TaskType.EARNINGS_CHECK: {
                "interval_seconds": agents_config.earnings_check.frequency_seconds,
                "enabled": agents_config.earnings_check.enabled
            },
            TaskType.NEWS_MONITORING: {
                "interval_seconds": agents_config.news_monitoring.frequency_seconds,
                "enabled": agents_config.news_monitoring.enabled
            },
            TaskType.HEALTH_CHECK: {
                "interval_seconds": agents_config.health_check.frequency_seconds,
                "enabled": agents_config.health_check.enabled
            },
            TaskType.PORTFOLIO_SCAN: {
                "interval_seconds": agents_config.portfolio_scan.frequency_seconds,
                "enabled": agents_config.portfolio_scan.enabled
            },
            TaskType.MARKET_SCREENING: {
                "interval_seconds": agents_config.market_screening.frequency_seconds,
                "enabled": agents_config.market_screening.enabled
            }
        }

    def get_current_config(self) -> Any:
        """Get current configuration.

        Returns:
            Current configuration object
        """
        return self._config
