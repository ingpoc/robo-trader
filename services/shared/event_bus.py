"""
Event Bus Service - RabbitMQ Integration
Handles async communication between microservices via event publishing/subscription
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional, List, Tuple
from uuid import uuid4

import aio_pika
from aio_pika.abc import AbstractIncomingMessage


logger = logging.getLogger(__name__)


class EventType(Enum):
    """All event types in the system"""

    # Market Events
    MARKET_PRICE_UPDATE = "market.price.update"
    MARKET_VOLUME_SPIKE = "market.volume.spike"
    MARKET_STATUS_CHANGE = "market.status.change"

    # Portfolio Events
    PORTFOLIO_POSITION_CHANGE = "portfolio.position.change"
    PORTFOLIO_PNL_UPDATE = "portfolio.pnl.update"
    PORTFOLIO_CASH_CHANGE = "portfolio.cash.change"
    PORTFOLIO_SNAPSHOT = "portfolio.snapshot"

    # Risk Events
    RISK_BREACH = "risk.breach"
    RISK_STOP_LOSS_TRIGGER = "risk.stop_loss.trigger"
    RISK_EXPOSURE_CHANGE = "risk.exposure.change"

    # Execution Events
    EXECUTION_ORDER_PLACED = "execution.order.placed"
    EXECUTION_ORDER_FILLED = "execution.order.filled"
    EXECUTION_ORDER_REJECTED = "execution.order.rejected"
    EXECUTION_ORDER_CANCELLED = "execution.order.cancelled"
    EXECUTION_ORDER_PARTIAL_FILL = "execution.order.partial_fill"

    # Analytics Events
    AI_ANALYSIS_COMPLETE = "ai.analysis.complete"
    AI_RECOMMENDATION = "ai.recommendation"
    AI_LEARNING_UPDATE = "ai.learning.update"

    # Task Events
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Alert Events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"


class Event:
    """Event envelope with metadata"""

    def __init__(
        self,
        event_type: EventType,
        data: Dict,
        source: str,
        correlation_id: Optional[str] = None,
    ):
        self.id = str(uuid4())
        self.type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.utcnow().isoformat()
        self.correlation_id = correlation_id or str(uuid4())

    def to_dict(self) -> Dict:
        """Convert event to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        """Create event from dictionary"""
        event = cls(
            event_type=EventType(data["type"]),
            data=data["data"],
            source=data["source"],
            correlation_id=data.get("correlation_id"),
        )
        event.id = data["id"]
        event.timestamp = data["timestamp"]
        return event


class EventBus:
    """RabbitMQ-based event bus for async service communication"""

    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.subscriptions: Dict[str, List[Tuple]] = {}
        self.consumer_tasks: List[asyncio.Task] = []

    async def connect(self) -> None:
        """Connect to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()

            self.exchange = await self.channel.declare_exchange(
                "robo-trader",
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            logger.info("✅ Connected to RabbitMQ event bus")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ and cleanup subscriptions"""
        try:
            for task in self.consumer_tasks:
                task.cancel()

            for queues in self.subscriptions.values():
                for queue, _ in queues:
                    try:
                        await queue.delete()
                    except Exception as e:
                        logger.debug(f"Error deleting queue: {e}")
        except Exception as e:
            logger.debug(f"Error during subscription cleanup: {e}")

        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def publish(self, event: Event, timeout: float = 5.0) -> None:
        """Publish event to message bus with timeout protection"""
        if not self.exchange:
            raise RuntimeError("Cannot publish event: Event bus not connected")

        try:
            message = aio_pika.Message(
                body=json.dumps(event.to_dict()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                priority=self._get_priority(event.type),
                timestamp=datetime.utcnow(),
                content_type="application/json",
            )

            await asyncio.wait_for(
                self.exchange.publish(message, routing_key=event.type.value),
                timeout=timeout,
            )

            logger.debug(
                f"📤 Published event: {event.type.value} (id={event.id}) from {event.source}"
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout publishing event {event.type.value}")
            raise
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def subscribe(
        self, event_type: EventType, callback: Callable, queue_name: Optional[str] = None
    ) -> asyncio.Task:
        """Subscribe to events of a specific type - returns background task handle"""
        if not self.channel or not self.exchange:
            raise RuntimeError("Event bus not connected")

        queue_name = queue_name or f"{event_type.value}.{uuid4()}"

        try:
            queue = await self.channel.declare_queue(queue_name, exclusive=True)
            await queue.bind(self.exchange, routing_key=event_type.value)

            logger.info(f"📥 Subscribed to {event_type.value}")

            if event_type.value not in self.subscriptions:
                self.subscriptions[event_type.value] = []

            async def consume_events():
                """Background task to consume events"""
                try:
                    async with queue.iterator() as queue_iter:
                        async for message in queue_iter:
                            async with message.process():
                                try:
                                    data = json.loads(message.body)
                                    event = Event.from_dict(data)

                                    logger.debug(
                                        f"📨 Received event: {event.type.value} (id={event.id})"
                                    )

                                    await callback(event)
                                except json.JSONDecodeError as e:
                                    logger.error(f"Invalid event JSON: {e}")
                                except Exception as e:
                                    logger.error(f"Error processing event: {e}")
                except asyncio.CancelledError:
                    logger.debug(f"Event subscription {event_type.value} cancelled")
                except Exception as e:
                    logger.error(f"Error in event consumer for {event_type.value}: {e}")

            task = asyncio.create_task(consume_events())
            self.subscriptions[event_type.value].append((queue, task))
            self.consumer_tasks.append(task)

            return task

        except Exception as e:
            logger.error(f"Failed to subscribe to {event_type.value}: {e}")
            raise

    async def subscribe_multi(
        self, event_types: list, callback: Callable
    ) -> List[asyncio.Task]:
        """Subscribe to multiple event types - returns list of task handles"""
        tasks = []
        for event_type in event_types:
            task = await self.subscribe(event_type, callback)
            tasks.append(task)
        return tasks

    @staticmethod
    def _get_priority(event_type: EventType) -> int:
        """Get priority for event based on type"""
        critical_events = [
            EventType.RISK_BREACH,
            EventType.RISK_STOP_LOSS_TRIGGER,
            EventType.EXECUTION_ORDER_FILLED,
            EventType.ALERT_TRIGGERED,
        ]
        return 10 if event_type in critical_events else 5

    async def health_check(self) -> bool:
        """Check if event bus is healthy"""
        if not self.connection or not self.channel:
            return False

        try:
            if self.connection.is_closed:
                return False
            return True
        except Exception as e:
            logger.error(f"Event bus health check failed: {e}")
            return False
