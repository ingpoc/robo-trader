import os
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.dependencies import get_container
from src.web.routes.zerodha_auth import router


class _FakeOAuthService:
    async def handle_callback(self, request_token, state=None):
        return {
            "success": True,
            "user_id": "WH6470",
            "access_token": "token-123",
            "login_time": "2026-03-23T11:11:11.192506+00:00",
            "expires_at": "2026-03-24T11:11:11.192506+00:00",
        }


class _FakeKiteService:
    def __init__(self):
        self.bound_token = None

    async def _set_access_token(self, access_token):
        self.bound_token = access_token
        return True


class _FakeQuoteStreamAdapter:
    def __init__(self):
        self.updated_with = None

    async def update_credentials(self, *, api_key=None, access_token=None):
        self.updated_with = {"api_key": api_key, "access_token": access_token}


class _FakeMarketDataService:
    def __init__(self):
        self.quote_stream_adapter = _FakeQuoteStreamAdapter()
        self.refreshed = False

    async def refresh_active_subscriptions(self):
        self.refreshed = True
        return ["HDFC"]


class _FakeContainer:
    def __init__(self):
        self.oauth_service = _FakeOAuthService()
        self.kite_service = _FakeKiteService()
        self.market_data_service = _FakeMarketDataService()
        self.config = SimpleNamespace(
            integration=SimpleNamespace(
                zerodha_api_key="api-key-123",
                zerodha_access_token=None,
            )
        )

    async def get(self, key: str):
        if key == "zerodha_oauth_service":
            return self.oauth_service
        if key == "kite_connect_service":
            return self.kite_service
        if key == "market_data_service":
            return self.market_data_service
        raise KeyError(key)


def test_zerodha_callback_binds_runtime_to_fresh_access_token(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    container = _FakeContainer()

    async def override_get_container():
        return container

    monkeypatch.delenv("ZERODHA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("ZERODHA_USER_ID", raising=False)
    monkeypatch.delenv("ZERODHA_TOKEN_EXPIRES_AT", raising=False)

    app.dependency_overrides[get_container] = override_get_container

    with TestClient(app) as client:
        response = client.get(
            "/api/auth/zerodha/callback?request_token=req-123&action=login&type=login&status=success"
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert container.kite_service.bound_token == "token-123"
    assert container.config.integration.zerodha_access_token == "token-123"
    assert container.market_data_service.refreshed is True
    assert container.market_data_service.quote_stream_adapter.updated_with == {
        "api_key": "api-key-123",
        "access_token": "token-123",
    }
    assert os.environ["ZERODHA_ACCESS_TOKEN"] == "token-123"
    assert os.environ["ZERODHA_USER_ID"] == "WH6470"
    assert os.environ["ZERODHA_TOKEN_EXPIRES_AT"] == "2026-03-24T11:11:11.192506+00:00"
