from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.models.scheduler import QueueName
from src.services.scheduler.queue_manager import SequentialQueueManager


@pytest.mark.asyncio
async def test_execute_queues_skips_ai_related_executors_on_startup(monkeypatch):
    started_queues: list[str] = []

    class _FakeExecutor:
        def __init__(self, *, queue_name, task_service, loop, on_task_complete, on_task_failed):
            self.queue_name = queue_name

        async def start(self):
            started_queues.append(self.queue_name)

    monkeypatch.setattr(
        "src.services.scheduler.queue_manager.ThreadSafeQueueExecutor",
        _FakeExecutor,
    )

    task_service = SimpleNamespace(
        store=SimpleNamespace(get_completed_task_ids_today=AsyncMock(return_value=[]))
    )
    manager = SequentialQueueManager(task_service)

    await manager.execute_queues()

    assert started_queues == [
        QueueName.PORTFOLIO_SYNC.value,
        QueueName.DATA_FETCHER.value,
        QueueName.PAPER_TRADING_EXECUTION.value,
    ]
