"""
Decision Maker for Recommendation Engine

Handles recommendation logic:
- Weighted score calculation
- Recommendation type determination (BUY/HOLD/SELL)
- Confidence level assessment
- Risk assessment
- Time horizon determination
"""

import logging
from typing import Any, Dict

from loguru import logger

from .models import RecommendationConfig, RecommendationFactors

logger = logging.getLogger(__name__)


class DecisionMaker:
    """Makes recommendation decisions based on calculated factors."""

    def __init__(self, config: RecommendationConfig):
        self.config = config

    def calculate_weighted_score(self, factors: RecommendationFactors) -> float:
        """Calculate overall weighted score from individual factors."""
        try:
            weights = self.config.scoring_weights
            score = 0.0
            total_weight = 0.0

            # Fundamental score (35% weight)
            if factors.fundamental_score is not None:
                score += factors.fundamental_score * weights.get(
                    "fundamental_score", 0.35
                )
                total_weight += weights.get("fundamental_score", 0.35)

            # Valuation score (25% weight)
            if factors.valuation_score is not None:
                score += factors.valuation_score * weights.get("valuation_score", 0.25)
                total_weight += weights.get("valuation_score", 0.25)

            # Growth score (20% weight)
            if factors.growth_score is not None:
                score += factors.growth_score * weights.get("growth_score", 0.20)
                total_weight += weights.get("growth_score", 0.20)

            # Risk score (15% weight) - inverted since lower risk is better
            if factors.risk_score is not None:
                # Risk score: Higher is better (represents lower risk)
                score += factors.risk_score * weights.get("risk_score", 0.15)
                total_weight += weights.get("risk_score", 0.15)

            # Qualitative score (5% weight)
            if factors.qualitative_score is not None:
                score += factors.qualitative_score * weights.get(
                    "qualitative_score", 0.05
                )
                total_weight += weights.get("qualitative_score", 0.05)

            # Normalize to 100 if we don't have all factors
            if total_weight > 0:
                return (score / total_weight) * 100
            else:
                return 50.0  # Neutral score if no factors available

        except Exception as e:
            logger.error(f"Error calculating weighted score: {e}")
            return 50.0

    def determine_recommendation_type(
        self, overall_score: float, factors: RecommendationFactors
    ) -> str:
        """Determine recommendation type based on thresholds."""
        try:
            thresholds = self.config.thresholds

            # Check BUY conditions
            if (
                overall_score >= thresholds["buy"]["min_overall"]
                and (factors.fundamental_score or 0)
                >= thresholds["buy"]["min_fundamental"]
                and (factors.risk_score or 50) >= (100 - thresholds["buy"]["max_risk"])
                and (factors.growth_score or 50) >= thresholds["buy"]["min_growth"]
            ):
                return "BUY"

            # Check SELL conditions
            if (
                overall_score <= thresholds["sell"]["max_overall"]
                and (factors.fundamental_score or 0)
                <= thresholds["sell"]["max_fundamental"]
                and (factors.risk_score or 50) <= (100 - thresholds["sell"]["min_risk"])
            ):
                return "SELL"

            # Default to HOLD
            return "HOLD"

        except Exception as e:
            logger.error(f"Error determining recommendation type: {e}")
            return "HOLD"  # Default to conservative recommendation

    def calculate_confidence_level(self, overall_score: float) -> str:
        """Calculate confidence level based on score distribution."""
        try:
            confidence_levels = self.config.confidence_levels

            if overall_score >= confidence_levels["high"]["min_score"]:
                return "HIGH"
            elif overall_score >= confidence_levels["medium"]["min_score"]:
                return "MEDIUM"
            else:
                return "LOW"

        except Exception as e:
            logger.error(f"Error calculating confidence level: {e}")
            return "LOW"

    def assess_risk_level(self, factors: RecommendationFactors) -> str:
        """Assess risk level based on factors."""
        try:
            # Risk assessment based on risk score and other factors
            risk_score = factors.risk_score or 50.0

            # Check volatility indicators (through risk score)
            if risk_score < 30:
                return "HIGH"
            elif risk_score < 70:
                return "MEDIUM"
            else:
                return "LOW"

        except Exception as e:
            logger.error(f"Error assessing risk level: {e}")
            return "MEDIUM"

    def determine_time_horizon(
        self, factors: RecommendationFactors, recommendation_type: str
    ) -> str:
        """Determine recommended time horizon."""
        try:
            # For BUY recommendations, look at growth prospects
            if recommendation_type == "BUY":
                growth_score = factors.growth_score or 50.0
                if growth_score > 80:
                    return "LONG_TERM"
                elif growth_score > 60:
                    return "MEDIUM_TERM"
                else:
                    return "SHORT_TERM"

            # For HOLD recommendations, medium term is usually appropriate
            elif recommendation_type == "HOLD":
                return "MEDIUM_TERM"

            # For SELL recommendations, immediate action is implied
            else:  # SELL
                return "IMMEDIATE"

        except Exception as e:
            logger.error(f"Error determining time horizon: {e}")
            return "MEDIUM_TERM"

    def confidence_to_score(self, confidence_level: str) -> float:
        """Convert confidence level back to score range."""
        try:
            confidence_levels = self.config.confidence_levels

            if confidence_level.upper() == "HIGH":
                return (
                    confidence_levels["high"]["min_score"]
                    + confidence_levels["high"]["max_score"]
                ) / 2
            elif confidence_level.upper() == "MEDIUM":
                return (
                    confidence_levels["medium"]["min_score"]
                    + confidence_levels["medium"]["max_score"]
                ) / 2
            elif confidence_level.upper() == "LOW":
                return (
                    confidence_levels["low"]["min_score"]
                    + confidence_levels["low"]["max_score"]
                ) / 2
            else:
                return 60.0  # Default medium confidence

        except Exception as e:
            logger.error(f"Error converting confidence to score: {e}")
            return 60.0

    def make_decision(
        self, factors: RecommendationFactors, symbol: str
    ) -> Dict[str, Any]:
        """Make complete recommendation decision based on factors."""
        try:
            # Calculate weighted overall score
            overall_score = self.calculate_weighted_score(factors)

            # Determine recommendation type and confidence
            recommendation_type = self.determine_recommendation_type(
                overall_score, factors
            )
            confidence_level = self.calculate_confidence_level(overall_score)

            # Assess risk and time horizon
            risk_level = self.assess_risk_level(factors)
            time_horizon = self.determine_time_horizon(factors, recommendation_type)

            return {
                "recommendation_type": recommendation_type,
                "confidence_level": confidence_level,
                "overall_score": overall_score,
                "risk_level": risk_level,
                "time_horizon": time_horizon,
                "symbol": symbol,
            }

        except Exception as e:
            logger.error(f"Error making decision for {symbol}: {e}")
            # Return conservative default decision
            return {
                "recommendation_type": "HOLD",
                "confidence_level": "LOW",
                "overall_score": 50.0,
                "risk_level": "MEDIUM",
                "time_horizon": "MEDIUM_TERM",
                "symbol": symbol,
            }
