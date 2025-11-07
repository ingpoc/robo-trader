"""
Token Efficient Cache for MCP Operations.

Implements multi-level caching with differential updates to minimize
Claude token usage while maximizing data freshness and relevance.
"""

import asyncio
import logging
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import aiofiles
import os

from src.core.di import DependencyContainer
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels for different storage strategies."""
    L1_MEMORY = "l1_memory"  # In-memory for current session
    L2_PERSISTENT = "l2_persistent"  # File-based for recent results
    L3_ARCHIVE = "l3_archive"  # Compressed for long-term storage


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    level: CacheLevel
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: int = 300  # 5 minutes default
    size_bytes: int = 0
    version: str = "1.0"
    tags: Set[str] = field(default_factory=set)
    checksum: str = ""

    def __post_init__(self):
        if isinstance(self.tags, list):
            self.tags = set(self.tags)
        if isinstance(self.value, str):
            self.size_bytes = len(self.value.encode('utf-8'))
        elif isinstance(self.value, (dict, list)):
            self.size_bytes = len(json.dumps(self.value).encode('utf-8'))
        self._calculate_checksum()

    def _calculate_checksum(self) -> None:
        """Calculate checksum for data integrity."""
        data_str = json.dumps(self.value, sort_keys=True, default=str) if isinstance(self.value, (dict, list)) else str(self.value)
        self.checksum = hashlib.md5(data_str.encode('utf-8')).hexdigest()

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        expiration_time = self.accessed_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiration_time

    def update_access(self) -> None:
        """Update access information."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1


@dataclass
class CacheConfig:
    """Configuration for cache behavior."""
    l1_max_entries: int = 100
    l1_max_size_mb: int = 10  # 10MB
    l2_max_entries: int = 500
    l2_max_size_mb: int = 50  # 50MB
    l3_max_entries: int = 2000
    l3_max_size_mb: int = 200  # 200MB
    default_ttl_seconds: int = 300
    cleanup_interval_seconds: int = 60
    compression_threshold_kb: int = 10  # Compress items larger than 10KB


@dataclass
class DifferentialUpdate:
    """Differential update for efficient data transfer."""
    base_version: str
    delta_data: Dict[str, Any]
    timestamp: datetime
    delta_size_bytes: int = 0
    compression_ratio: float = 0.0


