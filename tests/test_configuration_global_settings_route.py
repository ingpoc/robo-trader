from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.dependencies import get_container
from src.web.routes.configuration import router


class _FakeConfigState:
    def __init__(self) -> None:
        self.updated_with = None
        self.ai_agent_updated = None

    async def update_global_settings_config(self, settings_data):
        self.updated_with = settings_data
        return True

    async def update_ai_agent_config(self, agent_name, config_data):
        self.ai_agent_updated = {"agent_name": agent_name, "config_data": config_data}
        return True


class _FailingMarketDataService:
    def __init__(self) -> None:
        self.calls = []

    async def apply_runtime_preferences(self, *, provider=None, mode=None):
        self.calls.append({"provider": provider, "mode": mode})
        raise RuntimeError("quote stream unavailable")


class _SlowMarketDataService:
    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds
        self.calls = []

    async def apply_runtime_preferences(self, *, provider=None, mode=None):
        self.calls.append({"provider": provider, "mode": mode})
        await asyncio.sleep(self.delay_seconds)


class _FakeContainer:
    def __init__(self, config_state, market_data_service) -> None:
        self._config_state = config_state
        self._market_data_service = market_data_service

    async def get(self, key: str):
        if key == "configuration_state":
            return self._config_state
        if key == "market_data_service":
            return self._market_data_service
        raise KeyError(key)


class _FailingContainer(_FakeContainer):
    async def get(self, key: str):
        if key == "market_data_service":
            raise RuntimeError("container lookup failed")
        return await super().get(key)


def test_update_global_settings_succeeds_when_runtime_refresh_fails():
    app = FastAPI()
    app.include_router(router)

    config_state = _FakeConfigState()
    market_data_service = _FailingMarketDataService()
    container = _FakeContainer(config_state, market_data_service)

    async def override_get_container():
        return container

    app.dependency_overrides[get_container] = override_get_container

    payload = {
        "quoteStreamProvider": "zerodha_kite",
        "quoteStreamMode": "ltpc",
        "quoteStreamSymbolLimit": 50,
    }

    with TestClient(app) as client:
        response = client.put("/api/configuration/global-settings", json=payload)
        time.sleep(0.05)

    assert response.status_code == 200
    assert response.json() == {"status": "Global settings updated"}
    assert config_state.updated_with == payload
    assert market_data_service.calls == [
        {"provider": "zerodha_kite", "mode": "ltpc"}
    ]


def test_update_global_settings_does_not_wait_for_runtime_refresh():
    app = FastAPI()
    app.include_router(router)

    config_state = _FakeConfigState()
    market_data_service = _SlowMarketDataService(delay_seconds=0.4)
    container = _FakeContainer(config_state, market_data_service)

    async def override_get_container():
        return container

    app.dependency_overrides[get_container] = override_get_container

    payload = {
        "quoteStreamProvider": "zerodha_kite",
        "quoteStreamMode": "ltpc",
        "quoteStreamSymbolLimit": 50,
    }

    with TestClient(app) as client:
        started_at = time.perf_counter()
        response = client.put("/api/configuration/global-settings", json=payload)
        elapsed = time.perf_counter() - started_at
        time.sleep(0.05)

    assert response.status_code == 200
    assert response.json() == {"status": "Global settings updated"}
    assert elapsed < 0.2
    assert config_state.updated_with == payload
    assert market_data_service.calls == [
        {"provider": "zerodha_kite", "mode": "ltpc"}
    ]


def test_update_global_settings_succeeds_when_market_data_service_lookup_fails():
    app = FastAPI()
    app.include_router(router)

    config_state = _FakeConfigState()
    market_data_service = _FailingMarketDataService()
    container = _FailingContainer(config_state, market_data_service)

    async def override_get_container():
        return container

    app.dependency_overrides[get_container] = override_get_container

    payload = {
        "quoteStreamProvider": "zerodha_kite",
        "quoteStreamMode": "ltpc",
        "quoteStreamSymbolLimit": 50,
    }

    with TestClient(app) as client:
        response = client.put("/api/configuration/global-settings", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "Global settings updated"}
    assert config_state.updated_with == payload


def test_update_ai_agent_config_passes_frontend_payload_through():
    app = FastAPI()
    app.include_router(router)

    config_state = _FakeConfigState()
    market_data_service = _FailingMarketDataService()
    container = _FakeContainer(config_state, market_data_service)

    async def override_get_container():
        return container

    app.dependency_overrides[get_container] = override_get_container

    payload = {
        "enabled": True,
        "useClaude": True,
        "tools": ["news", "earnings"],
        "responseFrequency": 30,
        "responseFrequencyUnit": "minutes",
        "scope": "portfolio",
        "maxTokensPerRequest": 2000,
    }

    with TestClient(app) as client:
        response = client.put("/api/configuration/ai-agents/portfolio_analyzer", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "status": "Configuration updated",
        "agent": "portfolio_analyzer",
    }
    assert config_state.ai_agent_updated == {
        "agent_name": "portfolio_analyzer",
        "config_data": payload,
    }
