"""
Data Gatherer for Portfolio Intelligence

Handles:
- Stock selection (stocks with recent updates)
- Data gathering (earnings, news, fundamentals)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PortfolioDataGatherer:
    """Gathers data for portfolio intelligence analysis."""

    def __init__(self, state_manager, config_state):
        self.state_manager = state_manager
        self.config_state = config_state

    async def get_stocks_with_updates(self) -> List[str]:
        """Get stocks from portfolio that have recent updates (earnings, news, fundamentals)."""
        try:
            # Get portfolio holdings
            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.warning("No portfolio holdings found")
                return []

            portfolio_symbols = [
                holding.get("symbol")
                for holding in portfolio.holdings
                if holding.get("symbol")
            ]

            if not portfolio_symbols:
                return []

            # Get stock state store
            stock_state_store = self.state_manager.get_stock_state_store()
            await stock_state_store.initialize()

            # Find stocks with recent updates (within last 7 days)
            stocks_with_updates = []
            cutoff_date = date.today() - timedelta(days=7)

            for symbol in portfolio_symbols:
                state = await stock_state_store.get_state(symbol)

                # Check if any data type was updated recently
                # Convert date strings to date objects if needed
                news_check_date = self._parse_date(state.last_news_check)
                earnings_check_date = self._parse_date(state.last_earnings_check)
                fundamentals_check_date = self._parse_date(
                    state.last_fundamentals_check
                )

                has_recent_news = (
                    news_check_date
                    and isinstance(news_check_date, date)
                    and news_check_date >= cutoff_date
                )
                has_recent_earnings = (
                    earnings_check_date
                    and isinstance(earnings_check_date, date)
                    and earnings_check_date >= cutoff_date
                )
                has_recent_fundamentals = (
                    fundamentals_check_date
                    and isinstance(fundamentals_check_date, date)
                    and fundamentals_check_date >= cutoff_date
                )

                if has_recent_news or has_recent_earnings or has_recent_fundamentals:
                    stocks_with_updates.append(symbol)

            # If no stocks with recent updates, return stocks that need updates (oldest first)
            if not stocks_with_updates:
                logger.info("No stocks with recent updates, selecting oldest stocks")
                news_stocks = await stock_state_store.get_oldest_news_stocks(
                    portfolio_symbols, limit=5
                )
                earnings_stocks = await stock_state_store.get_oldest_earnings_stocks(
                    portfolio_symbols, limit=5
                )
                fundamentals_stocks = (
                    await stock_state_store.get_oldest_fundamentals_stocks(
                        portfolio_symbols, limit=5
                    )
                )
                stocks_with_updates = list(
                    set(news_stocks + earnings_stocks + fundamentals_stocks)
                )[:10]

            logger.info(
                f"Cutoff date: {cutoff_date}, Found {len(stocks_with_updates)} stocks with updates: {stocks_with_updates}"
            )

            # Add debug info for first few stocks
            if portfolio_symbols:
                sample_symbol = portfolio_symbols[0]
                sample_state = await stock_state_store.get_state(sample_symbol)
                logger.info(
                    f"Sample stock {sample_symbol}: news={sample_state.last_news_check}, earnings={sample_state.last_earnings_check}, fundamentals={sample_state.last_fundamentals_check}"
                )

            return stocks_with_updates

        except Exception as e:
            logger.error(f"Error getting stocks with updates: {e}", exc_info=True)
            return []

    async def gather_stocks_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Gather all available data (earnings, news, fundamentals) for each stock."""
        stocks_data = {}

        for symbol in symbols:
            try:
                # Get earnings data
                earnings = await self.state_manager.get_earnings_for_symbol(
                    symbol, limit=5
                )

                # Get news data
                news = await self.state_manager.get_news_for_symbol(symbol, limit=10)

                # Get fundamental analysis (if available)
                fundamental_analysis = (
                    await self.state_manager.get_fundamental_analysis(symbol, limit=1)
                )

                # Get stock state (last check dates)
                stock_state_store = self.state_manager.get_stock_state_store()
                await stock_state_store.initialize()
                state = await stock_state_store.get_state(symbol)

                stocks_data[symbol] = {
                    "symbol": symbol,
                    "earnings": earnings,
                    "news": news,
                    "fundamental_analysis": [
                        fa.to_dict() if hasattr(fa, "to_dict") else fa
                        for fa in fundamental_analysis
                    ],
                    "last_news_check": (
                        state.last_news_check.isoformat()
                        if state.last_news_check
                        and hasattr(state.last_news_check, "isoformat")
                        else (
                            str(state.last_news_check)
                            if state.last_news_check
                            else None
                        )
                    ),
                    "last_earnings_check": (
                        state.last_earnings_check.isoformat()
                        if state.last_earnings_check
                        and hasattr(state.last_earnings_check, "isoformat")
                        else (
                            str(state.last_earnings_check)
                            if state.last_earnings_check
                            else None
                        )
                    ),
                    "last_fundamentals_check": (
                        state.last_fundamentals_check.isoformat()
                        if state.last_fundamentals_check
                        and hasattr(state.last_fundamentals_check, "isoformat")
                        else (
                            str(state.last_fundamentals_check)
                            if state.last_fundamentals_check
                            else None
                        )
                    ),
                    "data_summary": {
                        "earnings_count": len(earnings),
                        "news_count": len(news),
                        "fundamental_count": len(fundamental_analysis),
                    },
                }

            except Exception as e:
                logger.error(f"Error gathering data for {symbol}: {e}")
                stocks_data[symbol] = {
                    "symbol": symbol,
                    "error": str(e),
                    "data_summary": {
                        "earnings_count": 0,
                        "news_count": 0,
                        "fundamental_count": 0,
                    },
                }

        return stocks_data

    def _parse_date(self, date_value):
        """Parse date string to date object."""
        if isinstance(date_value, str):
            try:
                # Handle YYYY-MM-DD format from database
                if len(date_value) == 10 and date_value.count("-") == 2:
                    return datetime.strptime(date_value, "%Y-%m-%d").date()
                else:
                    # Handle ISO datetime format with timezone
                    return datetime.fromisoformat(
                        date_value.replace("Z", "+00:00")
                    ).date()
            except (ValueError, AttributeError):
                return None
        return date_value