class TokenEfficientCache:
    """
    Multi-level cache with differential updates for token efficiency.

    Features:
    - L1 (Memory): Fast access for current session
    - L2 (Persistent): File-based cache for recent results
    - L3 (Archive): Compressed storage for historical data
    - Differential updates to minimize data transfer
    - Intelligent eviction policies
    - Cache analytics and optimization
    """

    def __init__(self, container: DependencyContainer, cache_dir: Optional[str] = None):
        """Initialize token efficient cache."""
        self.container = container
        self.cache_dir = cache_dir or os.path.join(container.config.state_dir, "cache")
        self.config = CacheConfig()

        # Cache storage
        self._l1_cache: Dict[str, CacheEntry] = {}
        self._l2_cache_file = os.path.join(self.cache_dir, "l2_cache.json")
        self._l3_cache_file = os.path.join(self.cache_dir, "l3_archive.json.gz")

        # Cache statistics
        self._stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "l3_hits": 0,
            "l3_misses": 0,
            "total_requests": 0,
            "cache_saves": 0,
            "differential_updates": 0,
            "tokens_saved": 0,
            "bytes_saved": 0
        }

        # Background tasks
        self._cleanup_task = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize cache system."""
        if self._initialized:
            return

        try:
            # Create cache directory
            os.makedirs(self.cache_dir, exist_ok=True)

            # Load persistent cache
            await self._load_l2_cache()

            # Start background cleanup task
            self._cleanup_task = asyncio.create_task(self._background_cleanup())

            self._initialized = True
            logger.info("Token Efficient Cache initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Token Efficient Cache: {e}")
            raise TradingError(
                f"Cache initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def get(self, key: str, context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Get value from cache with multi-level lookup.

        Args:
            key: Cache key
            context: Optional context for filtering

        Returns:
            Cached value or None if not found
        """
        if not self._initialized:
            return None

        self._stats["total_requests"] += 1

        # Try L1 cache first
        value, hit_level = await self._get_from_l1(key)
        if value is not None:
            self._stats[f"{hit_level.value}_hits"] += 1
            await self._update_cache_access(hit_level, key)
            logger.debug(f"L1 cache hit: {key}")
            return value

        # Try L2 cache
        value, hit_level = await self._get_from_l2(key)
        if value is not None:
            self._stats[f"{hit_level.value}_hits"] += 1
            await self._update_cache_access(hit_level, key)
            # Promote to L1
            await self._promote_to_l1(key, value)
            logger.debug(f"L2 cache hit: {key}")
            return value

        # Try L3 archive
        value, hit_level = await self._get_from_l3(key)
        if value is not None:
            self._stats[f"{hit_level.value}_hits"] += 1
            await self._update_cache_access(hit_level, key)
            # Promote to higher levels
            await self._promote_to_l2(key, value)
            await self._promote_to_l1(key, value)
            logger.debug(f"L3 cache hit: {key}")
            return value

        # Cache miss
        self._stats["l1_misses"] += 1
        logger.debug(f"Cache miss: {key}")
        return None

    async def _get_from_l1(self, key: str) -> Tuple[Optional[Any], Optional[CacheLevel]]:
        """Get value from L1 memory cache."""
        entry = self._l1_cache.get(key)
        if entry and not entry.is_expired():
            entry.update_access()
            return entry.value, CacheLevel.L1_MEMORY
        return None, None

    async def _get_from_l2(self, key: str) -> Tuple[Optional[Any], Optional[CacheLevel]]:
        """Get value from L2 persistent cache."""
        try:
            # Load L2 cache if not in memory
            if not hasattr(self, '_l2_cache_memory'):
                await self._load_l2_cache()

            entry = self._l2_cache_memory.get(key)
            if entry and not entry.is_expired():
                entry.update_access()
                return entry.value, CacheLevel.L2_PERSISTENT
        except Exception as e:
            logger.error(f"Error accessing L2 cache: {e}")
        return None, None

    async def _get_from_l3(self, key: str) -> Tuple[Optional[Any], Optional[CacheLevel]]:
        """Get value from L3 archive cache."""
        try:
            # L3 cache is compressed and needs special handling
            # For now, return None - L3 would need file decompression
            pass
        except Exception as e:
            logger.error(f"Error accessing L3 cache: {e}")
        return None, None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
                   tags: Optional[Set[str]] = None, level: Optional[CacheLevel] = None) -> None:
        """
        Set value in cache with multi-level storage.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            tags: Optional tags for categorization
            level: Target cache level
        """
        if not self._initialized:
            return

        # Determine target level
        if level is None:
            level = CacheLevel.L1_MEMORY

        # Create cache entry
        ttl = ttl_seconds or self.config.default_ttl_seconds
        entry = CacheEntry(
            key=key,
            value=value,
            level=level,
            created_at=datetime.utcnow(),
            accessed_at=datetime.utcnow(),
            ttl_seconds=ttl,
            tags=tags or set()
        )

        # Store in appropriate level
        if level == CacheLevel.L1_MEMORY:
            await self._store_in_l1(key, entry)
        elif level == CacheLevel.L2_PERSISTENT:
            await self._store_in_l2(key, entry)
            # Also store in L1 for faster access
            await self._store_in_l1(key, entry)

        self._stats["cache_saves"] += 1
        logger.debug(f"Cache set: {key} in {level.value}")

    async def _store_in_l1(self, key: str, entry: CacheEntry) -> None:
        """Store in L1 memory cache."""
        # Check size limits
        if len(self._l1_cache) >= self.config.l1_max_entries:
            await self._evict_from_l1()

        # Check memory limits
        total_size = sum(e.size_bytes for e in self._l1_cache.values())
        if total_size + entry.size_bytes > self.config.l1_max_size_mb * 1024 * 1024:
            await self._evict_from_l1_by_size(entry.size_bytes)

        self._l1_cache[key] = entry

    async def _store_in_l2(self, key: str, entry: CacheEntry) -> None:
        """Store in L2 persistent cache."""
        try:
            if not hasattr(self, '_l2_cache_memory'):
                self._l2_cache_memory = {}

            # Check size limits
            if len(self._l2_cache_memory) >= self.config.l2_max_entries:
                await self._evict_from_l2()

            # Store in memory and file
            self._l2_cache_memory[key] = entry
            await self._save_l2_cache()

        except Exception as e:
            logger.error(f"Error storing in L2 cache: {e}")

    async def _evict_from_l1(self) -> None:
        """Evict entries from L1 cache using LRU."""
        if not self._l1_cache:
            return

        # Sort by last access time
        sorted_entries = sorted(self._l1_cache.items(),
                                 key=lambda x: x[1].accessed_at)

        # Remove oldest 20% of entries
        evict_count = max(1, len(sorted_entries) // 5)
        for i in range(evict_count):
            key, entry = sorted_entries[i]
            # Promote to L2 if still valid
            if not entry.is_expired():
                await self._promote_to_l2(key, entry.value)
            del self._l1_cache[key]

        logger.debug(f"Evicted {evict_count} entries from L1 cache")

    async def _evict_from_l1_by_size(self, required_size: int) -> None:
        """Evict entries from L1 cache by size."""
        if not self._l1_cache:
            return

        # Sort by size (largest first)
        sorted_entries = sorted(self._l1_cache.items(),
                                 key=lambda x: x[1].size_bytes,
                                 reverse=True)

        removed_size = 0
        for key, entry in sorted_entries:
            del self._l1_cache[key]
            removed_size += entry.size_bytes
            if removed_size >= required_size:
                break

        logger.debug(f"Evicted {len(sorted_entries)} entries from L1 cache by size")

    async def _evict_from_l2(self) -> None:
        """Evict entries from L2 cache using LRU."""
        if not hasattr(self, '_l2_cache_memory') or not self._l2_cache_memory:
            return

        # Sort by last access time
        sorted_entries = sorted(self._l2_cache_memory.items(),
                                 key=lambda x: x[1].accessed_at)

        # Remove oldest 10% of entries
        evict_count = max(1, len(sorted_entries) // 10)
        for i in range(evict_count):
            del self._l2_cache_memory[sorted_entries[i][0]]

        # Save updated L2 cache
        await self._save_l2_cache()
        logger.debug(f"Evicted {evict_count} entries from L2 cache")

    async def _promote_to_l1(self, key: str, value: Any) -> None:
        """Promote value to L1 cache."""
        await self.set(key, value, level=CacheLevel.L1_MEMORY)

    async def _promote_to_l2(self, key: str, value: Any) -> None:
        """Promote value to L2 cache."""
        await self.set(key, value, level=CacheLevel.L2_PERSISTENT)

    async def get_differential_update(self, key: str, base_version: str) -> Optional[DifferentialUpdate]:
        """
        Get differential update for a cache key.

        Args:
            key: Cache key
            base_version: Base version to calculate delta from

        Returns:
            Differential update or None if not available
        """
        try:
            current_value = await self.get(key)
            if current_value is None:
                return None

            # Calculate delta
            delta_data = self._calculate_delta(current_value, base_version)

            if not delta_data:
                return None

            # Create differential update
            current_data_str = json.dumps(current_value, sort_keys=True, default=str)
            base_data_str = json.dumps(base_version, sort_keys=True, default=str) if isinstance(base_version, (dict, list)) else str(base_version)

            update = DifferentialUpdate(
                base_version=hashlib.md5(base_data_str.encode('utf-8')).hexdigest()[:8],
                delta_data=delta_data,
                timestamp=datetime.utcnow(),
                delta_size_bytes=len(json.dumps(delta_data).encode('utf-8')),
                compression_ratio=len(json.dumps(delta_data).encode('utf-8')) / len(current_data_str.encode('utf-8'))
            )

            self._stats["differential_updates"] += 1
            self._stats["bytes_saved"] += update.bytes_saved

            return update

        except Exception as e:
            logger.error(f"Error calculating differential update: {e}")
            return None

    def _calculate_delta(self, current_value: Any, base_value: Any) -> Optional[Dict[str, Any]]:
        """Calculate delta between current and base values."""
        try:
            if isinstance(current_value, dict) and isinstance(base_value, dict):
                delta = {}
                for key, value in current_value.items():
                    if key not in base_value or base_value[key] != value:
                        delta[key] = value
                return delta if delta else None
            elif current_value != base_value:
                return {"value": current_value}
            else:
                return None
        except Exception:
            return None

    async def apply_differential_update(self, key: str, differential_update: DifferentialUpdate) -> bool:
        """
        Apply differential update to cached value.

        Args:
            key: Cache key
            differential_update: Differential update to apply

        Returns:
            True if update was applied successfully
        """
        try:
            current_value = await self.get(key)
            if current_value is None:
                return False

            # Apply delta (simplified implementation)
            if isinstance(current_value, dict) and isinstance(differential_update.delta_data, dict):
                for key, value in differential_update.delta_data.items():
                    current_value[key] = value

                # Update cache with new value
                await self.set(key, current_value)
                return True

        except Exception as e:
            logger.error(f"Error applying differential update: {e}")

        return False

    async def _update_cache_access(self, level: CacheLevel, key: str) -> None:
        """Update access information for cache entry."""
        try:
            if level == CacheLevel.L1_MEMORY and key in self._l1_cache:
                self._l1_cache[key].update_access()
            elif level == CacheLevel.L2_PERSISTENT and hasattr(self, '_l2_cache_memory') and key in self._l2_cache_memory:
                self._l2_cache_memory[key].update_access()
                await self._save_l2_cache()
        except Exception as e:
            logger.error(f"Error updating cache access: {e}")

    async def _load_l2_cache(self) -> None:
        """Load L2 cache from file."""
        try:
            if os.path.exists(self._l2_cache_file):
                async with aiofiles.open(self._l2_cache_file, 'r') as f:
                    content = await f.read()
                    if content:
                        cache_data = json.loads(content)
                        self._l2_cache_memory = {}
                        for key, entry_data in cache_data.items():
                            entry = CacheEntry(**entry_data)
                            # Convert timestamp strings back to datetime
                            entry.created_at = datetime.fromisoformat(entry.created_at)
                            entry.accessed_at = datetime.fromisoformat(entry.accessed_at)
                            self._l2_cache_memory[key] = entry
        except Exception as e:
            logger.error(f"Error loading L2 cache: {e}")
            self._l2_cache_memory = {}

    async def _save_l2_cache(self) -> None:
        """Save L2 cache to file."""
        try:
            if not hasattr(self, '_l2_cache_memory'):
                return

            cache_data = {}
            for key, entry in self._l2_cache_memory.items():
                entry_dict = asdict(entry)
                # Convert datetime objects to strings
                entry_dict['created_at'] = entry.created_at.isoformat()
                entry_dict['accessed_at'] = entry.accessed_at.isoformat()
                entry_dict['tags'] = list(entry.tags)
                cache_data[key] = entry_dict

            async with aiofiles.open(self._l2_cache_file, 'w') as f:
                await f.write(json.dumps(cache_data, indent=2))
        except Exception as e:
            logger.error(f"Error saving L2 cache: {e}")

    async def _background_cleanup(self) -> None:
        """Background task for cache cleanup."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired_entries()
                await self._optimize_cache_size()
            except asyncio.CancelledError:
                logger.info("Cache cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired cache entries."""
        # Clean L1 cache
        expired_l1 = [key for key, entry in self._l1_cache.items() if entry.is_expired()]
        for key in expired_l1:
            del self._l1_cache[key]

        # Clean L2 cache
        if hasattr(self, '_l2_cache_memory'):
            expired_l2 = [key for key, entry in self._l2_cache_memory.items() if entry.is_expired()]
            for key in expired_l2:
                del self._l2_cache_memory[key]

        if expired_l1 or expired_l2:
            await self._save_l2_cache()
            logger.debug(f"Cleaned up {len(expired_l1) + len(expired_l2)} expired cache entries")

    async def _optimize_cache_size(self) -> None:
        """Optimize cache size and performance."""
        # Promote frequently accessed L2 items to L1
        if hasattr(self, '_l2_cache_memory'):
            hot_l2_items = [(key, entry) for key, entry in self._l2_cache_memory.items()
                           if entry.access_count > 3 and not entry.is_expired()]

            # Sort by access frequency
            hot_l2_items.sort(key=lambda x: x[1].access_count, reverse=True)

            # Promote top 10 hot items to L1
            for key, entry in hot_l2_items[:10]:
                if len(self._l1_cache) < self.config.l1_max_entries:
                    await self._promote_to_l1(key, entry.value)

    async def get_cache_analytics(self) -> Dict[str, Any]:
        """Get comprehensive cache analytics."""
        if not self._initialized:
            return {"error": "Cache not initialized"}

        total_requests = self._stats["total_requests"]
        if total_requests == 0:
            total_requests = 1

        return {
            "statistics": {
                **self._stats,
                "l1_hit_rate": self._stats["l1_hits"] / total_requests,
                "l2_hit_rate": self._stats["l2_hits"] / total_requests,
                "l3_hit_rate": self._stats["l3_hits"] / total_requests,
                "overall_hit_rate": (self._stats["l1_hits"] + self._stats["l2_hits"] + self._stats["l3_hits"]) / total_requests
            },
            "current_usage": {
                "l1_entries": len(self._l1_cache),
                "l1_size_mb": sum(e.size_bytes for e in self._l1_cache.values()) / (1024 * 1024),
                "l2_entries": len(self._l2_cache_memory) if hasattr(self, '_l2_cache_memory') else 0,
                "l2_size_mb": sum(e.size_bytes for e in self._l2_cache_memory.values()) / (1024 * 1024) if hasattr(self, '_l2_cache_memory') else 0
            },
            "efficiency": {
                "tokens_saved": self._stats["tokens_saved"],
                "bytes_saved": self._stats["bytes_saved"],
                "differential_updates": self._stats["differential_updates"],
                "compression_ratio": self._stats["bytes_saved"] / max(1, sum(e.size_bytes for e in self._l1_cache.values())) if self._l1_cache else 1
            },
            "configuration": asdict(self.config)
        }

    async def cleanup(self) -> None:
        """Cleanup cache resources."""
        try:
            # Cancel background task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Save L2 cache
            await self._save_l2_cache()

            # Clear memory caches
            self._l1_cache.clear()
            if hasattr(self, '_l2_cache_memory'):
                self._l2_cache_memory.clear()

            self._initialized = False
            logger.info("Token Efficient Cache cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")