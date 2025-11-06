"""
Recommendation Engine Module

AI-powered trading recommendation system that combines multiple analysis factors
with Claude Agent SDK for intelligent reasoning and actionable BUY/SELL/HOLD recommendations.

All components are modularized for maintainability.
"""

from .engine import RecommendationEngine
from .models import (RecommendationConfig, RecommendationFactors,
                     RecommendationResult)

__all__ = [
    "RecommendationEngine",
    "RecommendationFactors",
    "RecommendationResult",
    "RecommendationConfig",
]
