"""Queue Orchestration Layer - Advanced task orchestration and coordination."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ....models.scheduler import QueueName, SchedulerTask, TaskStatus, TaskType
from ....services.scheduler.task_service import SchedulerTaskService
from ....core.event_bus import EventBus, Event, EventType
from ..config.service_config import QueueManagementConfig

logger = logging.getLogger(__name__)


class OrchestrationMode(Enum):
    """Orchestration execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    EVENT_DRIVEN = "event_driven"


class QueuePriority(Enum):
    """Queue execution priorities."""
    CRITICAL = 10
    HIGH = 7
    NORMAL = 5
    LOW = 3
    BACKGROUND = 1


@dataclass
class OrchestrationRule:
    """Rule for orchestrating queue execution."""
    rule_id: str
    source_queues: List[QueueName]
    target_queues: List[QueueName]
    trigger_events: List[EventType]
    conditions: Dict[str, Any]
    priority: QueuePriority = QueuePriority.NORMAL
    timeout_seconds: int = 300
    max_concurrent: int = 1


@dataclass
class ExecutionContext:
    """Context for queue execution."""
    execution_id: str
    mode: OrchestrationMode
    start_time: datetime
    queues: List[QueueName]
    rules: List[OrchestrationRule]
    metadata: Dict[str, Any]


