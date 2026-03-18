"""Regression tests for the store-backed paper trading authority path."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from src.models.paper_trading import AccountType, RiskLevel, TradeType
from src.mcp.enhanced_paper_trading_server import calculate_monthly_pnl
from src.services.claude_agent.tool_executor import ToolExecutor
from src.services.paper_trading.account_manager import PaperTradingAccountManager
from src.services.paper_trading.trade_executor import PaperTradeExecutor
from src.stores.paper_trading_store import PaperTradingStore


@pytest.fixture
async def store():
    """Create an in-memory paper trading store."""
    db = await aiosqlite.connect(":memory:")
    trading_store = PaperTradingStore(db)
    await trading_store.initialize()
    try:
        yield trading_store
    finally:
        await db.close()


@pytest.fixture
async def seeded_store(store):
    """Create a paper account with one open and two closed trades."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_main",
    )

    open_trade = await store.create_trade(
        account_id=account.account_id,
        symbol="INFY",
        trade_type=TradeType.BUY,
        quantity=5,
        entry_price=100.0,
        strategy_rationale="momentum",
        claude_session_id="session-open",
    )
    winning_trade = await store.create_trade(
        account_id=account.account_id,
        symbol="TCS",
        trade_type=TradeType.BUY,
        quantity=10,
        entry_price=100.0,
        strategy_rationale="momentum",
        claude_session_id="session-win",
    )
    losing_trade = await store.create_trade(
        account_id=account.account_id,
        symbol="RELIANCE",
        trade_type=TradeType.BUY,
        quantity=5,
        entry_price=100.0,
        strategy_rationale="mean_reversion",
        claude_session_id="session-loss",
    )

    await store.close_trade(winning_trade.trade_id, exit_price=110.0, realized_pnl=100.0)
    await store.close_trade(losing_trade.trade_id, exit_price=95.0, realized_pnl=-25.0)

    return {
        "store": store,
        "account_id": account.account_id,
        "open_trade": open_trade,
        "winning_trade": winning_trade,
        "losing_trade": losing_trade,
    }


@pytest.mark.asyncio
async def test_get_open_trades_normalizes_current_schema(seeded_store):
    """Open trades created through the current schema should round-trip cleanly."""
    store = seeded_store["store"]

    open_trades = await store.get_open_trades(seeded_store["account_id"])

    assert len(open_trades) == 1
    assert open_trades[0].trade_id == seeded_store["open_trade"].trade_id
    assert open_trades[0].symbol == "INFY"
    assert open_trades[0].trade_type.value == "buy"
    assert open_trades[0].status.value == "open"


@pytest.mark.asyncio
async def test_store_calculates_truthful_daily_performance_metrics(seeded_store):
    """Daily metrics should come from the store-backed trade authority."""
    store = seeded_store["store"]
    review_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    metrics = await store.calculate_daily_performance_metrics(
        account_id=seeded_store["account_id"],
        review_date=review_date,
        current_prices={"INFY": 120.0},
    )

    assert metrics["daily_pnl"] == pytest.approx(175.0)
    assert metrics["realized_pnl"] == pytest.approx(75.0)
    assert metrics["unrealized_pnl"] == pytest.approx(100.0)
    assert metrics["open_positions_count"] == 1
    assert metrics["closed_positions_count"] == 2
    assert metrics["win_rate"] == pytest.approx(50.0)
    assert {trade["symbol"] for trade in metrics["trades_reviewed"]} == {"INFY", "TCS", "RELIANCE"}
    assert metrics["strategy_performance"]["momentum"]["total_pnl"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_store_calculates_truthful_monthly_pnl(seeded_store):
    """Monthly P&L should be based on closed trades in the selected month."""
    store = seeded_store["store"]
    today = datetime.now(timezone.utc)

    monthly = await store.calculate_monthly_pnl(
        account_id=seeded_store["account_id"],
        year=today.year,
        month=today.month,
    )

    assert monthly["total_pnl"] == pytest.approx(75.0)
    assert monthly["total_trades"] == 2
    assert monthly["win_rate"] == pytest.approx(50.0)
    assert monthly["best_trade"] == pytest.approx(100.0)
    assert monthly["worst_trade"] == pytest.approx(-25.0)
    assert monthly["top_strategies"][0]["name"] == "momentum"


@pytest.mark.asyncio
async def test_monthly_pnl_tool_uses_store_backed_authority():
    """The MCP monthly P&L tool should resolve the account explicitly and read from the store path."""
    container = MagicMock()
    store = AsyncMock()
    account_manager = AsyncMock()
    account_manager.get_all_accounts.return_value = [SimpleNamespace(account_id="paper_main")]
    store.calculate_monthly_pnl.return_value = {
        "total_pnl": 2500.0,
        "win_rate": 60.0,
        "total_trades": 5,
        "best_trade": 1200.0,
        "worst_trade": -300.0,
        "top_strategies": [{"name": "momentum", "pnl": 2000.0, "win_rate": 66.7, "trades": 3}],
    }

    async def get_service(name):
        if name == "paper_trading_store":
            return store
        if name == "paper_trading_account_manager":
            return account_manager
        raise ValueError(name)

    container.get = AsyncMock(side_effect=get_service)

    result = await calculate_monthly_pnl.handler(
        {"month": "March", "year": 2026, "include_details": True},
        container,
    )

    store.calculate_monthly_pnl.assert_awaited_once_with("paper_main", 2026, 3)
    content = result["content"][0]["text"]
    assert "Account: paper_main" in content
    assert "Win Rate: 60.0%" in content
    assert "momentum" in content


@pytest.mark.asyncio
async def test_tool_executor_requires_explicit_account_id_for_business_validation():
    """Business validation should fail before any account lookup when account_id is missing."""
    container = MagicMock()
    container.get = AsyncMock()
    executor = ToolExecutor(container=container, config={})

    error = await executor._validate_business_rules(
        "execute_trade",
        {
            "symbol": "TCS",
            "action": "buy",
            "quantity": 1,
            "entry_price": 100.0,
            "strategy_rationale": "momentum",
        },
    )

    assert "account_id is required" in error
    container.get.assert_not_called()


@pytest.mark.asyncio
async def test_open_positions_expose_stale_mark_status_when_live_data_is_unavailable(store):
    """Open positions should explicitly mark stale pricing instead of pretending quotes are live."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_marks",
    )
    await store.create_trade(
        account_id=account.account_id,
        symbol="INFY",
        trade_type=TradeType.BUY,
        quantity=5,
        entry_price=100.0,
        strategy_rationale="momentum",
        claude_session_id="session-open",
    )

    account_manager = PaperTradingAccountManager(store=store, market_data_service=None)
    positions = await account_manager.get_open_positions(account.account_id)

    assert len(positions) == 1
    assert positions[0].current_price == pytest.approx(100.0)
    assert positions[0].market_price_status == "stale_entry"
    assert "MarketDataService is not configured" in (positions[0].market_price_detail or "")


@pytest.mark.asyncio
async def test_execute_buy_fails_loud_without_live_market_data(store):
    """BUY execution should not silently substitute a synthetic price when live marks are unavailable."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_exec",
    )

    account_manager = PaperTradingAccountManager(store=store, market_data_service=None)
    executor = PaperTradeExecutor(store=store, account_manager=account_manager, market_data_service=None)

    result = await executor.execute_buy(
        account_id=account.account_id,
        symbol="INFY",
        quantity=1,
        entry_price=100.0,
        strategy_rationale="momentum",
        claude_session_id="session-open",
        use_market_price=True,
    )

    assert result["success"] is False
    assert "live market data is unavailable" in result["error"]
