"""
Perplexity Prompt Management Module

Handles database-backed prompt fetching with fallback to hardcoded prompts.
Includes caching to avoid repeated database calls.
"""

from typing import Dict, Optional, Any
from loguru import logger


class PromptManager:
    """Manages prompts for Perplexity queries with database and fallback support."""

    def __init__(self, configuration_state: Optional[Any] = None):
        """Initialize prompt manager.

        Args:
            configuration_state: ConfigurationState instance for database access
        """
        self.configuration_state = configuration_state
        self._prompt_cache: Dict[str, str] = {}

    async def get_prompt(self, prompt_name: str) -> str:
        """Get prompt content from database with fallback to hardcoded prompts.

        Args:
            prompt_name: Name of the prompt to retrieve

        Returns:
            Prompt content string
        """
        # Check cache first
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]

        # Try to fetch from database
        if self.configuration_state:
            try:
                prompt_data = await self.configuration_state.get_prompt_config(prompt_name)
                if prompt_data and prompt_data.get('content'):
                    self._prompt_cache[prompt_name] = prompt_data['content']
                    logger.info(f"Using database prompt for {prompt_name}")
                    return prompt_data['content']
            except Exception as e:
                logger.warning(f"Failed to fetch prompt {prompt_name} from database: {e}")

        # Fallback to hardcoded prompts
        logger.info(f"Using hardcoded fallback prompt for {prompt_name}")
        fallback_prompt = self._get_fallback_prompt(prompt_name)
        self._prompt_cache[prompt_name] = fallback_prompt
        return fallback_prompt

    @staticmethod
    def _get_fallback_prompt(prompt_name: str) -> str:
        """Get hardcoded fallback prompt for when database is unavailable.

        Args:
            prompt_name: Name of the prompt

        Returns:
            Hardcoded prompt content
        """
        prompts = {
            "earnings_processor": """For each stock, provide DETAILED earnings and financial fundamentals data in JSON format.

EARNINGS DATA (required):
- Latest quarterly earnings report date and fiscal period
- EPS (Actual vs Estimated): include exact numbers
- Revenue (Actual vs Estimated): include exact numbers in millions/billions
- EPS Surprise percentage
- Management guidance and outlook
- Next earnings date
- Year-over-year earnings growth rate (%)
- Quarter-over-quarter earnings growth rate (%)
- Net profit margins (gross, operating, net %)
- Revenue growth rate (YoY and QoQ %)

FUNDAMENTAL METRICS (required):
- Net profit growth trend (last 3-4 quarters with percentages)
- Current quarter profit growth vs prior quarter (%)
- Debt-to-Equity ratio
- Return on Equity (ROE %)
- Profit margins: Gross %, Operating %, Net %
- Return on Assets (ROA %)""",

            "news_processor": """For each stock, provide recent market-moving news in JSON format.

NEWS DATA (required for each item):
- News title
- News summary (2-3 sentences)
- Full content/detailed analysis
- News source and exact publication date
- Type: (earnings_announcement, product_launch, regulatory, merger, guidance, dividend, stock_split, bankruptcy, restructuring, industry_trend, analyst_rating_change, contract_win, other)
- Sentiment: (positive, negative, neutral)
- Impact level: (high, medium, low) on stock price
- Relevance to stock price: (direct_impact, indirect_impact, contextual)
- Key metrics mentioned: list any financial metrics, growth rates, or numbers mentioned
- Why this is important: brief explanation of significance

SPECIFIC FOCUS (priority order):
1. Earnings announcements or reports from last 7 days with beat/miss info
2. Analyst upgrades/downgrades/rating changes from last 7 days
3. Major product launches, approvals, or announcements
4. Regulatory approvals, challenges, or compliance issues
5. M&A activity (acquisitions, mergers, divestitures)
6. Dividend announcements or changes
7. Major contract wins or losses
8. Industry trends affecting multiple companies in sector
9. Market analyst commentary and price targets""",

            "fundamental_analyzer": """Analyze fundamental data and provide comprehensive financial analysis in JSON format.

ANALYSIS REQUIREMENTS:
- Company financial health assessment
- Growth trajectory evaluation
- Valuation analysis with industry comparisons
- Risk assessment and investment recommendations
- Key financial ratios and metrics interpretation
- Future outlook based on current fundamentals""",
        }

        return prompts.get(prompt_name, f"Provide analysis for {prompt_name}.")

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._prompt_cache.clear()
        logger.info("Prompt cache cleared")
