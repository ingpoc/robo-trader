"""Recommendation engine package with lazy exports to avoid import-time side effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import RecommendationEngine
    from .models import RecommendationConfig, RecommendationFactors, RecommendationResult

__all__ = [
    "RecommendationEngine",
    "RecommendationFactors",
    "RecommendationResult",
    "RecommendationConfig",
]


def __getattr__(name: str):
    if name == "RecommendationEngine":
        from .engine import RecommendationEngine

        return RecommendationEngine
    if name in {"RecommendationFactors", "RecommendationResult", "RecommendationConfig"}:
        from .models import RecommendationConfig, RecommendationFactors, RecommendationResult

        return {
            "RecommendationFactors": RecommendationFactors,
            "RecommendationResult": RecommendationResult,
            "RecommendationConfig": RecommendationConfig,
        }[name]
    raise AttributeError(name)
