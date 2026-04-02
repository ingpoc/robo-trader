from datetime import datetime, timedelta, timezone

import pytest

class _FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.base_url = "http://127.0.0.1:8765"
        self.timeout_seconds = 20.0

    async def get_health(self):
        return self.payload

    async def validate_runtime(self, *, timeout_seconds=None):
        return self.payload


def _load_ai_runtime_auth_module():
    from src.web.routes import paper_trading  # noqa: F401
    from src.auth import ai_runtime_auth

    return ai_runtime_auth


@pytest.mark.asyncio
async def test_recent_successful_validation_survives_aborted_runtime_request(monkeypatch):
    ai_runtime_auth = _load_ai_runtime_auth_module()
    recent_validation_at = (datetime.now(timezone.utc) - timedelta(seconds=15)).isoformat()
    payload = {
        "status": "blocked",
        "authenticated": True,
        "provider": "codex",
        "message": "The operation was aborted",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-5.4",
        "reasoning_profile": "low",
        "mode": "local_runtime_service",
    }

    monkeypatch.setattr(ai_runtime_auth, "_build_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(ai_runtime_auth, "_last_successful_runtime_validation_at", recent_validation_at)

    status = await ai_runtime_auth.validate_ai_runtime_auth()

    assert status.is_valid is True
    assert status.error is None
    assert status.metadata["reused_recent_validation"] is True


@pytest.mark.asyncio
async def test_recent_validation_is_not_reused_for_auth_failures(monkeypatch):
    ai_runtime_auth = _load_ai_runtime_auth_module()
    recent_validation_at = (datetime.now(timezone.utc) - timedelta(seconds=15)).isoformat()
    payload = {
        "status": "blocked",
        "authenticated": False,
        "provider": "codex",
        "message": "Authentication required. Please sign in again.",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-5.4",
        "reasoning_profile": "low",
        "mode": "local_runtime_service",
    }

    monkeypatch.setattr(ai_runtime_auth, "_build_client", lambda: _FakeClient(payload))
    monkeypatch.setattr(ai_runtime_auth, "_last_successful_runtime_validation_at", recent_validation_at)

    status = await ai_runtime_auth.validate_ai_runtime_auth()

    assert status.is_valid is False
    assert "sign in" in (status.error or "").lower()
    assert status.metadata["reused_recent_validation"] is False


@pytest.mark.asyncio
async def test_force_refresh_uses_extended_validation_timeout(monkeypatch):
    ai_runtime_auth = _load_ai_runtime_auth_module()
    payload = {
        "status": "ready",
        "authenticated": True,
        "provider": "codex",
        "message": "Codex runtime is reachable.",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-5.4",
        "reasoning_profile": "low",
        "mode": "local_runtime_service",
    }
    captured: dict[str, float | None] = {}

    class _TimeoutCapturingClient(_FakeClient):
        def __init__(self, payload):
            super().__init__(payload)
            self.timeout_seconds = 90.0

        async def validate_runtime(self, *, timeout_seconds=None):
            captured["timeout_seconds"] = timeout_seconds
            return self.payload

    monkeypatch.setattr(ai_runtime_auth, "_build_client", lambda: _TimeoutCapturingClient(payload))
    monkeypatch.setattr(ai_runtime_auth, "_runtime_force_validation_timeout_seconds", 45.0)

    status = await ai_runtime_auth.validate_ai_runtime_auth(force_refresh=True)

    assert status.is_valid is True
    assert captured["timeout_seconds"] == 45.0
