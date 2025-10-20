"""Paper trading account management service."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from ...models.paper_trading import PaperTradingAccount, AccountType, RiskLevel
from ...stores.paper_trading_store import PaperTradingStore

logger = logging.getLogger(__name__)


class PaperTradingAccountManager:
    """Manage paper trading accounts."""

    def __init__(self, store: PaperTradingStore):
        """Initialize manager."""
        self.store = store

    async def create_account(
        self,
        account_name: str,
        initial_balance: float = 100000.0,
        strategy_type: AccountType = AccountType.SWING,
        risk_level: RiskLevel = RiskLevel.MODERATE,
        max_position_size: float = 5.0,
        max_portfolio_risk: float = 10.0
    ) -> PaperTradingAccount:
        """Create new paper trading account."""
        account = await self.store.create_account(
            account_name=account_name,
            initial_balance=initial_balance,
            strategy_type=strategy_type,
            risk_level=risk_level,
            max_position_size=max_position_size,
            max_portfolio_risk=max_portfolio_risk
        )
        logger.info(f"Account created: {account.account_id}")
        return account

    async def get_account(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Get account by ID."""
        return await self.store.get_account(account_id)

    async def get_account_balance(self, account_id: str) -> Dict[str, float]:
        """Get account balance details."""
        account = await self.get_account(account_id)
        if not account:
            return {}

        return {
            "current_balance": account.current_balance,
            "buying_power": account.buying_power,
            "initial_balance": account.initial_balance,
            "deployed_capital": account.current_balance - account.buying_power,
            "available_percentage": (account.buying_power / account.initial_balance) * 100
        }

    async def can_execute_trade(
        self,
        account_id: str,
        trade_value: float,
        max_position_pct: float
    ) -> tuple[bool, Optional[str]]:
        """
        Check if trade can be executed.

        Returns:
            (can_execute, error_message)
        """
        account = await self.get_account(account_id)
        if not account:
            return False, "Account not found"

        # Check buying power
        if trade_value > account.buying_power:
            return False, f"Insufficient buying power. Required: {trade_value}, Available: {account.buying_power}"

        # Check position size limit (relative to initial balance)
        max_allowed = account.initial_balance * (max_position_pct / 100)
        if trade_value > max_allowed:
            return False, f"Position exceeds max size limit. Max: {max_allowed}, Requested: {trade_value}"

        return True, None

    async def update_balance(
        self,
        account_id: str,
        amount_change: float
    ) -> Optional[PaperTradingAccount]:
        """Update account balance after trade execution."""
        account = await self.get_account(account_id)
        if not account:
            return None

        new_balance = account.current_balance + amount_change
        new_buying_power = account.buying_power + amount_change

        await self.store.update_account_balance(account_id, new_balance, new_buying_power)
        logger.info(f"Account {account_id} balance updated: {account.current_balance} → {new_balance}")

        return await self.get_account(account_id)

    async def lock_buying_power(
        self,
        account_id: str,
        amount: float
    ) -> Optional[PaperTradingAccount]:
        """Lock buying power for pending trade."""
        account = await self.get_account(account_id)
        if not account:
            return None

        new_buying_power = account.buying_power - amount
        await self.store.update_account_balance(account_id, account.current_balance, new_buying_power)

        return await self.get_account(account_id)

    async def unlock_buying_power(
        self,
        account_id: str,
        amount: float
    ) -> Optional[PaperTradingAccount]:
        """Unlock buying power from pending trade."""
        account = await self.get_account(account_id)
        if not account:
            return None

        new_buying_power = account.buying_power + amount
        await self.store.update_account_balance(account_id, account.current_balance, new_buying_power)

        return await self.get_account(account_id)

    async def reset_monthly(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Reset account for new month."""
        await self.store.reset_monthly_account(account_id)
        return await self.get_account(account_id)

    async def to_dict(self, account: PaperTradingAccount) -> Dict[str, Any]:
        """Convert account to dictionary."""
        return account.to_dict()
