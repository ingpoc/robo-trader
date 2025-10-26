"""
Fundamental analysis task executor.

Orchestrates data flow: Perplexity API → Processor → Store
Handles task execution, error management, and event emission.
"""

from typing import Dict, List, Any, Optional
import uuid

import aiosqlite
from loguru import logger

from ..clients.perplexity_client import PerplexityClient
from ..processors.deep_fundamental_processor import DeepFundamentalProcessor
from ..processors.earnings_processor import EarningsProcessor
from ..processors.news_processor import NewsProcessor
from ..stores.fundamental_store import FundamentalStore
from ...event_bus import EventBus, Event, EventType


class FundamentalExecutor:
    """Executes fundamental analysis tasks with full error handling."""

    def __init__(
        self,
        perplexity_client: PerplexityClient,
        db_connection: aiosqlite.Connection,
        event_bus: EventBus,
    ):
        """Initialize executor with dependencies.

        Args:
            perplexity_client: Perplexity API client
            db_connection: Database connection
            event_bus: Event bus for broadcasting completion
        """
        self.perplexity_client = perplexity_client
        self.store = FundamentalStore(db_connection)
        self.event_bus = event_bus

    async def execute_earnings_fundamentals(
        self, symbols: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch and store earnings fundamentals.

        Args:
            symbols: List of stock symbols
            metadata: Task metadata with context

        Returns:
            Status dict with success/failure information
        """
        try:
            logger.info(f"Executing earnings fundamentals for {symbols}")

            response = await self.perplexity_client.fetch_earnings_fundamentals(
                symbols
            )

            if not response:
                logger.warning("Empty response from Perplexity API")
                return {"status": "failed", "error": "Empty API response"}

            parsed_data = EarningsProcessor.parse_comprehensive_earnings(response)

            if not parsed_data:
                logger.warning("Failed to parse earnings data")
                return {"status": "failed", "error": "Parse failure"}

            success = await self.store.store_earnings_fundamentals(symbols, parsed_data)

            if success:
                await self.event_bus.publish(
                    Event(
                        id=str(uuid.uuid4()),
                        type=EventType.MARKET_DATA_UPDATE,
                        source="FundamentalExecutor",
                        data={
                            "task_type": "earnings_fundamentals",
                            "symbols": symbols,
                            "status": "completed",
                        },
                    )
                )
                return {"status": "success", "symbols": symbols}
            else:
                return {"status": "failed", "error": "Storage failure"}

        except Exception as e:
            logger.error(f"Error executing earnings fundamentals: {e}")
            return {"status": "failed", "error": str(e)}

    async def execute_market_news_analysis(
        self, symbols: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch and store categorized market news.

        Args:
            symbols: List of stock symbols
            metadata: Task metadata with context

        Returns:
            Status dict with success/failure information
        """
        try:
            logger.info(f"Executing market news analysis for {symbols}")

            response = await self.perplexity_client.fetch_market_news(symbols)

            if not response:
                logger.warning("Empty response from Perplexity API")
                return {"status": "failed", "error": "Empty API response"}

            parsed_data = NewsProcessor.parse_categorized_news(response)

            if not parsed_data:
                logger.warning("Failed to parse news data")
                return {"status": "failed", "error": "Parse failure"}

            news_items = self._transform_news_items(parsed_data, symbols)

            success = await self.store.store_market_news(news_items)

            if success:
                await self.event_bus.publish(
                    Event(
                        id=str(uuid.uuid4()),
                        type=EventType.MARKET_DATA_UPDATE,
                        source="FundamentalExecutor",
                        data={
                            "task_type": "market_news_analysis",
                            "symbols": symbols,
                            "status": "completed",
                        },
                    )
                )
                return {"status": "success", "symbols": symbols, "items": len(news_items)}
            else:
                return {"status": "failed", "error": "Storage failure"}

        except Exception as e:
            logger.error(f"Error executing market news analysis: {e}")
            return {"status": "failed", "error": str(e)}

    async def execute_deep_fundamental_analysis(
        self, symbols: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch and store deep fundamental analysis.

        Args:
            symbols: List of stock symbols
            metadata: Task metadata with context

        Returns:
            Status dict with success/failure information
        """
        try:
            logger.info(f"Executing deep fundamental analysis for {symbols}")

            response = await self.perplexity_client.fetch_deep_fundamentals(symbols)

            if not response:
                logger.warning("Empty response from Perplexity API")
                return {"status": "failed", "error": "Empty API response"}

            parsed_data = DeepFundamentalProcessor.parse_deep_fundamentals(response)

            if not parsed_data:
                logger.warning("Failed to parse deep fundamentals")
                return {"status": "failed", "error": "Parse failure"}

            success = await self.store.store_deep_fundamentals(symbols, parsed_data)

            if success:
                await self.event_bus.publish(
                    Event(
                        id=str(uuid.uuid4()),
                        type=EventType.MARKET_DATA_UPDATE,
                        source="FundamentalExecutor",
                        data={
                            "task_type": "deep_fundamental_analysis",
                            "symbols": symbols,
                            "status": "completed",
                        },
                    )
                )
                return {"status": "success", "symbols": symbols}
            else:
                return {"status": "failed", "error": "Storage failure"}

        except Exception as e:
            logger.error(f"Error executing deep fundamental analysis: {e}")
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def _transform_news_items(
        parsed_data: Dict[str, Any], symbols: List[str]
    ) -> List[Dict[str, Any]]:
        """Transform parsed news data to storage format.

        Args:
            parsed_data: Parsed news data from API
            symbols: Original symbols requested

        Returns:
            List of formatted news items
        """
        news_items = []

        if isinstance(parsed_data, dict):
            articles = parsed_data.get("articles", [])
            if isinstance(articles, list):
                for article in articles:
                    news_items.append(
                        {
                            "symbol": article.get("symbol", symbols[0] if symbols else ""),
                            "headline": article.get("headline", article.get("title", "")),
                            "content": article.get("content", article.get("summary", "")),
                            "source": article.get("source", "Perplexity"),
                            "article_type": article.get("type", "news"),
                            "category": article.get("category", "general"),
                            "sentiment": article.get("sentiment", "neutral"),
                            "impact_score": article.get("impact_score", 0.5),
                            "relevance_score": article.get("relevance_score", 0.5),
                            "key_points": article.get("key_points", []),
                        }
                    )

        return news_items
