"""
Paper Trading Stock Discovery Service

Implements autonomous stock discovery for paper trading using:
- Perplexity API for market research
- Claude Agent SDK for analysis
- Sector and market cap screening
- Technical and fundamental analysis
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from loguru import logger

from ...core.event_bus import EventHandler, Event, EventType
from ...core.background_scheduler.clients.perplexity_client import PerplexityClient
from ...models.scheduler import TaskType, QueueName
from ...core.errors import TradingError, ErrorCategory, ErrorSeverity


class StockDiscoveryService(EventHandler):
    """
    Implements autonomous stock discovery for paper trading.

    Features:
    - Market-wide stock screening
    - Sector-focused discovery
    - Event-driven discovery (earnings, news, etc.)
    - Claude-powered analysis
    - Watchlist management
    """

    def __init__(
        self,
        state_manager,
        perplexity_client: PerplexityClient,
        event_bus,
        config: Dict[str, Any]
    ):
        self.state_manager = state_manager
        self.perplexity = perplexity_client
        self.event_bus = event_bus
        self.config = config

        # Default discovery criteria
        self.default_criteria = {
            "min_market_cap": "small",  # small, mid, large, mega
            "max_market_cap": "mega",
            "exclude_penny_stocks": True,
            "min_price": 50.0,
            "max_price": 5000.0,
            "sectors": [],  # Empty means all sectors
            "liquidity_min": "medium"  # low, medium, high
        }

        self._running = False

    async def initialize(self) -> None:
        """Initialize the stock discovery service."""
        logger.info("Initializing Stock Discovery Service")

        # Note: Event subscriptions deferred until EventType enums are defined
        # For now, service can be triggered manually via API

        self._running = True
        logger.info("Stock Discovery Service initialized")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Note: Event subscriptions deferred until EventType enums are defined
        self._running = False
        logger.info("Stock Discovery Service cleaned up")

    async def run_discovery_session(
        self,
        session_type: str = "daily_screen",
        custom_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a stock discovery session.

        Args:
            session_type: Type of discovery session
            custom_criteria: Override default criteria

        Returns:
            Session results with discovered stocks
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting stock discovery session: {session_id}")

            # Create session record
            await self._create_discovery_session(session_id, session_type, custom_criteria)

            # Get discovery criteria
            criteria = {**self.default_criteria, **(custom_criteria or {})}

            # Step 1: Market-wide screening
            screened_stocks = await self._screen_market(criteria)

            # Step 2: Deep analysis of top candidates
            analyzed_stocks = await self._analyze_candidates(screened_stocks[:50], criteria)

            # Step 3: Score and rank stocks
            scored_stocks = await self._score_stocks(analyzed_stocks)

            # Step 4: Update watchlist with top candidates
            watchlist_updates = await self._update_watchlist(scored_stocks[:20])

            # Complete session
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            await self._complete_discovery_session(
                session_id,
                duration_ms,
                len(screened_stocks),
                len(analyzed_stocks),
                len([s for s in scored_stocks if s.get('score', 0) > 70])
            )

            return {
                "session_id": session_id,
                "session_type": session_type,
                "total_scanned": len(screened_stocks),
                "analyzed": len(analyzed_stocks),
                "high_potential": len([s for s in scored_stocks if s.get('score', 0) > 70]),
                "watchlist_updates": watchlist_updates,
                "top_candidates": scored_stocks[:10],
                "duration_ms": duration_ms,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Stock discovery session failed: {e}")
            await self._fail_discovery_session(session_id, str(e))
            raise TradingError(
                f"Stock discovery failed: {e}",
                category=ErrorCategory.ANALYSIS,
                severity=ErrorSeverity.HIGH
            )

    async def _screen_market(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Screen the market for potential stocks.

        This is a simplified implementation - in production, this would
        integrate with market data providers for comprehensive screening.
        """
        logger.info("Screening market for stocks")

        # For now, use a predefined list of NSE stocks
        # In production, this would fetch from market data API
        market_stocks = [
            {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy"},
            {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "Technology"},
            {"symbol": "HDFC", "name": "HDFC Bank", "sector": "Banking"},
            {"symbol": "INFY", "name": "Infosys", "sector": "Technology"},
            {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
            {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
            {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
            {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
            {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
            {"symbol": "WIPRO", "name": "Wipro", "sector": "Technology"},
            {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Banking"},
            {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Automobile"},
            {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financial Services"},
            {"symbol": "ASIANPAINT", "name": "Asian Paints", "sector": "Paints"},
            {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Energy"},
            {"symbol": "TITAN", "name": "Titan Company", "sector": "Luxury"},
            {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
            {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Cement"},
            {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories", "sector": "Pharma"},
            {"symbol": "ADANIPORTS", "name": "Adani Ports", "sector": "Logistics"},
            {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Automobile"},
            {"symbol": "GRASIM", "name": "Grasim Industries", "sector": "Textiles"},
            {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "Technology"},
            {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "Technology"},
            {"symbol": "NTPC", "name": "NTPC", "sector": "Energy"},
            {"symbol": "IOC", "name": "Indian Oil Corporation", "sector": "Energy"},
            {"symbol": "COALINDIA", "name": "Coal India", "sector": "Energy"},
            {"symbol": "BPCL", "name": "Bharat Petroleum", "sector": "Energy"},
            {"symbol": "ONGC", "name": "Oil and Natural Gas Corporation", "sector": "Energy"},
            {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "Steel"},
            {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Aluminium"},
            {"symbol": "ITC", "name": "ITC", "sector": "FMCG"},
            {"symbol": "DIVISLAB", "name": "Dr. Reddy's Laboratories", "sector": "Pharma"},
            {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp", "sector": "Automobile"},
            {"symbol": "M&M", "name": "Mahindra & Mahindra", "sector": "Automobile"},
            {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Automobile"},
            {"symbol": "DABUR", "name": "Dabur", "sector": "FMCG"},
            {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "Automobile"},
            {"symbol": "ZEEENT", "name": "Zee Entertainment", "sector": "Media"},
            {"symbol": "UBL", "name": "United Breweries", "sector": "Beverages"},
            {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "Chemicals"},
            {"symbol": "COFORGE", "name": "Coal India", "sector": "Energy"},
            {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking"},
            {"symbol": "GAIL", "name": "Gas Authority of India", "sector": "Energy"},
            {"symbol": "VODAFONE", "name": "Vodafone Idea", "sector": "Telecom"},
            {"symbol": "PFC", "name": "Power Finance Corporation", "sector": "Financial Services"},
            {"symbol": "RELIANCEPWR", "name": "Reliance Power", "sector": "Energy"},
            {"symbol": "JIOFINANCIAL", "name": "Jio Financial Services", "sector": "Financial Services"},
            {"symbol": "SIEMENS", "name": "Siemens", "sector": "Industrial"},
            {"symbol": "HAVELLS", "name": "Havells India", "sector": "Electrical Equipment"},
            {"symbol": "BERGEPAINT", "name": "Berger Paints", "sector": "Paints"},
            {"symbol": "MARUTI-SUZUKI", "name": "Maruti Suzuki", "sector": "Automobile"},
            {"symbol": "TATAMOTORS-DVR", "name": "Tata Motors DVR", "sector": "Automobile"},
            {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance", "sector": "Financial Services"},
            {"symbol": "GODREJCP", "name": "Godrej Consumer Products", "sector": "FMCG"},
            {"symbol": "ABBOTINDIA", "name": "Abbott India", "sector": "Pharma"},
            {"symbol": "GLENMARK", "name": "Glenmark Pharmaceuticals", "sector": "Pharma"},
            {"symbol": "LUPIN", "name": "Lupin", "sector": "Pharma"},
            {"symbol": "AUROPHARMA", "name": "Aurobindo Pharma", "sector": "Pharma"},
            {"symbol": "CIPLA", "name": "Cipla", "sector": "Pharma"},
            {"symbol": "DIVISLAB", "name": "Dr. Reddy's Laboratories", "sector": "Pharma"},
            {"symbol": "TORNTPOWER", "name": "Torrent Power", "sector": "Energy"},
            {"symbol": "NHPC", "name": "NHPC", "sector": "Energy"},
            {"symbol": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Energy"},
            {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Steel"},
            {"symbol": "JSWENERGY", "name": "JSW Energy", "sector": "Energy"},
            {"symbol": "JINDALSTEL", "name": "Jindal Steel & Power", "sector": "Steel"},
            {"symbol": "NMDC", "name": "NMDC", "sector": "Mining"},
            {"symbol": "COAL INDIA", "name": "Coal India", "sector": "Energy"},
        ]

        # Apply filters
        filtered_stocks = []
        for stock in market_stocks:
            # Skip if sector is excluded
            if criteria.get("sectors") and stock["sector"] not in criteria["sectors"]:
                continue

            # TODO: Add price and market cap filtering when market data is available

            filtered_stocks.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "sector": stock["sector"],
                "discovery_source": "market_screen",
                "screening_criteria": criteria
            })

        logger.info(f"Screened {len(market_stocks)} stocks, found {len(filtered_stocks)} candidates")
        return filtered_stocks

    async def _analyze_candidates(
        self,
        stocks: List[Dict[str, Any]],
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze candidate stocks using Perplexity API and Claude.
        """
        logger.info(f"Analyzing {len(stocks)} candidate stocks")

        analyzed_stocks = []

        # Process in batches to avoid overwhelming the API
        batch_size = 3
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]

            for stock in batch:
                try:
                    # Research with Perplexity
                    perplexity_research = await self._research_stock_perplexity(stock)

                    # Claude analysis
                    claude_analysis = await self._analyze_stock_claude(stock, perplexity_research)

                    analyzed_stock = {
                        **stock,
                        "perplexity_research": perplexity_research,
                        "claude_analysis": claude_analysis,
                        "research_timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    analyzed_stocks.append(analyzed_stock)

                except Exception as e:
                    logger.error(f"Failed to analyze stock {stock.get('symbol')}: {e}")
                    # Add with basic info only
                    analyzed_stocks.append({
                        **stock,
                        "analysis_error": str(e),
                        "research_timestamp": datetime.now(timezone.utc).isoformat()
                    })

        return analyzed_stocks

    async def _research_stock_perplexity(self, stock: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research a stock using Perplexity API.
        """
        try:
            symbol = stock["symbol"]
            queries = [
                f"Latest news and developments for {symbol} stock",
                f"{symbol} stock financial performance and quarterly results",
                f"Technical analysis and price targets for {symbol}",
                f"Analyst recommendations and ratings for {symbol} stock"
            ]

            research_results = []
            sources = []

            for query in queries:
                try:
                    response = await self.perplexity.query(query)
                    research_results.append({
                        "query": query,
                        "response": response.get("response", ""),
                        "sources": response.get("sources", [])
                    })
                    sources.extend(response.get("sources", []))
                except Exception as e:
                    logger.warning(f"Perplexity query failed for {symbol}: {e}")
                    research_results.append({
                        "query": query,
                        "error": str(e)
                    })

            return {
                "symbol": symbol,
                "research_queries": queries,
                "research_results": research_results,
                "sources": list(set(sources)),
                "research_timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Perplexity research failed for {stock.get('symbol')}: {e}")
            return {
                "symbol": stock.get("symbol"),
                "error": str(e),
                "research_timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _analyze_stock_claude(
        self,
        stock: Dict[str, Any],
        perplexity_research: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze stock using Claude Agent SDK.

        This would integrate with the existing Claude Agent SDK
        for comprehensive analysis.
        """
        # This is a placeholder - in production, this would use Claude Agent SDK
        # For now, return a basic analysis based on available data

        return {
            "symbol": stock["symbol"],
            "analysis_type": "basic",
            "recommendation": "HOLD",  # Would be determined by Claude
            "confidence": 0.5,
            "key_factors": [
                "Market position",
                "Sector trends",
                "Recent performance"
            ],
            "risks": [
                "Market volatility",
                "Sector risks"
            ],
            "opportunities": [
                "Growth potential",
                "Market leadership"
            ]
        }

    async def _score_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score and rank stocks based on analysis.
        """
        scored_stocks = []

        for stock in stocks:
            score = 0
            recommendation = "HOLD"

            # Simple scoring algorithm - in production, this would be more sophisticated
            if "claude_analysis" in stock:
                claude = stock["claude_analysis"]

                # Recommendation scoring
                rec_scores = {"STRONG_BUY": 90, "BUY": 75, "HOLD": 50, "AVOID": 25, "STRONG_AVOID": 10}
                score = rec_scores.get(claude.get("recommendation", "HOLD"), 50)
                recommendation = claude.get("recommendation", "HOLD")

                # Confidence adjustment
                confidence = claude.get("confidence", 0.5)
                score *= confidence

            scored_stocks.append({
                **stock,
                "score": score,
                "recommendation": recommendation,
                "scoring_timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Sort by score (descending)
        scored_stocks.sort(key=lambda x: x.get("score", 0), reverse=True)

        return scored_stocks

    async def get_watchlist(
        self,
        status: str = "ACTIVE",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get stocks from the discovery watchlist.

        Args:
            status: Filter by status (ACTIVE, ARCHIVED, etc.)
            limit: Maximum number of stocks to return

        Returns:
            List of watchlist stocks with their analysis data
        """
        try:
            watchlist = await self.state_manager.paper_trading.get_discovery_watchlist(
                status=status,
                limit=limit
            )
            logger.info(f"Retrieved {len(watchlist)} stocks from watchlist")
            return watchlist
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
            return []

    async def _update_watchlist(
        self,
        stocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update the watchlist with new discoveries.
        """
        updates = {"added": 0, "updated": 0, "skipped": 0}

        for stock in stocks:
            try:
                # Check if already in watchlist
                existing = await self.state_manager.paper_trading.get_discovery_watchlist_by_symbol(stock["symbol"])

                if existing:
                    # Update existing record
                    await self.state_manager.paper_trading.update_discovery_watchlist(
                        stock["symbol"],
                        {
                            "current_price": stock.get("current_price"),
                            "recommendation": stock.get("recommendation", "WATCH"),
                            "confidence_score": stock.get("score", 0) / 100,
                            "research_summary": json.dumps({
                                "perplexity": stock.get("perplexity_research"),
                                "claude": stock.get("claude_analysis")
                            }),
                            "last_analyzed": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    updates["updated"] += 1
                else:
                    # Add new record
                    await self.state_manager.paper_trading.add_to_discovery_watchlist({
                        "symbol": stock["symbol"],
                        "company_name": stock.get("name"),
                        "sector": stock.get("sector"),
                        "discovery_date": datetime.now(timezone.utc).date().isoformat(),
                        "discovery_source": stock.get("discovery_source", "autonomous"),
                        "discovery_reason": "Stock discovery analysis",
                        "current_price": stock.get("current_price"),
                        "recommendation": stock.get("recommendation", "WATCH"),
                        "confidence_score": stock.get("score", 0) / 100,
                        "research_summary": json.dumps({
                            "perplexity": stock.get("perplexity_research"),
                            "claude": stock.get("claude_analysis")
                        }),
                        "status": "ACTIVE",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    updates["added"] += 1

            except Exception as e:
                logger.error(f"Failed to update watchlist for {stock.get('symbol')}: {e}")
                updates["skipped"] += 1

        return updates

    async def _create_discovery_session(
        self,
        session_id: str,
        session_type: str,
        custom_criteria: Optional[Dict[str, Any]]
    ) -> None:
        """Create a discovery session record."""
        await self.state_manager.paper_trading.create_discovery_session({
            "id": session_id,
            "session_date": datetime.now(timezone.utc).date().isoformat(),
            "session_type": session_type,
            "screening_criteria": json.dumps(custom_criteria or self.default_criteria),
            "total_stocks_scanned": 0,
            "stocks_discovered": 0,
            "high_potential_stocks": 0,
            "session_status": "RUNNING",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    async def _complete_discovery_session(
        self,
        session_id: str,
        duration_ms: int,
        total_scanned: int,
        analyzed: int,
        high_potential: int
    ) -> None:
        """Complete a discovery session."""
        await self.state_manager.paper_trading.update_discovery_session(session_id, {
            "total_stocks_scanned": total_scanned,
            "stocks_discovered": analyzed,
            "high_potential_stocks": high_potential,
            "session_duration_ms": duration_ms,
            "session_status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

    async def _fail_discovery_session(self, session_id: str, error_message: str) -> None:
        """Mark a discovery session as failed."""
        await self.state_manager.paper_trading.update_discovery_session(session_id, {
            "session_status": "FAILED",
            "error_message": error_message,
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

    async def handle_event(self, event: Event) -> None:
        """Handle market events for reactive discovery."""
        if not self._running:
            return

        # Event-driven discovery temporarily disabled due to missing EventType enums
        # if event.type == EventType.MARKET_NEWS:
        #     # Trigger discovery if news is significant
        #     await self._handle_market_news_event(event)
        # elif event.type == EventType.MARKET_EARNINGS:  # Use existing enum
        #     # Research companies announcing earnings
        #     await self._handle_earnings_event(event)
        # elif event.type == EventType.SECTOR_UPDATE:  # TODO: Add this enum if needed
        #     # Screen sector for opportunities
        #     await self._handle_sector_event(event)

    async def _handle_market_news_event(self, event: Event) -> None:
        """Handle significant market news."""
        data = event.data
        if data.get("significance") == "high":
            # Trigger focused discovery on affected sectors
            pass

    async def _handle_earnings_event(self, event: Event) -> None:
        """Handle earnings announcements."""
        data = event.data
        symbol = data.get("symbol")
        if symbol:
            # Research the announcing company
            pass

    async def _handle_sector_event(self, event: Event) -> None:
        """Handle sector updates."""
        data = event.data
        sector = data.get("sector")
        if sector:
            # Screen sector for opportunities
            pass