"""
Scalability & Performance Service

Provides horizontal scaling support, database optimization, caching, API rate limiting,
and background job processing optimization for high-performance trading operations.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import redis.asyncio as redis
import aiosqlite
from loguru import logger

from src.config import Config
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from ..core.errors import TradingError, APIError


class CacheStrategy(Enum):
    """Caching strategies."""
    LRU = "lru"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"


class ScalingMode(Enum):
    """Horizontal scaling modes."""
    SINGLE_NODE = "single_node"
    MULTI_NODE = "multi_node"
    CLUSTERED = "clustered"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    ttl_seconds: Optional[int]
    created_at: str
    access_count: int = 0
    last_accessed: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at


@dataclass
class RateLimitRule:
    """API rate limiting rule."""
    endpoint: str
    requests_per_minute: int
    burst_limit: int
    cooldown_seconds: int


@dataclass
class PerformanceMetrics:
    """Performance optimization metrics."""
    operation: str
    execution_time: float
    cache_hit: bool
    database_queries: int
    timestamp: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ScalabilityService(EventHandler):
    """
    Scalability & Performance Service.

    Responsibilities:
    - Horizontal scaling support and load balancing
    - Database optimization and query performance
    - Multi-level caching (Redis + in-memory)
    - API rate limiting and throttling
    - Background job processing optimization
    - Performance monitoring and bottleneck detection
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "scalability.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connections
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._redis_client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()

        # Caching
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_strategy = CacheStrategy.TTL
        self._default_ttl = 300  # 5 minutes

        # Rate limiting
        self._rate_limits: Dict[str, RateLimitRule] = {}
        self._request_counts: Dict[str, List[datetime]] = {}

        # Scaling configuration
        self._scaling_mode = ScalingMode.SINGLE_NODE
        self._max_concurrent_jobs = 10
        self._job_queue_size = 1000

        # Performance monitoring
        self._performance_metrics: List[PerformanceMetrics] = []
        self._slow_query_threshold = 1.0  # seconds

        # Background tasks
        self._cache_cleanup_task: Optional[asyncio.Task] = None
        self._performance_monitor_task: Optional[asyncio.Task] = None

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_PLACED, self)
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)

    async def initialize(self) -> None:
        """Initialize the scalability service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()

            # Initialize Redis if configured
            await self._initialize_redis()

            # Setup default rate limits
            await self._setup_default_rate_limits()

            logger.info("Scalability service initialized")

            # Start background tasks
            self._cache_cleanup_task = asyncio.create_task(self._cache_cleanup())
            self._performance_monitor_task = asyncio.create_task(self._performance_monitoring())

    async def _create_tables(self) -> None:
        """Create scalability database tables."""
        schema = """
        -- Performance metrics
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY,
            operation TEXT NOT NULL,
            execution_time REAL NOT NULL,
            cache_hit INTEGER NOT NULL,
            database_queries INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        );

        -- Cache statistics
        CREATE TABLE IF NOT EXISTS cache_stats (
            id INTEGER PRIMARY KEY,
            cache_key TEXT NOT NULL,
            hits INTEGER DEFAULT 0,
            misses INTEGER DEFAULT 0,
            last_updated TEXT NOT NULL
        );

        -- Rate limit violations
        CREATE TABLE IF NOT EXISTS rate_limit_violations (
            id INTEGER PRIMARY KEY,
            endpoint TEXT NOT NULL,
            client_id TEXT,
            violation_count INTEGER NOT NULL,
            last_violation TEXT NOT NULL,
            blocked_until TEXT
        );

        -- Database query optimization
        CREATE TABLE IF NOT EXISTS query_optimization (
            id INTEGER PRIMARY KEY,
            query_hash TEXT UNIQUE NOT NULL,
            query_text TEXT NOT NULL,
            execution_count INTEGER DEFAULT 0,
            avg_execution_time REAL DEFAULT 0.0,
            last_executed TEXT NOT NULL,
            optimization_suggestions TEXT
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics(operation);
        CREATE INDEX IF NOT EXISTS idx_cache_stats_key ON cache_stats(cache_key);
        CREATE INDEX IF NOT EXISTS idx_rate_limit_endpoint ON rate_limit_violations(endpoint);
        CREATE INDEX IF NOT EXISTS idx_query_hash ON query_optimization(query_hash);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _initialize_redis(self) -> None:
        """Initialize Redis client if configured."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            await self._redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed, using memory cache only: {e}")
            self._redis_client = None

    async def _setup_default_rate_limits(self) -> None:
        """Setup default API rate limiting rules."""
        default_rules = [
            RateLimitRule("/api/orders", 60, 10, 60),  # 60 per minute, burst 10, 1min cooldown
            RateLimitRule("/api/market-data", 300, 50, 30),  # 300 per minute for market data
            RateLimitRule("/api/portfolio", 120, 20, 30),  # 120 per minute for portfolio
            RateLimitRule("/api/analytics", 60, 10, 60),  # 60 per minute for analytics
        ]

        for rule in default_rules:
            self._rate_limits[rule.endpoint] = rule

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache with fallback to Redis."""
        # Try memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]

            # Check TTL
            if entry.ttl_seconds:
                created = datetime.fromisoformat(entry.created_at)
                if (datetime.now(timezone.utc) - created).total_seconds() > entry.ttl_seconds:
                    del self._memory_cache[key]
                    await self._update_cache_stats(key, hit=False)
                    return None

            entry.access_count += 1
            entry.last_accessed = datetime.now(timezone.utc).isoformat()
            await self._update_cache_stats(key, hit=True)
            return entry.value

        # Try Redis cache
        if self._redis_client:
            try:
                value_json = await self._redis_client.get(f"cache:{key}")
                if value_json:
                    value = json.loads(value_json)
                    # Store in memory cache for faster access
                    entry = CacheEntry(key=key, value=value, ttl_seconds=self._default_ttl)
                    self._memory_cache[key] = entry
                    await self._update_cache_stats(key, hit=True)
                    return value
            except Exception as e:
                logger.error(f"Redis cache get error: {e}")

        await self._update_cache_stats(key, hit=False)
        return None

    async def cache_set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl_seconds or self._default_ttl

        # Store in memory cache
        entry = CacheEntry(key=key, value=value, ttl_seconds=ttl)
        self._memory_cache[key] = entry

        # Store in Redis if available
        if self._redis_client:
            try:
                value_json = json.dumps(value)
                await self._redis_client.setex(f"cache:{key}", ttl, value_json)
            except Exception as e:
                logger.error(f"Redis cache set error: {e}")

    async def cache_delete(self, key: str) -> None:
        """Delete value from cache."""
        # Remove from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]

        # Remove from Redis
        if self._redis_client:
            try:
                await self._redis_client.delete(f"cache:{key}")
            except Exception as e:
                logger.error(f"Redis cache delete error: {e}")

    async def _update_cache_stats(self, key: str, hit: bool) -> None:
        """Update cache statistics."""
        try:
            cursor = await self._db_connection.execute(
                "SELECT hits, misses FROM cache_stats WHERE cache_key = ?", (key,)
            )
            row = await cursor.fetchone()

            if row:
                hits, misses = row
                if hit:
                    hits += 1
                else:
                    misses += 1
                await self._db_connection.execute(
                    "UPDATE cache_stats SET hits = ?, misses = ?, last_updated = ? WHERE cache_key = ?",
                    (hits, misses, datetime.now(timezone.utc).isoformat(), key)
                )
            else:
                hits = 1 if hit else 0
                misses = 0 if hit else 1
                await self._db_connection.execute(
                    "INSERT INTO cache_stats (cache_key, hits, misses, last_updated) VALUES (?, ?, ?, ?)",
                    (key, hits, misses, datetime.now(timezone.utc).isoformat())
                )

            await self._db_connection.commit()

        except Exception as e:
            logger.error(f"Failed to update cache stats: {e}")

    async def check_rate_limit(self, endpoint: str, client_id: str = "anonymous") -> Dict[str, Any]:
        """Check if request is within rate limits."""
        if endpoint not in self._rate_limits:
            return {"allowed": True, "remaining": 999, "reset_in": 60}

        rule = self._rate_limits[endpoint]
        client_key = f"{endpoint}:{client_id}"

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)

        # Get request timestamps for this client
        if client_key not in self._request_counts:
            self._request_counts[client_key] = []

        # Clean old requests outside the window
        self._request_counts[client_key] = [
            ts for ts in self._request_counts[client_key] if ts > window_start
        ]

        request_count = len(self._request_counts[client_key])

        # Check burst limit
        if request_count >= rule.requests_per_minute:
            # Check if in cooldown
            if self._request_counts[client_key]:
                oldest_request = min(self._request_counts[client_key])
                cooldown_end = oldest_request + timedelta(seconds=rule.cooldown_seconds)

                if now < cooldown_end:
                    remaining_cooldown = int((cooldown_end - now).total_seconds())
                    await self._record_rate_limit_violation(endpoint, client_id)
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_in": remaining_cooldown,
                        "retry_after": remaining_cooldown
                    }

        # Check regular rate limit
        if request_count >= rule.requests_per_minute:
            reset_in = 60  # Reset in 1 minute
            return {
                "allowed": False,
                "remaining": 0,
                "reset_in": reset_in,
                "retry_after": reset_in
            }

        # Add current request
        self._request_counts[client_key].append(now)

        remaining = rule.requests_per_minute - request_count - 1
        return {
            "allowed": True,
            "remaining": remaining,
            "reset_in": 60
        }

    async def _record_rate_limit_violation(self, endpoint: str, client_id: str) -> None:
        """Record a rate limit violation."""
        try:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self._db_connection.execute(
                "SELECT violation_count FROM rate_limit_violations WHERE endpoint = ? AND client_id = ?",
                (endpoint, client_id)
            )
            row = await cursor.fetchone()

            if row:
                violation_count = row[0] + 1
                await self._db_connection.execute(
                    "UPDATE rate_limit_violations SET violation_count = ?, last_violation = ? WHERE endpoint = ? AND client_id = ?",
                    (violation_count, now, endpoint, client_id)
                )
            else:
                await self._db_connection.execute(
                    "INSERT INTO rate_limit_violations (endpoint, client_id, violation_count, last_violation) VALUES (?, ?, 1, ?)",
                    (endpoint, client_id, now)
                )

            await self._db_connection.commit()

        except Exception as e:
            logger.error(f"Failed to record rate limit violation: {e}")

    async def optimize_database_query(self, query: str, execution_time: float) -> None:
        """Record and analyze database query performance."""
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()

            cursor = await self._db_connection.execute(
                "SELECT execution_count, avg_execution_time FROM query_optimization WHERE query_hash = ?",
                (query_hash,)
            )
            row = await cursor.fetchone()

            now = datetime.now(timezone.utc).isoformat()

            if row:
                execution_count, avg_time = row
                new_count = execution_count + 1
                new_avg = ((avg_time * execution_count) + execution_time) / new_count

                suggestions = self._generate_query_optimization_suggestions(query, execution_time)

                await self._db_connection.execute("""
                    UPDATE query_optimization SET
                    execution_count = ?, avg_execution_time = ?, last_executed = ?, optimization_suggestions = ?
                    WHERE query_hash = ?
                """, (new_count, new_avg, now, json.dumps(suggestions), query_hash))
            else:
                suggestions = self._generate_query_optimization_suggestions(query, execution_time)
                await self._db_connection.execute("""
                    INSERT INTO query_optimization
                    (query_hash, query_text, execution_count, avg_execution_time, last_executed, optimization_suggestions)
                    VALUES (?, ?, 1, ?, ?, ?)
                """, (query_hash, query, execution_time, now, json.dumps(suggestions)))

            await self._db_connection.commit()

        except Exception as e:
            logger.error(f"Failed to optimize database query: {e}")

    def _generate_query_optimization_suggestions(self, query: str, execution_time: float) -> List[str]:
        """Generate query optimization suggestions."""
        suggestions = []

        if execution_time > self._slow_query_threshold:
            suggestions.append("Query execution time exceeds threshold - consider optimization")

        if "SELECT *" in query.upper():
            suggestions.append("Avoid SELECT * - specify required columns")

        if "WHERE" not in query.upper() and "LIMIT" not in query.upper():
            suggestions.append("Consider adding WHERE clause or LIMIT to reduce result set")

        return suggestions

    async def record_performance_metric(self, operation: str, execution_time: float,
                                      cache_hit: bool, database_queries: int) -> None:
        """Record performance metric."""
        try:
            metric = PerformanceMetrics(
                operation=operation,
                execution_time=execution_time,
                cache_hit=cache_hit,
                database_queries=database_queries
            )

            self._performance_metrics.append(metric)

            # Store in database
            await self._db_connection.execute("""
                INSERT INTO performance_metrics
                (operation, execution_time, cache_hit, database_queries, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metric.operation,
                metric.execution_time,
                int(metric.cache_hit),
                metric.database_queries,
                metric.timestamp
            ))

            await self._db_connection.commit()

        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        try:
            # Cache statistics
            cache_stats = await self._get_cache_statistics()

            # Database performance
            db_stats = await self._get_database_performance_stats()

            # Rate limiting stats
            rate_limit_stats = await self._get_rate_limit_statistics()

            return {
                "cache_performance": cache_stats,
                "database_performance": db_stats,
                "rate_limiting": rate_limit_stats,
                "system_load": {
                    "active_connections": len(asyncio.all_tasks()),
                    "memory_cache_size": len(self._memory_cache),
                    "redis_available": self._redis_client is not None
                }
            }

        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {"error": str(e)}

    async def _get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        cursor = await self._db_connection.execute("""
            SELECT SUM(hits) as total_hits, SUM(misses) as total_misses,
                   COUNT(*) as cached_keys
            FROM cache_stats
        """)

        row = await cursor.fetchone()
        total_hits = row[0] or 0
        total_misses = row[1] or 0
        total_requests = total_hits + total_misses

        return {
            "total_requests": total_requests,
            "hit_rate": total_hits / total_requests if total_requests > 0 else 0,
            "miss_rate": total_misses / total_requests if total_requests > 0 else 0,
            "cached_keys": row[2] or 0,
            "memory_cache_size": len(self._memory_cache)
        }

    async def _get_database_performance_stats(self) -> Dict[str, Any]:
        """Get database performance statistics."""
        cursor = await self._db_connection.execute("""
            SELECT AVG(execution_time) as avg_query_time,
                   MAX(execution_time) as max_query_time,
                   COUNT(*) as total_queries
            FROM performance_metrics
            WHERE operation LIKE '%db%'
        """)

        row = await cursor.fetchone()

        return {
            "average_query_time": row[0] or 0,
            "max_query_time": row[1] or 0,
            "total_queries": row[2] or 0,
            "slow_queries": await self._count_slow_queries()
        }

    async def _count_slow_queries(self) -> int:
        """Count slow database queries."""
        cursor = await self._db_connection.execute("""
            SELECT COUNT(*) FROM performance_metrics
            WHERE operation LIKE '%db%' AND execution_time > ?
        """, (self._slow_query_threshold,))

        row = await cursor.fetchone()
        return row[0] if row else 0

    async def _get_rate_limit_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        cursor = await self._db_connection.execute("""
            SELECT COUNT(*) as total_violations,
                   COUNT(DISTINCT endpoint) as affected_endpoints
            FROM rate_limit_violations
        """)

        row = await cursor.fetchone()

        return {
            "total_violations": row[0] or 0,
            "affected_endpoints": row[1] or 0,
            "active_rules": len(self._rate_limits)
        }

    async def _cache_cleanup(self) -> None:
        """Background task to clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Clean up every minute

                now = datetime.now(timezone.utc)
                expired_keys = []

                for key, entry in self._memory_cache.items():
                    if entry.ttl_seconds:
                        created = datetime.fromisoformat(entry.created_at)
                        if (now - created).total_seconds() > entry.ttl_seconds:
                            expired_keys.append(key)

                for key in expired_keys:
                    del self._memory_cache[key]

                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            except asyncio.CancelledError:
                logger.info("Cache cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(30)

    async def _performance_monitoring(self) -> None:
        """Background performance monitoring."""
        while True:
            try:
                await asyncio.sleep(300)  # Monitor every 5 minutes

                # Analyze performance trends
                await self._analyze_performance_trends()

                # Check for bottlenecks
                await self._detect_bottlenecks()

            except asyncio.CancelledError:
                logger.info("Performance monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(60)

    async def _analyze_performance_trends(self) -> None:
        """Analyze performance trends and generate insights."""
        # This would analyze recent performance metrics and identify trends
        pass

    async def _detect_bottlenecks(self) -> None:
        """Detect system bottlenecks and performance issues."""
        # This would analyze various metrics to detect bottlenecks
        pass

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        # Performance monitoring for high-frequency events
        pass

    async def close(self) -> None:
        """Close the scalability service."""
        # Cancel background tasks
        if self._cache_cleanup_task:
            self._cache_cleanup_task.cancel()
            try:
                await self._cache_cleanup_task
            except asyncio.CancelledError:
                pass

        if self._performance_monitor_task:
            self._performance_monitor_task.cancel()
            try:
                await self._performance_monitor_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if self._redis_client:
            await self._redis_client.close()

        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None