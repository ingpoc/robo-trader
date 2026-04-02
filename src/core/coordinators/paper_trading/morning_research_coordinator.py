"""Morning Research Coordinator.

Executes batch stock research using the active AI runtime.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus

if TYPE_CHECKING:
    from src.core.di import DependencyContainer
    from src.services.ai_market_research_service import AIMarketResearchService


class MorningResearchCoordinator(BaseCoordinator):
    """Researches stocks using AI-runtime web research in batched concurrent runs."""

    def __init__(self, config: Config, event_bus: EventBus, container: "DependencyContainer"):
        super().__init__(config, event_bus)
        self.container = container
        self.market_research_service: Optional["AIMarketResearchService"] = None

    async def initialize(self) -> None:
        """Initialize with the AI market research service from DI."""
        try:
            self.market_research_service = await self.container.get("ai_market_research_service")
        except ValueError:
            self._log_warning("ai_market_research_service not registered - research disabled")
            self.market_research_service = None
        self._initialized = True

    async def research_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Research selected stocks with the active AI runtime."""
        if not stocks:
            return []

        if not self.market_research_service:
            self._log_warning("AI market research service not available - skipping research")
            return [
                {
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": {"note": "Research service not available"},
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for stock in stocks
            ]

        symbols = [stock["symbol"] for stock in stocks]
        company_names = {
            stock["symbol"]: stock.get("company_name") or stock.get("name") or stock["symbol"]
            for stock in stocks
        }

        try:
            batch_result = await self.market_research_service.collect_batch_symbol_research(
                symbols,
                company_names=company_names,
                research_brief=(
                    "Prepare factual pre-market research for swing-trading idea generation. "
                    "Focus on fresh company news, current fundamentals, filings, and market context."
                ),
                max_concurrent=3,
            )
        except Exception as exc:
            self._log_warning(f"Batch research failed: {exc}")
            return [
                {
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": {"error": str(exc)},
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for stock in stocks
            ]

        research_results: List[Dict[str, Any]] = []
        for stock in stocks:
            symbol = stock["symbol"]
            research = batch_result.get(symbol, {})
            research_results.append(
                {
                    "symbol": symbol,
                    "market_data": stock,
                    "research": {
                        "summary": research.get("summary"),
                        "fundamentals": research.get("financial_data"),
                        "news": research.get("news"),
                        "filings": research.get("filings"),
                        "market_context": research.get("market_context"),
                        "evidence": research.get("evidence", []),
                        "risks": research.get("risks", []),
                        "source_summary": research.get("source_summary", []),
                        "note": "AI runtime web research completed successfully",
                        "errors": research.get("errors", []),
                    },
                    "timestamp": research.get(
                        "research_timestamp",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                }
            )

        return research_results

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("MorningResearchCoordinator cleanup complete")
