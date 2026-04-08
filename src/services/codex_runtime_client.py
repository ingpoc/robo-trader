"""HTTP client for the local Codex runtime sidecar."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Optional

import httpx


class CodexRuntimeError(RuntimeError):
    """Raised when the local Codex runtime returns an actionable failure."""

    def __init__(
        self,
        message: str,
        *,
        usage_limited: bool = False,
        authenticated: bool = True,
        timed_out: bool = False,
        status_code: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.usage_limited = usage_limited
        self.authenticated = authenticated
        self.timed_out = timed_out
        self.status_code = status_code
        self.payload = payload or {}


class CodexRuntimeClient:
    """Thin async client for the repo-local Codex runtime service."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 90.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _runtime_validation_timeout(self, timeout_seconds: Optional[float]) -> float:
        return timeout_seconds or min(self.timeout_seconds, 45.0)

    async def get_health(self) -> Dict[str, Any]:
        return await self._request_json("GET", "/health", timeout_seconds=min(self.timeout_seconds, 20.0))

    async def validate_runtime(self, *, timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        request_timeout = self._runtime_validation_timeout(timeout_seconds)
        return await self._request_json(
            "POST",
            "/v1/runtime/validate",
            json_body={"timeout_seconds": request_timeout},
            timeout_seconds=request_timeout,
        )

    async def run_structured(
        self,
        *,
        system_prompt: str,
        prompt: str,
        output_schema: Dict[str, Any],
        model: Optional[str] = None,
        reasoning: Optional[str] = None,
        prompt_cache_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        web_search_enabled: bool = False,
        web_search_mode: Optional[str] = None,
        network_access_enabled: bool = False,
        working_directory: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_schema = _normalize_output_schema(output_schema)
        return await self._request_json(
            "POST",
            "/v1/structured/run",
            json_body={
                "system_prompt": system_prompt,
                "prompt": prompt,
                "output_schema": normalized_schema,
                "model": model,
                "reasoning": reasoning,
                "prompt_cache_key": prompt_cache_key,
                "timeout_seconds": timeout_seconds or self.timeout_seconds,
                "web_search_enabled": web_search_enabled,
                "web_search_mode": web_search_mode,
                "network_access_enabled": network_access_enabled,
                "working_directory": working_directory,
                "session_id": session_id,
            },
            timeout_seconds=timeout_seconds,
        )

    async def run_focused_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/research/focused",
            json_body=payload,
            timeout_seconds=payload.get("timeout_seconds"),
        )

    async def collect_batch_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/research/batch",
            json_body=payload,
            timeout_seconds=payload.get("timeout_seconds"),
        )

    async def discover_market_opportunities(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/research/discovery-scout",
            json_body=payload,
            timeout_seconds=payload.get("timeout_seconds"),
        )

    async def analyze_prompt_optimization(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/prompt-optimization/analyze",
            json_body=payload,
            timeout_seconds=payload.get("timeout_seconds"),
        )

    async def run_improvement_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v1/improvement/review",
            json_body=payload,
            timeout_seconds=payload.get("timeout_seconds"),
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        timeout = timeout_seconds or self.timeout_seconds
        url = f"{self.base_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, json=_drop_none(json_body))
        except httpx.TimeoutException as exc:
            raise CodexRuntimeError(
                f"Codex runtime timed out after {timeout:.1f}s.",
                authenticated=True,
                timed_out=True,
                status_code=504,
            ) from exc
        except httpx.RequestError as exc:
            raise CodexRuntimeError(
                f"Codex runtime is unavailable at {self.base_url}. {exc}",
                authenticated=False,
            ) from exc

        payload: Dict[str, Any]
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {}

        if response.status_code >= 400:
            detail = payload.get("detail") or payload.get("message") or payload.get("error") or response.text
            usage_limited = bool(payload.get("usage_limited") or response.status_code == 429)
            authenticated = payload.get("authenticated")
            if authenticated is None:
                authenticated = not any(
                    marker in str(detail).lower()
                    for marker in ("sign in", "login", "not authenticated", "auth required")
                )
            raise CodexRuntimeError(
                str(detail).strip() or f"Codex runtime request failed with HTTP {response.status_code}",
                usage_limited=usage_limited,
                authenticated=bool(authenticated),
                status_code=response.status_code,
                payload=payload,
            )

        return payload


MAX_SCHEMA_NORMALIZATION_DEPTH = 64


def _normalize_output_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Tighten JSON Schema for Codex/OpenAI structured output constraints.

    The runtime requires every object schema to:
    - explicitly set ``additionalProperties`` to ``false``
    - provide ``required`` listing every key in ``properties``
    """
    return _normalize_schema_node(deepcopy(schema), depth=0)


def _normalize_schema_node(node: Any, *, depth: int) -> Any:
    if depth > MAX_SCHEMA_NORMALIZATION_DEPTH:
        raise ValueError(
            f"Output schema exceeds maximum normalization depth of {MAX_SCHEMA_NORMALIZATION_DEPTH}"
        )

    if isinstance(node, list):
        return [_normalize_schema_node(item, depth=depth + 1) for item in node]

    if not isinstance(node, dict):
        return node

    normalized = {
        key: _normalize_schema_node(value, depth=depth + 1)
        for key, value in node.items()
    }

    if "$defs" in normalized and isinstance(normalized["$defs"], dict):
        normalized["$defs"] = {
            key: _normalize_schema_node(value, depth=depth + 1)
            for key, value in normalized["$defs"].items()
        }

    properties = normalized.get("properties")
    is_object_schema = (
        normalized.get("type") == "object"
        or isinstance(properties, dict)
        or "additionalProperties" in normalized
    )
    if is_object_schema:
        if not isinstance(properties, dict):
            properties = {}
        normalized["type"] = "object"
        normalized["properties"] = {
            key: _normalize_schema_node(value, depth=depth + 1)
            for key, value in properties.items()
        }
        normalized["additionalProperties"] = False
        normalized["required"] = list(normalized["properties"].keys())

    if "items" in normalized:
        normalized["items"] = _normalize_schema_node(normalized["items"], depth=depth + 1)
    if "anyOf" in normalized and isinstance(normalized["anyOf"], list):
        normalized["anyOf"] = [_normalize_schema_node(item, depth=depth + 1) for item in normalized["anyOf"]]
    if "allOf" in normalized and isinstance(normalized["allOf"], list):
        normalized["allOf"] = [_normalize_schema_node(item, depth=depth + 1) for item in normalized["allOf"]]
    if "oneOf" in normalized and isinstance(normalized["oneOf"], list):
        normalized["oneOf"] = [_normalize_schema_node(item, depth=depth + 1) for item in normalized["oneOf"]]

    return normalized


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_none(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value
