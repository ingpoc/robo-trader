"""Regression tests for the store-backed paper trading authority path."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from src.core.errors import MarketDataError
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
async def test_initialize_normalizes_legacy_uppercase_open_status():
    db = await aiosqlite.connect(":memory:")
    await db.execute(
        """
        CREATE TABLE paper_trading_accounts (
            account_id TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            initial_balance REAL NOT NULL,
            current_balance REAL NOT NULL,
            buying_power REAL NOT NULL,
            strategy_type TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            max_position_size REAL NOT NULL,
            max_portfolio_risk REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            month_start_date TEXT NOT NULL,
            monthly_pnl REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE paper_trades (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            entry_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            entry_reason TEXT NOT NULL,
            strategy_tag TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO paper_trading_accounts (
            account_id, account_name, initial_balance, current_balance, buying_power,
            strategy_type, risk_level, max_position_size, max_portfolio_risk,
            is_active, month_start_date, monthly_pnl, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "paper_main",
            "Main",
            100000.0,
            100000.0,
            100000.0,
            "swing",
            "moderate",
            5.0,
            10.0,
            1,
            "2026-03-01",
            0.0,
            now,
            now,
        ),
    )
    await db.execute(
        """
        INSERT INTO paper_trades (
            id, account_id, symbol, side, quantity, entry_price, entry_date,
            status, entry_reason, strategy_tag, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-trade-1",
            "paper_main",
            "INFY",
            "BUY",
            5,
            100.0,
            now,
            "OPEN",
            "legacy row",
            "swing",
            now,
            now,
        ),
    )
    await db.commit()

    store = PaperTradingStore(db)
    await store.initialize()
    open_trades = await store.get_open_trades("paper_main")

    assert len(open_trades) == 1
    assert open_trades[0].status.value == "open"

    cursor = await db.execute("SELECT status FROM paper_trades WHERE account_id = ?", ("paper_main",))
    row = await cursor.fetchone()
    await cursor.close()
    assert row[0] == "open"

    await db.close()


@pytest.mark.asyncio
async def test_manual_run_audit_persists_metadata(store):
    started_at = datetime.now(timezone.utc).isoformat()
    completed_at = datetime.now(timezone.utc).isoformat()

    await store.record_manual_run_audit(
        run_id="run_123",
        account_id="paper_main",
        route_name="paper_trading.discovery",
        status="ready",
        status_reason="Manual run completed successfully.",
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=1250,
        dependency_state={"runtime_mode": "manual_only"},
        provider_metadata={"provider": "codex", "model": "gpt-5.4"},
    )

    cursor = await store.db_connection.execute(
        "SELECT status, status_reason, duration_ms, dependency_state, provider_metadata FROM manual_run_audit WHERE run_id = ?",
        ("run_123",),
    )
    row = await cursor.fetchone()
    await cursor.close()

    assert row[0] == "ready"
    assert row[1] == "Manual run completed successfully."
    assert row[2] == 1250
    assert "manual_only" in row[3]
    assert "gpt-5.4" in row[4]


@pytest.mark.asyncio
async def test_get_manual_run_audit_entries_returns_recent_runs(store):
    await store.record_manual_run_audit(
        run_id="run_a",
        account_id="paper_main",
        route_name="paper_trading.discovery",
        status="ready",
        status_reason="first",
        started_at="2026-03-28T09:00:00+00:00",
        completed_at="2026-03-28T09:00:02+00:00",
        duration_ms=2000,
        dependency_state={"runtime_mode": "manual_only"},
        provider_metadata={"provider": "codex"},
    )
    await store.record_manual_run_audit(
        run_id="run_b",
        account_id="paper_main",
        route_name="paper_trading.review",
        status="blocked",
        status_reason="second",
        started_at="2026-03-28T10:00:00+00:00",
        completed_at="2026-03-28T10:00:03+00:00",
        duration_ms=3000,
        dependency_state={"runtime_mode": "manual_only"},
        provider_metadata={"provider": "codex"},
    )

    entries = await store.get_manual_run_audit_entries("paper_main", limit=10)

    assert [entry["run_id"] for entry in entries[:2]] == ["run_b", "run_a"]
    assert entries[0]["dependency_state"]["runtime_mode"] == "manual_only"
    assert entries[0]["provider_metadata"]["provider"] == "codex"


@pytest.mark.asyncio
async def test_automation_run_persists_and_decodes_json_metadata(store):
    now = datetime.now(timezone.utc).isoformat()
    await store.create_automation_run(
        {
            "run_id": "autorun_1",
            "account_id": "paper_main",
            "job_type": "daily_review_cycle",
            "provider": "codex_subscription_local",
            "runtime_session_id": None,
            "status": "queued",
            "status_reason": "",
            "block_reason": "",
            "schedule_source": "manual",
            "trigger_reason": "operator refresh",
            "input_digest": "abc123",
            "provider_metadata": {"provider": "codex", "model": "gpt-5.4"},
            "tool_trace": [{"tool": "operator_snapshot"}],
            "artifact_path": None,
            "started_at": now,
            "completed_at": None,
            "timeout_at": None,
            "duration_ms": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    row = await store.get_automation_run("autorun_1")

    assert row is not None
    assert row["provider_metadata"]["model"] == "gpt-5.4"
    assert row["tool_trace"][0]["tool"] == "operator_snapshot"


@pytest.mark.asyncio
async def test_automation_controls_and_active_run_lookup_work(store):
    now = datetime.now(timezone.utc).isoformat()
    await store.upsert_automation_job_control(
        {
            "job_type": "research_cycle",
            "enabled": True,
            "schedule_minutes": 60,
            "last_run_at": None,
            "next_run_at": now,
            "paused_at": None,
            "pause_reason": "",
            "updated_at": now,
        }
    )
    await store.set_automation_global_pause(True, reason="maintenance")
    await store.create_automation_run(
        {
            "run_id": "autorun_active",
            "account_id": "paper_main",
            "job_type": "research_cycle",
            "provider": "codex_subscription_local",
            "runtime_session_id": None,
            "status": "in_progress",
            "status_reason": "",
            "block_reason": "",
            "schedule_source": "manual",
            "trigger_reason": "",
            "input_digest": "digest",
            "provider_metadata": {},
            "tool_trace": [],
            "artifact_path": None,
            "started_at": now,
            "completed_at": None,
            "timeout_at": None,
            "duration_ms": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    controls = await store.get_automation_job_control("research_cycle")
    global_pause = await store.get_automation_global_pause()
    active = await store.get_active_automation_run("paper_main", "research_cycle")

    assert controls is not None
    assert controls["enabled"] is True
    assert global_pause["paused"] is True
    assert global_pause["reason"] == "maintenance"
    assert active is not None
    assert active["run_id"] == "autorun_active"


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
async def test_open_positions_fail_loud_when_live_data_is_unavailable(store):
    """Open positions should fail loud instead of synthesizing stale entry-price marks."""
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
    with pytest.raises(MarketDataError, match="Live market data is unavailable"):
        await account_manager.get_open_positions(account.account_id)


@pytest.mark.asyncio
async def test_store_backed_open_positions_return_readable_degraded_rows(store):
    """Store-backed position reads should stay available without live quotes."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_store_backed",
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
    positions = await account_manager.get_store_backed_open_positions(account.account_id)

    assert len(positions) == 1
    assert positions[0].symbol == "INFY"
    assert positions[0].current_price is None
    assert positions[0].current_value is None
    assert positions[0].unrealized_pnl is None
    assert positions[0].unrealized_pnl_pct is None
    assert positions[0].market_price_status == "quote_unavailable"
    assert "no entry-price substitution" in str(positions[0].market_price_detail)


@pytest.mark.asyncio
async def test_store_backed_position_metrics_match_open_trade_ledger(store):
    """Store-backed deployed capital must come from the open-trade ledger only."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_position_metrics",
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
    await store.create_trade(
        account_id=account.account_id,
        symbol="TCS",
        trade_type=TradeType.BUY,
        quantity=2,
        entry_price=300.0,
        strategy_rationale="trend",
        claude_session_id="session-open-2",
    )

    account_manager = PaperTradingAccountManager(store=store, market_data_service=None)
    metrics = await account_manager.get_store_backed_position_metrics(account.account_id)

    assert metrics["open_positions_count"] == 2
    assert metrics["deployed_capital"] == pytest.approx(1100.0)


@pytest.mark.asyncio
async def test_open_positions_reject_stale_cached_quotes(store):
    """Cached quotes older than the freshness threshold must not be exposed as live marks."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_stale_cache",
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

    market_data_service = SimpleNamespace(
        get_multiple_market_data=AsyncMock(
            return_value={
                "INFY": SimpleNamespace(
                    ltp=120.0,
                    timestamp="2026-03-27T12:03:49+00:00",
                )
            }
        ),
        get_quote_stream_status=AsyncMock(
            return_value=SimpleNamespace(
                connected=True,
                status="ready",
                summary="Connected",
                detail=None,
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={"INFY": object()}),
        subscribe_market_data=AsyncMock(),
    )

    account_manager = PaperTradingAccountManager(store=store, market_data_service=market_data_service)
    with pytest.raises(MarketDataError, match="Live market data is unavailable"):
        await account_manager.get_open_positions(account.account_id)


@pytest.mark.asyncio
async def test_open_positions_tolerate_legacy_date_only_entry_timestamps(store):
    """Legacy date-only timestamps should not break open-position rendering."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_legacy_dates",
    )
    trade = await store.create_trade(
        account_id=account.account_id,
        symbol="INFY",
        trade_type=TradeType.BUY,
        quantity=5,
        entry_price=100.0,
        strategy_rationale="momentum",
        claude_session_id="session-open",
    )
    await store.db_connection.execute(
        "UPDATE paper_trades SET entry_timestamp = ? WHERE trade_id = ?",
        ("2025-12-26", trade.trade_id),
    )
    await store.db_connection.commit()

    market_data_service = SimpleNamespace(
        get_quote_stream_status=AsyncMock(
            return_value=SimpleNamespace(
                connected=True,
                status="ready",
                summary="Connected",
                detail=None,
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={"INFY": object()}),
        subscribe_market_data=AsyncMock(),
        get_multiple_market_data=AsyncMock(
            return_value={
                "INFY": SimpleNamespace(
                    ltp=120.0,
                    timestamp="2026-03-30T12:03:49+00:00",
                )
            }
        ),
    )

    account_manager = PaperTradingAccountManager(store=store, market_data_service=market_data_service)
    positions = await account_manager.get_open_positions(account.account_id)

    assert len(positions) == 1
    assert positions[0].days_held >= 1
    assert positions[0].market_price_timestamp == "2026-03-30T12:03:49+00:00"


@pytest.mark.asyncio
async def test_open_positions_fall_back_quickly_when_market_data_times_out(store):
    """Operator views should fall back to stale entry marks when live market data stalls."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_timeout_marks",
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

    async def slow_subscriptions():
        await asyncio.sleep(1.1)
        return {}

    market_data_service = SimpleNamespace(
        get_quote_stream_status=AsyncMock(
            return_value=SimpleNamespace(
                connected=True,
                status="ready",
                summary="Quote stream is ready.",
                detail="",
            )
        ),
        get_active_subscriptions=AsyncMock(side_effect=slow_subscriptions),
        subscribe_market_data=AsyncMock(),
        get_multiple_market_data=AsyncMock(return_value={}),
    )
    account_manager = PaperTradingAccountManager(store=store, market_data_service=market_data_service)
    account_manager.MARKET_DATA_FETCH_TIMEOUT_SECONDS = 1.0

    with pytest.raises(MarketDataError, match="Live market data is unavailable"):
        await account_manager.get_open_positions(account.account_id)
    market_data_service.get_multiple_market_data.assert_awaited()


@pytest.mark.asyncio
async def test_open_positions_skip_live_fetch_when_quote_stream_is_already_unhealthy(store):
    """Known-bad quote stream state should not trigger another blocking broker fetch."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_unhealthy_stream",
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

    market_data_service = SimpleNamespace(
        get_multiple_market_data=AsyncMock(return_value={}),
        get_quote_stream_status=AsyncMock(
            return_value=SimpleNamespace(
                connected=False,
                status="degraded",
                summary="Quote stream is unhealthy.",
                detail="KiteTicker connection timeout.",
            )
        ),
        get_active_subscriptions=AsyncMock(return_value={}),
        subscribe_market_data=AsyncMock(),
    )
    account_manager = PaperTradingAccountManager(store=store, market_data_service=market_data_service)

    with pytest.raises(MarketDataError, match="Live market data is unavailable"):
        await account_manager.get_open_positions(account.account_id)
    market_data_service.subscribe_market_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_performance_metrics_fail_loud_without_live_quotes_for_open_positions(store):
    """Performance metrics should fail loud instead of zeroing unrealized P&L from entry-price fallback."""
    account = await store.create_account(
        account_name="Main",
        initial_balance=100000.0,
        strategy_type=AccountType.SWING,
        risk_level=RiskLevel.MODERATE,
        max_position_size=5.0,
        max_portfolio_risk=10.0,
        account_id="paper_perf_fail_loud",
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

    market_data_service = SimpleNamespace(
        get_multiple_market_data=AsyncMock(return_value={}),
    )
    account_manager = PaperTradingAccountManager(store=store, market_data_service=market_data_service)

    with pytest.raises(MarketDataError, match="Live market data is unavailable"):
        await account_manager.get_performance_metrics(account.account_id, period="all-time")


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
