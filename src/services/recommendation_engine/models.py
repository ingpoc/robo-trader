"""
Recommendation Engine Data Models

Contains dataclasses and type definitions for recommendation engine.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


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
        data["factors"] = self.factors.to_dict()
        return data


@dataclass
class RecommendationConfig:
    """Configuration for recommendation engine."""

    scoring_weights: Dict[str, float]
    thresholds: Dict[str, Dict[str, Any]]
    confidence_levels: Dict[str, Dict[str, Any]]

    @classmethod
    def default(cls) -> "RecommendationConfig":
        """Create default configuration."""
        return cls(
            scoring_weights={
                "fundamental_score": 0.35,
                "valuation_score": 0.25,
                "growth_score": 0.20,
                "risk_score": 0.15,
                "qualitative_score": 0.05,
            },
            thresholds={
                "buy": {
                    "min_overall": 75,
                    "min_fundamental": 70,
                    "max_risk": 30,
                    "min_growth": 65,
                },
                "hold": {"min_overall": 45, "max_overall": 74},
                "sell": {"max_overall": 44, "max_fundamental": 40, "min_risk": 70},
            },
            confidence_levels={
                "high": {"min_score": 80, "max_score": 100},
                "medium": {"min_score": 60, "max_score": 79},
                "low": {"min_score": 40, "max_score": 59},
            },
        )
