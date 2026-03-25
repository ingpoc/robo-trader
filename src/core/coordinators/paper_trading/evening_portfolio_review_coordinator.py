"""
Evening Portfolio Review Coordinator

Handles portfolio data gathering for the evening review session:
- Resolving the review account
- Fetching current market prices for open positions
- Retrieving open positions
- Calculating daily performance metrics
- Compiling market observations from recent news
"""

from typing import Dict, Any, List

from src.config import Config
from src.core.event_bus import EventBus
from ..base_coordinator import BaseCoordinator


class EveningPortfolioReviewCoordinator(BaseCoordinator):
    """Gathers portfolio data and market observations for evening review."""

    def __init__(self, config: Config, event_bus: EventBus, container: Any):
        super().__init__(config, event_bus)
        self.container = container

    async def initialize(self) -> None:
        """Initialize with required services."""
        self.state_manager = await self.container.get("state_manager")
        self.paper_trading_state = self.state_manager.paper_trading
        self.paper_trading_store = await self.container.get("paper_trading_store")
        self.account_manager = await self.container.get("paper_trading_account_manager")

        try:
            self.market_data_service = await self.container.get("market_data_service")
        except ValueError:
            self._log_warning("market_data_service not registered - real-time evening marks disabled")
            self.market_data_service = None

        self._initialized = True

    async def resolve_review_account_id(self) -> str:
        """Resolve the paper account used by the evening review."""
        from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

        accounts = await self.account_manager.get_all_accounts()
        if not accounts:
            raise TradingError(
                "Evening review cannot run because no paper trading account exists",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
            )

        if len(accounts) > 1:
            account_ids = ", ".join(account.account_id for account in accounts)
            raise TradingError(
                f"Evening review requires an explicit paper trading account selection; available accounts: {account_ids}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
            )

        return accounts[0].account_id

    async def fetch_current_prices(self, account_id: str) -> Dict[str, float]:
        """Fetch current prices for open positions without fabricating marks."""
        if not self.market_data_service:
            return {}

        open_trades = await self.paper_trading_store.get_open_trades(account_id)
        symbols = sorted({trade.symbol for trade in open_trades})
        if not symbols:
            return {}

        market_data_map = await self.market_data_service.get_multiple_market_data(symbols)
        return {
            symbol: market_data.ltp
            for symbol, market_data in market_data_map.items()
            if market_data and market_data.ltp is not None
        }

    async def get_performance_metrics(
        self, account_id: str, review_date: str, current_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate daily performance metrics."""
        return await self.paper_trading_store.calculate_daily_performance_metrics(
            account_id=account_id,
            review_date=review_date,
            current_prices=current_prices,
        )

    async def get_open_positions(self, account_id: str) -> List[Any]:
        """Fetch current open positions."""
        return await self.account_manager.get_open_positions(account_id)

    async def compile_market_observations(self) -> Dict[str, Any]:
        """Compile market observations and conditions from recent news."""
        try:
            observations = {
                "market_sentiment": "NEUTRAL",
                "volatility": "NORMAL",
                "key_events": [],
                "sector_notes": []
            }

            cursor = await self.state_manager.news_earnings_state.get_recent_news(days=1, limit=10)
            if cursor:
                news_items = await cursor.fetchall()

                positive_count = sum(1 for item in news_items if item[5] == "positive")
                negative_count = sum(1 for item in news_items if item[5] == "negative")

                if positive_count > negative_count * 1.5:
                    observations["market_sentiment"] = "BULLISH"
                elif negative_count > positive_count * 1.5:
                    observations["market_sentiment"] = "BEARISH"

                for item in news_items[:5]:
                    observations["key_events"].append({
                        "title": item[2],
                        "sentiment": item[5],
                        "impact": "HIGH" if abs(item[6] or 0) > 0.7 else "MEDIUM"
                    })

            return observations

        except Exception as e:
            self._log_error(f"Failed to compile market observations: {e}")
            return {
                "market_sentiment": "UNKNOWN",
                "volatility": "UNKNOWN",
                "key_events": [],
                "sector_notes": []
            }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("EveningPortfolioReviewCoordinator cleanup complete")
