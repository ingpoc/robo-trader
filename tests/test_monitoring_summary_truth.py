"""Regression tests for truthful monitoring summary output."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.web import app as web_app
from src.web.routes.monitoring import get_system_status
from src.web.routes.zerodha_auth import zerodha_oauth_callback


class _DummyCursor:
    async def fetchone(self):
        return (1,)

    async def close(self):
        return None


class _DummyConnection:
    async def execute(self, _query):
        return _DummyCursor()


class _DummyLifecycleCoordinator:
    def __init__(self, connected: bool):
        self._connected = connected

    def is_connected(self) -> bool:
        return self._connected


class _DummySessionCoordinator:
    def __init__(self, authenticated: bool, connected: bool):
        self._authenticated = authenticated
        self.lifecycle_coordinator = _DummyLifecycleCoordinator(connected)

    def is_authenticated(self) -> bool:
        return self._authenticated


class _DummyBackgroundScheduler:
    def __init__(self, running: bool = True, ready: bool = True, init_error: str | None = None):
        self._running = running
        self._ready = ready
        self._init_error = init_error

    async def get_scheduler_status(self):
        return {
            "running": self._running,
            "event_driven": True,
            "uptime_seconds": 123,
            "last_run_time": "2026-03-18T00:00:00+00:00",
        }

    def get_initialization_status(self):
        return (self._ready, self._init_error)

    def is_ready(self):
        return self._ready and self._init_error is None


@pytest.mark.asyncio
async def test_monitoring_summary_reports_live_runtime_truth(monkeypatch):
    state_manager = SimpleNamespace(
        db=SimpleNamespace(_connection_pool=_DummyConnection()),
        get_portfolio=AsyncMock(return_value={}),
    )
    orchestrator = SimpleNamespace(
        session_coordinator=_DummySessionCoordinator(authenticated=True, connected=True)
    )
    background_scheduler = _DummyBackgroundScheduler(running=True, ready=True)
    connection_manager = SimpleNamespace(get_connection_count=AsyncMock(return_value=2))

    async def get_service(name):
        services = {
            "state_manager": state_manager,
            "event_bus": object(),
            "background_scheduler": background_scheduler,
        }
        return services.get(name)

    container = MagicMock()
    container.get_orchestrator = AsyncMock(return_value=orchestrator)
    container.get = AsyncMock(side_effect=get_service)

    request = MagicMock()
    request.app.state = SimpleNamespace(
        connection_manager=connection_manager,
        orchestrator_init_task=SimpleNamespace(done=lambda: True),
    )

    monkeypatch.setitem(web_app.initialization_status, "orchestrator_initialized", True)
    monkeypatch.setitem(web_app.initialization_status, "bootstrap_completed", True)
    monkeypatch.setitem(web_app.initialization_status, "initialization_errors", [])
    monkeypatch.setitem(web_app.initialization_status, "last_error", None)

    payload = await get_system_status.__wrapped__(request=request, container=container)

    assert payload["status"] == "healthy"
    assert payload["components"]["orchestrator"]["status"] == "healthy"
    assert payload["components"]["database"]["status"] == "healthy"
    assert payload["components"]["background_scheduler"]["status"] == "healthy"
    assert payload["components"]["websocket"]["status"] == "healthy"
    assert payload["blockers"] == []


@pytest.mark.asyncio
async def test_monitoring_summary_surfaces_initialization_failures(monkeypatch):
    state_manager = SimpleNamespace(
        db=SimpleNamespace(_connection_pool=None),
        get_portfolio=AsyncMock(return_value=None),
    )
    orchestrator = SimpleNamespace(
        session_coordinator=_DummySessionCoordinator(authenticated=False, connected=False)
    )
    background_scheduler = _DummyBackgroundScheduler(running=False, ready=False, init_error="queue executor crashed")

    async def get_service(name):
        services = {
            "state_manager": state_manager,
            "event_bus": object(),
            "background_scheduler": background_scheduler,
        }
        return services.get(name)

    container = MagicMock()
    container.get_orchestrator = AsyncMock(return_value=orchestrator)
    container.get = AsyncMock(side_effect=get_service)

    request = MagicMock()
    request.app.state = SimpleNamespace(
        connection_manager=SimpleNamespace(get_connection_count=AsyncMock(return_value=0)),
        orchestrator_init_task=SimpleNamespace(done=lambda: True),
    )

    monkeypatch.setitem(web_app.initialization_status, "orchestrator_initialized", False)
    monkeypatch.setitem(web_app.initialization_status, "bootstrap_completed", False)
    monkeypatch.setitem(web_app.initialization_status, "initialization_errors", ["boom"])
    monkeypatch.setitem(web_app.initialization_status, "last_error", "boom")

    payload = await get_system_status.__wrapped__(request=request, container=container)

    assert payload["status"] == "error"
    assert payload["components"]["orchestrator"]["status"] == "error"
    assert payload["components"]["database"]["status"] == "error"
    assert payload["components"]["background_scheduler"]["status"] == "error"
    assert "boom" in payload["blockers"][0]


@pytest.mark.asyncio
async def test_monitoring_summary_treats_disabled_event_driven_scheduler_as_idle(monkeypatch):
    state_manager = SimpleNamespace(
        db=SimpleNamespace(_connection_pool=_DummyConnection()),
        get_portfolio=AsyncMock(return_value={}),
    )
    orchestrator = SimpleNamespace(
        session_coordinator=_DummySessionCoordinator(authenticated=True, connected=True)
    )
    background_scheduler = _DummyBackgroundScheduler(running=False, ready=False)
    connection_manager = SimpleNamespace(get_connection_count=AsyncMock(return_value=1))

    async def get_service(name):
        services = {
            "state_manager": state_manager,
            "event_bus": object(),
            "background_scheduler": background_scheduler,
        }
        return services.get(name)

    container = MagicMock()
    container.get_orchestrator = AsyncMock(return_value=orchestrator)
    container.get = AsyncMock(side_effect=get_service)

    request = MagicMock()
    request.app.state = SimpleNamespace(
        connection_manager=connection_manager,
        orchestrator_init_task=SimpleNamespace(done=lambda: True),
    )

    monkeypatch.setitem(web_app.initialization_status, "orchestrator_initialized", True)
    monkeypatch.setitem(web_app.initialization_status, "bootstrap_completed", True)
    monkeypatch.setitem(web_app.initialization_status, "initialization_errors", [])
    monkeypatch.setitem(web_app.initialization_status, "last_error", None)

    payload = await get_system_status.__wrapped__(request=request, container=container)

    assert payload["status"] == "healthy"
    assert payload["components"]["background_scheduler"]["status"] == "idle"
    assert "intentionally idle" in payload["components"]["background_scheduler"]["summary"]
    assert payload["blockers"] == []


@pytest.mark.asyncio
async def test_zerodha_callback_binds_live_runtime_services():
    oauth_service = AsyncMock()
    oauth_service.handle_callback.return_value = {
        "user_id": "Z123",
        "login_time": "2026-03-18T09:00:00+00:00",
        "expires_at": "2026-03-18T15:00:00+00:00",
    }

    kite_service = AsyncMock()
    kite_service.authenticate.return_value = {"user_id": "Z123", "user_name": "Guru"}

    market_data_service = AsyncMock()
    market_data_service.refresh_active_subscriptions.return_value = ["INFY", "TCS"]

    async def get_service(name):
        services = {
            "zerodha_oauth_service": oauth_service,
            "kite_connect_service": kite_service,
            "market_data_service": market_data_service,
        }
        return services.get(name)

    container = MagicMock()
    container.get = AsyncMock(side_effect=get_service)
    container.get_orchestrator = AsyncMock()

    response = await zerodha_oauth_callback.__wrapped__(
        request=MagicMock(),
        request_token="request-token",
        status=None,
        state="oauth-state",
        container=container,
    )

    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["broker_session_bound"] is True
    assert payload["market_data_refreshed"] == 2
    oauth_service.handle_callback.assert_awaited_once_with("request-token", "oauth-state")
    kite_service.authenticate.assert_awaited_once_with("request-token")
    market_data_service.refresh_active_subscriptions.assert_awaited_once()
    container.get_orchestrator.assert_not_called()
