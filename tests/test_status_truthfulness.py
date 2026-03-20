from types import SimpleNamespace

import pytest

from src.core.coordinators.status.aggregation.status_aggregation_coordinator import (
    StatusAggregationCoordinator,
)
from src.core.coordinators.status.infrastructure_status_coordinator import (
    InfrastructureStatusCoordinator,
)


class _DummyStateManager:
    async def get_portfolio(self):
        return {}


class _DummyContainer:
    def __init__(self, queue_coordinator):
        self._queue_coordinator = queue_coordinator

    async def get(self, name):
        if name == "queue_coordinator":
            return self._queue_coordinator
        return None


class _DummyQueueCoordinator:
    def __init__(self, payload):
        self._payload = payload

    async def get_queue_status(self):
        return self._payload


def _config():
    return SimpleNamespace()


@pytest.mark.asyncio
async def test_infrastructure_resources_fail_loud_when_psutil_missing(monkeypatch):
    coordinator = InfrastructureStatusCoordinator(_config(), _DummyStateManager())

    original_import = __import__

    def _raising_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("psutil missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _raising_import)

    resources = await coordinator.get_system_resources()

    assert resources["status"] == "error"
    assert resources["cpu"] is None
    assert "psutil" in resources["error"]


@pytest.mark.asyncio
async def test_status_aggregation_uses_real_queue_failures():
    aggregation = StatusAggregationCoordinator(_config(), SimpleNamespace(), SimpleNamespace(), SimpleNamespace())
    aggregation.set_container(
        _DummyContainer(
            _DummyQueueCoordinator(
                {
                    "timestamp": "2026-03-18T00:00:00+00:00",
                    "queues": {
                        "paper_trading_execution": {
                            "status": "active",
                            "failed_tasks": 2,
                            "running": True,
                        }
                    },
                    "stats": {
                        "total_queues": 1,
                        "running_queues": 1,
                        "total_tasks": 3,
                    },
                }
            )
        )
    )

    status = await aggregation.get_queue_status()

    assert status["status"] == "error"
    assert status["failedTasks"] == 2
    assert status["totalQueues"] == 1
    assert status["runningQueues"] == 1
