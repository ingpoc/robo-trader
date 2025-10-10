"""
State Coordinator

Central coordinator for all focused state stores.
Provides unified interface compatible with legacy StateManager.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

from .state import PortfolioState, Intent, Signal
from .alerts import AlertManager
from .stores import PortfolioStore, IntentLedger, PlanningStore, AnalyticsCache


class StateCoordinator:
    """
    Coordinates access to all focused state stores.

    This class provides a unified interface while delegating to specialized stores.
    Maintains backward compatibility with existing StateManager API.
    """

    def __init__(self, state_dir: Path, cache_ttl_seconds: int = 300):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.portfolio_store = PortfolioStore(state_dir)
        self.intent_ledger = IntentLedger(state_dir)
        self.planning_store = PlanningStore(state_dir)
        self.analytics_cache = AnalyticsCache(state_dir, cache_ttl_seconds)
        self.alert_manager = AlertManager(state_dir)

        logger.info("StateCoordinator initialized with focused stores")

    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        return await self.portfolio_store.get_portfolio()

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        await self.portfolio_store.update_portfolio(portfolio)

    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        return await self.intent_ledger.get_intent(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """Get all intents."""
        return await self.intent_ledger.get_all_intents()

    async def create_intent(
        self,
        symbol: str,
        signal: Optional[Signal] = None,
        source: str = "system"
    ) -> Intent:
        """Create new trading intent."""
        return await self.intent_ledger.create_intent(symbol, signal, source)

    async def update_intent(self, intent: Intent) -> None:
        """Update existing intent."""
        await self.intent_ledger.update_intent(intent)

    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update screening results cache."""
        await self.analytics_cache.update_screening_results(results)

    async def get_screening_results(self) -> Optional[Dict[str, Any]]:
        """Get screening results from cache."""
        return await self.analytics_cache.get_screening_results()

    async def update_strategy_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update strategy results cache."""
        await self.analytics_cache.update_strategy_results(results)

    async def get_strategy_results(self) -> Optional[Dict[str, Any]]:
        """Get strategy results from cache."""
        return await self.analytics_cache.get_strategy_results()

    async def save_daily_plan(self, plan: Dict) -> None:
        """Save AI-generated daily work plan."""
        await self.planning_store.save_daily_plan(plan)

    async def load_daily_plan(self, date: str) -> Optional[Dict]:
        """Load daily plan for specific date."""
        return await self.planning_store.load_daily_plan(date)

    async def save_analysis_history(self, symbol: str, analysis: Dict) -> None:
        """Save detailed analysis history per stock."""
        await self.analytics_cache.save_analysis_history(symbol, analysis)

    async def get_analysis_history(
        self,
        symbol: str,
        include_compressed: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """Get analysis history for a symbol."""
        return await self.analytics_cache.get_analysis_history(
            symbol,
            include_compressed,
            limit
        )

    async def add_priority_item(self, symbol: str, reason: str, priority: str) -> None:
        """Add item to priority queue for urgent analysis."""
        await self.planning_store.add_priority_item(symbol, reason, priority)

    async def get_priority_items(self) -> List[Dict]:
        """Get items needing urgent attention."""
        return await self.planning_store.get_priority_items()

    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """Add AI recommendation to user approval queue."""
        await self.planning_store.add_to_approval_queue(recommendation)

    async def get_pending_approvals(self) -> List[Dict]:
        """Get recommendations awaiting user approval."""
        return await self.planning_store.get_pending_approvals()

    async def update_approval_status(
        self,
        recommendation_id: str,
        status: str,
        user_feedback: Optional[str] = None
    ) -> bool:
        """Update approval status for a recommendation."""
        return await self.planning_store.update_approval_status(
            recommendation_id,
            status,
            user_feedback
        )

    async def save_weekly_plan(self, plan: Dict) -> None:
        """Save AI-generated weekly work distribution plan."""
        await self.planning_store.save_weekly_plan(plan)

    async def load_weekly_plan(self) -> Optional[Dict]:
        """Load current weekly plan."""
        return await self.planning_store.load_weekly_plan()

    async def save_learning_insights(self, insights: Dict) -> None:
        """Save AI learning insights from recommendation outcomes."""
        await self.planning_store.save_learning_insights(insights)

    async def get_learning_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent learning insights."""
        return await self.planning_store.get_learning_insights(limit)

    async def create_checkpoint(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a checkpoint of current portfolio state."""
        return await self.portfolio_store.create_checkpoint(name, metadata)

    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore portfolio state from checkpoint."""
        return await self.portfolio_store.restore_checkpoint(checkpoint_id)

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics from all stores."""
        from datetime import datetime, timezone

        portfolio_stats = await self.portfolio_store.get_stats()
        intent_stats = await self.intent_ledger.get_stats()
        planning_stats = await self.planning_store.get_stats()
        cache_stats = await self.analytics_cache.get_cache_stats()

        return {
            "portfolio": portfolio_stats,
            "intents": intent_stats,
            "planning": planning_stats,
            "analytics_cache": cache_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Cleanup old data across all stores."""
        intents_removed = await self.intent_ledger.cleanup_old_intents(days)

        logger.info(f"Cleanup complete: {intents_removed} old intents removed")

        return {
            "intents_removed": intents_removed
        }
