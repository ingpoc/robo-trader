"""
Claude Analyzer for Recommendation Engine

Handles AI-powered analysis using Claude Agent SDK:
- Qualitative analysis
- Reasoning generation
- Target price calculations
- Alternative suggestions
"""

import logging
from typing import Dict, Any, Optional
import json

from loguru import logger
from claude_agent_sdk import ClaudeAgentOptions

from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout
from .models import RecommendationFactors

logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    """AI-powered analysis using Claude Agent SDK."""

    def __init__(self, config: Dict[str, Any], kite_service=None):
        self.config = config
        self.client_manager = None
        self.kite_service = kite_service  # Injected for real-time price fetching
        self.claude_model = config.get('claude_model', 'claude-3-5-sonnet-20241022')
        self.claude_temperature = config.get('temperature', 0.3)
        self.claude_options = ClaudeAgentOptions(
            allowed_tools=[],  # No tools needed for analysis
            system_prompt="You are an expert financial analyst providing detailed stock recommendations.",
            max_turns=10
        )
        logger.info("Claude Agent SDK integration configured for recommendation engine")

    async def initialize(self) -> None:
        """Initialize Claude SDK client."""
        try:
            self.client_manager = await ClaudeSDKClientManager.get_instance()
            logger.info("Claude analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Claude analyzer: {e}")
            raise

    async def get_claude_recommendation_analysis(
        self,
        symbol: str,
        factors: RecommendationFactors,
        current_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI-powered recommendation analysis from Claude.

        Args:
            symbol: Stock symbol
            factors: Calculated recommendation factors
            current_price: Current market price (optional)

        Returns:
            Dictionary with analysis results or None if Claude unavailable
        """
        try:
            if not self.client_manager:
                await self.initialize()

            client = await self.client_manager.get_client("trading", self.claude_options)

            # Build the analysis prompt
            prompt = self._build_claude_analysis_prompt(symbol, factors, current_price)

            # Query Claude with timeout protection
            response_text = await query_with_timeout(
                client,
                prompt,
                timeout=30.0  # 30 second timeout
            )

            # Parse Claude's response
            analysis = self._parse_claude_response(response_text)

            return analysis

        except Exception as e:
            logger.error(f"Error getting Claude analysis for {symbol}: {e}")
            return None

    def _build_claude_analysis_prompt(
        self,
        symbol: str,
        factors: RecommendationFactors,
        current_price: Optional[float] = None
    ) -> str:
        """Build comprehensive analysis prompt for Claude."""
        factors_dict = factors.to_dict()

        prompt = f"""Please provide a detailed investment analysis for {symbol} based on the following scoring factors:

FACTOR SCORES (0-100 scale):
- Fundamental Score: {factors_dict.get('fundamental_score', 'N/A')}
- Valuation Score: {factors_dict.get('valuation_score', 'N/A')}
- Growth Score: {factors_dict.get('growth_score', 'N/A')}
- Risk Score: {factors_dict.get('risk_score', 'N/A')} (Higher = Lower Risk)
- Qualitative Score: {factors_dict.get('qualitative_score', 'N/A')}

CURRENT MARKET DATA:
{f"- Current Price: ${current_price}" if current_price else "- Current Price: Not available"}

Please provide your analysis in JSON format with the following structure:
{{
    "qualitative_assessment": "Your qualitative assessment of the stock",
    "reasoning": "Detailed reasoning for your recommendation",
    "target_price": {{
        "bull_case": price_for_optimistic_scenario,
        "base_case": price_for_realistic_scenario,
        "bear_case": price_for_pessimistic_scenario
    }},
    "stop_loss": {{
        "tight": stop_loss_for_conervative_investors,
        "moderate": stop_loss_for_moderate_investors,
        "wide": stop_loss_for_long_term_investors
    }},
    "key_risks": ["risk1", "risk2", "risk3"],
    "catalysts": ["positive_catalyst1", "positive_catalyst2"],
    "alternative_scenarios": {{
        "if_growth_accelerates": "recommendation_change",
        "if_risk_factors_increase": "recommendation_change",
        "if_market_conditions_worsen": "recommendation_change"
    }},
    "time_horizon_analysis": {{
        "short_term": "outlook_3_6_months",
        "medium_term": "outlook_1_2_years",
        "long_term": "outlook_3_plus_years"
    }}
}}

Focus on:
1. Quality of the business model and competitive advantages
2. Management effectiveness and strategy
3. Industry trends and positioning
4. Financial health beyond the quantitative scores
5. Potential risks that might not be captured in the scores
6. Catalysts that could drive the stock higher

Please be thorough but concise. Your analysis will be used to generate final investment recommendations."""

        return prompt

    def _parse_claude_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Claude's response into structured format."""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                analysis = json.loads(json_text)
                return analysis
            else:
                # If no JSON found, create basic analysis from text
                return {
                    "qualitative_assessment": response_text[:500],
                    "reasoning": response_text[:1000],
                    "target_price": None,
                    "stop_loss": None,
                    "key_risks": [],
                    "catalysts": [],
                    "alternative_scenarios": {},
                    "time_horizon_analysis": {}
                }

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Claude JSON response: {e}")
            # Return basic analysis from text
            return {
                "qualitative_assessment": response_text[:500],
                "reasoning": response_text[:1000],
                "target_price": None,
                "stop_loss": None,
                "key_risks": [],
                "catalysts": [],
                "alternative_scenarios": {},
                "time_horizon_analysis": {}
            }

        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            return None

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol from Zerodha via KiteConnectService."""
        try:
            if not self.kite_service:
                logger.warning(f"KiteConnectService not available for price lookup: {symbol}")
                return None

            price = await self.kite_service.get_current_price(symbol)
            if price:
                logger.debug(f"Got current price for {symbol}: {price}")
            return price

        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None