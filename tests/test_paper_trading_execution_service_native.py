from types import SimpleNamespace

import pytest

from src.services.paper_trading_execution_service import PaperTradingExecutionService


class _AccountManager:
    async def get_account(self, account_id):
        return SimpleNamespace(account_id=account_id)

    async def get_account_balance(self, _account_id):
        return {"current_balance": 95000.0, "buying_power": 90000.0}


class _TradeExecutor:
    def __init__(self):
        self.buy_calls = []

    async def execute_buy(self, **kwargs):
        self.buy_calls.append(kwargs)
        return {
            "success": True,
            "trade_id": "trade-123",
            "timestamp": "2026-03-18T10:00:00+00:00",
        }

    async def get_current_price(self, _symbol):
        raise AssertionError("get_current_price should not be used when an explicit price is provided")


@pytest.mark.asyncio
async def test_native_execution_service_uses_explicit_price_without_claude():
    trade_executor = _TradeExecutor()
    service = PaperTradingExecutionService(
        trade_executor=trade_executor,
        account_manager=_AccountManager(),
        store=SimpleNamespace(),
    )
    await service.initialize()

    result = await service.execute_buy_trade(
        account_id="paper_main",
        symbol="tcs",
        quantity=5,
        order_type="LIMIT",
        price=4020.5,
        strategy_rationale="Manual operator request",
    )

    assert result["success"] is True
    assert result["symbol"] == "TCS"
    assert result["price"] == pytest.approx(4020.5)
    assert "Validated natively" in result["validation_reason"]
    assert trade_executor.buy_calls[0]["entry_price"] == pytest.approx(4020.5)
