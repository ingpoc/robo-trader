import httpx
import pytest

from src.services.codex_runtime_client import CodexRuntimeClient, CodexRuntimeError, _drop_none, _normalize_output_schema


def test_normalize_output_schema_recursively_strictifies_objects():
    schema = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "nested": {
                "type": "object",
                "properties": {
                    "confidence": {"type": "number"},
                },
            },
            "optional_block": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "flag": {"type": "boolean"},
                        },
                    },
                    {"type": "null"},
                ],
            },
        },
    }

    normalized = _normalize_output_schema(schema)

    assert normalized["additionalProperties"] is False
    assert normalized["required"] == ["symbol", "nested", "optional_block"]

    nested = normalized["properties"]["nested"]
    assert nested["additionalProperties"] is False
    assert nested["required"] == ["confidence"]

    optional_block = normalized["properties"]["optional_block"]["anyOf"][0]
    assert optional_block["additionalProperties"] is False
    assert optional_block["required"] == ["flag"]


def test_drop_none_removes_null_fields_from_request_payloads():
    payload = {
        "model": "gpt-5.4",
        "reasoning": None,
        "options": {
            "timeout_seconds": 45,
            "web_search_mode": None,
        },
        "items": [
            {"symbol": "INFY", "note": None},
            None,
            {"symbol": "TCS"},
        ],
    }

    pruned = _drop_none(payload)

    assert pruned == {
        "model": "gpt-5.4",
        "options": {
            "timeout_seconds": 45,
        },
        "items": [
            {"symbol": "INFY"},
            None,
            {"symbol": "TCS"},
        ],
    }


@pytest.mark.asyncio
async def test_codex_runtime_client_marks_timeouts_as_timed_out(monkeypatch):
    class _TimeoutAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, *args, **kwargs):
            raise httpx.ReadTimeout("slow research")

    monkeypatch.setattr(
        "src.services.codex_runtime_client.httpx.AsyncClient",
        _TimeoutAsyncClient,
    )

    client = CodexRuntimeClient("http://127.0.0.1:8765", timeout_seconds=12.0)

    with pytest.raises(CodexRuntimeError) as exc_info:
        await client.get_health()

    assert exc_info.value.timed_out is True
    assert exc_info.value.authenticated is True
    assert "timed out after" in str(exc_info.value)


@pytest.mark.asyncio
async def test_codex_runtime_client_validate_runtime_hits_validation_endpoint(monkeypatch):
    captured = {}

    class _Response:
        status_code = 200

        def json(self):
            return {"status": "ready", "authenticated": True, "checked_at": "2026-03-29T00:00:00Z"}

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, json=None):
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            return _Response()

    monkeypatch.setattr(
        "src.services.codex_runtime_client.httpx.AsyncClient",
        _AsyncClient,
    )

    client = CodexRuntimeClient("http://127.0.0.1:8765", timeout_seconds=12.0)
    payload = await client.validate_runtime()

    assert captured == {
        "method": "POST",
        "url": "http://127.0.0.1:8765/v1/runtime/validate",
        "json": {"timeout_seconds": 12.0},
    }
    assert payload["status"] == "ready"
