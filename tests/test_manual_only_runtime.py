import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.coordinators.queue.queue_event_coordinator import QueueEventCoordinator
from src.core.manual_only_scheduler import ManualOnlyScheduler
from src.web.dependencies import get_container
from src.web.routes.configuration import router


class _FakeCursor:
    def __init__(self, value):
        self._value = value

    async def fetchone(self):
        return (self._value,)


class _FakeDB:
    def __init__(self, queued: int):
        self.queued = queued
        self.executed = []
        self.committed = False

    async def execute(self, query: str):
        self.executed.append(query)
        if query.startswith("SELECT COUNT(*)"):
            return _FakeCursor(self.queued)
        return None

    async def commit(self):
        self.committed = True


class _MissingQueueTableDB(_FakeDB):
    async def execute(self, query: str):
        self.executed.append(query)
        raise sqlite3.OperationalError("no such table: queue_tasks")


@pytest.mark.asyncio
async def test_manual_only_scheduler_reports_disabled_runtime():
    scheduler = ManualOnlyScheduler()

    started = await scheduler.start()
    status = await scheduler.get_scheduler_status()

    assert started == []
    assert status["status"] == "manual_only"
    assert status["running"] is False
    assert status["active_jobs"] == 0


@pytest.mark.asyncio
async def test_manual_only_scheduler_clears_stale_non_terminal_tasks():
    db = _FakeDB(queued=3)
    scheduler = ManualOnlyScheduler(db)

    await scheduler.initialize()

    assert any("SELECT COUNT(*) FROM queue_tasks" in query for query in db.executed)
    assert any("DELETE FROM queue_tasks" in query for query in db.executed)
    assert db.committed is True


@pytest.mark.asyncio
async def test_manual_only_scheduler_ignores_missing_legacy_queue_table():
    db = _MissingQueueTableDB(queued=0)
    scheduler = ManualOnlyScheduler(db)

    await scheduler.initialize()

    assert db.committed is False


@pytest.mark.asyncio
async def test_queue_event_coordinator_does_not_auto_start_routing():
    coordinator = QueueEventCoordinator(
        config=SimpleNamespace(),
        event_bus=MagicMock(),
        event_router_service=AsyncMock(),
    )

    await coordinator.initialize()

    coordinator.event_bus.subscribe.assert_not_called()
    coordinator.event_router_service.start.assert_not_called()


def test_configuration_status_reports_manual_only_runtime():
    app = FastAPI()
    app.include_router(router)

    config_state = MagicMock()
    config_state.get_system_status = AsyncMock(
        return_value={
            "status": "manual_only",
            "manualOnly": True,
            "backgroundSchedulers": {
                "status": "removed",
                "active": 0,
            },
            "aiAgents": {
                "configured": 0,
                "enabled": 0,
            },
            "globalSettings": {},
            "checkedAt": "2026-03-28T00:00:00+00:00",
        }
    )

    class _Container:
        async def get(self, key: str):
            if key == "configuration_state":
                return config_state
            raise KeyError(key)

    async def override_get_container():
        return _Container()

    app.dependency_overrides[get_container] = override_get_container

    with TestClient(app) as client:
        response = client.get("/api/configuration/status")

    assert response.status_code == 200
    payload = response.json()["configuration_status"]
    assert payload["status"] == "manual_only"
    assert payload["manualOnly"] is True
