"""
Earnings and Fundamentals Query Module for Perplexity API

Handles earnings announcements, financial fundamentals, and deep analysis queries.
"""

from typing import List, Optional, Any
from loguru import logger

from .perplexity_prompt_manager import PromptManager


class EarningsQueries:
    """Handles earnings and fundamental analysis queries to Perplexity API."""

    def __init__(
        self,
        api_caller: Any,
        prompt_manager: PromptManager,
    ):
        """Initialize earnings queries handler.

        Args:
            api_caller: Callable API handler (e.g., _call_perplexity_api)
            prompt_manager: PromptManager instance
        """
        self.api_caller = api_caller
        self.prompt_manager = prompt_manager

    async def fetch_earnings_fundamentals(
        self,
        symbols: List[str],
        max_tokens: int = 4000
    ) -> Optional[str]:
        """Fetch comprehensive earnings and financial fundamentals data.

        Requests detailed metrics needed for fundamental analysis including
        growth rates, profitability, valuation, and financial health.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with earnings and fundamentals data, or None on failure
        """
        prompt_template = await self.prompt_manager.get_prompt("earnings_processor")

        symbols_str = ", ".join(symbols)
        symbols_list = "\n".join([f"- {symbol}" for symbol in symbols])
        
        # Explicitly request structured JSON format matching our schema
        query = f"""You are a financial data analyst with access to comprehensive financial databases. 
Provide earnings and financial fundamentals data for ALL {len(symbols)} stocks listed below.

STOCKS TO ANALYZE ({len(symbols)} total):
{symbols_list}

{prompt_template}

SEARCH INSTRUCTIONS:
- Search for EACH stock individually using its ticker symbol and full company name
- Use stock exchanges (NSE, BSE for Indian stocks; NYSE, NASDAQ for US stocks)
- Search recent earnings announcements, quarterly reports, and financial statements
- Extract data from official company filings, press releases, and financial databases
- For Indian stocks, search NSE/BSE filings and company investor relations pages
- If data is available from news or analyst reports, extract the specific numbers mentioned

DATA EXTRACTION REQUIREMENTS:
- Extract ALL available metrics - do not skip fields just because some are missing
- Revenue: Extract from earnings reports (in actual currency units: rupees, dollars, etc.)
- EPS: Extract actual EPS numbers from quarterly results
- Margins: Extract gross margin, operating margin, net margin percentages
- Growth Rates: Calculate or extract YoY and QoQ growth percentages for revenue and profit
- Dates: Extract actual report dates and next earnings dates from announcements
- If a metric is mentioned in news or reports but not in official filings, use the reported value

CRITICAL REQUIREMENTS:
- MUST provide data for EVERY stock listed above ({len(symbols)} stocks total)
- If you cannot find data for a stock, search more broadly or use historical data
- Do NOT return empty objects {{}} - always include at least basic earnings information
- For each stock, you MUST include the "earnings" object with required fields

REQUIRED JSON STRUCTURE:
Return data in this EXACT structure:
{{
  "stocks": {{
    "SYMBOL1": {{
      "earnings": {{
        "latest_quarter": {{
          "period": "Q1 2024",
          "date": "2024-01-15",
          "eps_actual": 1.25,
          "eps_estimated": 1.20,
          "revenue_actual": 5000000000,
          "revenue_estimated": 4800000000,
          "eps": 1.25,
          "revenue": 5000000000
        }},
        "growth_rates": {{
          "eps_yoy_growth": 15.5,
          "eps_qoq_growth": 5.2,
          "revenue_yoy_growth": 12.3,
          "revenue_qoq_growth": 3.1
        }},
        "margins": {{
          "gross_margin": 45.2,
          "operating_margin": 25.8,
          "net_margin": 18.5,
          "outlook": "Positive guidance for next quarter"
        }},
        "next_earnings_date": "2024-04-15"
      }},
      "fundamentals": {{
        "valuation": {{}},
        "profitability": {{}},
        "financial_health": {{}},
        "growth": {{}}
      }},
      "analysis": {{
        "recommendation": "buy",
        "confidence_score": 0.85,
        "risk_level": "medium",
        "key_drivers": [],
        "risk_factors": []
      }}
    }},
    "SYMBOL2": {{ ... same structure ... }}
  }}
}}

CRITICAL INSTRUCTIONS:
- MUST return data for ALL {len(symbols)} stocks listed above
- DO NOT return empty objects {{}} for any stock - if data is limited, include at minimum:
  * "earnings" object with "latest_quarter" containing at least: period, date, eps_actual or eps_estimated
  * If actual earnings not available, provide estimated or most recent available data
- Each stock entry MUST have "earnings" object with at minimum:
  * "latest_quarter" object (required)
  * "growth_rates" object (can be empty {{}} if unavailable)
  * "margins" object (can be empty {{}} if unavailable)
  * "next_earnings_date" (string or null)
- Use exact stock symbols as keys in the "stocks" object (case-sensitive): {symbols_str}
- Search thoroughly for each stock - use alternative names, company names, or search broader if needed
- All numeric values should be actual numbers, not null or empty strings
- If a stock has no earnings history, search for company information and provide best available data"""

        # Log the query being sent
        logger.info("=" * 80)
        logger.info("PERPLEXITY QUERY (EARNINGS):")
        logger.info("=" * 80)
        logger.info(query)
        logger.info("=" * 80)

        response = await self.api_caller(
            query=query,
            search_recency="month",  # Increased from "week" to get more comprehensive data
            max_search_results=20,   # Increased from 15 to search more sources
            max_tokens=max_tokens,
            response_format="json"
        )
        
        # Log the response received
        if response:
            logger.info("=" * 80)
            logger.info("PERPLEXITY RESPONSE (EARNINGS):")
            logger.info("=" * 80)
            logger.info(f"Response length: {len(response)} chars")
            logger.info(f"FULL RESPONSE:\n{response}")
            logger.info("=" * 80)
        else:
            logger.warning("PERPLEXITY RESPONSE (EARNINGS): Empty response received")
        
        return response

    async def fetch_news_and_earnings(
        self,
        symbols: List[str],
        max_tokens: int = 4000
    ) -> Optional[str]:
        """Fetch both news and earnings data in a single query.

        Combines news and earnings processing to reduce API calls.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with combined news and earnings data
        """
        earnings_prompt = await self.prompt_manager.get_prompt("earnings_processor")
        news_prompt = await self.prompt_manager.get_prompt("news_processor")

        symbols_str = ", ".join(symbols)
        query = f"""For each stock ({symbols_str}), provide:

EARNINGS DATA:
{earnings_prompt}

NEWS DATA:
{news_prompt}

Format as JSON with 'earnings' and 'news' keys."""

        return await self.api_caller(
            query=query,
            search_recency="week",
            max_search_results=20,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_deep_fundamentals(
        self,
        symbols: List[str],
        max_tokens: int = 6000
    ) -> Optional[str]:
        """Fetch deep fundamental analysis for comprehensive evaluation.

        Provides extended analysis with additional metrics and comparisons.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response (higher for deep analysis)

        Returns:
            JSON string with deep fundamental analysis data
        """
        prompt_template = await self.prompt_manager.get_prompt("earnings_processor")

        symbols_str = ", ".join(symbols)
        query = f"""Provide DEEP FUNDAMENTAL ANALYSIS for stocks: {symbols_str}

{prompt_template}

ADDITIONAL ANALYSIS:
- Peer comparison metrics
- Historical trend analysis (last 3 years)
- Key catalysts and risk factors
- Industry positioning and competitive advantage
- Management quality assessment
- Dividend sustainability analysis
- Debt maturity schedule and refinancing risk"""

        return await self.api_caller(
            query=query,
            search_recency="month",
            max_search_results=25,
            max_tokens=max_tokens,
            response_format="json"
        )
