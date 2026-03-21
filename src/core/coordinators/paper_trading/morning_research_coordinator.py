"""Morning Research Coordinator

Executes batch stock research using the Perplexity API.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus
from src.core.perplexity_client import PerplexityClient

if TYPE_CHECKING:
    from src.core.di import DependencyContainer


class MorningResearchCoordinator(BaseCoordinator):
    """Researches stocks using Perplexity API batch queries. Max 150 lines."""

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container
        self.perplexity_service: Optional[PerplexityClient] = None

    async def initialize(self) -> None:
        """Initialize with Perplexity service from DI container."""
        try:
            self.perplexity_service = await self.container.get("perplexity_service")
        except ValueError:
            self._log_warning("perplexity_service not registered - research disabled")
            self.perplexity_service = None

        self._initialized = True

    async def research_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Research selected stocks using Perplexity API.

        Args:
            stocks: List of stock dicts with at least 'symbol' key.

        Returns:
            List of research result dicts with symbol, market_data, research, timestamp.
        """
        research_results = []

        if not self.perplexity_service:
            self._log_warning("Perplexity service not available - skipping research")
            for stock in stocks:
                research_results.append({
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": {"note": "Research service not available"},
                    "timestamp": datetime.utcnow().isoformat()
                })
            return research_results

        try:
            from src.core.perplexity_client import QueryType
            symbols = [stock["symbol"] for stock in stocks]
            batch_result = await self.perplexity_service.fetch_batch_data(
                symbols=symbols,
                query_type=QueryType.COMPREHENSIVE,
                batch_size=5,
                max_concurrent=2
            )

            fundamentals_map = {f.symbol: f for f in batch_result.fundamentals}
            news_map = {n.symbol: n for n in batch_result.news}

            for stock in stocks:
                symbol = stock["symbol"]
                research_data = {
                    "fundamentals": (
                        fundamentals_map[symbol].model_dump()
                        if symbol in fundamentals_map else None
                    ),
                    "news": (
                        news_map[symbol].model_dump()
                        if symbol in news_map else None
                    ),
                    "note": "Research completed successfully"
                }
                research_results.append({
                    "symbol": symbol,
                    "market_data": stock,
                    "research": research_data,
                    "timestamp": datetime.utcnow().isoformat()
                })

        except Exception as e:
            self._log_warning(f"Batch research failed: {e}")
            for stock in stocks:
                research_results.append({
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": {"error": str(e)},
                    "timestamp": datetime.utcnow().isoformat()
                })

        return research_results

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("MorningResearchCoordinator cleanup complete")
