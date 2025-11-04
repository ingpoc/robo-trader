"""
Fundamental analysis data persistence layer.

Handles storing earnings fundamentals, market news, and deep fundamental
analysis data to the database.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import aiosqlite
from loguru import logger


class FundamentalStore:
    """Manages fundamental analysis data persistence to PostgreSQL."""

    def __init__(self, db_connection: aiosqlite.Connection):
        """Initialize store with database connection.

        Args:
            db_connection: Active aiosqlite connection
        """
        self.db = db_connection

    async def store_earnings_fundamentals(
        self, symbols: List[str], parsed_data: Dict[str, Any]
    ) -> bool:
        """Store comprehensive earnings data with fundamental metrics.

        Args:
            symbols: List of stock symbols
            parsed_data: Parsed earnings data from API

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Storing earnings fundamentals for {symbols}: {len(str(parsed_data))} chars of data")
            
            # Log the parsed_data structure for debugging
            if isinstance(parsed_data, dict):
                logger.debug(f"parsed_data keys: {list(parsed_data.keys())}")
                if "stocks" in parsed_data:
                    stocks_keys = list(parsed_data["stocks"].keys()) if isinstance(parsed_data["stocks"], dict) else "not a dict"
                    logger.debug(f"stocks keys: {stocks_keys}")
            else:
                logger.debug(f"parsed_data type: {type(parsed_data)}")
            
            now = datetime.now().isoformat()
            stored_count = 0

            # Perplexity API returns data in this format:
            # {
            #   "stocks": {
            #     "SYMBOL1": {
            #       "earnings": {...},
            #       "fundamentals": {...},
            #       "analysis": {...}
            #     }
            #   }
            # }
            
            # Extract stocks object from parsed_data
            stocks_data = parsed_data.get("stocks", {}) if isinstance(parsed_data, dict) else {}
            
            # If stocks is empty, try legacy format (earnings at top level)
            if not stocks_data and isinstance(parsed_data, dict):
                if "earnings" in parsed_data:
                    # Legacy format: earnings at top level, organized by symbol
                    stocks_data = parsed_data.get("earnings", {})
                    # If it's not organized by symbol, treat as single stock response
                    if isinstance(stocks_data, dict) and "latest_quarter" in stocks_data:
                        # Single stock format - create stocks structure
                        stocks_data = {symbols[0] if symbols else "UNKNOWN": {"earnings": stocks_data}}
                elif any(symbol in parsed_data for symbol in symbols):
                    # Data is directly organized by symbol keys
                    stocks_data = parsed_data
            
            logger.debug(f"Parsed stocks_data structure: {list(stocks_data.keys()) if isinstance(stocks_data, dict) else 'not a dict'}")
            
            for symbol in symbols:
                try:
                    # Try to get symbol-specific data from stocks structure
                    symbol_data = None
                    symbol_earnings = None
                    
                    if isinstance(stocks_data, dict):
                        # Check if symbol is a key in stocks (case-insensitive)
                        symbol_upper = symbol.upper()
                        for key, value in stocks_data.items():
                            if key.upper() == symbol_upper:
                                symbol_data = value
                                break
                        
                        # If not found, try symbol as-is
                        if not symbol_data and symbol in stocks_data:
                            symbol_data = stocks_data[symbol]
                    
                    # Extract earnings from symbol_data
                    if isinstance(symbol_data, dict):
                        # Check if symbol_data is empty (Perplexity returned empty object)
                        if len(symbol_data) == 0:
                            logger.warning(f"symbol_data for {symbol} is empty dict {{}} - Perplexity returned no data for this stock")
                            continue
                        
                        # Log symbol_data structure for debugging
                        logger.debug(f"symbol_data for {symbol}: keys={list(symbol_data.keys())}")
                        
                        # Check if earnings key exists (Perplexity format)
                        if "earnings" in symbol_data:
                            symbol_earnings = symbol_data["earnings"]
                            logger.debug(f"Found earnings key for {symbol}")
                        # Check if data is already earnings structure (has latest_quarter)
                        elif "latest_quarter" in symbol_data:
                            symbol_earnings = symbol_data
                            logger.debug(f"Found latest_quarter in symbol_data for {symbol}")
                        # If symbol_data itself looks like earnings data
                        elif any(key in symbol_data for key in ["eps_actual", "eps", "revenue", "revenue_actual"]):
                            symbol_earnings = symbol_data
                            logger.debug(f"Found earnings-like keys in symbol_data for {symbol}")
                        else:
                            # Log what's actually in symbol_data
                            logger.warning(f"symbol_data for {symbol} exists but has unexpected structure. Keys: {list(symbol_data.keys())}, Content: {str(symbol_data)[:300]}")
                    
                    if not symbol_earnings:
                        logger.warning(f"No earnings data found for {symbol} in parsed_data. Available keys in stocks_data: {list(stocks_data.keys()) if isinstance(stocks_data, dict) else 'N/A'}")
                        if symbol_data:
                            logger.info(f"symbol_data for {symbol} exists but has no earnings. Type: {type(symbol_data)}, Keys: {list(symbol_data.keys()) if isinstance(symbol_data, dict) else type(symbol_data)}, Content: {str(symbol_data)[:200]}")
                        else:
                            logger.info(f"symbol_data for {symbol} is None or empty")
                        continue

                    # Extract earnings metrics
                    latest_quarter = symbol_earnings.get("latest_quarter", {})
                    growth_rates = symbol_earnings.get("growth_rates", {})
                    margins = symbol_earnings.get("margins", {})

                    # Map to earnings_reports table schema
                    fiscal_period = latest_quarter.get("period", "Q1")
                    report_date = latest_quarter.get("date", datetime.now().date().isoformat())
                    
                    # Extract EPS and revenue - try multiple field names
                    eps_actual = (latest_quarter.get("eps_actual") or 
                                 latest_quarter.get("eps") or
                                 latest_quarter.get("earnings_per_share"))
                    eps_estimated = (latest_quarter.get("eps_estimated") or 
                                   latest_quarter.get("eps_estimate") or
                                   latest_quarter.get("eps_estimated_value"))
                    revenue_actual = (latest_quarter.get("revenue_actual") or 
                                     latest_quarter.get("revenue") or
                                     latest_quarter.get("total_revenue") or
                                     latest_quarter.get("sales") or
                                     latest_quarter.get("net_sales"))
                    revenue_estimated = (latest_quarter.get("revenue_estimated") or 
                                        latest_quarter.get("revenue_estimate") or
                                        latest_quarter.get("revenue_estimated_value"))
                    
                    # Calculate surprise percentage if both actual and estimated exist
                    surprise_pct = None
                    if eps_actual is not None and eps_estimated is not None and eps_estimated != 0:
                        surprise_pct = ((eps_actual - eps_estimated) / abs(eps_estimated)) * 100
                    
                    # Extract guidance and next earnings date - try multiple field names
                    guidance = (symbol_earnings.get("guidance") or 
                               margins.get("outlook") or
                               symbol_earnings.get("management_outlook") or
                               symbol_earnings.get("management_guidance") or
                               margins.get("management_outlook"))
                    next_earnings_date = (symbol_earnings.get("next_earnings_date") or
                                        symbol_earnings.get("next_earnings") or
                                        latest_quarter.get("next_earnings_date"))
                    
                    # Extract growth rates if available from growth_rates object
                    growth_rates = symbol_earnings.get("growth_rates", {})
                    if isinstance(growth_rates, dict):
                        # Try to get revenue growth from growth_rates if not already in margins
                        if not revenue_actual and growth_rates.get("revenue_yoy_growth"):
                            logger.debug(f"Found revenue_yoy_growth for {symbol}: {growth_rates.get('revenue_yoy_growth')}")
                    
                    # Extract margins - try multiple field names
                    if isinstance(margins, dict):
                        # Net margin might be in margins or profitability
                        net_margin = (margins.get("net_margin") or
                                    margins.get("net_profit_margin") or
                                    margins.get("profit_margin") or
                                    (isinstance(symbol_earnings.get("fundamentals", {}), dict) and 
                                     symbol_earnings.get("fundamentals", {}).get("profitability", {}).get("net_margin")) or
                                    None)
                        operating_margin = (margins.get("operating_margin") or
                                          margins.get("operating_profit_margin") or
                                          None)
                        gross_margin = (margins.get("gross_margin") or
                                      margins.get("gross_profit_margin") or
                                      None)

                    # Parse fiscal year and quarter from fiscal_period if possible
                    fiscal_year = None
                    fiscal_quarter = None
                    if isinstance(fiscal_period, str):
                        # Try to extract year from report_date or fiscal_period
                        try:
                            if report_date:
                                date_obj = datetime.fromisoformat(report_date.replace('Z', '+00:00'))
                                fiscal_year = date_obj.year
                                # Try to extract quarter from fiscal_period (e.g., "Q1 2024", "Q1", "2024-Q1")
                                if "Q" in fiscal_period.upper():
                                    quarter_match = re.search(r'Q([1-4])', fiscal_period.upper())
                                    if quarter_match:
                                        fiscal_quarter = int(quarter_match.group(1))
                        except (ValueError, AttributeError):
                            pass

                    # Insert or replace earnings report
                    query = """
                        INSERT OR REPLACE INTO earnings_reports
                        (symbol, fiscal_period, fiscal_year, fiscal_quarter, report_date,
                         eps_actual, eps_estimated, revenue_actual, revenue_estimated,
                         surprise_pct, guidance, next_earnings_date, fetched_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    await self.db.execute(
                        query,
                        (
                            symbol,
                            fiscal_period,
                            fiscal_year,
                            fiscal_quarter,
                            report_date,
                            eps_actual,
                            eps_estimated,
                            revenue_actual,
                            revenue_estimated,
                            surprise_pct,
                            guidance,
                            next_earnings_date,
                            now,
                            now
                        ),
                    )
                    
                    stored_count += 1
                    logger.info(f"Stored earnings data for {symbol}: {fiscal_period} on {report_date}")

                except Exception as e:
                    logger.error(f"Error storing earnings data for {symbol}: {e}")
                    continue

            await self.db.commit()
            logger.info(f"Stored earnings fundamentals for {stored_count}/{len(symbols)} symbols")
            return stored_count > 0

        except Exception as e:
            logger.error(f"Error storing earnings fundamentals: {e}")
            await self.db.rollback()
            return False

    async def store_market_news(self, news_items: List[Dict[str, Any]]) -> bool:
        """Store categorized market news with sentiment analysis.

        Args:
            news_items: List of news items with metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now().isoformat()
            stored_count = 0

            for item in news_items:
                # Map to news_items table schema (not news_feed)
                symbol = item.get("symbol", "")
                title = item.get("headline") or item.get("title", "")
                summary = item.get("content") or item.get("summary", "")
                content = item.get("content", summary)  # Use content if available, fallback to summary
                source = item.get("source", "Perplexity")
                sentiment = item.get("sentiment", "neutral")
                relevance_score = item.get("relevance_score") or item.get("impact_score", 0.5)
                published_at = item.get("published_at") or now
                
                # Extract key_points if available (might be in different fields)
                key_points = item.get("key_points", [])
                citations = item.get("citations", key_points)  # Use key_points as citations if no citations
                
                query = """
                    INSERT OR REPLACE INTO news_items
                    (symbol, title, summary, content, source, sentiment, relevance_score,
                     published_at, fetched_at, citations, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                citations_json = json.dumps(citations) if citations else None

                await self.db.execute(
                    query,
                    (
                        symbol,
                        title,
                        summary,
                        content,
                        source,
                        sentiment,
                        relevance_score,
                        published_at,
                        now,
                        citations_json,
                        now
                    ),
                )
                stored_count += 1
                logger.debug(f"Stored news item for {symbol}: {title[:50]}...")

            await self.db.commit()
            logger.info(f"Stored {stored_count}/{len(news_items)} news items to news_items table")
            return stored_count > 0

        except Exception as e:
            logger.error(f"Error storing news: {e}")
            await self.db.rollback()
            return False

    async def store_deep_fundamentals(
        self, symbols: List[str], analysis_data: Dict[str, Any]
    ) -> bool:
        """Store comprehensive deep fundamental analysis data.

        Args:
            symbols: List of stock symbols
            analysis_data: Deep fundamental analysis from API

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Storing deep fundamentals for {symbols}: {len(str(analysis_data))} chars of data")

            for symbol in symbols:
                query = """
                    INSERT INTO fundamental_analysis (
                        symbol, analysis_date, pe_ratio, pb_ratio, roe, roa,
                        debt_to_equity, current_ratio, profit_margins,
                        revenue_growth, earnings_growth, dividend_yield,
                        market_cap, sector_pe, industry_rank, overall_score,
                        recommendation, analysis_data, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, analysis_date) DO UPDATE SET
                    pe_ratio = excluded.pe_ratio,
                    overall_score = excluded.overall_score,
                    recommendation = excluded.recommendation,
                    analysis_data = excluded.analysis_data,
                    updated_at = excluded.updated_at
                """

                now = datetime.now().isoformat()
                analysis_data_json = json.dumps(analysis_data)

                await self.db.execute(
                    query,
                    (
                        symbol,
                        datetime.now().date(),
                        analysis_data.get("pe_ratio"),
                        analysis_data.get("pb_ratio"),
                        analysis_data.get("roe"),
                        analysis_data.get("roa"),
                        analysis_data.get("debt_to_equity"),
                        analysis_data.get("current_ratio"),
                        analysis_data.get("profit_margins"),
                        analysis_data.get("revenue_growth"),
                        analysis_data.get("earnings_growth"),
                        analysis_data.get("dividend_yield"),
                        analysis_data.get("market_cap"),
                        analysis_data.get("sector_pe"),
                        analysis_data.get("industry_rank"),
                        analysis_data.get("overall_score"),
                        analysis_data.get("recommendation"),
                        analysis_data_json,
                        now,
                        now,
                    ),
                )

            await self.db.commit()
            logger.info(f"Stored deep fundamentals for {len(symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"Error storing deep fundamentals: {e}")
            await self.db.rollback()
            return False

    async def get_latest_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve latest fundamental metrics for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Fundamental metrics dict or None
        """
        try:
            query = """
                SELECT * FROM fundamental_metrics
                WHERE symbol = ?
                ORDER BY analysis_date DESC
                LIMIT 1
            """

            cursor = await self.db.execute(query, (symbol,))
            row = await cursor.fetchone()

            if row:
                return dict(row)

            return None

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {symbol}: {e}")
            return None
