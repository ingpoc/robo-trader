"""
Feature Management Database

Handles persistence of feature configurations, states, and dependencies
using SQLite with async operations.
"""

import asyncio
import json
import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from .models import (
    FeatureConfig, FeatureState, FeatureMetadata, FeatureDependency,
    FeatureToggleRequest, BulkFeatureUpdate, DependencyResolutionResult
)


class FeatureDatabase:
    """
    Database layer for feature management persistence.
    
    Provides async database operations for all feature-related data
    with proper error handling and connection management.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the database and create tables."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            logger.info(f"Feature database initialized at {self.db_path}")

    async def _create_tables(self) -> None:
        """Create all necessary database tables."""
        schema = """
        -- Feature configurations table
        CREATE TABLE IF NOT EXISTS feature_configs (
            feature_id TEXT PRIMARY KEY,
            metadata TEXT NOT NULL,
            dependencies TEXT NOT NULL,
            default_enabled BOOLEAN NOT NULL DEFAULT 0,
            auto_start BOOLEAN NOT NULL DEFAULT 0,
            restart_on_failure BOOLEAN NOT NULL DEFAULT 1,
            max_retries INTEGER NOT NULL DEFAULT 3,
            timeout_seconds INTEGER NOT NULL DEFAULT 30,
            resource_requirements TEXT NOT NULL DEFAULT '{}',
            environment_variables TEXT NOT NULL DEFAULT '{}',
            configuration_schema TEXT,
            health_check_url TEXT,
            metrics_enabled BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Feature states table
        CREATE TABLE IF NOT EXISTS feature_states (
            feature_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT 0,
            last_enabled_at TEXT,
            last_disabled_at TEXT,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            last_error_at TEXT,
            restart_count INTEGER NOT NULL DEFAULT 0,
            health_status TEXT NOT NULL DEFAULT 'unknown',
            last_health_check TEXT,
            metrics TEXT NOT NULL DEFAULT '{}',
            configuration TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (feature_id) REFERENCES feature_configs(feature_id) ON DELETE CASCADE
        );

        -- Feature audit log table
        CREATE TABLE IF NOT EXISTS feature_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id TEXT NOT NULL,
            action TEXT NOT NULL,
            old_state TEXT,
            new_state TEXT,
            reason TEXT,
            requested_by TEXT,
            timestamp TEXT NOT NULL,
            correlation_id TEXT,
            FOREIGN KEY (feature_id) REFERENCES feature_configs(feature_id) ON DELETE CASCADE
        );

        -- Dependency resolution cache table
        CREATE TABLE IF NOT EXISTS dependency_cache (
            cache_key TEXT PRIMARY KEY,
            resolution_result TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        -- Feature metrics table
        CREATE TABLE IF NOT EXISTS feature_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_unit TEXT,
            timestamp TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (feature_id) REFERENCES feature_configs(feature_id) ON DELETE CASCADE
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_feature_configs_enabled ON feature_configs(default_enabled);
        CREATE INDEX IF NOT EXISTS idx_feature_configs_type ON feature_configs(feature_id);
        CREATE INDEX IF NOT EXISTS idx_feature_states_status ON feature_states(status);
        CREATE INDEX IF NOT EXISTS idx_feature_states_enabled ON feature_states(enabled);
        CREATE INDEX IF NOT EXISTS idx_feature_audit_log_feature_id ON feature_audit_log(feature_id);
        CREATE INDEX IF NOT EXISTS idx_feature_audit_log_timestamp ON feature_audit_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_feature_metrics_feature_id ON feature_metrics(feature_id);
        CREATE INDEX IF NOT EXISTS idx_feature_metrics_timestamp ON feature_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_dependency_cache_expires ON dependency_cache(expires_at);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    # Feature Configuration Operations

    async def create_feature_config(self, config: FeatureConfig) -> bool:
        """Create a new feature configuration."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute("""
                INSERT INTO feature_configs (
                    feature_id, metadata, dependencies, default_enabled, auto_start,
                    restart_on_failure, max_retries, timeout_seconds,
                    resource_requirements, environment_variables, configuration_schema,
                    health_check_url, metrics_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config.feature_id,
                json.dumps(config.metadata.to_dict()),
                json.dumps([dep.to_dict() for dep in config.dependencies]),
                config.default_enabled,
                config.auto_start,
                config.restart_on_failure,
                config.max_retries,
                config.timeout_seconds,
                json.dumps(config.resource_requirements),
                json.dumps(config.environment_variables),
                json.dumps(config.configuration_schema) if config.configuration_schema else None,
                config.health_check_url,
                config.metrics_enabled,
                now,
                now
            ))
            await self._db_connection.commit()
            
            # Create initial state
            await self.create_feature_state(FeatureState(
                feature_id=config.feature_id,
                status=config.default_enabled and "enabled" or "disabled",
                enabled=config.default_enabled
            ))
            
            logger.info(f"Created feature config: {config.feature_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create feature config {config.feature_id}: {e}")
            return False

    async def get_feature_config(self, feature_id: str) -> Optional[FeatureConfig]:
        """Get a feature configuration by ID."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT feature_id, metadata, dependencies, default_enabled, auto_start,
                       restart_on_failure, max_retries, timeout_seconds,
                       resource_requirements, environment_variables, configuration_schema,
                       health_check_url, metrics_enabled, created_at, updated_at
                FROM feature_configs
                WHERE feature_id = ?
            """, (feature_id,))
            
            row = await cursor.fetchone()
            if row:
                return self._row_to_feature_config(row)
            return None

    async def get_all_feature_configs(self) -> List[FeatureConfig]:
        """Get all feature configurations."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT feature_id, metadata, dependencies, default_enabled, auto_start,
                       restart_on_failure, max_retries, timeout_seconds,
                       resource_requirements, environment_variables, configuration_schema,
                       health_check_url, metrics_enabled, created_at, updated_at
                FROM feature_configs
                ORDER BY feature_id
            """)
            
            configs = []
            async for row in cursor:
                configs.append(self._row_to_feature_config(row))
            return configs

    async def update_feature_config(self, config: FeatureConfig) -> bool:
        """Update an existing feature configuration."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute("""
                UPDATE feature_configs SET
                    metadata = ?, dependencies = ?, default_enabled = ?, auto_start = ?,
                    restart_on_failure = ?, max_retries = ?, timeout_seconds = ?,
                    resource_requirements = ?, environment_variables = ?, configuration_schema = ?,
                    health_check_url = ?, metrics_enabled = ?, updated_at = ?
                WHERE feature_id = ?
            """, (
                json.dumps(config.metadata.to_dict()),
                json.dumps([dep.to_dict() for dep in config.dependencies]),
                config.default_enabled,
                config.auto_start,
                config.restart_on_failure,
                config.max_retries,
                config.timeout_seconds,
                json.dumps(config.resource_requirements),
                json.dumps(config.environment_variables),
                json.dumps(config.configuration_schema) if config.configuration_schema else None,
                config.health_check_url,
                config.metrics_enabled,
                now,
                config.feature_id
            ))
            await self._db_connection.commit()
            
            logger.info(f"Updated feature config: {config.feature_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update feature config {config.feature_id}: {e}")
            return False

    async def delete_feature_config(self, feature_id: str) -> bool:
        """Delete a feature configuration."""
        try:
            await self._db_connection.execute("""
                DELETE FROM feature_configs WHERE feature_id = ?
            """, (feature_id,))
            await self._db_connection.commit()
            
            logger.info(f"Deleted feature config: {feature_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete feature config {feature_id}: {e}")
            return False

    # Feature State Operations

    async def create_feature_state(self, state: FeatureState) -> bool:
        """Create a new feature state."""
        try:
            await self._db_connection.execute("""
                INSERT INTO feature_states (
                    feature_id, status, enabled, last_enabled_at, last_disabled_at,
                    error_count, last_error, last_error_at, restart_count,
                    health_status, last_health_check, metrics, configuration,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.feature_id,
                state.status.value,
                state.enabled,
                state.last_enabled_at,
                state.last_disabled_at,
                state.error_count,
                state.last_error,
                state.last_error_at,
                state.restart_count,
                state.health_status,
                state.last_health_check,
                json.dumps(state.metrics),
                json.dumps(state.configuration),
                state.created_at,
                state.updated_at
            ))
            await self._db_connection.commit()
            
            logger.debug(f"Created feature state: {state.feature_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create feature state {state.feature_id}: {e}")
            return False

    async def get_feature_state(self, feature_id: str) -> Optional[FeatureState]:
        """Get a feature state by ID."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT feature_id, status, enabled, last_enabled_at, last_disabled_at,
                       error_count, last_error, last_error_at, restart_count,
                       health_status, last_health_check, metrics, configuration,
                       created_at, updated_at
                FROM feature_states
                WHERE feature_id = ?
            """, (feature_id,))
            
            row = await cursor.fetchone()
            if row:
                return self._row_to_feature_state(row)
            return None

    async def get_all_feature_states(self) -> List[FeatureState]:
        """Get all feature states."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT feature_id, status, enabled, last_enabled_at, last_disabled_at,
                       error_count, last_error, last_error_at, restart_count,
                       health_status, last_health_check, metrics, configuration,
                       created_at, updated_at
                FROM feature_states
                ORDER BY feature_id
            """)
            
            states = []
            async for row in cursor:
                states.append(self._row_to_feature_state(row))
            return states

    async def update_feature_state(self, state: FeatureState) -> bool:
        """Update an existing feature state."""
        try:
            await self._db_connection.execute("""
                UPDATE feature_states SET
                    status = ?, enabled = ?, last_enabled_at = ?, last_disabled_at = ?,
                    error_count = ?, last_error = ?, last_error_at = ?, restart_count = ?,
                    health_status = ?, last_health_check = ?, metrics = ?, configuration = ?,
                    updated_at = ?
                WHERE feature_id = ?
            """, (
                state.status.value,
                state.enabled,
                state.last_enabled_at,
                state.last_disabled_at,
                state.error_count,
                state.last_error,
                state.last_error_at,
                state.restart_count,
                state.health_status,
                state.last_health_check,
                json.dumps(state.metrics),
                json.dumps(state.configuration),
                state.updated_at,
                state.feature_id
            ))
            await self._db_connection.commit()
            
            logger.debug(f"Updated feature state: {state.feature_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update feature state {state.feature_id}: {e}")
            return False

    # Audit Log Operations

    async def log_feature_action(
        self,
        feature_id: str,
        action: str,
        old_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        requested_by: str = "system",
        correlation_id: Optional[str] = None
    ) -> bool:
        """Log a feature action to the audit log."""
        try:
            await self._db_connection.execute("""
                INSERT INTO feature_audit_log (
                    feature_id, action, old_state, new_state, reason,
                    requested_by, timestamp, correlation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feature_id,
                action,
                json.dumps(old_state) if old_state else None,
                json.dumps(new_state) if new_state else None,
                reason,
                requested_by,
                datetime.now(timezone.utc).isoformat(),
                correlation_id
            ))
            await self._db_connection.commit()
            
            logger.debug(f"Logged feature action: {feature_id} - {action}")
            return True
        except Exception as e:
            logger.error(f"Failed to log feature action {feature_id}: {e}")
            return False

    async def get_feature_audit_log(
        self,
        feature_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        query = """
            SELECT id, feature_id, action, old_state, new_state, reason,
                   requested_by, timestamp, correlation_id
            FROM feature_audit_log
        """
        params = []
        
        if feature_id:
            query += " WHERE feature_id = ?"
            params.append(feature_id)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with self._lock:
            cursor = await self._db_connection.execute(query, params)
            
            entries = []
            async for row in cursor:
                entries.append({
                    "id": row[0],
                    "feature_id": row[1],
                    "action": row[2],
                    "old_state": json.loads(row[3]) if row[3] else None,
                    "new_state": json.loads(row[4]) if row[4] else None,
                    "reason": row[5],
                    "requested_by": row[6],
                    "timestamp": row[7],
                    "correlation_id": row[8]
                })
            return entries

    # Dependency Cache Operations

    async def cache_dependency_resolution(
        self,
        cache_key: str,
        result: DependencyResolutionResult,
        ttl_seconds: int = 300
    ) -> bool:
        """Cache a dependency resolution result."""
        try:
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
            
            await self._db_connection.execute("""
                INSERT OR REPLACE INTO dependency_cache (
                    cache_key, resolution_result, created_at, expires_at
                ) VALUES (?, ?, ?, ?)
            """, (
                cache_key,
                json.dumps(result.to_dict()),
                now.isoformat(),
                expires_at
            ))
            await self._db_connection.commit()
            
            return True
        except Exception as e:
            logger.error(f"Failed to cache dependency resolution: {e}")
            return False

    async def get_cached_dependency_resolution(self, cache_key: str) -> Optional[DependencyResolutionResult]:
        """Get a cached dependency resolution result."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT resolution_result FROM dependency_cache
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now(timezone.utc).isoformat()))
            
            row = await cursor.fetchone()
            if row:
                return DependencyResolutionResult.from_dict(json.loads(row[0]))
            return None

    # Metrics Operations

    async def record_feature_metric(
        self,
        feature_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a feature metric."""
        try:
            await self._db_connection.execute("""
                INSERT INTO feature_metrics (
                    feature_id, metric_name, metric_value, metric_unit, timestamp, tags
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                feature_id,
                metric_name,
                metric_value,
                metric_unit,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(tags or {})
            ))
            await self._db_connection.commit()
            
            return True
        except Exception as e:
            logger.error(f"Failed to record feature metric: {e}")
            return False

    async def get_feature_metrics(
        self,
        feature_id: str,
        metric_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get feature metrics."""
        query = """
            SELECT metric_name, metric_value, metric_unit, timestamp, tags
            FROM feature_metrics
            WHERE feature_id = ?
        """
        params = [feature_id]
        
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        async with self._lock:
            cursor = await self._db_connection.execute(query, params)
            
            metrics = []
            async for row in cursor:
                metrics.append({
                    "metric_name": row[0],
                    "metric_value": row[1],
                    "metric_unit": row[2],
                    "timestamp": row[3],
                    "tags": json.loads(row[4])
                })
            return metrics

    # Utility Methods

    def _row_to_feature_config(self, row) -> FeatureConfig:
        """Convert database row to FeatureConfig."""
        return FeatureConfig(
            feature_id=row[0],
            metadata=FeatureMetadata.from_dict(json.loads(row[1])),
            dependencies=[FeatureDependency.from_dict(dep) for dep in json.loads(row[2])],
            default_enabled=bool(row[3]),
            auto_start=bool(row[4]),
            restart_on_failure=bool(row[5]),
            max_retries=row[6],
            timeout_seconds=row[7],
            resource_requirements=json.loads(row[8]),
            environment_variables=json.loads(row[9]),
            configuration_schema=json.loads(row[10]) if row[10] else None,
            health_check_url=row[11],
            metrics_enabled=bool(row[12])
        )

    def _row_to_feature_state(self, row) -> FeatureState:
        """Convert database row to FeatureState."""
        return FeatureState(
            feature_id=row[0],
            status=row[1],
            enabled=bool(row[2]),
            last_enabled_at=row[3],
            last_disabled_at=row[4],
            error_count=row[5],
            last_error=row[6],
            last_error_at=row[7],
            restart_count=row[8],
            health_status=row[9],
            last_health_check=row[10],
            metrics=json.loads(row[11]),
            configuration=json.loads(row[12]),
            created_at=row[13],
            updated_at=row[14]
        )

    async def close(self) -> None:
        """Close the database connection."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
            logger.info("Feature database connection closed")

    async def cleanup_expired_cache(self) -> int:
        """Clean up expired dependency cache entries."""
        try:
            cursor = await self._db_connection.execute("""
                DELETE FROM dependency_cache WHERE expires_at <= ?
            """, (datetime.now(timezone.utc).isoformat(),))
            
            deleted_count = cursor.rowcount
            await self._db_connection.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0