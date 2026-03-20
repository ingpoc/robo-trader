from types import SimpleNamespace

import pytest

from src.core.coordinators.paper_trading.claude_paper_trading_coordinator import (
    ClaudePaperTradingCoordinator,
)


class _DummyEventBus:
    def subscribe(self, *_args, **_kwargs):
        return None

    def unsubscribe(self, *_args, **_kwargs):
        return None


class _DummyAccountManager:
    def __init__(self, accounts):
        self._accounts = accounts

    async def get_all_accounts(self):
        return self._accounts


def _coordinator(accounts):
    return ClaudePaperTradingCoordinator(
        config=SimpleNamespace(),
        state_manager=SimpleNamespace(),
        event_bus=_DummyEventBus(),
        account_manager=_DummyAccountManager(accounts),
        trade_executor=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_claude_paper_trading_requires_existing_account():
    coordinator = _coordinator([])

    with pytest.raises(ValueError, match="no paper trading account exists"):
        await coordinator._resolve_autonomous_account_id()


@pytest.mark.asyncio
async def test_claude_paper_trading_requires_explicit_selection_when_multiple_accounts_exist():
    coordinator = _coordinator(
        [
            SimpleNamespace(account_id="paper_main"),
            SimpleNamespace(account_id="paper_alt"),
        ]
    )

    with pytest.raises(ValueError, match="requires an explicit account selection"):
        await coordinator._resolve_autonomous_account_id()
