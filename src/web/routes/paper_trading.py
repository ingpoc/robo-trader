"""Paper trading account and position routes - ALL REAL DATA."""

import asyncio
import json
import logging
import os
import uuid
from typing import Awaitable, Callable, Dict, Any, List, Literal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from typing import Optional
from pydantic import BaseModel, Field

from src.core.di import DependencyContainer
from src.core.errors import ErrorSeverity, MarketDataError
from src.web.models.trade_request import BuyTradeRequest, SellTradeRequest
from src.core.errors import TradingError
from src.models.agent_artifacts import DiscoveryEnvelope, DecisionEnvelope, ResearchEnvelope, ReviewEnvelope
from src.models.dto import QueueStatusDTO
from src.models.paper_trading_automation import AutomationJobType
from src.auth.ai_runtime_auth import get_ai_runtime_status
from src.services.claude_agent.agent_artifact_service import AgentArtifactService
from src.services.paper_trading_automation_service import AutomationPausedError, DuplicateAutomationRunError
from ..dependencies import get_container


from ..utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)


class ModifyTradeRequest(BaseModel):
    """Request model for modifying trade stop loss and target."""
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None


class ResearchRunRequest(BaseModel):
    """Request body for focused single-candidate research runs."""

    candidate_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)


class ExecutionPreflightRequest(BaseModel):
    action: Literal["buy", "sell", "close", "modify_risk"]
    symbol: Optional[str] = None
    trade_id: Optional[str] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    target_price: Optional[float] = Field(default=None, gt=0)
    dry_run: bool = True


class EvaluateClosedTradesRequest(BaseModel):
    limit: int = Field(default=50, gt=0, le=500)
    symbol: Optional[str] = None


class PromotableImprovementDecisionRequest(BaseModel):
    decision: Literal["promote", "watch", "reject"]
    owner: str = "paper_trading_operator"
    reason: str = ""
    benchmark_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    guardrail: str = ""


class SessionRetrospectiveRequest(BaseModel):
    session_id: Optional[str] = None
    keep: List[Dict[str, Any]] = Field(default_factory=list)
    remove: List[Dict[str, Any]] = Field(default_factory=list)
    fix: List[Dict[str, Any]] = Field(default_factory=list)
    improve: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    owner: str = "paper_trading_operator"
    promotion_state: str = "queued"


class AutomationTriggerRequest(BaseModel):
    limit: Optional[int] = Field(default=None, ge=1, le=50)
    candidate_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    dry_run: bool = True
    schedule_source: Literal["manual", "scheduled"] = "manual"
    trigger_reason: str = ""


class AutomationControlRequest(BaseModel):
    job_types: List[AutomationJobType] = Field(default_factory=list)
    reason: str = ""

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["paper-trading"])

limiter = Limiter(key_func=get_remote_address)

paper_trading_limit = os.getenv("RATE_LIMIT_PAPER_TRADING", "20/minute")
DISCOVERY_TIMEOUT_SECONDS = 60.0
RESEARCH_TIMEOUT_SECONDS = 60.0
DECISION_TIMEOUT_SECONDS = 30.0
DAILY_REVIEW_TIMEOUT_SECONDS = 30.0
OPERATOR_RUNTIME_TIMEOUT_SECONDS = 15.0
RUNTIME_VALIDATION_TIMEOUT_SECONDS = 25.0


async def _get_required_account(account_manager, account_id: str):
    """Return the account or a fail-loud 404 response when it does not exist."""
    account = await account_manager.get_account(account_id)
    if account is None:
        return None, JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": (
                    f"Paper trading account '{account_id}' was not found. "
                    "Create the account first via POST /api/paper-trading/accounts/create."
                ),
            },
        )

    return account, None


async def _require_account_or_error(
    container: DependencyContainer,
    account_id: str,
):
    """Resolve an account or return the fail-loud response object."""
    account_manager = await container.get("paper_trading_account_manager")
    _, error_response = await _get_required_account(account_manager, account_id)
    return error_response


def _blocked_discovery_envelope(
    *,
    blockers: Optional[list[str]] = None,
    provider_metadata: Optional[Dict[str, Any]] = None,
) -> DiscoveryEnvelope:
    """Return a fail-loud discovery envelope without stale watchlist candidates."""
    return DiscoveryEnvelope(
        status="blocked",
        context_mode="stateful_watchlist",
        blockers=list(blockers or ["AI runtime is not ready for discovery generation."]),
        artifact_count=0,
        criteria=AgentArtifactService.discovery_criteria(),
        considered=["Discovery did not load any watchlist candidates because the stage is blocked."],
        candidates=[],
        provider_metadata=provider_metadata or {},
    )


def _blocked_research_envelope(*, blockers: Optional[list[str]] = None) -> ResearchEnvelope:
    return ResearchEnvelope(
        status="blocked",
        context_mode="single_candidate_research",
        blockers=list(blockers or ["AI runtime is not ready for research generation."]),
        artifact_count=0,
        criteria=AgentArtifactService.research_criteria(),
        considered=["No candidate is currently being researched because the stage is blocked."],
        research=None,
    )


def _blocked_decision_envelope(*, blockers: Optional[list[str]] = None) -> DecisionEnvelope:
    return DecisionEnvelope(
        status="blocked",
        context_mode="delta_position_review",
        blockers=list(blockers or ["AI runtime is not ready for decision generation."]),
        artifact_count=0,
        criteria=AgentArtifactService.decision_criteria(),
        considered=["No open positions are being reviewed because the stage is blocked."],
        decisions=[],
    )


def _blocked_review_envelope(*, blockers: Optional[list[str]] = None) -> ReviewEnvelope:
    return ReviewEnvelope(
        status="blocked",
        context_mode="delta_daily_review",
        blockers=list(blockers or ["AI runtime is not ready for review generation."]),
        artifact_count=0,
        criteria=AgentArtifactService.review_criteria(),
        considered=["No realized outcomes are being reviewed because the stage is blocked."],
        review=None,
    )


def _derive_status_reason(status: str, blockers: list[str]) -> str:
    if blockers:
        return blockers[0]
    if status == "ready":
        return "Manual run completed successfully."
    if status == "empty":
        return "Manual run completed without any eligible artifacts."
    return "Manual run completed."


