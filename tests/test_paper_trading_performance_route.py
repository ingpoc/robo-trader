from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.dependencies import get_container
from src.web.routes import paper_trading


def test_performance_route_returns_metrics_when_closed_trades_exist():
    app = FastAPI()
    app.include_router(paper_trading.router)

    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(
        account_id="paper_main",
        initial_balance=100000.0,
    )
    account_manager.get_performance_metrics.return_value = {
        "total_pnl": -10038.75,
        "total_pnl_percentage": -10.03875,
        "win_rate": 0.0,
        "total_trades": 3,
        "winning_trades": 0,
        "losing_trades": 1,
        "avg_win": 0.0,
        "avg_loss": -10038.75,
        "profit_factor": 0.0,
        "sharpe_ratio": None,
    }

    store = AsyncMock()
    store.get_closed_trades.return_value = [
        SimpleNamespace(realized_pnl=-10038.75, realized_pnl_pct=-73.00909090909092, entry_timestamp="2025-12-26T00:00:00+00:00"),
    ]

    performance_calculator = SimpleNamespace(
        calculate_drawdown=lambda trades, initial_balance: {
            "max_drawdown": 10038.75,
            "max_drawdown_percentage": 10.03875,
        }
    )

    class _Container:
        async def get(self, key: str):
            if key == "paper_trading_account_manager":
                return account_manager
            if key == "performance_calculator":
                return performance_calculator
            if key == "paper_trading_store":
                return store
            raise KeyError(key)

    async def override_get_container():
        return _Container()

    app.dependency_overrides[get_container] = override_get_container

    with TestClient(app) as client:
        response = client.get("/api/paper-trading/accounts/paper_main/performance?period=month")

    assert response.status_code == 200
    payload = response.json()["performance"]
    assert payload["totalReturn"] == -10038.75
    assert payload["maxDrawdown"] == 10038.75
    assert payload["winningTrades"] == 0
    assert payload["losingTrades"] == 1


def test_performance_route_derives_volatility_when_realized_pct_is_missing():
    app = FastAPI()
    app.include_router(paper_trading.router)

    account_manager = AsyncMock()
    account_manager.get_account.return_value = SimpleNamespace(
        account_id="paper_main",
        initial_balance=100000.0,
    )
    account_manager.get_performance_metrics.return_value = {
        "total_pnl": -21777.0,
        "total_pnl_percentage": -21.777,
        "win_rate": 0.0,
        "total_trades": 3,
        "winning_trades": 0,
        "losing_trades": 3,
        "avg_win": 0.0,
        "avg_loss": -7259.0,
        "profit_factor": 0.0,
        "sharpe_ratio": None,
    }

    store = AsyncMock()
    store.get_closed_trades.return_value = [
        SimpleNamespace(
            realized_pnl=-10038.75,
            realized_pnl_pct=-73.00909090909092,
            entry_price=2750.0,
            quantity=5,
            entry_timestamp="2025-12-26T00:00:00+00:00",
        ),
        SimpleNamespace(
            realized_pnl=-6555.0,
            realized_pnl_pct=None,
            entry_price=2650.0,
            quantity=5,
            entry_timestamp="2025-12-27T00:00:00+00:00",
        ),
        SimpleNamespace(
            realized_pnl=-5222.0,
            realized_pnl_pct=None,
            entry_price=3450.0,
            quantity=5,
            entry_timestamp="2025-12-28T00:00:00+00:00",
        ),
    ]

    performance_calculator = SimpleNamespace(
        calculate_drawdown=lambda trades, initial_balance: {
            "max_drawdown": 21815.75,
            "max_drawdown_percentage": 21.81575,
        }
    )

    class _Container:
        async def get(self, key: str):
            if key == "paper_trading_account_manager":
                return account_manager
            if key == "performance_calculator":
                return performance_calculator
            if key == "paper_trading_store":
                return store
            raise KeyError(key)

    async def override_get_container():
        return _Container()

    app.dependency_overrides[get_container] = override_get_container

    with TestClient(app) as client:
        response = client.get("/api/paper-trading/accounts/paper_main/performance?period=month")

    assert response.status_code == 200
    payload = response.json()["performance"]
    assert payload["losingTrades"] == 3
    assert payload["avgLoss"] == -7259.0
    assert payload["volatility"] > 0
