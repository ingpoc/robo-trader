from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.dependencies import get_container
from src.web.routes import paper_trading
from src.web.routes.configuration import router as configuration_router


def test_configuration_status_includes_operator_truth():
    app = FastAPI()
    app.include_router(configuration_router)

    config_state = MagicMock()
    config_state.get_system_status = AsyncMock(
        return_value={
            "status": "manual_only",
            "manualOnly": True,
            "backgroundSchedulers": {"status": "removed", "active": 0},
            "aiAgents": {"configured": 1, "enabled": 1},
            "aiRuntime": {"provider": "codex", "ready": True, "authenticated": True},
            "globalSettings": {
                "quoteStreamProvider": "zerodha_kite",
                "quoteStreamMode": "ltpc",
                "quoteStreamSymbolLimit": 50,
            },
            "checkedAt": "2026-04-01T10:00:00+00:00",
        }
    )

    class _Container:
        config = SimpleNamespace(
            integration=SimpleNamespace(
                quote_stream_provider="upstox",
                upstox_stream_mode="ltpc",
            )
        )

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
    assert payload["effectiveQuoteStream"] == {
        "provider": "zerodha_kite",
        "mode": "ltpc",
        "symbolLimit": 50,
    }
    assert payload["effectiveExecutionPosture"]["mode"] == "operator_confirmed_execution"
    assert payload["persistence"]["source"] == "database_first"
    assert payload["runtimeIdentityLink"] == {
        "source": "/api/health",
        "field": "runtime_identity",
    }


def test_account_policy_routes_round_trip():
    app = FastAPI()
    app.include_router(paper_trading.router)

    policy = {
        "account_id": "paper_main",
        "execution_mode": "operator_confirmed_execution",
        "max_open_positions": 8,
        "max_new_entries_per_day": 3,
        "max_deployed_capital_pct": 80.0,
        "default_stop_loss_pct": 5.0,
        "default_target_pct": 10.0,
        "per_trade_exposure_pct": 5.0,
        "max_portfolio_risk_pct": 10.0,
        "risk_level": "moderate",
        "updated_at": "2026-04-01T10:00:00+00:00",
        "created_at": "2026-04-01T09:00:00+00:00",
    }
    account_manager = MagicMock()
    account_manager.get_account = AsyncMock(return_value=SimpleNamespace(account_id="paper_main"))
    account_manager.get_account_policy = AsyncMock(return_value=SimpleNamespace(to_dict=lambda: policy))
    account_manager.update_account_policy = AsyncMock(return_value=SimpleNamespace(to_dict=lambda: {**policy, "max_open_positions": 10}))

    class _Container:
        async def get(self, key: str):
            if key == "paper_trading_account_manager":
                return account_manager
            raise KeyError(key)

    async def override_get_container():
        return _Container()

    app.dependency_overrides[get_container] = override_get_container

    with TestClient(app) as client:
        get_response = client.get("/api/paper-trading/accounts/paper_main/policy")
        put_response = client.put(
            "/api/paper-trading/accounts/paper_main/policy",
            json={"max_open_positions": 10},
        )

    assert get_response.status_code == 200
    assert get_response.json()["policy"]["execution_mode"] == "operator_confirmed_execution"
    assert put_response.status_code == 200
    assert put_response.json()["policy"]["max_open_positions"] == 10
    account_manager.update_account_policy.assert_awaited_once_with("paper_main", {"max_open_positions": 10})


def test_overview_summary_payload_contains_operator_sections():
    payload = paper_trading._build_overview_summary_payload(
        account_id="paper_main",
        capability_snapshot={"overall_status": "ready", "blockers": []},
        account_policy={
            "execution_mode": "operator_confirmed_execution",
            "per_trade_exposure_pct": 5,
            "max_portfolio_risk_pct": 10,
            "max_open_positions": 8,
            "max_new_entries_per_day": 3,
            "max_deployed_capital_pct": 80,
        },
        overview={"data": {"buying_power": 76000, "deployed_capital": 24000, "balance": 100000, "valuation_status": "live"}},
        performance={"performance": {"portfolio_value": 101250, "total_pnl": 1250, "win_rate": 64, "winning_trades": 8, "losing_trades": 4}},
        discovery={"status": "ready", "generated_at": "2026-04-01T10:00:00+00:00", "considered": ["INFY"], "status_reason": "Fresh discovery ready."},
        research={"status": "blocked", "generated_at": "2026-04-01T10:01:00+00:00", "considered": [], "status_reason": "Select candidate.", "freshness_state": "unknown", "empty_reason": "requires_selection"},
        decisions={"status": "blocked", "generated_at": "2026-04-01T10:02:00+00:00", "considered": [], "status_reason": "No positions.", "freshness_state": "unknown", "empty_reason": "no_candidates"},
        review={"status": "ready", "generated_at": "2026-04-01T10:03:00+00:00", "considered": ["INFY"], "status_reason": "Review ready.", "freshness_state": "fresh"},
        learning_readiness={"unevaluated_closed_trade_count": 1, "queued_promotable_count": 2, "decision_pending_improvement_count": 1},
        promotion_report={"ready_now": 1},
        run_history={"runs": [{}, {}]},
        staleness={"discovery": {"status": "fresh"}},
        operator_recommendation={"summary": "Run research", "detail": "Research the top candidate."},
        positions_health={"position_count": 0, "status": "ready"},
        incidents=[{"summary": "Review queued"}],
    )

    assert payload["readiness"]["overall_status"] == "ready"
    assert payload["selected_account"]["buying_power"] == 76000
    assert payload["queue"]["queued_promotable_improvements"] == 2
    assert payload["performance"]["closed_trades"] == 12
    assert len(payload["recent_stage_outputs"]) == 4
    assert payload["guardrails"]["max_open_positions"] == 8
    assert payload["act_now"][0]["label"] == "Evaluate closed trades"
    assert payload["recent_stage_outputs"][1]["empty_reason"] == "requires_selection"