async def _collect_dependency_state(container: DependencyContainer, account_id: str) -> Dict[str, Any]:
    dependency_state: Dict[str, Any] = {
        "account_id": account_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        runtime_status = await container.get("trading_capability_service")
        snapshot = await runtime_status.get_snapshot(account_id=account_id)
        dependency_state["capability_snapshot"] = snapshot.to_dict()
    except Exception as exc:  # noqa: BLE001
        dependency_state["capability_snapshot_error"] = str(exc)

    try:
        config_state = await container.get("configuration_state")
        dependency_state["runtime_mode"] = (await config_state.get_system_status()).get("status")
    except Exception as exc:  # noqa: BLE001
        dependency_state["runtime_mode_error"] = str(exc)

    return dependency_state


async def _record_manual_run_audit(
    container: DependencyContainer,
    *,
    run_id: str,
    account_id: str,
    route_name: str,
    status: str,
    status_reason: str,
    started_at: str,
    completed_at: str,
    duration_ms: int,
    dependency_state: Dict[str, Any],
    provider_metadata: Dict[str, Any],
) -> None:
    try:
        store = await container.get("paper_trading_store")
        await store.record_manual_run_audit(
            run_id=run_id,
            account_id=account_id,
            route_name=route_name,
            status=status,
            status_reason=status_reason,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            dependency_state=dependency_state,
            provider_metadata=provider_metadata,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist manual run audit for %s (%s): %s", route_name, run_id, exc)


async def _execute_manual_run(
    *,
    container: DependencyContainer,
    account_id: str,
    route_name: str,
    timeout_seconds: float,
    action: Callable[[], Awaitable[DiscoveryEnvelope | ResearchEnvelope | DecisionEnvelope | ReviewEnvelope]],
    timeout_factory: Callable[[str], DiscoveryEnvelope | ResearchEnvelope | DecisionEnvelope | ReviewEnvelope],
) -> Dict[str, Any]:
    run_id = f"run_{uuid.uuid4().hex[:16]}"
    started_at = datetime.now(timezone.utc).isoformat()
    dependency_state = await _collect_dependency_state(container, account_id)
    envelope = None

    try:
        envelope = await asyncio.wait_for(action(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        envelope = timeout_factory(
            f"Manual run exceeded the {int(timeout_seconds)}s deadline and was cancelled before completion."
        )
    except Exception:
        completed_at = datetime.now(timezone.utc).isoformat()
        duration_ms = max(
            int(
                (
                    datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
                ).total_seconds()
                * 1000
            ),
            0,
        )
        await _record_manual_run_audit(
            container,
            run_id=run_id,
            account_id=account_id,
            route_name=route_name,
            status="error",
            status_reason="Manual run raised an unhandled exception.",
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            dependency_state=dependency_state,
            provider_metadata={},
        )
        raise

    completed_at = datetime.now(timezone.utc).isoformat()
    duration_ms = max(
        int(
            (
                datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
            ).total_seconds()
            * 1000
        ),
        0,
    )
    status_reason = _derive_status_reason(envelope.status, list(envelope.blockers))
    provider_metadata = dict(envelope.provider_metadata or {})
    logger.info(
        "manual_run_completed route=%s run_id=%s account_id=%s status=%s duration_ms=%s provider=%s model=%s",
        route_name,
        run_id,
        account_id,
        envelope.status,
        duration_ms,
        provider_metadata.get("provider"),
        provider_metadata.get("model"),
    )
    await _record_manual_run_audit(
        container,
        run_id=run_id,
        account_id=account_id,
        route_name=route_name,
        status=envelope.status,
        status_reason=status_reason,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        dependency_state=dependency_state,
        provider_metadata=provider_metadata,
    )
    return envelope.model_copy(
        update={
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "status_reason": status_reason,
        }
    ).model_dump(mode="json")


async def _execute_automation_action(
    *,
    container: DependencyContainer,
    account_id: str,
    timeout_seconds: float,
    action: Callable[[], Awaitable[DiscoveryEnvelope | ResearchEnvelope | DecisionEnvelope | ReviewEnvelope]],
    timeout_factory: Callable[[str], DiscoveryEnvelope | ResearchEnvelope | DecisionEnvelope | ReviewEnvelope],
) -> Dict[str, Any]:
    """Execute an automation action without writing manual-run audit state."""
    started_at = datetime.now(timezone.utc).isoformat()
    dependency_state = await _collect_dependency_state(container, account_id)
    try:
        envelope = await asyncio.wait_for(action(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        envelope = timeout_factory(
            f"Automation run exceeded the {int(timeout_seconds)}s deadline and was cancelled before completion."
        )
    except Exception as exc:
        completed_at = datetime.now(timezone.utc).isoformat()
        duration_ms = max(
            int(
                (
                    datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
                ).total_seconds()
                * 1000
            ),
            0,
        )
        return {
            "status": "error",
            "blockers": [str(exc).strip() or "Automation run raised an unhandled exception."],
            "provider_metadata": {},
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "status_reason": "Automation run raised an unhandled exception.",
            "dependency_state": dependency_state,
        }

    completed_at = datetime.now(timezone.utc).isoformat()
    duration_ms = max(
        int(
            (
                datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
            ).total_seconds()
            * 1000
        ),
        0,
    )
    status_reason = _derive_status_reason(envelope.status, list(envelope.blockers))
    return envelope.model_copy(
        update={
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "status_reason": status_reason,
        }
    ).model_dump(mode="json") | {"dependency_state": dependency_state}


async def _build_queue_status_payload(container: DependencyContainer) -> Dict[str, Any]:
    """Return the current queue snapshot without routing through the HTTP layer."""
    queue_repo = await container.get("queue_state_repository")
    if not queue_repo:
        return {
            "queues": [],
            "stats": {},
            "status": "service_unavailable",
            "error": "QueueStateRepository not available",
        }

    all_queue_states = await queue_repo.get_all_statuses()
    summary = await queue_repo.get_queue_statistics_summary()
    queue_dtos: List[Dict[str, Any]] = []
    for queue_name, queue_state in all_queue_states.items():
        dto = QueueStatusDTO.from_queue_state(queue_state)
        queue_dtos.append(dto.to_dict())

    stats = {
        "total_queues": summary["total_queues"],
        "total_pending_tasks": summary["total_pending"],
        "total_active_tasks": summary["total_running"],
        "total_completed_tasks": summary["total_completed_today"],
        "total_failed_tasks": summary["total_failed"],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    has_failed = any(queue["failed_count"] > 0 for queue in queue_dtos)
    has_running = any(queue["running_count"] > 0 for queue in queue_dtos)
    status = "healthy"
    if has_failed:
        status = "degraded"
    elif has_running:
        status = "active"

    return {
        "queues": queue_dtos,
        "stats": stats,
        "status": status,
    }


def _serialize_position(pos: Any) -> Dict[str, Any]:
    """Normalize an open-position response for API and WebMCP consumers."""
    return {
        "id": pos.trade_id,
        "tradeId": pos.trade_id,
        "symbol": pos.symbol,
        "quantity": pos.quantity,
        "avgPrice": pos.entry_price,
        "entryPrice": pos.entry_price,
        "ltp": pos.current_price,
        "currentPrice": pos.current_price,
        "pnl": pos.unrealized_pnl,
        "pnlPercent": pos.unrealized_pnl_pct,
        "daysHeld": pos.days_held,
        "target": pos.target_price,
        "stopLoss": pos.stop_loss,
        "strategy": pos.strategy_rationale,
        "currentValue": pos.current_value,
        "tradeType": pos.trade_type,
        "markStatus": pos.market_price_status,
        "markDetail": pos.market_price_detail,
        "markTimestamp": pos.market_price_timestamp,
    }


def _trading_error_code(error: TradingError) -> str:
    context = getattr(error, "context", None)
    return str(getattr(context, "code", "") or "").strip().upper()


def _trading_error_detail(error: TradingError) -> Optional[str]:
    context = getattr(error, "context", None)
    detail = getattr(context, "details", None)
    return str(detail).strip() if detail else None


async def _load_positions_for_read_surface(
    account_manager: Any,
    account_id: str,
) -> tuple[List[Any], str, Optional[str]]:
    """Return live-valued positions when available, otherwise explicit degraded rows."""
    try:
        return await account_manager.get_open_positions(account_id), "live", None
    except MarketDataError as error:
        if _trading_error_code(error) != "MARKET_DATA_LIVE_QUOTES_REQUIRED":
            raise
        detail = _trading_error_detail(error) or str(error)
        positions = await account_manager.get_store_backed_open_positions(
            account_id,
            mark_status="quote_unavailable",
            mark_detail=detail,
        )
        return positions, "quote_unavailable", detail


def _serialize_closed_trade(trade: Any) -> Dict[str, Any]:
    """Normalize a closed trade for API and WebMCP consumers."""
    hold_days = trade.holding_period_days
    if hold_days < 1:
        hold_time = "< 1 day"
    elif hold_days == 1:
        hold_time = "1 day"
    else:
        hold_time = f"{hold_days} days"

    return {
        "id": trade.trade_id,
        "date": trade.exit_date,
        "symbol": trade.symbol,
        "action": trade.trade_type,
        "entryPrice": trade.entry_price,
        "exitPrice": trade.exit_price,
        "quantity": trade.quantity,
        "holdTime": hold_time,
        "pnl": trade.realized_pnl,
        "pnlPercent": trade.realized_pnl_pct,
        "strategy": trade.strategy_rationale,
    }


def _unwrap_route_payload(name: str, payload: Any) -> Any:
    """Fail loud when an internal route call returned an error response."""
    if not isinstance(payload, JSONResponse):
        return payload

    try:
        body = json.loads(payload.body.decode("utf-8")) if getattr(payload, "body", None) else {}
    except Exception:
        body = {}

    raise TradingError(
        str(body.get("error") or body.get("message") or f"{name} failed."),
        code=body.get("code"),
        severity=ErrorSeverity.HIGH,
        recoverable=bool(body.get("recoverable", False)),
        route_name=name,
        route_status_code=getattr(payload, "status_code", None),
        route_category=body.get("category"),
    )


def _execution_mode() -> str:
    return "operator_confirmed_execution"


def _age_seconds(timestamp: Optional[str]) -> Optional[float]:
    if not timestamp:
        return None
    try:
        normalized = timestamp.replace("Z", "+00:00")
        observed = datetime.fromisoformat(normalized)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return max((datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds(), 0.0)
    except ValueError:
        return None


async def _load_symbol_quote_freshness(
    container: DependencyContainer,
    symbol: str,
    *,
    freshness_threshold_seconds: int = 5 * 60,
) -> Dict[str, Any]:
    market_data_service = await container.get("market_data_service")
    if market_data_service is None:
        return {
            "status": "missing",
            "summary": "MarketDataService is not configured for this runtime.",
            "timestamp": "",
            "age_seconds": None,
            "provider": "",
            "price": None,
        }

    quote = await market_data_service.get_market_data(symbol)
    if quote is None:
        try:
            await asyncio.wait_for(
                market_data_service.subscribe_market_data(symbol),
                timeout=OPERATOR_RUNTIME_TIMEOUT_SECONDS,
            )
            quote = await market_data_service.get_market_data(symbol)
        except Exception:
            quote = None

    if quote is None:
        return {
            "status": "missing",
            "summary": f"No live market quote is currently available for {symbol}.",
            "timestamp": "",
            "age_seconds": None,
            "provider": "",
            "price": None,
        }

    raw_timestamp = getattr(quote, "timestamp", None)
    timestamp = raw_timestamp.isoformat() if hasattr(raw_timestamp, "isoformat") else str(raw_timestamp or "")
    age_seconds = _age_seconds(timestamp)
    status = "fresh" if age_seconds is not None and age_seconds <= freshness_threshold_seconds else "stale"
    price = getattr(quote, "ltp", None)
    return {
        "status": status,
        "summary": (
            f"Live market quote for {symbol} is fresh."
            if status == "fresh"
            else f"Live market quote for {symbol} is stale or missing a reliable timestamp."
        ),
        "timestamp": timestamp,
        "age_seconds": age_seconds,
        "provider": str(getattr(quote, "provider", "") or ""),
        "price": float(price) if price is not None else None,
    }


async def _build_position_health_payload(
    container: DependencyContainer,
    account_id: str,
) -> Dict[str, Any]:
    account_manager = await container.get("paper_trading_account_manager")
    positions = await account_manager.get_open_positions(account_id)
    serialized_positions = [_serialize_position(position) for position in positions]
    stale_positions = [item for item in serialized_positions if item.get("markStatus") != "live"]
    healthy_positions = [item for item in serialized_positions if item.get("markStatus") == "live"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "execution_mode": _execution_mode(),
        "position_count": len(serialized_positions),
        "healthy_count": len(healthy_positions),
        "stale_count": len(stale_positions),
        "status": "ready" if not stale_positions else "degraded",
        "positions": serialized_positions,
        "stale_positions": stale_positions,
    }


async def _build_execution_preflight_payload(
    container: DependencyContainer,
    *,
    account_id: str,
    preflight: ExecutionPreflightRequest,
) -> Dict[str, Any]:
    account_manager = await container.get("paper_trading_account_manager")
    store = await container.get("paper_trading_store")
    learning_service = await container.get("paper_trading_learning_service")
    queue_status = await _build_queue_status_payload(container)
    account = await account_manager.get_account(account_id)

    symbol = str(preflight.symbol or "").strip().upper() or None
    trade = None
    if preflight.trade_id:
        trade = await store.get_trade(preflight.trade_id)
        if trade is not None and not symbol:
            symbol = str(getattr(trade, "symbol", "") or "").strip().upper() or None

    quote_freshness = (
        await _load_symbol_quote_freshness(container, symbol)
        if symbol
        else {
            "status": "missing",
            "summary": "No symbol was provided for execution preflight.",
            "timestamp": "",
            "age_seconds": None,
            "provider": "",
            "price": None,
        }
    )
    positions = await account_manager.get_open_positions(account_id) if account is not None else []
    open_symbol_conflict = next(
        (position for position in positions if str(getattr(position, "symbol", "")).upper() == (symbol or "")),
        None,
    )

    latest_research = None
    latest_decision = None
    latest_review = None
    if learning_service is not None and symbol:
        latest_research = await learning_service.learning_store.get_latest_research_memory(account_id, symbol)
        latest_decision = await learning_service.get_latest_decision_packet(account_id, symbol)
        latest_review = await learning_service.get_latest_review_report(account_id)

    reasons: List[str] = []
    risk_checks = {
        "account_exists": bool(account),
        "queue_clean": int((queue_status.get("stats") or {}).get("total_pending_tasks") or 0) == 0
        and int((queue_status.get("stats") or {}).get("total_active_tasks") or 0) == 0,
        "quote_fresh": quote_freshness.get("status") == "fresh",
        "duplicate_or_conflicting_action": False,
        "trade_open": False,
    }

    if not risk_checks["account_exists"]:
        reasons.append(f"Paper trading account '{account_id}' was not found.")
    if not risk_checks["queue_clean"]:
        reasons.append("Background queue work is active; manual-only execution cannot proceed until queues are clean.")
    if not risk_checks["quote_fresh"]:
        reasons.append(quote_freshness.get("summary") or "A fresh live quote is required before execution.")

    research_gate = {
        "required": preflight.action in {"buy", "sell"},
        "passed": False,
        "latest_research_id": latest_research.get("research_id") if latest_research else None,
        "confidence": float((latest_research or {}).get("confidence") or 0.0),
        "actionability": (latest_research or {}).get("actionability"),
        "external_evidence_status": (latest_research or {}).get("external_evidence_status"),
    }
    if research_gate["required"]:
        research_gate["passed"] = bool(
            latest_research
            and float((latest_research or {}).get("confidence") or 0.0) >= 0.60
            and str((latest_research or {}).get("actionability") or "") == "actionable"
            and str((latest_research or {}).get("external_evidence_status") or "") == "fresh"
        )
        if open_symbol_conflict is not None:
            risk_checks["duplicate_or_conflicting_action"] = True
            reasons.append(f"{symbol}: an open position already exists, so a new entry would be duplicative or conflicting.")
        if not research_gate["passed"]:
            reasons.append(
                f"{symbol or 'Entry'} lacks a fresh actionable research packet above the deterministic confidence threshold."
            )
    else:
        research_gate["passed"] = True

    decision_gate = {
        "required": preflight.action in {"close", "modify_risk"},
        "passed": False,
        "latest_decision_id": getattr(latest_decision, "decision_id", None),
        "confidence": float(getattr(latest_decision, "confidence", 0.0) or 0.0),
        "action": getattr(latest_decision, "action", None),
        "latest_review_id": getattr(latest_review, "review_id", None),
    }
    if decision_gate["required"]:
        trade_status = getattr(getattr(trade, "status", None), "value", getattr(trade, "status", ""))
        risk_checks["trade_open"] = bool(
            trade is not None
            and str(getattr(trade, "account_id", "")) == account_id
            and str(trade_status).strip().lower() == "open"
        )
        if not risk_checks["trade_open"]:
            reasons.append(f"{preflight.trade_id or 'Trade'} is not an open trade in account {account_id}.")
        allowed_actions = {"review_exit", "take_profit"} if preflight.action == "close" else {"review_exit", "tighten_stop", "take_profit"}
        decision_gate["passed"] = bool(
            latest_decision
            and float(getattr(latest_decision, "confidence", 0.0) or 0.0) >= 0.65
            and str(getattr(latest_decision, "action", "") or "") in allowed_actions
        )
        if not decision_gate["passed"]:
            reasons.append(
                f"{symbol or preflight.trade_id or 'Trade'} does not have a recent high-confidence decision packet authorizing this mutation."
            )
    else:
        decision_gate["passed"] = True

    if not symbol:
        reasons.append("A symbol could not be resolved for execution preflight.")

    idempotency_material = json.dumps(
        {
            "account_id": account_id,
            "action": preflight.action,
            "symbol": symbol,
            "trade_id": preflight.trade_id,
            "quantity": preflight.quantity,
            "price": preflight.price,
            "stop_loss": preflight.stop_loss,
            "target_price": preflight.target_price,
        },
        sort_keys=True,
    )
    state_signature_material = json.dumps(
        {
            "account_id": account_id,
            "symbol": symbol,
            "trade_id": preflight.trade_id,
            "quote_status": quote_freshness.get("status"),
            "quote_timestamp": quote_freshness.get("timestamp"),
            "queue_clean": risk_checks["queue_clean"],
            "quote_fresh": risk_checks["quote_fresh"],
            "trade_open": risk_checks["trade_open"],
            "duplicate_or_conflicting_action": risk_checks["duplicate_or_conflicting_action"],
            "research_gate": research_gate,
            "decision_gate": decision_gate,
        },
        sort_keys=True,
    )
    idempotency_key = f"ptx_{uuid.uuid5(uuid.NAMESPACE_URL, idempotency_material).hex}"
    state_signature = f"pts_{uuid.uuid5(uuid.NAMESPACE_URL, state_signature_material).hex}"
    allowed = not reasons

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "execution_mode": _execution_mode(),
        "action": preflight.action,
        "symbol": symbol,
        "trade_id": preflight.trade_id,
        "dry_run": preflight.dry_run,
        "allowed": allowed,
        "reasons": list(dict.fromkeys(reasons)),
        "freshness": quote_freshness,
        "risk_checks": risk_checks,
        "research_gate": research_gate,
        "decision_gate": decision_gate,
        "idempotency_key": idempotency_key,
        "state_signature": state_signature,
    }


def _build_execution_mutation_contract(
    account_id: str,
    preflight: ExecutionPreflightRequest,
    preflight_result: Dict[str, Any],
) -> Dict[str, Any]:
    symbol = str(preflight_result.get("symbol") or preflight.symbol or "").strip().upper() or None
    proposal_id = f"proposal_{uuid.uuid4().hex[:16]}"
    generated_at = datetime.now(timezone.utc)
    expires_at = (generated_at + timedelta(minutes=5)).replace(microsecond=0).isoformat()

    if preflight.action == "buy":
        endpoint = f"/api/paper-trading/accounts/{account_id}/trades/buy"
        http_method = "POST"
        exact_action_payload = {
            "symbol": symbol,
            "quantity": preflight.quantity,
            "order_type": "LIMIT" if preflight.price is not None else "MARKET",
            **({"price": preflight.price} if preflight.price is not None else {}),
        }
    elif preflight.action == "sell":
        endpoint = f"/api/paper-trading/accounts/{account_id}/trades/sell"
        http_method = "POST"
        exact_action_payload = {
            "symbol": symbol,
            "quantity": preflight.quantity,
            "order_type": "LIMIT" if preflight.price is not None else "MARKET",
            **({"price": preflight.price} if preflight.price is not None else {}),
        }
    elif preflight.action == "close":
        endpoint = f"/api/paper-trading/accounts/{account_id}/trades/{preflight.trade_id}/close"
        http_method = "POST"
        exact_action_payload = {"trade_id": preflight.trade_id}
    else:
        endpoint = f"/api/paper-trading/accounts/{account_id}/trades/{preflight.trade_id}"
        http_method = "PATCH"
        exact_action_payload = {
            key: value
            for key, value in {
                "stop_loss": preflight.stop_loss,
                "target_price": preflight.target_price,
            }.items()
            if value is not None
        }

    return {
        **preflight_result,
        "proposal_id": proposal_id,
        "expires_at": expires_at,
        "execution_endpoint": endpoint,
        "http_method": http_method,
        "exact_action_payload": exact_action_payload,
    }


def _build_readiness_payload(capability_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Project the capability snapshot into a lightweight readiness surface."""
    checks = capability_snapshot.get("checks", []) if isinstance(capability_snapshot, dict) else []

    def _find_check(key: str) -> Dict[str, Any]:
        return next((check for check in checks if check.get("key") == key), {"status": "unknown"})

    return {
        "container": "ready",
        "ai_runtime": _find_check("ai_runtime"),
        "quote_stream": _find_check("quote_stream"),
        "market_data": _find_check("market_data"),
        "broker_auth": _find_check("broker_auth"),
    }


async def _build_learning_readiness_payload(
    *,
    container: DependencyContainer,
    account_id: str,
) -> Dict[str, Any]:
    learning_service = await container.get("paper_trading_learning_service")
    readiness = await learning_service.get_learning_readiness(account_id)
    return readiness.model_dump(mode="json")


async def _build_artifact_staleness_payload(
    *,
    container: DependencyContainer,
    account_id: str,
    readiness: Dict[str, Any],
) -> Dict[str, Any]:
    learning_service = await container.get("paper_trading_learning_service")
    latest_review = await learning_service.get_latest_review_report(account_id)
    recent_research = await learning_service.learning_store.list_recent_research_memory(account_id, limit=1)
    recent_decision = await learning_service.learning_store.list_recent_decision_memory(account_id, limit=1)

    def _age_from_timestamp(timestamp: Optional[str]) -> Optional[float]:
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - parsed).total_seconds(), 2)

    ai_runtime = readiness.get("ai_runtime", {}) if isinstance(readiness, dict) else {}
    market_data = readiness.get("market_data", {}) if isinstance(readiness, dict) else {}
    market_data_meta = market_data.get("metadata", {}) if isinstance(market_data, dict) else {}
    ai_meta = ai_runtime.get("metadata", {}) if isinstance(ai_runtime, dict) else {}
    latest_research = recent_research[0] if recent_research else None
    latest_decision_entry = recent_decision[0] if recent_decision else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_validation_age_seconds": ai_meta.get("last_successful_validation_age_seconds"),
        "quote_freshness_age_seconds": market_data_meta.get("freshest_age_seconds"),
        "last_research_artifact_age_seconds": _age_from_timestamp((latest_research or {}).get("generated_at") if latest_research else None),
        "last_decision_artifact_age_seconds": _age_from_timestamp(getattr(latest_decision_entry, "generated_at", None)),
        "last_review_artifact_age_seconds": _age_from_timestamp(getattr(latest_review, "generated_at", None)),
    }


def _build_operator_recommendation(
    *,
    readiness: Dict[str, Any],
    positions_health: Dict[str, Any],
    learning_readiness: Dict[str, Any],
    queue_status: Dict[str, Any],
    recent_research: List[Dict[str, Any]],
    recent_decisions: List[Any],
) -> Dict[str, Any]:
    ai_ready = str((readiness.get("ai_runtime") or {}).get("status") or "") == "ready"
    market_ready = str((readiness.get("market_data") or {}).get("status") or "") == "ready"
    quote_ready = str((readiness.get("quote_stream") or {}).get("status") or "") == "ready"
    positions_ready = str(positions_health.get("status") or "") == "ready"
    queue_stats = queue_status.get("stats", {}) if isinstance(queue_status, dict) else {}
    queue_clean = int(queue_stats.get("total_pending_tasks") or 0) == 0 and int(queue_stats.get("total_active_tasks") or 0) == 0
    actionable_entry_ready = any(
        float((entry or {}).get("confidence") or 0.0) >= 0.60
        and str((entry or {}).get("actionability") or "") == "actionable"
        and str((entry or {}).get("external_evidence_status") or "") == "fresh"
        for entry in recent_research
    )
    mutation_authorized = any(
        float(getattr(entry, "confidence", 0.0) or 0.0) >= 0.65
        and str(getattr(entry, "action", "") or "") in {"review_exit", "tighten_stop", "take_profit"}
        for entry in recent_decisions
    )

    research_ready = ai_ready and queue_clean
    decision_ready = ai_ready and market_ready and quote_ready and positions_ready
    review_ready = ai_ready and queue_clean
    execution_blocked = not (ai_ready and market_ready and quote_ready and queue_clean and (actionable_entry_ready or mutation_authorized))

    reasons: List[str] = []
    if not ai_ready:
        reasons.append("AI runtime is not currently ready.")
    if not market_ready:
        reasons.append("Market data is not fresh enough for execution-sensitive decisions.")
    if not quote_ready:
        reasons.append("Quote stream is not currently delivering live ticks.")
    if not queue_clean:
        reasons.append("Background queue work remains active.")
    if not positions_ready:
        reasons.append("At least one open position still relies on stale marks.")
    if not actionable_entry_ready and not mutation_authorized:
        reasons.append("No fresh actionable research packet or authorized decision packet currently clears the mutation gate.")

    return {
        "research_ready": research_ready,
        "decision_ready": decision_ready,
        "review_ready": review_ready,
        "execution_blocked": execution_blocked,
        "reasons": reasons,
        "entry_execution_ready": actionable_entry_ready,
        "position_mutation_ready": mutation_authorized,
        "learning_pending": {
            "unevaluated_closed_trades": int(learning_readiness.get("unevaluated_closed_trade_count") or 0),
            "queued_promotable_improvements": int(learning_readiness.get("queued_promotable_count") or 0),
            "decision_pending_improvements": int(learning_readiness.get("decision_pending_improvement_count") or 0),
        },
    }


def _build_operator_incidents(
    *,
    capability_snapshot: Dict[str, Any],
    queue_status: Dict[str, Any],
    positions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Derive operator incidents from readiness, queue, and live-position state."""
    incidents: List[Dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).isoformat()

    for check in capability_snapshot.get("checks", []) if isinstance(capability_snapshot, dict) else []:
        status = str(check.get("status") or "")
        if status not in {"blocked", "degraded"}:
            continue
        incidents.append(
            {
                "incident_id": f"capability:{check.get('key')}",
                "type": "capability",
                "severity": "high" if status == "blocked" and check.get("blocking", True) else "medium",
                "status": status,
                "summary": check.get("summary"),
                "detail": check.get("detail"),
                "blocking": bool(check.get("blocking", True)),
                "generated_at": generated_at,
            }
        )

    stats = queue_status.get("stats", {}) if isinstance(queue_status, dict) else {}
    pending = int(stats.get("total_pending_tasks") or 0)
    running = int(stats.get("total_active_tasks") or 0)
    if pending > 0 or running > 0:
        incidents.append(
            {
                "incident_id": "queue:manual_only_violation",
                "type": "queue",
                "severity": "high",
                "status": "blocked",
                "summary": "Background queue work is active while the system is in manual-only mode.",
                "detail": f"{pending} pending and {running} running task(s) remain in the scheduler queues.",
                "blocking": True,
                "generated_at": generated_at,
            }
        )

    for position in positions:
        if position.get("markStatus") == "live":
            continue
        incidents.append(
            {
                "incident_id": f"mark:{position.get('tradeId')}",
                "type": "market_price",
                "severity": "medium",
                "status": "degraded",
                "summary": f"{position.get('symbol')} is operating on a stale entry mark.",
                "detail": position.get("markDetail")
                or "No fresh market mark is available for this position.",
                "blocking": False,
                "generated_at": generated_at,
            }
        )

    return incidents


async def _build_operator_snapshot_payload(
    *,
    request: Request,
    container: DependencyContainer,
    account_id: str,
    refresh_readiness: bool = False,
) -> Dict[str, Any]:
    """Assemble a deterministic operator snapshot for WebMCP and human operators."""
    def _route_impl(fn: Callable[..., Awaitable[Dict[str, Any]]]) -> Callable[..., Awaitable[Dict[str, Any]]]:
        return getattr(fn, "__wrapped__", fn)

    if refresh_readiness:
        await get_ai_runtime_status(force_refresh=True)

    capability_service = await container.get("trading_capability_service")
    capability_snapshot_obj = await capability_service.get_snapshot(account_id=account_id)
    capability_snapshot = capability_snapshot_obj.to_dict()
    learning_service = await container.get("paper_trading_learning_service")

    config_state = await container.get("configuration_state")
    configuration_status = await config_state.get_system_status()
    queue_status = await _build_queue_status_payload(container)

    (
        overview,
        positions_payload,
        trades_payload,
        performance,
        discovery,
        decisions,
        review,
        learning_summary,
        improvement_report,
        run_history,
        latest_retrospective,
        recent_trade_outcomes,
        promotable_improvements,
        positions_health,
        learning_readiness,
        recent_research_entries,
        recent_decision_entries,
    ) = await asyncio.gather(
        _route_impl(get_paper_trading_account_overview)(request=request, account_id=account_id, container=container),
        _route_impl(get_paper_trading_positions)(request=request, account_id=account_id, container=container),
        _route_impl(get_paper_trading_trades)(request=request, account_id=account_id, limit=20, container=container),
        _route_impl(get_paper_trading_performance)(request=request, account_id=account_id, period="month", container=container),
        _route_impl(get_paper_trading_discovery)(request=request, account_id=account_id, limit=10, container=container),
        _route_impl(get_paper_trading_decisions)(request=request, account_id=account_id, limit=3, container=container),
        _route_impl(get_paper_trading_review)(request=request, account_id=account_id, container=container),
        _route_impl(get_paper_trading_learning_summary)(request=request, account_id=account_id, container=container),
        _route_impl(get_paper_trading_improvement_report)(request=request, account_id=account_id, container=container),
        _route_impl(get_paper_trading_run_history)(request=request, account_id=account_id, limit=20, container=container),
        learning_service.get_latest_session_retrospective(account_id),
        learning_service.list_trade_outcomes(account_id, limit=10),
        learning_service.list_promotable_improvements(account_id, limit=10),
        _build_position_health_payload(container, account_id=account_id),
        _build_learning_readiness_payload(container=container, account_id=account_id),
        learning_service.learning_store.list_recent_research_memory(account_id, limit=10),
        learning_service.learning_store.list_recent_decision_memory(account_id, limit=10),
    )

    overview = _unwrap_route_payload("paper_trading.overview", overview)
    positions_payload = _unwrap_route_payload("paper_trading.positions", positions_payload)
    trades_payload = _unwrap_route_payload("paper_trading.trades", trades_payload)
    performance = _unwrap_route_payload("paper_trading.performance", performance)

    positions = positions_payload.get("positions", []) if isinstance(positions_payload, dict) else []
    readiness = _build_readiness_payload(capability_snapshot)
    staleness = await _build_artifact_staleness_payload(
        container=container,
        account_id=account_id,
        readiness=readiness,
    )
    latest_improvement_decisions = [
        improvement.model_dump(mode="json")
        for improvement in promotable_improvements
        if getattr(improvement, "decision", None)
    ][:5]
    promotion_report = {
        "ready_now": sum(1 for improvement in promotable_improvements if str(improvement.promotion_state) == "ready_now"),
        "watch": sum(1 for improvement in promotable_improvements if str(improvement.promotion_state) == "watch"),
        "rejected": sum(1 for improvement in promotable_improvements if str(improvement.promotion_state) == "rejected"),
        "last_decision_timestamp": next(
            (improvement.decided_at for improvement in promotable_improvements if getattr(improvement, "decided_at", None)),
            None,
        ),
        "last_owner": next(
            (
                improvement.decision_owner or improvement.owner
                for improvement in promotable_improvements
                if getattr(improvement, "decided_at", None)
            ),
            None,
        ),
    }
    operator_recommendation = _build_operator_recommendation(
        readiness=readiness,
        positions_health=positions_health,
        learning_readiness=learning_readiness,
        queue_status=queue_status,
        recent_research=recent_research_entries,
        recent_decisions=recent_decision_entries,
    )
    incidents = _build_operator_incidents(
        capability_snapshot=capability_snapshot,
        queue_status=queue_status,
        positions=positions,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_account_id": account_id,
        "execution_mode": _execution_mode(),
        "health": {
            "status": "healthy",
            "message": "Paper trading operator snapshot assembled.",
            "readiness": readiness,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "configuration_status": configuration_status,
        "queue_status": queue_status,
        "capability_snapshot": capability_snapshot,
        "overview": overview,
        "positions": positions,
        "trades": trades_payload.get("trades", []) if isinstance(trades_payload, dict) else [],
        "performance": performance,
        "discovery": discovery,
        "decisions": decisions,
        "review": review,
        "learning_summary": learning_summary,
        "improvement_report": improvement_report,
        "run_history": run_history,
        "latest_retrospective": latest_retrospective.model_dump(mode="json") if latest_retrospective else None,
        "learning_readiness": learning_readiness,
        "latest_improvement_decisions": latest_improvement_decisions,
        "promotion_report": promotion_report,
        "staleness": staleness,
        "operator_recommendation": operator_recommendation,
        "positions_health": positions_health,
        "recent_trade_outcomes": [evaluation.model_dump(mode="json") for evaluation in recent_trade_outcomes],
        "promotable_improvements": [improvement.model_dump(mode="json") for improvement in promotable_improvements],
        "incidents": incidents,
    }


async def _build_automation_job_execution(
    *,
    request: Request,
    container: DependencyContainer,
    account_id: str,
    job_type: AutomationJobType,
    trigger: AutomationTriggerRequest,
) -> tuple[float, Callable[[], Awaitable[Dict[str, Any]]]]:
    """Map an automation job type to an existing bounded cognition flow."""
    if job_type == "research_cycle":
        if not trigger.candidate_id and not trigger.symbol:
            raise TradingError(
                "Provide candidate_id or symbol before running research_cycle.",
                severity=ErrorSeverity.HIGH,
            )

        async def execute() -> Dict[str, Any]:
            artifact_service = await container.get("agent_artifact_service")
            async def action() -> ResearchEnvelope:
                return await artifact_service.get_research_view(
                    account_id,
                    candidate_id=trigger.candidate_id,
                    symbol=trigger.symbol,
                    refresh=True,
                )

            return await _execute_automation_action(
                container=container,
                account_id=account_id,
                timeout_seconds=RESEARCH_TIMEOUT_SECONDS,
                action=action,
                timeout_factory=lambda message: _blocked_research_envelope(blockers=[message]),
            )

        return RESEARCH_TIMEOUT_SECONDS, execute

    if job_type == "decision_review_cycle":
        limit = trigger.limit or 3

        async def execute() -> Dict[str, Any]:
            artifact_service = await container.get("agent_artifact_service")
            async def action() -> DecisionEnvelope:
                return await artifact_service.get_decision_view(account_id, limit=limit, refresh=True)

            return await _execute_automation_action(
                container=container,
                account_id=account_id,
                timeout_seconds=DECISION_TIMEOUT_SECONDS,
                action=action,
                timeout_factory=lambda message: _blocked_decision_envelope(blockers=[message]),
            )

        return DECISION_TIMEOUT_SECONDS, execute

    if job_type == "exit_check_cycle":
        limit = trigger.limit or 3

        async def execute() -> Dict[str, Any]:
            artifact_service = await container.get("agent_artifact_service")
            async def action() -> DecisionEnvelope:
                return await artifact_service.get_decision_view(account_id, limit=limit, refresh=True)

            return await _execute_automation_action(
                container=container,
                account_id=account_id,
                timeout_seconds=DECISION_TIMEOUT_SECONDS,
                action=action,
                timeout_factory=lambda message: _blocked_decision_envelope(blockers=[message]),
            )

        return DECISION_TIMEOUT_SECONDS, execute

    if job_type == "daily_review_cycle":
        async def execute() -> Dict[str, Any]:
            artifact_service = await container.get("agent_artifact_service")
            async def action() -> ReviewEnvelope:
                return await artifact_service.get_review_view(account_id, refresh=True)

            return await _execute_automation_action(
                container=container,
                account_id=account_id,
                timeout_seconds=DAILY_REVIEW_TIMEOUT_SECONDS,
                action=action,
                timeout_factory=lambda message: _blocked_review_envelope(blockers=[message]),
            )

        return DAILY_REVIEW_TIMEOUT_SECONDS, execute

    if job_type == "improvement_eval_cycle":
        async def execute() -> Dict[str, Any]:
            learning_service = await container.get("paper_trading_learning_service")
            improvement_service = await container.get("paper_trading_improvement_service")
            outcomes = await learning_service.list_trade_outcomes(account_id, limit=20)
            readiness = await learning_service.get_learning_readiness(account_id)
            report = await improvement_service.get_improvement_report(account_id)
            payload = {
                "status": "ready" if (report.get("promotable_proposals") or report.get("watch_proposals") or outcomes) else "empty",
                "blockers": [] if outcomes or report else ["No improvement evidence is currently available."],
                "context_mode": "benchmark_gated_improvement",
                "artifact_count": len(report.get("promotable_proposals") or []) + len(report.get("watch_proposals") or []),
                "provider_metadata": {
                    "provider": "codex",
                    "job_type": job_type,
                    "tools": ["learning_readiness", "benchmark_report"],
                },
                "improvement_report": report,
                "learning_readiness": readiness.model_dump(mode="json"),
                "recent_trade_outcomes": [item.model_dump(mode="json") for item in outcomes],
            }
            if payload["status"] == "empty":
                payload["status_reason"] = "Automation run completed without any eligible artifacts."
            return payload

        return DAILY_REVIEW_TIMEOUT_SECONDS, execute

    raise TradingError(f"Unsupported automation job '{job_type}'.", severity=ErrorSeverity.HIGH)


# ============================================================================
# ACCOUNT MANAGEMENT ENDPOINTS - Phase 1 Implementation (REAL DATA)
# ============================================================================

@router.post("/paper-trading/accounts/create")
@limiter.limit(paper_trading_limit)
async def create_paper_trading_account(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Create a new paper trading account."""
    try:
        account_manager = await container.get("paper_trading_account_manager")

        # Parse request body
        body = await request.json()
        account_name = body.get("account_name", "Paper Trading Account")
        initial_balance = body.get("initial_balance", 100000.0)
        strategy_type = body.get("strategy_type", "swing")

        # Import AccountType enum
        from src.models.paper_trading import AccountType, RiskLevel

        # Map strategy_type string to enum
        strategy_map = {
            "swing": AccountType.SWING,
            "day": AccountType.DAY_TRADING,
            "options": AccountType.OPTIONS,
        }
        strategy_enum = strategy_map.get(strategy_type.lower(), AccountType.SWING)

        # Create account
        account = await account_manager.create_account(
            account_name=account_name,
            initial_balance=initial_balance,
            strategy_type=strategy_enum,
            risk_level=RiskLevel.MODERATE
        )

        logger.info(f"Created new paper trading account: {account.account_id}")

        return {
            "success": True,
            "account": {
                "accountId": account.account_id,
                "accountName": account.account_name,
                "initialBalance": account.initial_balance,
                "currentBalance": account.current_balance,
                "strategyType": strategy_type,
                "createdAt": account.created_at if isinstance(account.created_at, str) else (account.created_at.isoformat() if hasattr(account, 'created_at') and account.created_at else datetime.now(timezone.utc).isoformat())
            }
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "create_paper_trading_account")


@router.delete("/paper-trading/accounts/{account_id}")
@limiter.limit(paper_trading_limit)
async def delete_paper_trading_account(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Delete a paper trading account."""
    try:
        store = await container.get("paper_trading_store")

        # Get account to verify it exists
        account = await store.get_account(account_id)
        if not account:
            return {
                "success": False,
                "error": f"Account {account_id} not found"
            }

        # Check if there are open positions
        open_trades = await store.get_open_trades(account_id)
        if open_trades:
            return {
                "success": False,
                "error": f"Cannot delete account with {len(open_trades)} open positions. Close all positions first."
            }

        # Delete account using store method (with proper locking)
        deleted = await store.delete_account(account_id)
        if not deleted:
            return {
                "success": False,
                "error": f"Failed to delete account {account_id}"
            }

        return {
            "success": True,
            "message": f"Account {account_id} deleted successfully"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "delete_paper_trading_account")


@router.get("/paper-trading/accounts")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_accounts(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get all paper trading accounts - REAL DATA from database."""
    try:
        account_manager = await container.get("paper_trading_account_manager")

        # Get all accounts from database
        all_accounts = await account_manager.get_all_accounts()

        # Format accounts for frontend
        accounts = []
        for acc in all_accounts:
            position_metrics = await account_manager.get_store_backed_position_metrics(acc.account_id)
            deployed_capital = float(position_metrics.get("deployed_capital") or 0.0)

            accounts.append({
                "accountId": acc.account_id,
                "accountName": getattr(acc, "account_name", acc.account_id),
                "accountType": acc.strategy_type.value if hasattr(acc.strategy_type, 'value') else str(acc.strategy_type),
                "currency": "INR",
                "createdDate": acc.created_at if isinstance(acc.created_at, str) else (acc.created_at.isoformat() if hasattr(acc, 'created_at') and acc.created_at else datetime.now(timezone.utc).isoformat()),
                "initialCapital": acc.initial_balance,
                "currentBalance": acc.current_balance,
                "totalInvested": deployed_capital,
                "marginAvailable": acc.buying_power,
            })

        logger.info(f"Retrieved {len(accounts)} paper trading accounts from database")
        return {"accounts": accounts}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_accounts")


@router.get("/paper-trading/accounts/{account_id}/overview")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_account_overview(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get paper trading account overview with REAL account data."""
    try:
        account_manager = await container.get("paper_trading_account_manager")

        account, error_response = await _get_required_account(account_manager, account_id)
        if error_response is not None:
            return error_response

        positions, positions_valuation_status, positions_valuation_detail = await _load_positions_for_read_surface(
            account_manager,
            account_id,
        )
        position_metrics = await account_manager.get_store_backed_position_metrics(account_id)
        open_positions_count = int(position_metrics.get("open_positions_count") or 0)
        deployed_capital = float(position_metrics.get("deployed_capital") or 0.0)

        metrics = None
        metrics_valuation_status = "live"
        metrics_valuation_detail = None
        try:
            metrics = await account_manager.get_performance_metrics(account_id, period="all-time")
        except MarketDataError as error:
            if _trading_error_code(error) != "MARKET_DATA_LIVE_QUOTES_REQUIRED":
                raise
            metrics_valuation_status = "quote_unavailable"
            metrics_valuation_detail = _trading_error_detail(error) or str(error)

        # Get closed trades for today
        store = await container.get("paper_trading_store")
        today = datetime.now(timezone.utc).date()
        all_closed = await store.get_closed_trades(account_id)
        closed_today = [
            t for t in all_closed
            if t.exit_timestamp and datetime.fromisoformat(t.exit_timestamp).date() == today
        ]

        valuation_status = (
            "live"
            if positions_valuation_status == "live" and metrics_valuation_status == "live"
            else "quote_unavailable"
        )
        valuation_detail = positions_valuation_detail or metrics_valuation_detail

        # Build overview response
        overview = {
            "accountId": account.account_id,
            "accountType": account.strategy_type.value if hasattr(account.strategy_type, 'value') else str(account.strategy_type),
            "currency": "INR",
            "createdDate": account.created_at if isinstance(account.created_at, str) else (account.created_at.isoformat() if hasattr(account, 'created_at') and account.created_at else "2025-01-01"),
            "initialCapital": account.initial_balance,
            "currentBalance": account.current_balance,
            "totalInvested": deployed_capital,
            "marginAvailable": account.buying_power,
            "todayPnL": (
                metrics.get("realized_pnl", 0) + metrics.get("unrealized_pnl", 0)
                if metrics is not None
                else None
            ),
            "monthlyROI": metrics.get("monthly_roi", 0) if metrics is not None else None,
            "winRate": metrics.get("win_rate", 0) if metrics is not None else None,
            "activeStrategy": "AI-Driven Strategy",
            "cashAvailable": account.buying_power,
            "deployedCapital": deployed_capital,
            "openPositions": open_positions_count,
            "closedTodayCount": len(closed_today),
            "valuationStatus": valuation_status,
            "valuationDetail": valuation_detail,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Retrieved account overview for {account_id}: Balance=₹{account.current_balance}, Open Positions={open_positions_count}")
        return overview

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_account_overview")


@router.get("/paper-trading/accounts/{account_id}/positions")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_positions(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get positions for paper trading account with REAL-TIME prices and P&L."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        _, error_response = await _get_required_account(account_manager, account_id)
        if error_response is not None:
            return error_response

        positions_data, valuation_status, valuation_detail = await _load_positions_for_read_surface(
            account_manager,
            account_id,
        )

        positions = []
        for pos in positions_data:
            payload = _serialize_position(pos)
            payload["trade_id"] = pos.trade_id
            payload["entryDate"] = pos.entry_date
            positions.append(payload)

        logger.info(
            "Retrieved %s open positions for account %s (valuation_status=%s)",
            len(positions),
            account_id,
            valuation_status,
        )
        return {
            "positions": positions,
            "valuationStatus": valuation_status,
            "valuationDetail": valuation_detail,
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_positions")


@router.get("/paper-trading/accounts/{account_id}/positions/health")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_position_health(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return deterministic position health with mark freshness and execution mode."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response
        return await _build_position_health_payload(container, account_id)
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_position_health")


@router.get("/paper-trading/accounts/{account_id}/trades")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_trades(
    request: Request,
    account_id: str,
    limit: int = 50,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get REAL closed trades for paper trading account from database."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        _, error_response = await _get_required_account(account_manager, account_id)
        if error_response is not None:
            return error_response

        # Fetch real closed trades from database
        closed_trades = await account_manager.get_closed_trades(
            account_id=account_id,
            limit=limit
        )

        trades = []
        for trade in closed_trades:
            payload = _serialize_closed_trade(trade)
            payload["notes"] = trade.reason_closed
            payload["status"] = "closed"
            trades.append(payload)

        logger.info(f"Retrieved {len(trades)} closed trades for account {account_id}")
        return {"trades": trades}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_trades")


@router.get("/paper-trading/accounts/{account_id}/performance")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_performance(
    request: Request,
    account_id: str,
    period: str = "all-time",
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get REAL performance data calculated from actual trades."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        performance_calculator = await container.get("performance_calculator")
        store = await container.get("paper_trading_store")
        _, error_response = await _get_required_account(account_manager, account_id)
        if error_response is not None:
            return error_response

        # Get real performance metrics
        metrics = await account_manager.get_performance_metrics(account_id, period=period)

        # Get all closed trades for advanced metrics calculation
        all_trades = await store.get_closed_trades(account_id)

        # Calculate max drawdown
        max_drawdown = 0.0
        if all_trades:
            max_drawdown = performance_calculator.calculate_max_drawdown([
                trade.realized_pnl for trade in all_trades
            ])

        # Calculate volatility (std dev of returns)
        volatility = 0.0
        if len(all_trades) > 1:
            returns = [trade.realized_pnl_pct for trade in all_trades]
            import statistics
            volatility = statistics.stdev(returns)

        # Format for frontend (camelCase keys)
        performance_data = {
            "period": period,
            "totalReturn": metrics.get("total_pnl", 0),
            "totalReturnPercent": metrics.get("total_pnl_percentage", 0),
            "winRate": metrics.get("win_rate", 0),
            "totalTrades": metrics.get("total_trades", 0),
            "winningTrades": metrics.get("winning_trades", 0),
            "losingTrades": metrics.get("losing_trades", 0),
            "avgWin": metrics.get("avg_win", 0),
            "avgLoss": metrics.get("avg_loss", 0),
            "profitFactor": metrics.get("profit_factor", 0),
            "maxDrawdown": max_drawdown,
            "sharpeRatio": metrics.get("sharpe_ratio"),
            "volatility": volatility,
            "benchmarkReturn": 0,  # TODO: Add benchmark comparison (NIFTY 50)
            "alpha": 0  # TODO: Add alpha calculation vs benchmark
        }

        logger.info(f"Retrieved performance metrics for {account_id} (period={period}): Total P&L=₹{metrics.get('total_pnl', 0)}, Win Rate={metrics.get('win_rate', 0)}%")
        return {"performance": performance_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_performance")


@router.get("/paper-trading/accounts/{account_id}/discovery")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_discovery(
    request: Request,
    account_id: str,
    limit: int = 10,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get the latest stored discovery watchlist without running discovery."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        artifact_service = await container.get("agent_artifact_service")
        envelope: DiscoveryEnvelope = await artifact_service.get_discovery_view(account_id, limit=limit)
        return envelope.model_dump(mode="json")
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_discovery")


@router.get("/paper-trading/accounts/{account_id}/decisions")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_decisions(
    request: Request,
    account_id: str,
    limit: int = 3,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get compact decision packets for open paper-trading positions."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        artifact_service = await container.get("agent_artifact_service")
        envelope: DecisionEnvelope = await artifact_service.get_decision_view(account_id, limit=limit)
        return envelope.model_dump(mode="json")
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_decisions")


@router.get("/paper-trading/accounts/{account_id}/research")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_research(
    request: Request,
    account_id: str,
    candidate_id: Optional[str] = None,
    symbol: Optional[str] = None,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get a focused research packet for the selected or top-ranked candidate."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        artifact_service = await container.get("agent_artifact_service")
        envelope: ResearchEnvelope = await artifact_service.get_research_view(
            account_id,
            candidate_id=candidate_id,
            symbol=symbol,
        )
        return envelope.model_dump(mode="json")
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_research")


@router.get("/paper-trading/accounts/{account_id}/review")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_review(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Generate a compact paper-trading review report."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        artifact_service = await container.get("agent_artifact_service")
        envelope: ReviewEnvelope = await artifact_service.get_review_view(account_id)
        return envelope.model_dump(mode="json")
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_review")


@router.get("/paper-trading/accounts/{account_id}/learning-summary")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_learning_summary(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return the current stateful learning summary for a paper-trading account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        summary = await learning_service.get_learning_summary(account_id, refresh=True)
        return summary.model_dump(mode="json")
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_learning_summary")


@router.get("/paper-trading/accounts/{account_id}/learning/readiness")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_learning_readiness(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return the current learning backlog and readiness state for the account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        return await _build_learning_readiness_payload(container=container, account_id=account_id)
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_learning_readiness")


@router.post("/paper-trading/accounts/{account_id}/learning/evaluate-closed-trades")
@limiter.limit("10/minute")
async def evaluate_paper_trading_closed_trades(
    request: Request,
    account_id: str,
    body: EvaluateClosedTradesRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Evaluate unevaluated closed trades and persist outcome lineage."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        created = await learning_service.evaluate_closed_trades(
            account_id,
            limit=body.limit,
            symbol=(body.symbol or "").strip().upper() or None,
        )
        readiness = await learning_service.get_learning_readiness(account_id)
        summary = await learning_service.get_learning_summary(account_id, refresh=False)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "symbol": (body.symbol or "").strip().upper() or None,
            "created_count": len(created),
            "evaluations": [evaluation.model_dump(mode="json") for evaluation in created],
            "learning_readiness": readiness.model_dump(mode="json"),
            "learning_summary": summary.model_dump(mode="json"),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "evaluate_paper_trading_closed_trades")


@router.get("/paper-trading/accounts/{account_id}/learning/outcomes")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_learning_outcomes(
    request: Request,
    account_id: str,
    limit: int = 20,
    symbol: Optional[str] = None,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return recent closed-trade outcome evaluations with artifact lineage."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        evaluations = await learning_service.list_trade_outcomes(account_id, symbol=symbol, limit=limit)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "symbol": symbol.upper() if symbol else None,
            "count": len(evaluations),
            "evaluations": [evaluation.model_dump(mode="json") for evaluation in evaluations],
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_learning_outcomes")


@router.get("/paper-trading/accounts/{account_id}/improvement-report")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_improvement_report(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return benchmarked strategy-improvement proposals for a paper-trading account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        improvement_service = await container.get("paper_trading_improvement_service")
        report = await improvement_service.get_improvement_report(account_id, refresh=True)
        return report.model_dump(mode="json")
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_improvement_report")


@router.get("/paper-trading/accounts/{account_id}/learning/promotable-improvements")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_promotable_improvements(
    request: Request,
    account_id: str,
    limit: int = 20,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return the current promotable improvement queue for the operator."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        improvements = await learning_service.list_promotable_improvements(account_id, limit=limit)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "count": len(improvements),
            "improvements": [improvement.model_dump(mode="json") for improvement in improvements],
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_promotable_improvements")


@router.post("/paper-trading/accounts/{account_id}/learning/promotable-improvements/{improvement_id}/decision")
@limiter.limit("10/minute")
async def decide_paper_trading_promotable_improvement(
    request: Request,
    account_id: str,
    improvement_id: str,
    body: PromotableImprovementDecisionRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Apply a deterministic promote/watch/reject decision to a queued improvement."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        updated = await learning_service.decide_promotable_improvement(
            account_id,
            improvement_id=improvement_id,
            decision=body.decision,
            owner=body.owner,
            reason=body.reason,
            benchmark_evidence=body.benchmark_evidence,
            guardrail=body.guardrail,
        )
        if updated is None:
            return JSONResponse(status_code=404, content={"error": f"Promotable improvement '{improvement_id}' was not found."})

        improvements = await learning_service.list_promotable_improvements(account_id, limit=10)
        latest_decisions = [item.model_dump(mode="json") for item in improvements if item.decision][:5]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "improvement": updated.model_dump(mode="json"),
            "latest_improvement_decisions": latest_decisions,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "decide_paper_trading_promotable_improvement")


@router.get("/paper-trading/accounts/{account_id}/runs/history")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_run_history(
    request: Request,
    account_id: str,
    limit: int = 20,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get recent manual-run audit history for the selected paper account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        store = await container.get("paper_trading_store")
        entries = await store.get_manual_run_audit_entries(account_id, limit=limit)
        return {
            "account_id": account_id,
            "count": len(entries),
            "runs": entries,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_run_history")


@router.post("/paper-trading/accounts/{account_id}/retrospectives")
@limiter.limit("10/minute")
async def create_paper_trading_retrospective(
    request: Request,
    account_id: str,
    body: SessionRetrospectiveRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Persist a structured operator retrospective and queue promotable improvements."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        retrospective = await learning_service.create_session_retrospective(
            account_id,
            session_id=body.session_id,
            keep=body.keep,
            remove=body.remove,
            fix=body.fix,
            improve=body.improve,
            evidence=body.evidence,
            owner=body.owner,
            promotion_state=body.promotion_state,
        )

        queued_improvements: List[Dict[str, Any]] = []
        for item in body.improve:
            title = str(item.get("title") or item.get("summary") or "").strip()
            if not title:
                continue
            category = str(item.get("category") or "").strip().lower()
            promotion_state = (
                "ready_now"
                if category in {"infra", "truthfulness", "reliability"}
                else str(item.get("promotion_state") or body.promotion_state or "queued")
            )
            improvement = await learning_service.enqueue_promotable_improvement(
                account_id,
                title=title,
                summary=str(item.get("summary") or title),
                owner=str(item.get("owner") or body.owner),
                promotion_state=promotion_state,
                category=str(item.get("category") or ""),
                retrospective_id=retrospective.retrospective_id,
                outcome_evidence=list(item.get("outcome_evidence") or body.evidence or []),
                benchmark_evidence=list(item.get("benchmark_evidence") or []),
                guardrail=str(item.get("guardrail") or ""),
            )
            queued_improvements.append(improvement.model_dump(mode="json"))

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "retrospective": retrospective.model_dump(mode="json"),
            "queued_improvements": queued_improvements,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "create_paper_trading_retrospective")


@router.get("/paper-trading/accounts/{account_id}/retrospectives/latest")
@limiter.limit(paper_trading_limit)
async def get_latest_paper_trading_retrospective(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return the latest persisted operator retrospective for the account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        learning_service = await container.get("paper_trading_learning_service")
        retrospective = await learning_service.get_latest_session_retrospective(account_id)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "retrospective": retrospective.model_dump(mode="json") if retrospective is not None else None,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_latest_paper_trading_retrospective")


@router.get("/paper-trading/accounts/{account_id}/operator-snapshot")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_operator_snapshot(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return a consolidated operator snapshot for WebMCP and manual supervision."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        return await _build_operator_snapshot_payload(
            request=request,
            container=container,
            account_id=account_id,
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_operator_snapshot")


@router.post("/paper-trading/accounts/{account_id}/operator/refresh-readiness")
@limiter.limit("10/minute")
async def refresh_paper_trading_operator_readiness(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Force a fresh operator readiness evaluation and return the refreshed snapshot."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        snapshot = await _build_operator_snapshot_payload(
            request=request,
            container=container,
            account_id=account_id,
            refresh_readiness=True,
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "snapshot": snapshot,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "refresh_paper_trading_operator_readiness")


@router.get("/paper-trading/accounts/{account_id}/operator-incidents")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_operator_incidents(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return the current operator incident list derived from readiness, queue, and mark freshness."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        snapshot = await _build_operator_snapshot_payload(
            request=request,
            container=container,
            account_id=account_id,
        )
        incidents = snapshot.get("incidents", [])
        return {
            "generated_at": snapshot.get("generated_at"),
            "account_id": account_id,
            "count": len(incidents),
            "incidents": incidents,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_operator_incidents")


@router.post("/paper-trading/runtime/validate-ai")
@limiter.limit("20/minute")
async def validate_paper_trading_ai_runtime(
    request: Request,
    account_id: Optional[str] = None,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Force a live AI runtime validation for the paper-trading operator surface."""
    try:
        if account_id:
            error_response = await _require_account_or_error(container, account_id)
            if error_response is not None:
                return error_response

        runtime_status = await asyncio.wait_for(
            get_ai_runtime_status(force_refresh=True),
            timeout=RUNTIME_VALIDATION_TIMEOUT_SECONDS,
        )
        capability_service = await container.get("trading_capability_service")
        try:
            capability_snapshot = await asyncio.wait_for(
                capability_service.get_snapshot(account_id=account_id),
                timeout=OPERATOR_RUNTIME_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "account_id": account_id,
                "ai_runtime": runtime_status.to_dict(),
                "capability_snapshot": {
                    "overall_status": "blocked",
                    "checks": [],
                    "blockers": [
                        f"Capability snapshot exceeded the {int(OPERATOR_RUNTIME_TIMEOUT_SECONDS)}s operator deadline."
                    ],
                },
            }
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "ai_runtime": runtime_status.to_dict(),
            "capability_snapshot": capability_snapshot.to_dict(),
        }
    except asyncio.TimeoutError:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "ai_runtime": {
                "status": "timeout",
                "provider": "codex",
                "is_valid": False,
                "authenticated": False,
                "error": (
                    f"AI runtime validation exceeded the {int(RUNTIME_VALIDATION_TIMEOUT_SECONDS)}s operator deadline."
                ),
            },
            "capability_snapshot": {
                "overall_status": "blocked",
                "checks": [],
                "blockers": [
                    f"AI runtime validation exceeded the {int(RUNTIME_VALIDATION_TIMEOUT_SECONDS)}s operator deadline."
                ],
            },
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "validate_paper_trading_ai_runtime")


@router.post("/paper-trading/accounts/{account_id}/runtime/refresh-market-data")
@limiter.limit("20/minute")
async def refresh_paper_trading_market_data_runtime(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Re-subscribe open symbols and refresh runtime market-data subscriptions."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        store = await container.get("paper_trading_store")
        market_data_service = await container.get("market_data_service")
        capability_service = await container.get("trading_capability_service")

        if market_data_service is None:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "account_id": account_id,
                "status": "blocked",
                "message": "MarketDataService is not configured for this runtime.",
                "symbols_requested": [],
                "symbols_subscribed": [],
                "errors": ["MarketDataService is not configured for this runtime."],
            }

        open_trades = await store.get_open_trades(account_id)
        symbols_requested = sorted({trade.symbol for trade in open_trades if getattr(trade, "symbol", None)})
        symbols_subscribed: List[str] = []
        errors: List[str] = []

        for symbol in symbols_requested:
            try:
                await asyncio.wait_for(
                    market_data_service.subscribe_market_data(symbol),
                    timeout=OPERATOR_RUNTIME_TIMEOUT_SECONDS,
                )
                symbols_subscribed.append(symbol)
            except asyncio.TimeoutError:
                errors.append(
                    f"{symbol}: subscribe_market_data exceeded the {int(OPERATOR_RUNTIME_TIMEOUT_SECONDS)}s operator deadline"
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{symbol}: {exc}")

        refreshed_symbols = []
        try:
            refreshed_symbols = await asyncio.wait_for(
                market_data_service.refresh_active_subscriptions(),
                timeout=OPERATOR_RUNTIME_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            errors.append(
                f"refresh_active_subscriptions exceeded the {int(OPERATOR_RUNTIME_TIMEOUT_SECONDS)}s operator deadline"
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"refresh_active_subscriptions: {exc}")

        quote_status = await asyncio.wait_for(
            market_data_service.get_quote_stream_status(),
            timeout=OPERATOR_RUNTIME_TIMEOUT_SECONDS,
        )
        capability_snapshot = await asyncio.wait_for(
            capability_service.get_snapshot(account_id=account_id),
            timeout=OPERATOR_RUNTIME_TIMEOUT_SECONDS,
        )
        status = "ready" if not errors else "degraded"
        if not symbols_requested:
            status = "ready"

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "status": status,
            "message": (
                "Market-data runtime refresh completed."
                if symbols_requested
                else "No open symbols required re-subscription; runtime status was refreshed."
            ),
            "symbols_requested": symbols_requested,
            "symbols_subscribed": symbols_subscribed,
            "refreshed_symbols": refreshed_symbols,
            "quote_stream_status": quote_status.to_metadata(),
            "capability_snapshot": capability_snapshot.to_dict(),
            "errors": errors,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "refresh_paper_trading_market_data_runtime")


@router.post("/paper-trading/accounts/{account_id}/runs/discovery")
@limiter.limit("10/minute")
async def run_paper_trading_discovery(
    request: Request,
    account_id: str,
    limit: int = 10,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Run a fresh discovery pass for the selected paper-trading account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        async def action() -> DiscoveryEnvelope:
            discovery_service = await container.get("stock_discovery_service")
            discovery_result = await discovery_service.run_discovery_session(
                session_type="manual_operator_refresh",
                account_id=account_id,
            )
            if discovery_result.get("status") == "blocked":
                return _blocked_discovery_envelope(
                    blockers=list(discovery_result.get("blockers") or ["AI runtime is not ready for discovery generation."]),
                    provider_metadata={
                        key: discovery_result[key]
                        for key in ("session_id", "session_type", "account_id", "duration_ms")
                        if discovery_result.get(key) is not None
                    },
                )

            artifact_service = await container.get("agent_artifact_service")
            return await artifact_service.get_discovery_view(account_id, limit=limit)

        return await _execute_manual_run(
            container=container,
            account_id=account_id,
            route_name="paper_trading.discovery",
            timeout_seconds=DISCOVERY_TIMEOUT_SECONDS,
            action=action,
            timeout_factory=lambda message: _blocked_discovery_envelope(blockers=[message]),
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "run_paper_trading_discovery")


@router.post("/paper-trading/accounts/{account_id}/automation/{job_type}")
@limiter.limit("10/minute")
async def submit_paper_trading_automation_run(
    request: Request,
    account_id: str,
    job_type: AutomationJobType,
    body: AutomationTriggerRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Submit an explicit local Codex-backed automation run."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        timeout_seconds, execute = await _build_automation_job_execution(
            request=request,
            container=container,
            account_id=account_id,
            job_type=job_type,
            trigger=body,
        )
        automation_service = await container.get("paper_trading_automation_service")
        run = await automation_service.submit_run(
            account_id=account_id,
            job_type=job_type,
            input_payload={"account_id": account_id, "job_type": job_type, **body.model_dump(mode="json")},
            timeout_seconds=timeout_seconds,
            trigger_reason=body.trigger_reason,
            schedule_source=body.schedule_source,
            execute=execute,
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "job_type": job_type,
            "run": run,
            "runtime_readiness": await automation_service.get_runtime_readiness(),
            "controls": (await automation_service.get_control_state()).model_dump(mode="json"),
        }
    except (AutomationPausedError, DuplicateAutomationRunError) as exc:
        return JSONResponse(
            status_code=409,
            content={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "account_id": account_id,
                "job_type": job_type,
                "status": "blocked",
                "error": str(exc),
            },
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "submit_paper_trading_automation_run")


@router.get("/paper-trading/accounts/{account_id}/automation/runs")
@limiter.limit(paper_trading_limit)
async def list_paper_trading_automation_runs(
    request: Request,
    account_id: str,
    limit: int = 20,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return recent explicit automation runs for the account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response
        automation_service = await container.get("paper_trading_automation_service")
        runs = await automation_service.list_runs(account_id, limit=min(limit, 100))
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "count": len(runs),
            "runs": runs,
            "runtime_readiness": await automation_service.get_runtime_readiness(),
            "controls": (await automation_service.get_control_state()).model_dump(mode="json"),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "list_paper_trading_automation_runs")


@router.get("/paper-trading/accounts/{account_id}/automation/runs/{run_id}")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_automation_run(
    request: Request,
    account_id: str,
    run_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return a single explicit automation run."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response
        automation_service = await container.get("paper_trading_automation_service")
        run = await automation_service.get_run(run_id)
        if run is None or run.get("account_id") != account_id:
            return JSONResponse(status_code=404, content={"error": f"Automation run '{run_id}' was not found."})
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "run": run,
            "runtime_readiness": await automation_service.get_runtime_readiness(),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_automation_run")


@router.post("/paper-trading/accounts/{account_id}/automation/runs/{run_id}/cancel")
@limiter.limit("10/minute")
async def cancel_paper_trading_automation_run(
    request: Request,
    account_id: str,
    run_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Cancel an active explicit automation run."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response
        automation_service = await container.get("paper_trading_automation_service")
        run = await automation_service.cancel_run(run_id)
        if run is None or run.get("account_id") != account_id:
            return JSONResponse(status_code=404, content={"error": f"Automation run '{run_id}' was not found."})
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "run": run,
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "cancel_paper_trading_automation_run")


@router.post("/paper-trading/automation/pause")
@limiter.limit("10/minute")
async def pause_paper_trading_automation(
    request: Request,
    body: AutomationControlRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Pause automation globally or for the selected job types."""
    try:
        automation_service = await container.get("paper_trading_automation_service")
        controls = await automation_service.pause(job_types=body.job_types or None, reason=body.reason)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "controls": controls.model_dump(mode="json"),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "pause_paper_trading_automation")


@router.post("/paper-trading/automation/resume")
@limiter.limit("10/minute")
async def resume_paper_trading_automation(
    request: Request,
    body: AutomationControlRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Resume automation globally or for the selected job types."""
    try:
        automation_service = await container.get("paper_trading_automation_service")
        controls = await automation_service.resume(job_types=body.job_types or None)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "controls": controls.model_dump(mode="json"),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "resume_paper_trading_automation")


@router.post("/paper-trading/accounts/{account_id}/runs/research")
@limiter.limit("10/minute")
async def run_paper_trading_research(
    request: Request,
    account_id: str,
    research_request: ResearchRunRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Run a focused research pass for one candidate or explicit symbol."""
    try:
        if not research_request.candidate_id and not research_request.symbol:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Provide candidate_id or symbol before running research.",
                },
            )

        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        async def action() -> ResearchEnvelope:
            artifact_service = await container.get("agent_artifact_service")
            return await artifact_service.get_research_view(
                account_id,
                candidate_id=research_request.candidate_id,
                symbol=research_request.symbol,
                refresh=True,
            )

        return await _execute_manual_run(
            container=container,
            account_id=account_id,
            route_name="paper_trading.research",
            timeout_seconds=RESEARCH_TIMEOUT_SECONDS,
            action=action,
            timeout_factory=lambda message: _blocked_research_envelope(blockers=[message]),
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "run_paper_trading_research")


@router.post("/paper-trading/accounts/{account_id}/runs/decision-review")
@limiter.limit("10/minute")
async def run_paper_trading_decision_review(
    request: Request,
    account_id: str,
    limit: int = 3,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Run a fresh decision review for current paper-trading positions."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        async def action() -> DecisionEnvelope:
            artifact_service = await container.get("agent_artifact_service")
            return await artifact_service.get_decision_view(account_id, limit=limit, refresh=True)

        return await _execute_manual_run(
            container=container,
            account_id=account_id,
            route_name="paper_trading.decision_review",
            timeout_seconds=DECISION_TIMEOUT_SECONDS,
            action=action,
            timeout_factory=lambda message: _blocked_decision_envelope(blockers=[message]),
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "run_paper_trading_decision_review")


@router.post("/paper-trading/accounts/{account_id}/runs/daily-review")
@limiter.limit("10/minute")
async def run_paper_trading_daily_review(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Run a fresh daily review for the selected paper-trading account."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        async def action() -> ReviewEnvelope:
            artifact_service = await container.get("agent_artifact_service")
            return await artifact_service.get_review_view(account_id, refresh=True)

        return await _execute_manual_run(
            container=container,
            account_id=account_id,
            route_name="paper_trading.daily_review",
            timeout_seconds=DAILY_REVIEW_TIMEOUT_SECONDS,
            action=action,
            timeout_factory=lambda message: _blocked_review_envelope(blockers=[message]),
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "run_paper_trading_daily_review")


@router.post("/paper-trading/accounts/{account_id}/runs/exit-check")
@limiter.limit("10/minute")
async def run_paper_trading_exit_check(
    request: Request,
    account_id: str,
    limit: int = 3,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Run an exit-check pass using the bounded decision packet flow."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response

        async def action() -> DecisionEnvelope:
            artifact_service = await container.get("agent_artifact_service")
            return await artifact_service.get_decision_view(account_id, limit=limit, refresh=True)

        return await _execute_manual_run(
            container=container,
            account_id=account_id,
            route_name="paper_trading.exit_check",
            timeout_seconds=DECISION_TIMEOUT_SECONDS,
            action=action,
            timeout_factory=lambda message: _blocked_decision_envelope(blockers=[message]),
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "run_paper_trading_exit_check")


# ============================================================================
# TRADE EXECUTION ENDPOINTS - Phase 1 Implementation (REAL EXECUTION)
# ============================================================================

@router.post("/paper-trading/accounts/{account_id}/execution/proposal")
@limiter.limit("20/minute")
async def build_paper_trading_execution_proposal(
    request: Request,
    account_id: str,
    body: ExecutionPreflightRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Build a proposal for a prospective paper-trading mutation without executing it."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response
        preflight_result = await _build_execution_preflight_payload(
            container,
            account_id=account_id,
            preflight=body,
        )
        return _build_execution_mutation_contract(account_id, body, preflight_result)
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "build_paper_trading_execution_proposal")


@router.post("/paper-trading/accounts/{account_id}/execution/preflight")
@limiter.limit("20/minute")
async def validate_paper_trading_execution_preflight(
    request: Request,
    account_id: str,
    body: ExecutionPreflightRequest,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Validate a prospective paper-trading mutation against deterministic gates."""
    try:
        error_response = await _require_account_or_error(container, account_id)
        if error_response is not None:
            return error_response
        return await _build_execution_preflight_payload(
            container,
            account_id=account_id,
            preflight=body,
        )
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "validate_paper_trading_execution_preflight")


@router.post("/paper-trading/accounts/{account_id}/trades/buy")
@limiter.limit(paper_trading_limit)
async def execute_buy_trade(
    request: Request,
    account_id: str,
    trade_request: BuyTradeRequest,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Execute a buy trade on a paper trading account with REAL market prices.

    Uses MarketDataService (Zerodha Kite SDK) for real-time pricing.
    """
    try:
        execution_service = await container.get("paper_trading_execution_service")

        # Execute trade with real market price
        result = await execution_service.execute_buy_trade(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            order_type=trade_request.order_type,
            price=trade_request.price
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "execute_buy_trade")


@router.post("/paper-trading/accounts/{account_id}/trades/sell")
@limiter.limit(paper_trading_limit)
async def execute_sell_trade(
    request: Request,
    account_id: str,
    trade_request: SellTradeRequest,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Execute a sell trade on a paper trading account with REAL market prices.

    Uses MarketDataService (Zerodha Kite SDK) for real-time pricing.
    """
    try:
        execution_service = await container.get("paper_trading_execution_service")

        # Execute trade with real market price
        result = await execution_service.execute_sell_trade(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            order_type=trade_request.order_type,
            price=trade_request.price
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "execute_sell_trade")


@router.post("/paper-trading/accounts/{account_id}/trades/{trade_id}/close")
@limiter.limit(paper_trading_limit)
async def close_trade(
    request: Request,
    account_id: str,
    trade_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Close an existing open trade with REAL market exit price.

    Uses MarketDataService (Zerodha Kite SDK) for real-time exit pricing.
    """
    try:
        execution_service = await container.get("paper_trading_execution_service")

        # Close trade with real market price
        result = await execution_service.close_trade(
            trade_id=trade_id
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "close_trade")


@router.patch("/paper-trading/accounts/{account_id}/trades/{trade_id}")
@limiter.limit(paper_trading_limit)
async def modify_trade(
    request: Request,
    account_id: str,
    trade_id: str,
    body: ModifyTradeRequest,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Modify stop loss and/or target price for an open trade.

    Args:
        account_id: Paper trading account ID
        trade_id: Trade ID to modify
        body: ModifyTradeRequest with stop_loss and/or target_price

    Returns:
        Updated trade information
    """
    try:
        # Validate at least one field is provided
        if body.stop_loss is None and body.target_price is None:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "At least one of stop_loss or target_price must be provided"
                }
            )

        store = await container.get("paper_trading_store")
        account_manager = await container.get("paper_trading_account_manager")

        account, error_response = await _get_required_account(account_manager, account_id)
        if error_response is not None:
            return error_response

        result = await store.update_trade_risk_levels(
            account_id=account.account_id,
            trade_id=trade_id,
            stop_loss=body.stop_loss,
            target_price=body.target_price,
        )

        if result is None:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": f"Trade {trade_id} not found in account {account_id} or is not open"
                }
            )

        logger.info(f"Modified trade {trade_id} in account {account_id}: "
                   f"stop_loss={body.stop_loss}, target_price={body.target_price}")

        return {
            "success": True,
            "trade": result.to_dict() if hasattr(result, "to_dict") else result,
            "message": f"Trade {trade_id} modified successfully"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "modify_trade")
