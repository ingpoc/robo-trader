"""
Recommendation Engine - Main Orchestrator

Coordinates all recommendation engine modules:
- Factor calculation
- Decision making
- Claude analysis
- Performance tracking

Provides 100% backward compatibility with original RecommendationEngine.
"""

import logging
from typing import Any, Dict, List, Optional

from loguru import logger

from src.config import Config
from src.core.database_state import DatabaseStateManager
from src.core.state_models import (FundamentalAnalysis)
from src.services.fundamental_service import FundamentalService
from src.services.risk_service import RiskService

from .claude_analyzer import ClaudeAnalyzer
from .decision_maker import DecisionMaker
from .factor_calculator import FactorCalculator
from .models import (RecommendationConfig, RecommendationFactors,
                     RecommendationResult)
from .performance_tracker import PerformanceTracker
from .price_calculator import TargetPriceCalculator

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Advanced recommendation engine that combines multiple analysis factors.

    Features:
    - Weighted multi-factor scoring system
    - Dynamic threshold-based recommendations
    - Confidence level assessment
    - Risk-adjusted target pricing
    - Performance tracking integration
    - Claude AI-powered qualitative analysis
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager,
        fundamental_service: FundamentalService,
        risk_service: RiskService,
    ):
        self.config = config
        self.state_manager = state_manager
        self.fundamental_service = fundamental_service
        self.risk_service = risk_service

        # Load recommendation engine configuration
        reco_config = getattr(config, "recommendation_engine", {})
        self.recommendation_config = RecommendationConfig.default()

        # Override with provided config if available
        if reco_config:
            if "scoring_weights" in reco_config:
                self.recommendation_config.scoring_weights.update(
                    reco_config["scoring_weights"]
                )
            if "thresholds" in reco_config:
                self.recommendation_config.thresholds.update(reco_config["thresholds"])
            if "confidence_levels" in reco_config:
                self.recommendation_config.confidence_levels.update(
                    reco_config["confidence_levels"]
                )

        # Initialize modules
        self.factor_calculator = FactorCalculator(fundamental_service, risk_service)
        self.decision_maker = DecisionMaker(self.recommendation_config)
        self.performance_tracker = PerformanceTracker(state_manager)
        self.claude_analyzer = ClaudeAnalyzer(reco_config)
        self.price_calculator = TargetPriceCalculator(self.claude_analyzer)

        logger.info("Recommendation engine initialized with modular architecture")

    async def generate_recommendation(
        self, symbol: str, force_refresh: bool = False
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

            # Step 1: Gather fundamental data
            fundamental_data = await self._get_fundamental_data(symbol, force_refresh)
            if not fundamental_data:
                logger.warning(f"No fundamental data available for {symbol}")
                return None

            # Step 2: Calculate all factors
            factors = await self.factor_calculator.calculate_all_factors(
                symbol, fundamental_data
            )

            # Step 3: Make decision based on factors
            decision = self.decision_maker.make_decision(factors, symbol)

            # Step 4: Get Claude analysis for qualitative insights
            claude_analysis = await self._get_claude_analysis_enhanced(symbol, factors)

            # Step 5: Build recommendation result
            result = await self._build_recommendation_result(
                symbol, decision, factors, claude_analysis, fundamental_data
            )

            # Step 6: Store recommendation for performance tracking
            await self.performance_tracker.store_recommendation(result)

            logger.info(
                f"Generated recommendation for {symbol}: {result.recommendation_type} (confidence: {result.confidence_level})"
            )
            return result

        except Exception as e:
            logger.error(f"Error generating recommendation for {symbol}: {e}")
            return None

    async def _get_fundamental_data(
        self, symbol: str, force_refresh: bool = False
    ) -> Optional[FundamentalAnalysis]:
        """Get fundamental data for symbol."""
        try:
            # Try to get cached data first
            if not force_refresh:
                # TODO: Implement caching logic
                pass

            # Get fresh data from fundamental service
            return await self.fundamental_service.get_fundamental_analysis(symbol)

        except Exception as e:
            logger.error(f"Error getting fundamental data for {symbol}: {e}")
            return None

    async def _get_claude_analysis_enhanced(
        self, symbol: str, factors: RecommendationFactors
    ) -> Optional[Dict[str, Any]]:
        """Get enhanced Claude analysis with current price."""
        try:
            # Get current price for better analysis
            current_price = await self.claude_analyzer.get_current_price(symbol)

            # Get Claude analysis
            return await self.claude_analyzer.get_claude_recommendation_analysis(
                symbol, factors, current_price
            )

        except Exception as e:
            logger.error(f"Error getting Claude analysis for {symbol}: {e}")
            return None

    async def _build_recommendation_result(
        self,
        symbol: str,
        decision: Dict[str, Any],
        factors: RecommendationFactors,
        claude_analysis: Optional[Dict[str, Any]],
        fundamental_data: Optional[FundamentalAnalysis],
    ) -> RecommendationResult:
        """Build complete recommendation result from all analysis components."""
        try:
            # Extract decision components
            recommendation_type = decision["recommendation_type"]
            confidence_level = decision["confidence_level"]
            overall_score = decision["overall_score"]
            risk_level = decision["risk_level"]
            time_horizon = decision["time_horizon"]

            # Calculate target prices and stop losses
            target_price, stop_loss = (
                await self.price_calculator.calculate_target_prices(
                    symbol, fundamental_data, recommendation_type, claude_analysis
                )
            )

            # Build reasoning
            reasoning = self.price_calculator.build_reasoning(
                factors, decision, claude_analysis
            )

            # Create recommendation result
            result = RecommendationResult(
                symbol=symbol,
                recommendation_type=recommendation_type,
                confidence_level=confidence_level,
                overall_score=overall_score,
                factors=factors,
                target_price=target_price,
                stop_loss=stop_loss,
                reasoning=reasoning,
                risk_level=risk_level,
                time_horizon=time_horizon,
            )

            return result

        except Exception as e:
            logger.error(f"Error building recommendation result for {symbol}: {e}")
            # Return basic result
            return RecommendationResult(
                symbol=symbol,
                recommendation_type=decision.get("recommendation_type", "HOLD"),
                confidence_level=decision.get("confidence_level", "LOW"),
                overall_score=decision.get("overall_score", 50.0),
                factors=factors,
                reasoning="Error building detailed recommendation",
            )

    async def generate_bulk_recommendations(
        self, symbols: List[str], force_refresh: bool = False
    ) -> Dict[str, RecommendationResult]:
        """Generate recommendations for multiple symbols."""
        recommendations = {}

        for symbol in symbols:
            try:
                recommendation = await self.generate_recommendation(
                    symbol, force_refresh
                )
                if recommendation:
                    recommendations[symbol] = recommendation
                else:
                    logger.warning(f"Could not generate recommendation for {symbol}")
            except Exception as e:
                logger.error(f"Error generating recommendation for {symbol}: {e}")

        logger.info(
            f"Generated {len(recommendations)} recommendations out of {len(symbols)} requested"
        )
        return recommendations

    async def _generate_rule_based_recommendation(
        self, symbol: str, fundamental_data: Optional[FundamentalAnalysis] = None
    ) -> Optional[RecommendationResult]:
        """Generate rule-based recommendation without Claude analysis."""
        try:
            if not fundamental_data:
                fundamental_data = (
                    await self.fundamental_service.get_fundamental_analysis(symbol)
                )
                if not fundamental_data:
                    return None

            # Calculate factors
            factors = await self.factor_calculator.calculate_all_factors(
                symbol, fundamental_data
            )

            # Make decision
            decision = self.decision_maker.make_decision(factors, symbol)

            # Build simple reasoning
            reasoning = f"Rule-based analysis - Overall score: {decision['overall_score']:.1f}, Risk level: {decision['risk_level']}"

            # Create recommendation
            result = RecommendationResult(
                symbol=symbol,
                recommendation_type=decision["recommendation_type"],
                confidence_level=decision["confidence_level"],
                overall_score=decision["overall_score"],
                factors=factors,
                reasoning=reasoning,
                risk_level=decision["risk_level"],
                time_horizon=decision["time_horizon"],
            )

            return result

        except Exception as e:
            logger.error(
                f"Error generating rule-based recommendation for {symbol}: {e}"
            )
            return None

    async def get_recommendation_history(
        self, symbol: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recommendation history."""
        return await self.performance_tracker.get_recommendation_history(symbol, limit)

    async def get_recommendation_stats(self) -> Dict[str, Any]:
        """Get recommendation engine statistics."""
        return await self.performance_tracker.get_recommendation_stats()
