"""
Recommendation Engine Service

AI-powered trading recommendation system that combines multiple analysis factors
with Claude Agent SDK for intelligent reasoning and actionable BUY/SELL/HOLD recommendations.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json

from loguru import logger
from claude_agent_sdk import tool, ClaudeSDKClient, ClaudeAgentOptions

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import (
    FundamentalAnalysis,
    Recommendation,
    RiskDecision,
    AnalysisPerformance
)
from ..services.fundamental_service import FundamentalService
from ..services.risk_service import RiskService
from ..core.perplexity_client import PerplexityClient, QueryType


@dataclass
class RecommendationFactors:
    """Individual scoring factors for recommendation calculation."""
    fundamental_score: Optional[float] = None
    valuation_score: Optional[float] = None
    growth_score: Optional[float] = None
    risk_score: Optional[float] = None
    qualitative_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class RecommendationResult:
    """Complete recommendation result with all factors and metadata."""
    symbol: str
    recommendation_type: str  # BUY, HOLD, SELL
    confidence_level: str  # HIGH, MEDIUM, LOW
    overall_score: float
    factors: RecommendationFactors
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    reasoning: str = ""
    risk_level: str = "MEDIUM"
    time_horizon: str = "MEDIUM_TERM"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['factors'] = self.factors.to_dict()
        return data


class RecommendationEngine:
    """
    Advanced recommendation engine that combines multiple analysis factors.

    Features:
    - Weighted multi-factor scoring system
    - Dynamic threshold-based recommendations
    - Confidence level assessment
    - Risk-adjusted target pricing
    - Performance tracking integration
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager,
        fundamental_service: FundamentalService,
        risk_service: RiskService
    ):
        self.config = config
        self.state_manager = state_manager
        self.fundamental_service = fundamental_service
        self.risk_service = risk_service

        # Initialize Claude Agent SDK for AI-powered analysis
        reco_config = getattr(config, 'recommendation_engine', {})
        claude_config = {
            'model': reco_config.get('claude_model', 'claude-3-5-sonnet-20241022'),
            'api_timeout_seconds': 30,
            'max_tokens': 2000,
            'temperature': 0.3  # Lower temperature for more consistent analysis
        }

        # Initialize Claude Agent SDK client (no direct API keys needed)
        # SDK handles authentication automatically via CLI
        self.claude_client = None  # Will be initialized on first use
        self.claude_model = claude_config['model']
        self.claude_temperature = claude_config['temperature']
        self.claude_options = ClaudeAgentOptions(
            allowed_tools=[],  # No tools needed for analysis
            system_prompt="You are an expert financial analyst providing detailed stock recommendations.",
            max_turns=10
        )
        logger.info("Claude Agent SDK integration configured for recommendation engine")

        # Load recommendation engine configuration
        self.reco_config = getattr(config, 'recommendation_engine', {})
        self.scoring_weights = self.reco_config.get('scoring_weights', {
            "fundamental_score": 0.35,
            "valuation_score": 0.25,
            "growth_score": 0.20,
            "risk_score": 0.15,
            "qualitative_score": 0.05
        })

        self.thresholds = self.reco_config.get('thresholds', {
            "buy": {"min_overall": 75, "min_fundamental": 70, "max_risk": 30, "min_growth": 65},
            "hold": {"min_overall": 45, "max_overall": 74},
            "sell": {"max_overall": 44, "max_fundamental": 40, "min_risk": 70}
        })

        self.confidence_levels = self.reco_config.get('confidence_levels', {
            "high": {"min_score": 80, "max_score": 100},
            "medium": {"min_score": 60, "max_score": 79},
            "low": {"min_score": 40, "max_score": 59}
        })

        logger.info("Recommendation engine initialized with configuration")

    async def generate_recommendation(
        self,
        symbol: str,
        force_refresh: bool = False
    ) -> Optional[RecommendationResult]:
        """
        Generate comprehensive recommendation for a symbol using AI-powered analysis.

        Args:
            symbol: Stock symbol to analyze
            force_refresh: Force refresh of underlying analysis data

        Returns:
            RecommendationResult with complete analysis or None if insufficient data
        """
        try:
            logger.info(f"Generating AI-powered recommendation for {symbol}")

            # Gather all analysis factors
            factors = await self._gather_analysis_factors(symbol, force_refresh)

            if not factors:
                logger.warning(f"Insufficient data to generate recommendation for {symbol}")
                return None

            # Use Claude for intelligent analysis if available
            if self.claude_client:
                claude_analysis = await self._get_claude_recommendation_analysis(symbol, factors)
                if claude_analysis:
                    # Override with Claude's analysis
                    recommendation_type = claude_analysis.get('recommendation', 'HOLD')
                    confidence_level = claude_analysis.get('confidence', 'MEDIUM')
                    reasoning = claude_analysis.get('reasoning', 'AI-powered analysis')
                    target_price = claude_analysis.get('target_price')
                    stop_loss = claude_analysis.get('stop_loss')
                    risk_level = claude_analysis.get('risk_level', 'MEDIUM')
                    time_horizon = claude_analysis.get('time_horizon', 'MEDIUM_TERM')

                    # Still calculate overall score for consistency
                    overall_score = self._calculate_weighted_score(factors)

                    result = RecommendationResult(
                        symbol=symbol,
                        recommendation_type=recommendation_type,
                        confidence_level=confidence_level,
                        overall_score=round(overall_score, 2),
                        factors=factors,
                        target_price=target_price,
                        stop_loss=stop_loss,
                        reasoning=reasoning,
                        risk_level=risk_level,
                        time_horizon=time_horizon
                    )
                else:
                    # Fallback to rule-based analysis
                    result = await self._generate_rule_based_recommendation(symbol, factors)
            else:
                # Rule-based analysis only
                result = await self._generate_rule_based_recommendation(symbol, factors)

            logger.info(f"Generated {result.recommendation_type} recommendation for {symbol} (score: {result.overall_score:.1f}, confidence: {result.confidence_level})")
            return result

        except Exception as e:
            logger.error(f"Failed to generate recommendation for {symbol}: {e}")
            return None

    async def _generate_rule_based_recommendation(
        self,
        symbol: str,
        factors: RecommendationFactors
    ) -> RecommendationResult:
        """Generate recommendation using rule-based analysis (fallback method)."""
        # Calculate weighted overall score
        overall_score = self._calculate_weighted_score(factors)

        # Determine recommendation type based on thresholds
        recommendation_type = self._determine_recommendation_type(factors, overall_score)

        # Calculate confidence level
        confidence_level = self._calculate_confidence_level(overall_score)

        # Generate target prices and stop losses
        target_price, stop_loss = await self._calculate_target_prices(symbol, recommendation_type, factors)

        # Build reasoning
        reasoning = self._build_reasoning(factors, overall_score, recommendation_type)

        # Assess risk level and time horizon
        risk_level = self._assess_risk_level(factors)
        time_horizon = self._determine_time_horizon(factors, recommendation_type)

        return RecommendationResult(
            symbol=symbol,
            recommendation_type=recommendation_type,
            confidence_level=confidence_level,
            overall_score=round(overall_score, 2),
            factors=factors,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            risk_level=risk_level,
            time_horizon=time_horizon
        )

    async def generate_bulk_recommendations(
        self,
        symbols: List[str],
        force_refresh: bool = False
    ) -> Dict[str, RecommendationResult]:
        """
        Generate recommendations for multiple symbols concurrently.

        Args:
            symbols: List of stock symbols
            force_refresh: Force refresh of underlying data

        Returns:
            Dictionary mapping symbols to recommendation results
        """
        if not symbols:
            return {}

        logger.info(f"Generating bulk recommendations for {len(symbols)} symbols")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(5)  # Limit concurrent recommendations

        async def generate_with_semaphore(symbol: str) -> Tuple[str, Optional[RecommendationResult]]:
            async with semaphore:
                result = await self.generate_recommendation(symbol, force_refresh)
                return symbol, result

        # Generate recommendations concurrently
        tasks = [generate_with_semaphore(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        recommendations = {}
        successful = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Bulk recommendation task failed: {result}")
                continue

            symbol, recommendation = result
            if recommendation:
                recommendations[symbol] = recommendation
                successful += 1

        logger.info(f"Bulk recommendations completed: {successful}/{len(symbols)} successful")
        return recommendations

    async def store_recommendation(self, result: RecommendationResult) -> Optional[int]:
        """
        Store recommendation in database and track performance.

        Args:
            result: Recommendation result to store

        Returns:
            Recommendation ID if stored successfully, None otherwise
        """
        try:
            # Convert to Recommendation model
            recommendation = Recommendation(
                symbol=result.symbol,
                recommendation_type=result.recommendation_type,
                confidence_score=self._confidence_to_score(result.confidence_level),
                target_price=result.target_price,
                stop_loss=result.stop_loss,
                reasoning=result.reasoning,
                analysis_type="COMPREHENSIVE",
                time_horizon=result.time_horizon,
                risk_level=result.risk_level,
                potential_impact=self._calculate_potential_impact(result),
                alternative_suggestions=self._generate_alternatives(result)
            )

            # Store in database
            recommendation_id = await self.state_manager.save_recommendation(recommendation)

            # Create performance tracking entry
            await self._create_performance_entry(result, recommendation_id)

            logger.info(f"Stored recommendation for {result.symbol} (ID: {recommendation_id})")
            return recommendation_id

        except Exception as e:
            logger.error(f"Failed to store recommendation for {result.symbol}: {e}")
            return None

    async def get_recommendation_history(
        self,
        symbol: str,
        limit: int = 10
    ) -> List[Recommendation]:
        """
        Get recommendation history for a symbol.

        Args:
            symbol: Stock symbol
            limit: Maximum number of recommendations to return

        Returns:
            List of historical recommendations
        """
        try:
            return await self.state_manager.get_recommendations(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to get recommendation history for {symbol}: {e}")
            return []

    async def _gather_analysis_factors(
        self,
        symbol: str,
        force_refresh: bool = False
    ) -> Optional[RecommendationFactors]:
        """Gather all analysis factors for recommendation calculation."""
        factors = RecommendationFactors()

        try:
            # Get fundamental analysis
            fundamental_data = await self.fundamental_service.fetch_fundamentals_batch([symbol], force_refresh)
            if symbol in fundamental_data:
                factors.fundamental_score = fundamental_data[symbol].overall_score

            # Calculate valuation score
            factors.valuation_score = await self._calculate_valuation_score(symbol, fundamental_data.get(symbol))

            # Calculate growth score
            factors.growth_score = await self._calculate_growth_score(symbol, fundamental_data.get(symbol))

            # Get risk score from risk service
            factors.risk_score = await self._calculate_risk_score(symbol)

            # Calculate qualitative score
            factors.qualitative_score = await self._calculate_qualitative_score(symbol)

            # Check if we have minimum required factors
            required_factors = [factors.fundamental_score, factors.valuation_score, factors.growth_score]
            if not any(required_factors):
                logger.warning(f"Insufficient analysis factors for {symbol}")
                return None

            return factors

        except Exception as e:
            logger.error(f"Failed to gather analysis factors for {symbol}: {e}")
            return None

    def _calculate_weighted_score(self, factors: RecommendationFactors) -> float:
        """Calculate weighted overall score from individual factors."""
        scores = []
        weights = []

        # Apply weights to available factors
        if factors.fundamental_score is not None:
            scores.append(factors.fundamental_score)
            weights.append(self.scoring_weights["fundamental_score"])

        if factors.valuation_score is not None:
            scores.append(factors.valuation_score)
            weights.append(self.scoring_weights["valuation_score"])

        if factors.growth_score is not None:
            scores.append(factors.growth_score)
            weights.append(self.scoring_weights["growth_score"])

        if factors.risk_score is not None:
            # Risk score is inverse (lower risk = higher score)
            risk_weighted = 100 - factors.risk_score
            scores.append(risk_weighted)
            weights.append(self.scoring_weights["risk_score"])

        if factors.qualitative_score is not None:
            scores.append(factors.qualitative_score)
            weights.append(self.scoring_weights["qualitative_score"])

        if not scores:
            return 0.0

        # Calculate weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        return min(100.0, max(0.0, weighted_score))

    def _determine_recommendation_type(
        self,
        factors: RecommendationFactors,
        overall_score: float
    ) -> str:
        """Determine BUY/HOLD/SELL recommendation based on thresholds."""
        buy_thresholds = self.thresholds["buy"]
        hold_thresholds = self.thresholds["hold"]
        sell_thresholds = self.thresholds["sell"]

        # Check BUY conditions
        if (overall_score >= buy_thresholds["min_overall"] and
            (factors.fundamental_score is None or factors.fundamental_score >= buy_thresholds["min_fundamental"]) and
            (factors.risk_score is None or factors.risk_score <= buy_thresholds["max_risk"]) and
            (factors.growth_score is None or factors.growth_score >= buy_thresholds["min_growth"])):
            return "BUY"

        # Check SELL conditions
        if (overall_score <= sell_thresholds["max_overall"] or
            (factors.fundamental_score is not None and factors.fundamental_score <= sell_thresholds["max_fundamental"]) or
            (factors.risk_score is not None and factors.risk_score >= sell_thresholds["min_risk"])):
            return "SELL"

        # Check HOLD conditions
        if hold_thresholds["min_overall"] <= overall_score <= hold_thresholds["max_overall"]:
            return "HOLD"

        # Default to HOLD for borderline cases
        return "HOLD"

    def _calculate_confidence_level(self, overall_score: float) -> str:
        """Calculate confidence level based on score."""
        if overall_score >= self.confidence_levels["high"]["min_score"]:
            return "HIGH"
        elif overall_score >= self.confidence_levels["medium"]["min_score"]:
            return "MEDIUM"
        else:
            return "LOW"

    async def _calculate_valuation_score(self, symbol: str, fundamental_data: Optional[FundamentalAnalysis]) -> Optional[float]:
        """Calculate valuation score based on P/E, P/B ratios."""
        if not fundamental_data:
            return None

        try:
            score_components = []

            # P/E Ratio valuation (lower is better, target < 20)
            if fundamental_data.pe_ratio:
                if fundamental_data.pe_ratio <= 15:
                    pe_score = 90
                elif fundamental_data.pe_ratio <= 20:
                    pe_score = 80
                elif fundamental_data.pe_ratio <= 25:
                    pe_score = 60
                elif fundamental_data.pe_ratio <= 30:
                    pe_score = 40
                else:
                    pe_score = 20
                score_components.append(pe_score)

            # P/B Ratio valuation (lower is better, target < 3)
            if fundamental_data.pb_ratio:
                if fundamental_data.pb_ratio <= 1.5:
                    pb_score = 90
                elif fundamental_data.pb_ratio <= 2.0:
                    pb_score = 80
                elif fundamental_data.pb_ratio <= 3.0:
                    pb_score = 60
                elif fundamental_data.pb_ratio <= 4.0:
                    pb_score = 40
                else:
                    pb_score = 20
                score_components.append(pb_score)

            if not score_components:
                return None

            return sum(score_components) / len(score_components)

        except Exception as e:
            logger.error(f"Failed to calculate valuation score for {symbol}: {e}")
            return None

    async def _calculate_growth_score(self, symbol: str, fundamental_data: Optional[FundamentalAnalysis]) -> Optional[float]:
        """Calculate growth score based on revenue/earnings growth."""
        if not fundamental_data:
            return None

        try:
            score_components = []

            # Revenue growth (higher is better, target > 10%)
            if fundamental_data.revenue_growth:
                if fundamental_data.revenue_growth >= 20:
                    revenue_score = 90
                elif fundamental_data.revenue_growth >= 15:
                    revenue_score = 80
                elif fundamental_data.revenue_growth >= 10:
                    revenue_score = 70
                elif fundamental_data.revenue_growth >= 5:
                    revenue_score = 60
                else:
                    revenue_score = 40
                score_components.append(revenue_score)

            # Earnings growth (higher is better, target > 15%)
            if fundamental_data.earnings_growth:
                if fundamental_data.earnings_growth >= 25:
                    earnings_score = 90
                elif fundamental_data.earnings_growth >= 20:
                    earnings_score = 80
                elif fundamental_data.earnings_growth >= 15:
                    earnings_score = 70
                elif fundamental_data.earnings_growth >= 10:
                    earnings_score = 60
                else:
                    earnings_score = 40
                score_components.append(earnings_score)

            if not score_components:
                return None

            return sum(score_components) / len(score_components)

        except Exception as e:
            logger.error(f"Failed to calculate growth score for {symbol}: {e}")
            return None

    async def _calculate_risk_score(self, symbol: str) -> Optional[float]:
        """Calculate risk score from risk service data."""
        try:
            # Get risk decision for the symbol
            risk_decision = await self.risk_service.create_risk_decision(symbol)

            # Convert risk decision to score (higher score = higher risk)
            if risk_decision.decision == "approve":
                return 20.0  # Low risk
            elif risk_decision.decision == "defer":
                return 50.0  # Medium risk
            else:  # deny
                return 80.0  # High risk

        except Exception as e:
            logger.error(f"Failed to calculate risk score for {symbol}: {e}")
            return 50.0  # Default medium risk

    async def _calculate_qualitative_score(self, symbol: str) -> Optional[float]:
        """Calculate qualitative score based on news sentiment and other factors."""
        try:
            # Get recent news sentiment
            news_items = await self.state_manager.get_news_for_symbol(symbol, 10)

            if not news_items:
                return 60.0  # Neutral score if no news

            # Calculate average sentiment
            sentiments = []
            for news in news_items:
                if hasattr(news, 'sentiment') and news.sentiment:
                    # Convert sentiment string to score
                    if news.sentiment.lower() == 'positive':
                        sentiments.append(80)
                    elif news.sentiment.lower() == 'negative':
                        sentiments.append(30)
                    else:  # neutral
                        sentiments.append(60)

            if sentiments:
                return sum(sentiments) / len(sentiments)
            else:
                return 60.0  # Neutral

        except Exception as e:
            logger.error(f"Failed to calculate qualitative score for {symbol}: {e}")
            return 60.0  # Default neutral

    async def _calculate_target_prices(
        self,
        symbol: str,
        recommendation_type: str,
        factors: RecommendationFactors
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate target price and stop loss based on recommendation."""
        try:
            # Get current price (simplified - would integrate with broker API)
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return None, None

            if recommendation_type == "BUY":
                # Target: 10-20% upside, Stop: 5-8% downside
                target_price = current_price * 1.15  # 15% target
                stop_loss = current_price * 0.95     # 5% stop
            elif recommendation_type == "SELL":
                # Target: 10-15% downside, Stop: 5-10% upside
                target_price = current_price * 0.90  # 10% target
                stop_loss = current_price * 1.08     # 8% stop
            else:  # HOLD
                # Wider ranges for hold
                target_price = current_price * 1.10  # 10% target
                stop_loss = current_price * 0.92     # 8% stop

            return round(target_price, 2), round(stop_loss, 2)

        except Exception as e:
            logger.error(f"Failed to calculate target prices for {symbol}: {e}")
            return None, None

    def _build_reasoning(
        self,
        factors: RecommendationFactors,
        overall_score: float,
        recommendation_type: str
    ) -> str:
        """Build human-readable reasoning for the recommendation."""
        reasons = []

        if factors.fundamental_score is not None:
            if factors.fundamental_score >= 70:
                reasons.append(f"Strong fundamentals (score: {factors.fundamental_score:.1f})")
            elif factors.fundamental_score <= 40:
                reasons.append(f"Weak fundamentals (score: {factors.fundamental_score:.1f})")

        if factors.valuation_score is not None:
            if factors.valuation_score >= 75:
                reasons.append(f"Attractive valuation (score: {factors.valuation_score:.1f})")
            elif factors.valuation_score <= 50:
                reasons.append(f"Expensive valuation (score: {factors.valuation_score:.1f})")

        if factors.growth_score is not None:
            if factors.growth_score >= 70:
                reasons.append(f"Strong growth prospects (score: {factors.growth_score:.1f})")
            elif factors.growth_score <= 50:
                reasons.append(f"Limited growth potential (score: {factors.growth_score:.1f})")

        if factors.risk_score is not None:
            if factors.risk_score <= 30:
                reasons.append(f"Low risk profile (score: {factors.risk_score:.1f})")
            elif factors.risk_score >= 70:
                reasons.append(f"High risk profile (score: {factors.risk_score:.1f})")

        if not reasons:
            reasons.append(f"Overall score: {overall_score:.1f}")

        return f"{recommendation_type} recommendation based on: {', '.join(reasons)}"

    def _assess_risk_level(self, factors: RecommendationFactors) -> str:
        """Assess overall risk level."""
        if factors.risk_score is None:
            return "MEDIUM"

        if factors.risk_score <= 30:
            return "LOW"
        elif factors.risk_score <= 60:
            return "MEDIUM"
        else:
            return "HIGH"

    def _determine_time_horizon(self, factors: RecommendationFactors, recommendation_type: str) -> str:
        """Determine recommended time horizon."""
        if recommendation_type == "BUY" and factors.growth_score and factors.growth_score >= 75:
            return "LONG_TERM"  # Growth stocks for longer holding
        elif recommendation_type == "SELL":
            return "SHORT_TERM"  # Quick exit for sells
        else:
            return "MEDIUM_TERM"  # Default

    def _confidence_to_score(self, confidence_level: str) -> Optional[float]:
        """Convert confidence level to numerical score."""
        mapping = {
            "HIGH": 85,
            "MEDIUM": 65,
            "LOW": 45
        }
        return mapping.get(confidence_level)

    def _calculate_potential_impact(self, result: RecommendationResult) -> Optional[str]:
        """Calculate potential impact of the recommendation."""
        if result.confidence_level == "HIGH" and result.recommendation_type in ["BUY", "SELL"]:
            return "HIGH"
        elif result.confidence_level == "MEDIUM":
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_alternatives(self, result: RecommendationResult) -> Optional[List[str]]:
        """Generate alternative suggestions."""
        alternatives = []

        if result.recommendation_type == "BUY":
            alternatives.extend(["Consider dollar-cost averaging", "Monitor for pullbacks"])
        elif result.recommendation_type == "SELL":
            alternatives.extend(["Consider partial position", "Wait for better exit"])
        else:  # HOLD
            alternatives.extend(["Accumulate on dips", "Consider options strategies"])

        return alternatives if alternatives else None

    async def _create_performance_entry(self, result: RecommendationResult, recommendation_id: int) -> None:
        """Create performance tracking entry."""
        try:
            performance = AnalysisPerformance(
                symbol=result.symbol,
                prediction_date=datetime.now(timezone.utc).isoformat(),
                recommendation_id=recommendation_id,
                predicted_direction=result.recommendation_type,
                model_version="RECOMMENDATION_ENGINE_V1"
            )

            await self.state_manager.save_analysis_performance(performance)

        except Exception as e:
            logger.error(f"Failed to create performance entry for {result.symbol}: {e}")

    async def _get_claude_recommendation_analysis(
        self,
        symbol: str,
        factors: RecommendationFactors
    ) -> Optional[Dict[str, Any]]:
        """Get AI-powered recommendation analysis from Claude using SDK."""
        try:
            # Use client manager instead of direct creation
            if not self.claude_client:
                from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
                client_manager = await ClaudeSDKClientManager.get_instance()
                self.claude_client = await client_manager.get_client("trading", self.claude_options)

            # Gather comprehensive data for Claude analysis
            fundamental_data = await self.state_manager.get_fundamental_analysis(symbol, 1)
            news_data = await self.state_manager.get_news_for_symbol(symbol, 10)
            earnings_data = await self.state_manager.get_earnings_for_symbol(symbol, 5)

            # Build comprehensive prompt for Claude
            prompt = self._build_claude_analysis_prompt(symbol, factors, fundamental_data, news_data, earnings_data)

            # Use timeout helpers (MANDATORY per architecture pattern)
            # query_with_timeout handles both query() and receive_response() internally
            from src.core.sdk_helpers import query_with_timeout
            response_text = await query_with_timeout(self.claude_client, prompt, timeout=60.0)

            # Parse Claude's response
            return self._parse_claude_response(response_text)

        except Exception as e:
            logger.error(f"Failed to get Claude SDK analysis for {symbol}: {e}")
            return None

    def _build_claude_analysis_prompt(
        self,
        symbol: str,
        factors: RecommendationFactors,
        fundamental_data: List[FundamentalAnalysis],
        news_data: List,
        earnings_data: List
    ) -> str:
        """Build comprehensive analysis prompt for Claude."""
        prompt = f"""
Please provide a comprehensive investment recommendation for {symbol} based on the following data:

**FUNDAMENTAL ANALYSIS DATA:**
"""

        if fundamental_data:
            fund = fundamental_data[0]
            prompt += f"""
- P/E Ratio: {fund.pe_ratio}
- P/B Ratio: {fund.pb_ratio}
- ROE: {fund.roe}%
- ROA: {fund.roa}%
- Debt-to-Equity: {fund.debt_to_equity}
- Dividend Yield: {fund.dividend_yield}%
- Market Cap: {fund.market_cap}
- Revenue Growth: {fund.revenue_growth}%
- Earnings Growth: {fund.earnings_growth}%
- Sector: {fund.sector}
- Industry: {fund.industry}
"""

        prompt += "\n**RECENT NEWS (Last 10 items):**\n"
        if news_data:
            for news in news_data[:5]:  # Limit to 5 most recent
                prompt += f"- {news.title} (Sentiment: {getattr(news, 'sentiment', 'neutral')})\n"
        else:
            prompt += "- No recent news available\n"

        prompt += "\n**EARNINGS DATA (Last 5 reports):**\n"
        if earnings_data:
            for earnings in earnings_data[:3]:  # Limit to 3 most recent
                prompt += f"- {earnings.fiscal_period}: EPS {earnings.eps_actual} (Est: {earnings.eps_estimated}), Revenue {earnings.revenue_actual}M (Est: {earnings.revenue_estimated}M), Surprise: {earnings.surprise_pct}%\n"
        else:
            prompt += "- No recent earnings data available\n"

        prompt += f"""
**ANALYSIS FRAMEWORK:**

1. **Fundamental Analysis (Primary Focus)**
   - Revenue and Earnings Growth: Look for consistent increases in revenue and earnings over time. Strong growth signals a company's ability to expand and remain profitable
   - Profit Margins: Check the gross, operating, and net margins. Higher margins indicate efficiency in turning revenue into profit.
   - Debt-to-Equity Ratio: This measures how much debt a company uses compared to its equity. A lower ratio suggests less financial risk.
   - Return on Equity (ROE): ROE shows how well a company generates profits from shareholders' equity. A higher ROE is a positive sign.
   - Analyze net profit growth year on year, check if there is uptrend. Also check the net profit growth in current quarter it should be in positive.

2. **Valuation Metrics**
   Valuation helps you determine if the stock is priced fairly relative to its earnings and growth potential.
   - Price-to-Earnings (P/E) Ratio: This compares the stock price to earnings per share. A lower P/E might suggest the stock is undervalued, but compare it to industry averages for context.
   - Price-to-Sales (P/S) Ratio: Useful for companies with low or no earnings, this compares price to revenue. A lower P/S may indicate undervaluation.
   - Price-to-Book (P/B) Ratio: This compares market value to book value. A P/B below 1 could mean the stock is undervalued, though industry norms matter.
   - PEG Ratio: The price/earnings-to-growth ratio factors in expected growth. A PEG below 1 suggests the stock is undervalued relative to its growth potential.

3. **Growth Potential**
   Consider whether the company and its industry have room to grow, which is key for long-term value.
   - Earnings Growth Rate: Look at forecasts for future earnings growth. Strong projections suggest a stock has upside potential.
   - Industry Trends: Evaluate the sector. Growth industries (e.g., tech, renewable energy) may offer more potential than declining ones.

4. **Risk Metrics**
   Understanding risk helps you decide if a stock fits your comfort level.
   - Beta: This measures volatility compared to the market. A beta above 1 means higher volatility (and risk), while below 1 suggests stability.
   - Standard Deviation: A direct measure of price fluctuation. Lower volatility suits conservative investors.
   - Company-Specific Risks: Look at risks like competition, regulatory challenges, or dependence on a single product.

5. **Market Conditions**
   The broader market environment can influence your decision.
   - Overall Market Trends: A bull market (rising prices) may favor adding stocks, while a bear market (declining prices) might suggest holding or waiting.
   - Interest Rates: Rising rates can hurt stock valuations, especially growth stocks, while lower rates often support higher prices.

6. **Qualitative Factors**
   Beyond numbers, consider these less tangible but impactful elements.
   - Management Quality: A capable, experienced leadership team can drive success. Research their track record.
   - Competitive Advantage: Companies with a strong edge (e.g., brand loyalty, patents) are more likely to thrive long-term.

**REQUIRED OUTPUT FORMAT:**
Provide your analysis in the following JSON format:
{{
  "recommendation": "BUY|SELL|HOLD",
  "confidence": "HIGH|MEDIUM|LOW",
  "reasoning": "Detailed explanation of your recommendation based on the analysis framework above",
  "target_price": 123.45,
  "stop_loss": 98.76,
  "risk_level": "LOW|MEDIUM|HIGH",
  "time_horizon": "SHORT_TERM|MEDIUM_TERM|LONG_TERM",
  "key_factors": ["factor1", "factor2", "factor3"]
}}

Be specific with numbers and provide clear reasoning. Consider current market conditions and recent news impact.
"""
        return prompt

    def _parse_claude_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Claude's JSON response."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())
            else:
                logger.warning("Could not extract JSON from Claude response")
                return None
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return None

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol (placeholder implementation)."""
        # In a real implementation, this would fetch from broker API
        # For now, return a simulated price
        base_prices = {
            "RELIANCE": 2685.40,
            "TCS": 4185.80,
            "HDFCBANK": 1720.90,
            "ICICIBANK": 1158.60,
            "INFY": 1925.75,
            "AARTIIND": 650.25
        }
        return base_prices.get(symbol, 1000.0)

    async def get_recommendation_stats(self) -> Dict[str, Any]:
        """Get recommendation engine statistics."""
        try:
            # This would query the database for recommendation statistics
            # For now, return placeholder stats
            return {
                "total_recommendations": 0,
                "buy_recommendations": 0,
                "sell_recommendations": 0,
                "hold_recommendations": 0,
                "average_confidence": 0.0,
                "success_rate": 0.0
            }
        except Exception as e:
            logger.error(f"Failed to get recommendation stats: {e}")
            return {}