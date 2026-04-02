"""Provider-neutral AI runtime status for the active paper-trading path."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

from src.services.codex_runtime_client import CodexRuntimeClient, CodexRuntimeError


class AIRuntimeStatus:
    """AI runtime authentication and availability status."""

    def __init__(
        self,
        *,
        is_valid: bool,
        authenticated: bool,
        provider: str,
        error: Optional[str] = None,
        account_info: Optional[Dict[str, Any]] = None,
        checked_at: Optional[str] = None,
        rate_limit_info: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.is_valid = is_valid
        self.authenticated = authenticated
        self.provider = provider
        self.error = error
        self.account_info = account_info or {}
        self.checked_at = checked_at or datetime.now(timezone.utc).isoformat()
        self.rate_limit_info = rate_limit_info or {}
        self.model = model
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "authenticated": self.authenticated,
            "provider": self.provider,
            "error": self.error,
            "account_info": self.account_info,
            "checked_at": self.checked_at,
            "rate_limit_info": self.rate_limit_info,
            "model": self.model,
            "metadata": self.metadata,
            "status": "connected" if self.is_valid else "disconnected",
        }


_last_recorded_runtime_limit: Dict[str, Any] = {}
_last_successful_runtime_validation_at: Optional[str] = None
_runtime_readiness_ttl_seconds = int(os.getenv("AI_RUNTIME_READY_TTL_SECONDS", "300"))
_runtime_force_validation_timeout_seconds = float(os.getenv("AI_RUNTIME_FORCE_VALIDATION_TIMEOUT_SECONDS", "45"))


def _build_client() -> CodexRuntimeClient:
    base_url = os.getenv("CODEX_RUNTIME_URL", "http://127.0.0.1:8765")
    timeout = float(os.getenv("AI_RUNTIME_TIMEOUT_SECONDS", "90"))
    return CodexRuntimeClient(base_url, timeout_seconds=timeout)


def record_ai_runtime_limit(message: str, *, code: Optional[str] = None) -> None:
    """Capture the most recent runtime limit so status reflects it immediately."""
    global _last_recorded_runtime_limit
    _last_recorded_runtime_limit = {
        "status": "exhausted",
        "code": code or "usage_limit",
        "message": message.strip(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def _age_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds(), 0.0)


def _looks_like_auth_failure(message: Optional[str]) -> bool:
    lowered = str(message or "").lower()
    return any(marker in lowered for marker in ("login", "sign in", "not authenticated", "auth required"))


def _can_reuse_recent_validation(*, payload: Dict[str, Any], recent_validation: bool, is_authenticated: bool) -> bool:
    if not recent_validation or not is_authenticated:
        return False
    if payload.get("usage_limited"):
        return False
    if payload.get("status") == "ready":
        return False
    return not _looks_like_auth_failure(payload.get("message"))


async def validate_ai_runtime_auth(*, force_refresh: bool = False) -> AIRuntimeStatus:
    """Validate the active AI runtime directly against the local sidecar."""
    global _last_successful_runtime_validation_at
    provider = os.getenv("AI_RUNTIME_PROVIDER", "codex")
    if provider != "codex":
        return AIRuntimeStatus(
            is_valid=False,
            authenticated=False,
            provider=provider,
            error=f"Unsupported AI runtime provider '{provider}' for this migration branch.",
        )

    client = _build_client()
    validation_timeout_seconds = min(client.timeout_seconds, _runtime_force_validation_timeout_seconds)
    try:
        payload = await (
            client.validate_runtime(timeout_seconds=validation_timeout_seconds)
            if force_refresh
            else client.get_health()
        )
    except CodexRuntimeError as exc:
        rate_limit_info = (
            {
                "status": "exhausted",
                "code": "usage_limit",
                "message": str(exc),
            }
            if exc.usage_limited
            else {}
        )
        return AIRuntimeStatus(
            is_valid=bool(exc.authenticated and exc.usage_limited),
            authenticated=exc.authenticated,
            provider="codex",
            error=str(exc),
            rate_limit_info=rate_limit_info or _last_recorded_runtime_limit,
            model=os.getenv("CODEX_MODEL", "gpt-5.4"),
            metadata={
                "mode": "local_runtime_service",
                "base_url": client.base_url,
                "status_code": exc.status_code,
                "last_successful_validation_at": _last_successful_runtime_validation_at,
                "readiness_ttl_seconds": _runtime_readiness_ttl_seconds,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"AI runtime health probe failed unexpectedly: {exc}")
        return AIRuntimeStatus(
            is_valid=False,
            authenticated=False,
            provider="codex",
            error=str(exc),
            model=os.getenv("CODEX_MODEL", "gpt-5.4"),
            metadata={
                "mode": "local_runtime_service",
                "base_url": client.base_url,
                "last_successful_validation_at": _last_successful_runtime_validation_at,
                "readiness_ttl_seconds": _runtime_readiness_ttl_seconds,
            },
        )

    payload_rate_limit = {}
    if payload.get("usage_limited"):
        payload_rate_limit = {
            "status": "exhausted",
            "code": "usage_limit",
            "message": payload.get("message") or "Codex runtime usage is temporarily exhausted.",
        }
    elif _last_recorded_runtime_limit:
        payload_rate_limit = {}

    payload_checked_at = str(payload.get("checked_at") or "")
    if payload.get("status") == "ready" and payload.get("authenticated"):
        _last_successful_runtime_validation_at = payload_checked_at or datetime.now(timezone.utc).isoformat()

    last_successful_validation_at = _last_successful_runtime_validation_at
    last_successful_age_seconds = _age_seconds(last_successful_validation_at)
    recent_validation = bool(
        last_successful_validation_at
        and last_successful_age_seconds is not None
        and last_successful_age_seconds <= _runtime_readiness_ttl_seconds
    )
    stale_validation_message = (
        f"AI runtime has not completed a successful validation run within the last "
        f"{_runtime_readiness_ttl_seconds}s."
    )
    is_authenticated = bool(payload.get("authenticated", False))
    recent_validation_still_authoritative = _can_reuse_recent_validation(
        payload=payload,
        recent_validation=recent_validation,
        is_authenticated=is_authenticated,
    )
    is_ready_now = (payload.get("status") == "ready" and is_authenticated and recent_validation) or (
        recent_validation_still_authoritative
    )
    if is_ready_now:
        error = None
    elif payload.get("status") == "ready" and is_authenticated:
        error = stale_validation_message
    else:
        error = payload.get("message")

    return AIRuntimeStatus(
        is_valid=is_ready_now,
        authenticated=is_authenticated,
        provider=str(payload.get("provider") or "codex"),
        error=error,
        account_info={
            "auth_method": "chatgpt_codex_local_runtime",
            "mode": payload.get("mode", "local_runtime_service"),
            "last_successful_validation_at": last_successful_validation_at,
        },
        checked_at=payload.get("checked_at"),
        rate_limit_info=payload_rate_limit,
        model=payload.get("model") or os.getenv("CODEX_MODEL", "gpt-5.4"),
        metadata={
            "reasoning_profile": payload.get("reasoning_profile"),
            "mode": payload.get("mode", "local_runtime_service"),
            "message": payload.get("message"),
            "base_url": client.base_url,
            "last_successful_validation_at": last_successful_validation_at,
            "last_successful_validation_age_seconds": last_successful_age_seconds,
            "readiness_ttl_seconds": _runtime_readiness_ttl_seconds,
            "last_runtime_health_status": payload.get("status"),
            "reused_recent_validation": recent_validation_still_authoritative,
        },
    )


async def get_ai_runtime_status(*, force_refresh: bool = False) -> AIRuntimeStatus:
    """Always return a live AI runtime status snapshot."""
    return await validate_ai_runtime_auth(force_refresh=force_refresh)


def get_ai_runtime_status_sync() -> AIRuntimeStatus:
    """Synchronous helper for code paths that cannot await."""
    return asyncio.run(get_ai_runtime_status())