class QueueOrchestrationLayer:
    """Advanced queue orchestration with complex coordination logic."""

    def __init__(
        self,
        task_service: SchedulerTaskService,
        event_bus: EventBus,
        config: QueueManagementConfig
    ):
        """Initialize orchestration layer."""
        self.task_service = task_service
        self.event_bus = event_bus
        self.config = config

        # Orchestration state
        self._running = False
        self._active_executions: Dict[str, ExecutionContext] = {}
        self._orchestration_rules: Dict[str, OrchestrationRule] = {}

        # Execution coordination
        self._execution_lock = asyncio.Lock()
        self._event_handlers_registered = False

        # Performance tracking
        self._execution_metrics: Dict[str, Dict[str, Any]] = {}

        # Setup default orchestration rules
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default orchestration rules for trading workflow."""
        # Portfolio sync → Data fetcher rule
        portfolio_to_data_rule = OrchestrationRule(
            rule_id="portfolio_to_data_fetcher",
            source_queues=[QueueName.PORTFOLIO_SYNC],
            target_queues=[QueueName.DATA_FETCHER],
            trigger_events=[EventType.TASK_COMPLETED],
            conditions={
                "task_types": ["sync_account_balances", "update_positions"],
                "success_required": True
            },
            priority=QueuePriority.HIGH,
            timeout_seconds=600
        )

        # Data fetcher → AI analysis rule
        data_to_ai_rule = OrchestrationRule(
            rule_id="data_fetcher_to_ai_analysis",
            source_queues=[QueueName.DATA_FETCHER],
            target_queues=[QueueName.AI_ANALYSIS],
            trigger_events=[EventType.TASK_COMPLETED, EventType.MARKET_NEWS],
            conditions={
                "task_types": ["fundamentals_update", "news_monitoring", "earnings_check"],
                "market_impact_threshold": 0.7
            },
            priority=QueuePriority.CRITICAL,
            timeout_seconds=900
        )

        # Market event trigger rule
        market_event_rule = OrchestrationRule(
            rule_id="market_event_trigger",
            source_queues=[QueueName.DATA_FETCHER],
            target_queues=[QueueName.AI_ANALYSIS],
            trigger_events=[EventType.MARKET_NEWS, EventType.EARNINGS_ANNOUNCEMENT],
            conditions={
                "impact_score": ">0.8",
                "sentiment": ["NEGATIVE", "HIGH_VOLATILITY"]
            },
            priority=QueuePriority.CRITICAL,
            timeout_seconds=300,
            max_concurrent=3
        )

        self._orchestration_rules = {
            rule.rule_id: rule for rule in [
                portfolio_to_data_rule,
                data_to_ai_rule,
                market_event_rule
            ]
        }

    async def initialize(self) -> None:
        """Initialize the orchestration layer."""
        logger.info("Initializing Queue Orchestration Layer...")

        # Register event handlers
        await self._register_event_handlers()

        logger.info("Queue Orchestration Layer initialized")

    async def start(self) -> None:
        """Start the orchestration layer."""
        if self._running:
            return

        self._running = True
        logger.info("Queue Orchestration Layer started")

    async def stop(self) -> None:
        """Stop the orchestration layer."""
        if not self._running:
            return

        self._running = False

        # Cancel active executions
        for execution_id in list(self._active_executions.keys()):
            await self._cancel_execution(execution_id)

        logger.info("Queue Orchestration Layer stopped")

    async def _register_event_handlers(self) -> None:
        """Register event handlers for orchestration triggers."""
        if self._event_handlers_registered:
            return

        # Create event handler for orchestration events
        class OrchestrationEventHandler:
            def __init__(self, orchestration_layer):
                self.orchestration_layer = orchestration_layer

            async def handle_event(self, event: Event) -> None:
                await self.orchestration_layer._handle_orchestration_event(event)

        handler = OrchestrationEventHandler(self)

        # Register for all orchestration-relevant events
        orchestration_events = [
            EventType.TASK_COMPLETED,
            EventType.TASK_FAILED,
            EventType.MARKET_NEWS,
            EventType.EARNINGS_ANNOUNCEMENT,
            EventType.RISK_BREACH,
            EventType.EXECUTION_ORDER_FILLED
        ]

        for event_type in orchestration_events:
            self.event_bus.subscribe(event_type, handler)

        self._event_handlers_registered = True
        logger.info("Orchestration event handlers registered")

    async def _handle_orchestration_event(self, event: Event) -> None:
        """Handle orchestration events and trigger rules."""
        if not self._running:
            return

        logger.debug(f"Processing orchestration event: {event.type.value}")

        # Find matching rules
        matching_rules = []
        for rule in self._orchestration_rules.values():
            if event.type in rule.trigger_events:
                if self._evaluate_rule_conditions(rule, event):
                    matching_rules.append(rule)

        if not matching_rules:
            return

        # Execute matching rules
        for rule in matching_rules:
            try:
                await self._execute_orchestration_rule(rule, event)
            except Exception as e:
                logger.error(f"Failed to execute orchestration rule {rule.rule_id}: {e}")

    def _evaluate_rule_conditions(self, rule: OrchestrationRule, event: Event) -> bool:
        """Evaluate if rule conditions are met for the event."""
        conditions = rule.conditions

        # Check task types condition
        if "task_types" in conditions:
            required_types = conditions["task_types"]
            event_task_type = event.data.get("task_type")
            if event_task_type not in required_types:
                return False

        # Check success condition
        if conditions.get("success_required", False):
            if not event.data.get("success", True):
                return False

        # Check impact score
        if "impact_score" in conditions:
            threshold = conditions["impact_score"]
            if isinstance(threshold, str) and threshold.startswith(">"):
                min_score = float(threshold[1:])
                event_score = event.data.get("impact_score", 0)
                if event_score <= min_score:
                    return False
            elif isinstance(threshold, (int, float)):
                if event.data.get("impact_score", 0) != threshold:
                    return False

        # Check market conditions
        if "market_impact_threshold" in conditions:
            threshold = conditions["market_impact_threshold"]
            impact_score = event.data.get("impact_score", 0)
            if impact_score < threshold:
                return False

        # Check sentiment
        if "sentiment" in conditions:
            required_sentiments = conditions["sentiment"]
            event_sentiment = event.data.get("sentiment")
            if event_sentiment not in required_sentiments:
                return False

        return True

    async def _execute_orchestration_rule(self, rule: OrchestrationRule, trigger_event: Event) -> None:
        """Execute an orchestration rule."""
        logger.info(f"Executing orchestration rule: {rule.rule_id}")

        execution_id = f"orchestration_{rule.rule_id}_{datetime.utcnow().timestamp()}"

        # Create execution context
        context = ExecutionContext(
            execution_id=execution_id,
            mode=OrchestrationMode.EVENT_DRIVEN,
            start_time=datetime.utcnow(),
            queues=rule.target_queues,
            rules=[rule],
            metadata={
                "trigger_event": trigger_event.to_dict(),
                "rule_id": rule.rule_id
            }
        )

        self._active_executions[execution_id] = context

        try:
            # Execute target queues
            await self._execute_queues_with_rule(
                rule.target_queues,
                OrchestrationMode.EVENT_DRIVEN,
                rule.max_concurrent,
                rule.timeout_seconds,
                context
            )

            # Track successful execution
            self._execution_metrics[execution_id] = {
                "status": "completed",
                "duration": (datetime.utcnow() - context.start_time).total_seconds(),
                "queues_executed": len(rule.target_queues),
                "rule_id": rule.rule_id
            }

        except Exception as e:
            logger.error(f"Orchestration rule execution failed: {e}")
            self._execution_metrics[execution_id] = {
                "status": "failed",
                "error": str(e),
                "duration": (datetime.utcnow() - context.start_time).total_seconds(),
                "rule_id": rule.rule_id
            }
            raise
        finally:
            # Clean up execution context
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]

    async def execute_sequential_workflow(self, queues: List[QueueName]) -> Dict[str, Any]:
        """Execute queues in strict sequential order."""
        execution_id = f"sequential_{datetime.utcnow().timestamp()}"

        context = ExecutionContext(
            execution_id=execution_id,
            mode=OrchestrationMode.SEQUENTIAL,
            start_time=datetime.utcnow(),
            queues=queues,
            rules=[],
            metadata={"workflow_type": "sequential"}
        )

        self._active_executions[execution_id] = context

        try:
            results = await self._execute_queues_sequentially(queues, context)
            return {
                "execution_id": execution_id,
                "status": "completed",
                "results": results,
                "duration": (datetime.utcnow() - context.start_time).total_seconds()
            }
        except Exception as e:
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e),
                "duration": (datetime.utcnow() - context.start_time).total_seconds()
            }
        finally:
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]

    async def execute_parallel_workflow(
        self,
        queues: List[QueueName],
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Execute queues in parallel with concurrency control."""
        execution_id = f"parallel_{datetime.utcnow().timestamp()}"

        context = ExecutionContext(
            execution_id=execution_id,
            mode=OrchestrationMode.PARALLEL,
            start_time=datetime.utcnow(),
            queues=queues,
            rules=[],
            metadata={"workflow_type": "parallel", "max_concurrent": max_concurrent}
        )

        self._active_executions[execution_id] = context

        try:
            results = await self._execute_queues_concurrently(queues, max_concurrent, context)
            return {
                "execution_id": execution_id,
                "status": "completed",
                "results": results,
                "duration": (datetime.utcnow() - context.start_time).total_seconds()
            }
        except Exception as e:
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e),
                "duration": (datetime.utcnow() - context.start_time).total_seconds()
            }
        finally:
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]

    async def _execute_queues_sequentially(
        self,
        queues: List[QueueName],
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Execute queues in sequential order."""
        results = []

        for queue_name in queues:
            if not self._running:
                break

            try:
                # Execute single queue
                queue_result = await self._execute_single_queue(queue_name, context)

                # Wait for event-driven triggers if not the last queue
                if queue_name != queues[-1]:
                    await asyncio.sleep(2)  # Allow time for events to propagate

                results.append(queue_result)

            except Exception as e:
                logger.error(f"Sequential execution failed for queue {queue_name.value}: {e}")
                results.append({
                    "queue": queue_name.value,
                    "status": "failed",
                    "error": str(e)
                })
                break  # Stop on first failure in sequential mode

        return results

    async def _execute_queues_concurrently(
        self,
        queues: List[QueueName],
        max_concurrent: int,
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Execute queues concurrently with semaphore control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def execute_with_semaphore(queue_name: QueueName):
            async with semaphore:
                try:
                    return await self._execute_single_queue(queue_name, context)
                except Exception as e:
                    logger.error(f"Concurrent execution failed for queue {queue_name.value}: {e}")
                    return {
                        "queue": queue_name.value,
                        "status": "failed",
                        "error": str(e)
                    }

        # Execute all queues concurrently
        tasks = [execute_with_semaphore(queue) for queue in queues]
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in concurrent_results:
            if isinstance(result, Exception):
                results.append({
                    "queue": "unknown",
                    "status": "failed",
                    "error": str(result)
                })
            else:
                results.append(result)

        return results

    async def _execute_queues_with_rule(
        self,
        queues: List[QueueName],
        mode: OrchestrationMode,
        max_concurrent: int,
        timeout_seconds: int,
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """Execute queues according to orchestration rule."""
        if mode == OrchestrationMode.SEQUENTIAL:
            return await self._execute_queues_sequentially(queues, context)
        elif mode == OrchestrationMode.PARALLEL:
            return await self._execute_queues_concurrently(queues, max_concurrent, context)
        else:
            # Default to sequential for safety
            return await self._execute_queues_sequentially(queues, context)

    async def _execute_single_queue(
        self,
        queue_name: QueueName,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute a single queue with orchestration context."""
        logger.info(f"Orchestrating execution of queue: {queue_name.value}")

        # Get pending tasks for the queue
        try:
            pending_tasks = await self.task_service.get_pending_tasks(queue_name)

            if not pending_tasks:
                return {
                    "queue": queue_name.value,
                    "status": "completed",
                    "tasks_executed": 0,
                    "message": "No pending tasks"
                }

            # Execute tasks (this would delegate to the actual queue implementation)
            executed_count = 0
            failed_count = 0

            for task in pending_tasks:
                try:
                    # Mark task as started
                    await self.task_service.mark_started(task.task_id)

                    # Simulate task execution (would be handled by actual queue)
                    await asyncio.sleep(0.1)  # Simulate processing time

                    # Mark as completed
                    await self.task_service.mark_completed(task.task_id)
                    executed_count += 1

                except Exception as e:
                    logger.error(f"Task execution failed: {task.task_id} - {e}")
                    await self.task_service.mark_failed(task.task_id, str(e))
                    failed_count += 1

            return {
                "queue": queue_name.value,
                "status": "completed",
                "tasks_executed": executed_count,
                "tasks_failed": failed_count,
                "execution_context": context.execution_id
            }

        except Exception as e:
            logger.error(f"Queue execution failed: {queue_name.value} - {e}")
            return {
                "queue": queue_name.value,
                "status": "failed",
                "error": str(e),
                "execution_context": context.execution_id
            }

    async def _cancel_execution(self, execution_id: str) -> None:
        """Cancel an active execution."""
        if execution_id not in self._active_executions:
            return

        context = self._active_executions[execution_id]
        logger.info(f"Cancelling execution: {execution_id}")

        # Cancel tasks in active queues
        for queue_name in context.queues:
            try:
                pending_tasks = await self.task_service.get_pending_tasks(queue_name)
                for task in pending_tasks:
                    if task.status == TaskStatus.RUNNING:
                        await self.task_service.mark_failed(
                            task.task_id,
                            f"Execution cancelled: {execution_id}"
                        )
            except Exception as e:
                logger.error(f"Error cancelling tasks in queue {queue_name.value}: {e}")

        # Remove from active executions
        del self._active_executions[execution_id]

    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        return {
            "running": self._running,
            "active_executions": len(self._active_executions),
            "orchestration_rules": len(self._orchestration_rules),
            "execution_metrics": self._execution_metrics,
            "active_execution_details": [
                {
                    "execution_id": ctx.execution_id,
                    "mode": ctx.mode.value,
                    "start_time": ctx.start_time.isoformat(),
                    "queues": [q.value for q in ctx.queues],
                    "duration": (datetime.utcnow() - ctx.start_time).total_seconds()
                }
                for ctx in self._active_executions.values()
            ]
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check if we can get pending tasks (basic connectivity test)
            pending_counts = {}
            for queue_name in QueueName:
                try:
                    pending = await self.task_service.get_pending_tasks(queue_name)
                    pending_counts[queue_name.value] = len(pending)
                except Exception as e:
                    pending_counts[queue_name.value] = f"error: {e}"

            return {
                "status": "healthy" if self._running else "stopped",
                "active_executions": len(self._active_executions),
                "pending_tasks_by_queue": pending_counts,
                "orchestration_rules_loaded": len(self._orchestration_rules)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }