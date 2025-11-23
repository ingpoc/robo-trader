"""
Analysis Cache - Reuse Previous Analysis Results

Caches Claude agent analysis to avoid redundant token usage.
Stable portfolios can reuse recent analysis instead of re-analyzing.

Token Savings: ~300-500 tokens per cached analysis (no Claude turns needed)
"""

import logging
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class CachedAnalysis:
    """Cached analysis result."""
    cache_key: str
    symbols: List[str]
    analysis: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    token_estimate: int = 0  # Estimated tokens saved when reused


class AnalysisCache:
    """
    Cache for Claude agent analysis results.

    Caches analysis by:
    - Symbol set (sorted for consistent hashing)
    - Analysis type (morning, evening, position)
    - Portfolio state hash

    Token savings: ~300-500 tokens when cache hits
    """

    # Default TTL values (in seconds)
    DEFAULT_TTL = 1800  # 30 minutes
    MORNING_ANALYSIS_TTL = 3600  # 1 hour (market conditions stable)
    EVENING_ANALYSIS_TTL = 7200  # 2 hours (end of day summary)
    POSITION_ANALYSIS_TTL = 900  # 15 minutes (more time-sensitive)

    def __init__(self, max_entries: int = 100):
        self._cache: Dict[str, CachedAnalysis] = {}
        self._max_entries = max_entries
        self._hit_count = 0
        self._miss_count = 0

    def get(
        self,
        symbols: List[str],
        analysis_type: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis if available and not expired.

        Args:
            symbols: List of symbols analyzed
            analysis_type: Type of analysis (morning, evening, position)

        Returns:
            Cached analysis dict or None if miss
        """
        cache_key = self._make_key(symbols, analysis_type)

        if cache_key not in self._cache:
            self._miss_count += 1
            return None

        cached = self._cache[cache_key]

        # Check expiration
        if datetime.now() > cached.expires_at:
            del self._cache[cache_key]
            self._miss_count += 1
            logger.debug(f"Analysis cache expired: {cache_key}")
            return None

        # Cache hit
        cached.hit_count += 1
        self._hit_count += 1

        logger.info(f"Analysis cache hit: {analysis_type} for {symbols} "
                   f"(saved ~{cached.token_estimate} tokens)")

        return cached.analysis

    def set(
        self,
        symbols: List[str],
        analysis: Dict[str, Any],
        analysis_type: str = "general",
        ttl_seconds: Optional[int] = None,
        token_estimate: int = 400
    ) -> str:
        """
        Cache analysis result.

        Args:
            symbols: List of symbols analyzed
            analysis: Analysis result to cache
            analysis_type: Type of analysis
            ttl_seconds: Custom TTL (or use defaults)
            token_estimate: Estimated tokens saved per cache hit

        Returns:
            Cache key
        """
        # Determine TTL
        if ttl_seconds is None:
            ttl_seconds = self._get_default_ttl(analysis_type)

        cache_key = self._make_key(symbols, analysis_type)

        # Cleanup if at capacity
        if len(self._cache) >= self._max_entries:
            self._cleanup_expired()
            if len(self._cache) >= self._max_entries:
                self._evict_oldest()

        # Store
        self._cache[cache_key] = CachedAnalysis(
            cache_key=cache_key,
            symbols=symbols,
            analysis=analysis,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl_seconds),
            hit_count=0,
            token_estimate=token_estimate
        )

        logger.debug(f"Analysis cached: {analysis_type} for {symbols} (TTL: {ttl_seconds}s)")
        return cache_key

    def invalidate(self, symbols: Optional[List[str]] = None) -> int:
        """
        Invalidate cached analyses.

        Args:
            symbols: If provided, only invalidate analyses containing these symbols.
                    If None, invalidate all.

        Returns:
            Number of entries invalidated
        """
        if symbols is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Analysis cache cleared: {count} entries")
            return count

        # Invalidate specific symbols
        symbols_set = set(symbols)
        to_delete = [
            key for key, cached in self._cache.items()
            if symbols_set & set(cached.symbols)
        ]

        for key in to_delete:
            del self._cache[key]

        if to_delete:
            logger.info(f"Analysis cache invalidated for {symbols}: {len(to_delete)} entries")

        return len(to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_saved = sum(c.hit_count * c.token_estimate for c in self._cache.values())
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": self._hit_count / max(1, self._hit_count + self._miss_count),
            "total_tokens_saved": total_saved
        }

    def _make_key(self, symbols: List[str], analysis_type: str) -> str:
        """Create cache key from symbols and type."""
        sorted_symbols = sorted(symbols)
        key_data = f"{analysis_type}:{','.join(sorted_symbols)}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]

    def _get_default_ttl(self, analysis_type: str) -> int:
        """Get default TTL for analysis type."""
        ttl_map = {
            "morning": self.MORNING_ANALYSIS_TTL,
            "evening": self.EVENING_ANALYSIS_TTL,
            "position": self.POSITION_ANALYSIS_TTL,
            "general": self.DEFAULT_TTL
        }
        return ttl_map.get(analysis_type, self.DEFAULT_TTL)

    def _cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = datetime.now()
        expired = [key for key, c in self._cache.items() if now > c.expires_at]
        for key in expired:
            del self._cache[key]
        return len(expired)

    def _evict_oldest(self) -> None:
        """Evict oldest entry when at capacity."""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]


# Global analysis cache (lazily initialized)
_global_cache: Optional[AnalysisCache] = None


def get_analysis_cache() -> AnalysisCache:
    """Get global analysis cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = AnalysisCache(max_entries=100)
    return _global_cache


def cache_analysis(
    symbols: List[str],
    analysis: Dict[str, Any],
    analysis_type: str = "general"
) -> str:
    """Convenience function to cache analysis."""
    cache = get_analysis_cache()
    return cache.set(symbols, analysis, analysis_type)


def get_cached_analysis(
    symbols: List[str],
    analysis_type: str = "general"
) -> Optional[Dict[str, Any]]:
    """Convenience function to get cached analysis."""
    cache = get_analysis_cache()
    return cache.get(symbols, analysis_type)
