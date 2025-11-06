"""
Database State Manager Facade for Robo Trader.

Coordinates all state managers and provides unified interface.
This is a thin facade that delegates to specialized managers.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from src.config import Config
from src.core.alerts import AlertManager
from src.core.event_bus import EventBus
from src.core.state_models import (AnalysisPerformance, FundamentalAnalysis,
                                   Intent, MarketConditions, PortfolioState,
                                   Recommendation, Signal)

from .analysis_state import AnalysisStateManager
from .approval_state import ApprovalStateManager
from .base import DatabaseConnection
from .intent_state import IntentStateManager
from .news_earnings_state import NewsEarningsStateManager
from .portfolio_state import PortfolioStateManager


class DatabaseStateManager:
    """
    Facade coordinating all database state operations.

    Delegates to specialized managers for each domain.
    Maintains backward compatibility with original interface.
    """

    def __init__(self, config: Config, event_bus: Optional[EventBus] = None):
        """
        Initialize database state manager facade.

        Args:
            config: Application configuration
            event_bus: Optional event bus for state change events
        """
        self.config = config
        self.event_bus = event_bus

        # Database connection
        self.db = DatabaseConnection(config)

        # Specialized state managers
        self.portfolio = PortfolioStateManager(self.db, event_bus)
        self.intents = IntentStateManager(self.db, event_bus)
        self.approvals = ApprovalStateManager(self.db, event_bus)
        self.news_earnings = NewsEarningsStateManager(self.db)
        self.analysis = AnalysisStateManager(self.db)
        self._stock_state = None  # Lazy initialize to avoid circular imports

        # Alert manager (not refactored yet)
        self.alert_manager = AlertManager(config.state_dir)

    async def initialize(self) -> None:
        """Initialize database and all state managers."""
        await self.db.initialize()
        await self.portfolio.initialize()
        await self.intents.initialize()
        await self.approvals.initialize()
        logger.info("Database state manager initialized")

    async def cleanup(self) -> None:
        """Cleanup all resources."""
        await self.db.cleanup()

    def get_stock_state_store(self):
        """Get stock state store for scheduler operations (lazy initialization)."""
        if self._stock_state is None:
            from src.core.background_scheduler.stores.stock_state_store import \
                StockStateStore

            self._stock_state = StockStateStore(self.db.connection)
        return self._stock_state

    # Portfolio operations - delegate to PortfolioStateManager
    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        return await self.portfolio.get_portfolio()

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        await self.portfolio.update_portfolio(portfolio)

    # Intent operations - delegate to IntentStateManager
    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        return await self.intents.get_intent(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """Get all intents."""
        return await self.intents.get_all_intents()

    async def create_intent(
        self, symbol: str, signal: Optional[Signal] = None, source: str = "system"
    ) -> Intent:
        """Create new trading intent."""
        return await self.intents.create_intent(symbol, signal, source)

    async def update_intent(self, intent: Intent) -> None:
        """Update existing intent."""
        await self.intents.update_intent(intent)

    # Approval operations - delegate to ApprovalStateManager
    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """Add recommendation to approval queue."""
        await self.approvals.add_to_approval_queue(recommendation)

    async def get_pending_approvals(self) -> List[Dict]:
        """Get pending approvals."""
        return await self.approvals.get_pending_approvals()

    async def update_approval_status(
        self, recommendation_id: str, status: str, user_feedback: Optional[str] = None
    ) -> bool:
        """Update approval status."""
        return await self.approvals.update_approval_status(
            recommendation_id, status, user_feedback
        )

    # News and Earnings operations - delegate to NewsEarningsStateManager
    async def save_news_item(
        self,
        symbol: str,
        title: str,
        summary: str,
        content: Optional[str] = None,
        **kwargs
    ) -> None:
        """Save news item."""
        await self.news_earnings.save_news_item(
            symbol, title, summary, content, **kwargs
        )

    async def save_earnings_report(
        self, symbol: str, fiscal_period: str, report_date: str, **kwargs
    ) -> None:
        """Save earnings report."""
        await self.news_earnings.save_earnings_report(
            symbol, fiscal_period, report_date, **kwargs
        )

    async def get_news_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Get news for symbol."""
        return await self.news_earnings.get_news_for_symbol(symbol, limit)

    async def get_earnings_for_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get earnings for symbol."""
        return await self.news_earnings.get_earnings_for_symbol(symbol, limit)

    async def get_upcoming_earnings(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming earnings."""
        return await self.news_earnings.get_upcoming_earnings(days_ahead)

    async def update_last_news_fetch(
        self, symbol: str, fetch_time: Optional[str] = None
    ) -> None:
        """Update last news fetch time."""
        await self.news_earnings.update_last_news_fetch(symbol, fetch_time)

    async def get_last_news_fetch(self, symbol: str) -> Optional[str]:
        """Get last news fetch time."""
        return await self.news_earnings.get_last_news_fetch(symbol)

    # Analysis operations - delegate to AnalysisStateManager
    async def save_fundamental_analysis(self, analysis: FundamentalAnalysis) -> int:
        """Save fundamental analysis."""
        return await self.analysis.save_fundamental_analysis(analysis)

    async def get_fundamental_analysis(
        self, symbol: str, limit: int = 1
    ) -> List[FundamentalAnalysis]:
        """Get fundamental analysis."""
        return await self.analysis.get_fundamental_analysis(symbol, limit)

    async def save_recommendation(self, recommendation: Recommendation) -> int:
        """Save trading recommendation."""
        return await self.analysis.save_recommendation(recommendation)

    async def get_recommendations(
        self, symbol: Optional[str] = None, limit: int = 20
    ) -> List[Recommendation]:
        """Get recommendations."""
        return await self.analysis.get_recommendations(symbol, limit)

    async def save_market_conditions(self, conditions: MarketConditions) -> int:
        """Save market conditions."""
        return await self.analysis.save_market_conditions(conditions)

    async def save_analysis_performance(self, performance: AnalysisPerformance) -> int:
        """Save analysis performance."""
        return await self.analysis.save_analysis_performance(performance)

    # Backward compatibility methods for methods not yet migrated
    # These would need to be implemented based on original file
    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update screening results - TODO: implement."""
        logger.warning(
            "update_screening_results not yet implemented in refactored version"
        )

    async def get_screening_results(self) -> Optional[Dict[str, Any]]:
        """Get screening results - TODO: implement."""
        logger.warning(
            "get_screening_results not yet implemented in refactored version"
        )
        return None

    async def save_daily_plan(self, plan: Dict) -> None:
        """Save daily plan - TODO: implement."""
        logger.warning("save_daily_plan not yet implemented in refactored version")

    async def load_weekly_plan(self) -> Optional[Dict]:
        """Load weekly plan - TODO: implement."""
        logger.warning("load_weekly_plan not yet implemented in refactored version")
        return None
