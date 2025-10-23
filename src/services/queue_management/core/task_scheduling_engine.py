"""Task Scheduling Engine - Advanced task scheduling with dependencies and priorities."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import heapq

from ....models.scheduler import QueueName, SchedulerTask, TaskStatus, TaskType
from ....services.scheduler.task_service import SchedulerTaskService
from ....core.event_bus import EventBus, Event, EventType
from ..config.service_config import QueueManagementConfig

logger = logging.getLogger(__name__)


class SchedulingStrategy(Enum):
    """Task scheduling strategies."""
    PRIORITY_QUEUE = "priority_queue"
    ROUND_ROBIN = "round_robin"
    FAIR_SHARE = "fair_share"
    DEADLINE_BASED = "deadline_based"


class TaskDependencyType(Enum):
    """Types of task dependencies."""
    COMPLETION = "completion"  # Task must complete before dependent task
    SUCCESS = "success"        # Task must succeed before dependent task
    FAILURE = "failure"        # Task must fail before dependent task (for retry logic)


@dataclass(order=True)
class ScheduledTask:
    """Task wrapper for priority scheduling."""
    priority: int
    task: SchedulerTask = field(compare=False)
    scheduled_time: datetime = field(compare=False)
    dependency_count: int = field(compare=False, default=0)

    def __lt__(self, other):
        # For heapq, lower priority number means higher priority
        return self.priority < other.priority


@dataclass
class SchedulingRule:
    """Rule for task scheduling decisions."""
    rule_id: str
    queue_name: QueueName
    task_types: List[TaskType]
    priority_boost: int = 0
    max_concurrent: int = 1
    timeout_seconds: int = 300
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)


class TaskSchedulingEngine:
    """Advanced task scheduling engine with dependency management and prioritization."""

    def __init__(
        self,
        task_service: SchedulerTaskService,
        event_bus: EventBus,
        config: QueueManagementConfig
    ):
        """Initialize scheduling engine."""
        self.task_service = task_service
        self.event_bus = event_bus
        self.config = config

        # Scheduling state
        self._running = False
        self._scheduling_strategy = SchedulingStrategy.PRIORITY_QUEUE

        # Task queues and dependencies
        self._priority_queue: List[ScheduledTask] = []
        self._task_dependencies: Dict[str, Set[str]] = {}  # task_id -> dependent task_ids
        self._reverse_dependencies: Dict[str, Set[str]] = {}  # task_id -> prerequisite task_ids
        self._running_tasks: Dict[str, SchedulerTask] = {}
        self._queue_concurrency: Dict[QueueName, asyncio.Semaphore] = {}

        # Scheduling rules
        self._scheduling_rules: Dict[str, SchedulingRule] = {}

        # Performance tracking
        self._scheduling_metrics: Dict[str, Any] = {
            "tasks_scheduled": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_queue_time": 0.0,
            "scheduling_cycles": 0
        }

        # Control
        self._scheduling_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

        # Setup default scheduling rules
        self._setup_default_scheduling_rules()

    def _setup_default_scheduling_rules(self) -> None:
        """Setup default scheduling rules for different task types."""
        # Portfolio sync rules
        portfolio_sync_rule = SchedulingRule(
            rule_id="portfolio_sync_high_priority",
            queue_name=QueueName.PORTFOLIO_SYNC,
            task_types=[TaskType.SYNC_ACCOUNT_BALANCES, TaskType.UPDATE_POSITIONS],
            priority_boost=5,
            max_concurrent=1,  # Sequential for data consistency
            timeout_seconds=300,
            retry_policy={"max_retries": 3, "backoff_factor": 2.0}
        )

        # Data fetcher rules
        data_fetcher_rule = SchedulingRule(
            rule_id="data_fetcher_parallel",
            queue_name=QueueName.DATA_FETCHER,
            task_types=[TaskType.NEWS_MONITORING, TaskType.EARNINGS_CHECK, TaskType.FUNDAMENTALS_UPDATE],
            priority_boost=3,
            max_concurrent=3,  # Allow parallel data fetching
            timeout_seconds=600,
            retry_policy={"max_retries": 5, "backoff_factor": 1.5}
        )

        # AI analysis rules - highest priority
        ai_analysis_rule = SchedulingRule(
            rule_id="ai_analysis_critical",
            queue_name=QueueName.AI_ANALYSIS,
            task_types=[TaskType.CLAUDE_MORNING_PREP, TaskType.RECOMMENDATION_GENERATION],
            priority_boost=8,
            max_concurrent=2,  # Limited concurrency for AI resource management
            timeout_seconds=900,
            retry_policy={"max_retries": 2, "backoff_factor": 3.0}
        )

        # Earnings scheduler - time-sensitive
        earnings_scheduler_rule = SchedulingRule(
            rule_id="earnings_scheduler_urgent",
            queue_name=QueueName.DATA_FETCHER,
            task_types=[TaskType.EARNINGS_SCHEDULER],
            priority_boost=7,
            max_concurrent=1,
            timeout_seconds=1800,  # Longer timeout for complex scheduling
            conditions={"market_hours": True}
        )

        self._scheduling_rules = {
            rule.rule_id: rule for rule in [
                portfolio_sync_rule,
                data_fetcher_rule,
                ai_analysis_rule,
                earnings_scheduler_rule
            ]
        }

        # Initialize concurrency semaphores
        for queue_name in QueueName:
            max_concurrent = max(
                rule.max_concurrent for rule in self._scheduling_rules.values()
                if rule.queue_name == queue_name
            ) if any(rule.queue_name == queue_name for rule in self._scheduling_rules.values()) else 1
            self._queue_concurrency[queue_name] = asyncio.Semaphore(max_concurrent)

    async def initialize(self) -> None:
        """Initialize the scheduling engine."""
        logger.info("Initializing Task Scheduling Engine...")

        # Register event handlers
        await self._register_event_handlers()

        # Load existing tasks and dependencies
        await self._load_existing_tasks()

        logger.info("Task Scheduling Engine initialized")

    async def start(self) -> None:
        """Start the scheduling engine."""
        if self._running:
            return

        self._running = True
        logger.info("Task Scheduling Engine started")

        # Start scheduling loop
        asyncio.create_task(self._scheduling_loop())

    async def stop(self) -> None:
        """Stop the scheduling engine."""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Cancel running tasks
        for task_id, task in self._running_tasks.items():
            logger.info(f"Cancelling running task: {task_id}")
            # Note: Actual task cancellation would be handled by the queue implementations

        self._running_tasks.clear()
        logger.info("Task Scheduling Engine stopped")

    async def _register_event_handlers(self) -> None:
        """Register event handlers for task lifecycle events."""
        class SchedulingEventHandler:
            def __init__(self, scheduling_engine):
                self.scheduling_engine = scheduling_engine

            async def handle_event(self, event: Event) -> None:
                await self.scheduling_engine._handle_task_event(event)

        handler = SchedulingEventHandler(self)

        # Register for task-related events
        task_events = [
            EventType.TASK_COMPLETED,
            EventType.TASK_FAILED,
            EventType.TASK_COMPLETED,  # For dependency resolution
        ]

        for event_type in task_events:
            self.event_bus.subscribe(event_type, handler)

        logger.info("Scheduling event handlers registered")

    async def _handle_task_event(self, event: Event) -> None:
        """Handle task lifecycle events for dependency management."""
        if not self._running:
            return

        task_id = event.data.get("task_id")
        if not task_id:
            return

        if event.type == EventType.TASK_COMPLETED:
            await self._resolve_task_dependencies(task_id, success=True)
        elif event.type == EventType.TASK_FAILED:
            await self._resolve_task_dependencies(task_id, success=False)

    async def _resolve_task_dependencies(self, completed_task_id: str, success: bool) -> None:
        """Resolve dependencies for a completed task."""
        if completed_task_id not in self._task_dependencies:
            return

        dependent_task_ids = self._task_dependencies[completed_task_id]

        for dependent_id in dependent_task_ids:
            # Check if all prerequisites are met
            if dependent_id in self._reverse_dependencies:
                prerequisites = self._reverse_dependencies[dependent_id]

                # Check if all prerequisites are satisfied
                all_satisfied = True
                for prereq_id in prerequisites:
                    prereq_task = await self.task_service.get_task(prereq_id)
                    if not prereq_task or prereq_task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        all_satisfied = False
                        break

                if all_satisfied:
                    # Mark dependent task as ready
                    dependent_task = await self.task_service.get_task(dependent_id)
                    if dependent_task and dependent_task.status == TaskStatus.PENDING:
                        # Update task to be schedulable
                        await self._schedule_task(dependent_task)

    async def _load_existing_tasks(self) -> None:
        """Load existing tasks and rebuild dependency graph."""
        logger.info("Loading existing tasks for scheduling...")

        # This would load tasks from the database and rebuild the dependency graph
        # For now, we'll start with an empty state
        pass

    async def _scheduling_loop(self) -> None:
        """Main scheduling loop."""
        logger.info("Starting scheduling loop")

        while not self._shutdown_event.is_set():
            try:
                await self._scheduling_cycle()
                self._scheduling_metrics["scheduling_cycles"] += 1

                # Wait before next cycle
                await asyncio.sleep(1)  # 1 second scheduling interval

            except Exception as e:
                logger.error(f"Scheduling cycle error: {e}")
                await asyncio.sleep(5)  # Back off on errors

        logger.info("Scheduling loop stopped")

    async def _scheduling_cycle(self) -> None:
        """Single scheduling cycle."""
        async with self._scheduling_lock:
            # Get pending tasks from all queues
            for queue_name in QueueName:
                try:
                    pending_tasks = await self.task_service.get_pending_tasks(queue_name)

                    for task in pending_tasks:
                        if task.task_id not in self._running_tasks:
                            await self._schedule_task(task)

                except Exception as e:
                    logger.error(f"Error processing queue {queue_name.value}: {e}")

            # Execute scheduled tasks
            await self._execute_scheduled_tasks()

    async def _schedule_task(self, task: SchedulerTask) -> None:
        """Schedule a task for execution."""
        # Apply scheduling rules
        rule = self._find_applicable_rule(task)
        priority = task.priority

        if rule:
            priority += rule.priority_boost

            # Check rule conditions
            if not self._evaluate_rule_conditions(rule, task):
                return  # Don't schedule if conditions not met

        # Create scheduled task
        scheduled_task = ScheduledTask(
            priority=priority,
            task=task,
            scheduled_time=datetime.utcnow(),
            dependency_count=len(task.dependencies)
        )

        # Add to priority queue
        heapq.heappush(self._priority_queue, scheduled_task)

        self._scheduling_metrics["tasks_scheduled"] += 1
        logger.debug(f"Scheduled task: {task.task_id} with priority {priority}")

    def _find_applicable_rule(self, task: SchedulerTask) -> Optional[SchedulingRule]:
        """Find the applicable scheduling rule for a task."""
        for rule in self._scheduling_rules.values():
            if rule.queue_name == task.queue_name and task.task_type in rule.task_types:
                return rule
        return None

    def _evaluate_rule_conditions(self, rule: SchedulingRule, task: SchedulerTask) -> bool:
        """Evaluate if rule conditions are met."""
        conditions = rule.conditions

        # Check market hours condition
        if "market_hours" in conditions:
            # This would check if market is open
            # For now, assume always true
            pass

        # Add more condition checks as needed
        return True

    async def _execute_scheduled_tasks(self) -> None:
        """Execute scheduled tasks respecting concurrency limits."""
        # Execute tasks from priority queue
        tasks_to_execute = []

        while self._priority_queue and len(self._running_tasks) < self.config.max_concurrent_tasks:
            scheduled_task = heapq.heappop(self._priority_queue)

            # Check if task is still valid
            current_task = await self.task_service.get_task(scheduled_task.task.task_id)
            if not current_task or current_task.status != TaskStatus.PENDING:
                continue

            # Check queue concurrency
            queue_semaphore = self._queue_concurrency[scheduled_task.task.queue_name]
            if queue_semaphore.locked():
                # Put back in queue if concurrency limit reached
                heapq.heappush(self._priority_queue, scheduled_task)
                break

            tasks_to_execute.append(scheduled_task)

        # Execute selected tasks
        for scheduled_task in tasks_to_execute:
            asyncio.create_task(self._execute_task_with_concurrency(scheduled_task))

    async def _execute_task_with_concurrency(self, scheduled_task: ScheduledTask) -> None:
        """Execute a task with concurrency control."""
        task = scheduled_task.task
        queue_semaphore = self._queue_concurrency[task.queue_name]

        async with queue_semaphore:
            self._running_tasks[task.task_id] = task

            try:
                # Execute the task
                result = await self.task_service.execute_task(task)

                if result["success"]:
                    self._scheduling_metrics["tasks_completed"] += 1
                    logger.info(f"Task completed: {task.task_id}")
                else:
                    self._scheduling_metrics["tasks_failed"] += 1
                    logger.error(f"Task failed: {task.task_id} - {result.get('error')}")

            except Exception as e:
                logger.error(f"Task execution error: {task.task_id} - {e}")
                self._scheduling_metrics["tasks_failed"] += 1
            finally:
                # Remove from running tasks
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]

    async def schedule_task_with_dependencies(
        self,
        queue_name: QueueName,
        task_type: TaskType,
        payload: Dict[str, Any],
        dependencies: Optional[List[str]] = None,
        priority: int = 5
    ) -> SchedulerTask:
        """Schedule a new task with dependency management."""
        # Create the task
        task = await self.task_service.create_task(
            queue_name=queue_name,
            task_type=task_type,
            payload=payload,
            priority=priority,
            dependencies=dependencies or []
        )

        # Register dependencies
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self._task_dependencies:
                    self._task_dependencies[dep_id] = set()
                self._task_dependencies[dep_id].add(task.task_id)

                if task.task_id not in self._reverse_dependencies:
                    self._reverse_dependencies[task.task_id] = set()
                self._reverse_dependencies[task.task_id].add(dep_id)

        # Schedule the task
        await self._schedule_task(task)

        return task

    def get_scheduling_status(self) -> Dict[str, Any]:
        """Get current scheduling status."""
        return {
            "running": self._running,
            "strategy": self._scheduling_strategy.value,
            "priority_queue_size": len(self._priority_queue),
            "running_tasks": len(self._running_tasks),
            "active_dependencies": len(self._task_dependencies),
            "scheduling_rules": len(self._scheduling_rules),
            "metrics": self._scheduling_metrics.copy(),
            "queue_concurrency": {
                queue.value: semaphore._value for queue, semaphore in self._queue_concurrency.items()
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if we can access task service
            stats = await self.task_service.get_all_queue_statistics()

            return {
                "status": "healthy" if self._running else "stopped",
                "priority_queue_size": len(self._priority_queue),
                "running_tasks": len(self._running_tasks),
                "queue_statistics_available": len(stats) > 0,
                "scheduling_cycles": self._scheduling_metrics["scheduling_cycles"]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }