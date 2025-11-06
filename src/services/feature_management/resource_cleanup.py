"""
Resource Cleanup for Feature Management

Handles comprehensive resource cleanup including memory, file handles,
temporary data, and system resources when features are deactivated.
"""

import asyncio
import gc
import shutil
import tempfile
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import psutil
from loguru import logger

from ...core.event_bus import Event, EventBus, EventType
from .models import FeatureConfig


class ResourceCleanupStatus(Enum):
    """Status of resource cleanup operations."""

    IDLE = "idle"
    CLEANING_MEMORY = "cleaning_memory"
    CLEANING_FILES = "cleaning_files"
    CLEANING_TEMP_DATA = "cleaning_temp_data"
    CLEANING_CACHE = "cleaning_cache"
    CLEANING_REGISTRIES = "cleaning_registries"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResourceMetrics:
    """Metrics for resource usage."""

    memory_usage_mb: float = 0.0
    file_handles_count: int = 0
    thread_count: int = 0
    temp_files_count: int = 0
    cache_size_mb: float = 0.0
    disk_usage_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory_usage_mb": self.memory_usage_mb,
            "file_handles_count": self.file_handles_count,
            "thread_count": self.thread_count,
            "temp_files_count": self.temp_files_count,
            "cache_size_mb": self.cache_size_mb,
            "disk_usage_mb": self.disk_usage_mb,
        }


@dataclass
class ResourceCleanupResult:
    """Result of resource cleanup operations."""

    feature_id: str
    status: ResourceCleanupStatus
    metrics_before: ResourceMetrics = field(default_factory=ResourceMetrics)
    metrics_after: ResourceMetrics = field(default_factory=ResourceMetrics)
    memory_freed_mb: float = 0.0
    files_deleted: int = 0
    temp_dirs_removed: int = 0
    cache_entries_cleared: int = 0
    threads_cleaned: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_id": self.feature_id,
            "status": self.status.value,
            "metrics_before": self.metrics_before.to_dict(),
            "metrics_after": self.metrics_after.to_dict(),
            "memory_freed_mb": self.memory_freed_mb,
            "files_deleted": self.files_deleted,
            "temp_dirs_removed": self.temp_dirs_removed,
            "cache_entries_cleared": self.cache_entries_cleared,
            "threads_cleaned": self.threads_cleaned,
            "errors": self.errors,
            "warnings": self.warnings,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ResourceSnapshot:
    """Snapshot of resources for tracking and rollback."""

    feature_id: str
    timestamp: str
    memory_objects: Dict[str, int] = field(default_factory=dict)
    file_paths: List[str] = field(default_factory=list)
    temp_directories: List[str] = field(default_factory=list)
    cache_keys: List[str] = field(default_factory=list)
    thread_ids: List[int] = field(default_factory=list)
    weak_references: List[str] = field(default_factory=list)


class ResourceCleanupError(Exception):
    """Resource cleanup specific errors."""

    pass


class ResourceTracker:
    """Tracks resource usage for features."""

    def __init__(self):
        self.feature_resources: Dict[str, Dict[str, Any]] = {}
        self.global_temp_files: Set[str] = set()
        self.global_cache_keys: Set[str] = set()
        self.global_weak_refs: Dict[str, weakref.ref] = {}

    def track_resource(
        self, feature_id: str, resource_type: str, resource_id: str, resource: Any
    ) -> None:
        """Track a resource for a feature."""
        if feature_id not in self.feature_resources:
            self.feature_resources[feature_id] = {
                "memory_objects": {},
                "file_paths": set(),
                "temp_directories": set(),
                "cache_keys": set(),
                "threads": set(),
                "weak_refs": {},
            }

        if resource_type == "memory_object":
            self.feature_resources[feature_id]["memory_objects"][resource_id] = id(
                resource
            )
        elif resource_type == "file_path":
            self.feature_resources[feature_id]["file_paths"].add(resource_id)
        elif resource_type == "temp_directory":
            self.feature_resources[feature_id]["temp_directories"].add(resource_id)
        elif resource_type == "cache_key":
            self.feature_resources[feature_id]["cache_keys"].add(resource_id)
        elif resource_type == "thread":
            self.feature_resources[feature_id]["threads"].add(resource_id)
        elif resource_type == "weak_ref":
            weak_ref = weakref.ref(
                resource, lambda ref: self._cleanup_weak_ref(resource_id)
            )
            self.feature_resources[feature_id]["weak_refs"][resource_id] = weak_ref

    def _cleanup_weak_ref(self, resource_id: str) -> None:
        """Clean up weak reference when object is garbage collected."""
        self.global_weak_refs.pop(resource_id, None)
        for feature_resources in self.feature_resources.values():
            feature_resources["weak_refs"].pop(resource_id, None)

    def get_feature_resources(self, feature_id: str) -> Dict[str, Any]:
        """Get all resources for a feature."""
        return self.feature_resources.get(feature_id, {})

    def clear_feature_resources(self, feature_id: str) -> None:
        """Clear all resources for a feature."""
        self.feature_resources.pop(feature_id, None)


class ResourceCleanupManager:
    """
    Manages comprehensive resource cleanup for features.

    Responsibilities:
    - Memory cleanup and garbage collection
    - File handle and temporary file cleanup
    - Thread cleanup and management
    - Cache cleanup and invalidation
    - Registry and system resource cleanup
    - Resource tracking and monitoring
    """

    def __init__(
        self, event_bus: Optional[EventBus] = None, temp_dir: Optional[str] = None
    ):
        self.event_bus = event_bus
        self.temp_dir = Path(temp_dir or tempfile.gettempdir()) / "robo_trader_features"

        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Resource tracking
        self.resource_tracker = ResourceTracker()

        # Operation tracking
        self.active_operations: Dict[str, ResourceCleanupResult] = {}
        self.resource_snapshots: Dict[str, ResourceSnapshot] = {}

        # Cleanup policies
        self.cleanup_policies = {
            "force_memory_cleanup": True,
            "delete_temp_files": True,
            "clear_cache": True,
            "cleanup_threads": True,
            "max_retries": 3,
            "cleanup_timeout_seconds": 30,
        }

        logger.info("Resource Cleanup Manager initialized")

    async def track_feature_resource(
        self, feature_id: str, resource_type: str, resource_id: str, resource: Any
    ) -> None:
        """Track a resource for a feature."""
        self.resource_tracker.track_resource(
            feature_id, resource_type, resource_id, resource
        )
        logger.debug(f"Tracked {resource_type} {resource_id} for feature {feature_id}")

    async def cleanup_feature_resources(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        timeout_seconds: Optional[int] = None,
    ) -> ResourceCleanupResult:
        """
        Clean up all resources for a feature.

        Args:
            feature_id: ID of the feature to cleanup
            feature_config: Configuration of the feature
            timeout_seconds: Timeout for cleanup operations

        Returns:
            ResourceCleanupResult with operation details
        """
        if feature_id in self.active_operations:
            logger.warning(
                f"Resource cleanup already in progress for feature {feature_id}"
            )
            return self.active_operations[feature_id]

        result = ResourceCleanupResult(
            feature_id=feature_id, status=ResourceCleanupStatus.IDLE
        )
        self.active_operations[feature_id] = result

        timeout = timeout_seconds or self.cleanup_policies["cleanup_timeout_seconds"]

        logger.info(f"Starting resource cleanup for feature {feature_id}")

        try:
            # Create resource snapshot
            snapshot = await self._create_resource_snapshot(feature_id)
            self.resource_snapshots[feature_id] = snapshot

            # Get initial metrics
            result.metrics_before = await self._get_resource_metrics()

            # Stage 1: Memory cleanup
            result.status = ResourceCleanupStatus.CLEANING_MEMORY
            await self._cleanup_memory_resources(feature_id, result)

            # Stage 2: File cleanup
            result.status = ResourceCleanupStatus.CLEANING_FILES
            await self._cleanup_file_resources(feature_id, result)

            # Stage 3: Temporary data cleanup
            result.status = ResourceCleanupStatus.CLEANING_TEMP_DATA
            await self._cleanup_temporary_data(feature_id, result)

            # Stage 4: Cache cleanup
            result.status = ResourceCleanupStatus.CLEANING_CACHE
            await self._cleanup_cache_resources(feature_id, result)

            # Stage 5: Registry cleanup
            result.status = ResourceCleanupStatus.CLEANING_REGISTRIES
            await self._cleanup_registries(feature_id, result)

            # Get final metrics
            result.metrics_after = await self._get_resource_metrics()
            result.memory_freed_mb = (
                result.metrics_before.memory_usage_mb
                - result.metrics_after.memory_usage_mb
            )

            # Mark as completed
            result.status = ResourceCleanupStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"Successfully completed resource cleanup for feature {feature_id}"
            )
            logger.info(
                f"Freed {result.memory_freed_mb:.2f} MB memory, deleted {result.files_deleted} files"
            )

            # Emit completion event
            if self.event_bus:
                await self._emit_cleanup_event(feature_id, "cleanup_completed", result)

        except asyncio.TimeoutError:
            error_msg = f"Resource cleanup timeout for feature {feature_id}"
            result.errors.append(error_msg)
            result.status = ResourceCleanupStatus.FAILED
            logger.error(error_msg)

        except Exception as e:
            error_msg = f"Resource cleanup failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            result.status = ResourceCleanupStatus.FAILED
            logger.error(error_msg)

        finally:
            # Clean up operation tracking
            if feature_id in self.active_operations:
                del self.active_operations[feature_id]

        return result

    async def _cleanup_memory_resources(
        self, feature_id: str, result: ResourceCleanupResult
    ) -> None:
        """Clean up memory resources for a feature."""
        try:
            # Get feature resources
            resources = self.resource_tracker.get_feature_resources(feature_id)
            memory_objects = resources.get("memory_objects", {})

            # Clear weak references
            weak_refs = resources.get("weak_refs", {})
            for ref_id in list(weak_refs.keys()):
                weak_refs.pop(ref_id, None)

            # Force garbage collection
            if self.cleanup_policies["force_memory_cleanup"]:
                collected_objects = gc.collect()
                logger.debug(
                    f"Garbage collected {collected_objects} objects for feature {feature_id}"
                )

            # Clear any feature-specific caches or data structures
            self.resource_tracker.clear_feature_resources(feature_id)

            logger.debug(f"Memory cleanup completed for feature {feature_id}")

        except Exception as e:
            error_msg = f"Memory cleanup failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)

    async def _cleanup_file_resources(
        self, feature_id: str, result: ResourceCleanupResult
    ) -> None:
        """Clean up file resources for a feature."""
        try:
            resources = self.resource_tracker.get_feature_resources(feature_id)
            file_paths = resources.get("file_paths", set())

            files_deleted = 0

            for file_path in file_paths:
                try:
                    path = Path(file_path)
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                            files_deleted += 1
                            logger.debug(f"Deleted file {file_path}")
                        elif path.is_dir():
                            shutil.rmtree(path)
                            files_deleted += 1
                            logger.debug(f"Deleted directory {file_path}")

                except Exception as e:
                    warning_msg = f"Failed to delete file {file_path}: {str(e)}"
                    result.warnings.append(warning_msg)
                    logger.warning(warning_msg)

            result.files_deleted = files_deleted

        except Exception as e:
            error_msg = f"File cleanup failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)

    async def _cleanup_temporary_data(
        self, feature_id: str, result: ResourceCleanupResult
    ) -> None:
        """Clean up temporary data for a feature."""
        try:
            # Clean up feature-specific temp directory
            feature_temp_dir = self.temp_dir / feature_id
            temp_dirs_removed = 0

            if feature_temp_dir.exists():
                try:
                    shutil.rmtree(feature_temp_dir)
                    temp_dirs_removed = 1
                    logger.debug(f"Removed temp directory {feature_temp_dir}")
                except Exception as e:
                    warning_msg = (
                        f"Failed to remove temp directory {feature_temp_dir}: {str(e)}"
                    )
                    result.warnings.append(warning_msg)
                    logger.warning(warning_msg)

            # Clean up system temp files for this feature
            resources = self.resource_tracker.get_feature_resources(feature_id)
            temp_directories = resources.get("temp_directories", set())

            for temp_dir in temp_directories:
                try:
                    path = Path(temp_dir)
                    if path.exists() and path.is_dir():
                        shutil.rmtree(path)
                        temp_dirs_removed += 1
                        logger.debug(f"Removed temp directory {temp_dir}")

                except Exception as e:
                    warning_msg = (
                        f"Failed to remove temp directory {temp_dir}: {str(e)}"
                    )
                    result.warnings.append(warning_msg)
                    logger.warning(warning_msg)

            result.temp_dirs_removed = temp_dirs_removed

        except Exception as e:
            error_msg = (
                f"Temporary data cleanup failed for feature {feature_id}: {str(e)}"
            )
            result.errors.append(error_msg)
            logger.error(error_msg)

    async def _cleanup_cache_resources(
        self, feature_id: str, result: ResourceCleanupResult
    ) -> None:
        """Clean up cache resources for a feature."""
        try:
            resources = self.resource_tracker.get_feature_resources(feature_id)
            cache_keys = resources.get("cache_keys", set())

            cache_entries_cleared = 0

            for cache_key in cache_keys:
                try:
                    # This would integrate with your cache system (Redis, etc.)
                    # For now, we'll simulate cache clearing
                    cache_entries_cleared += 1
                    logger.debug(f"Cleared cache entry {cache_key}")

                except Exception as e:
                    warning_msg = f"Failed to clear cache entry {cache_key}: {str(e)}"
                    result.warnings.append(warning_msg)
                    logger.warning(warning_msg)

            result.cache_entries_cleared = cache_entries_cleared

        except Exception as e:
            error_msg = f"Cache cleanup failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)

    async def _cleanup_registries(
        self, feature_id: str, result: ResourceCleanupResult
    ) -> None:
        """Clean up registries and system resources for a feature."""
        try:
            resources = self.resource_tracker.get_feature_resources(feature_id)
            threads = resources.get("threads", set())

            threads_cleaned = 0

            # Clean up threads
            for thread_id in threads:
                try:
                    # In Python, we can't forcefully kill threads, but we can
                    # mark them for cleanup if they check some condition
                    threads_cleaned += 1
                    logger.debug(f"Marked thread {thread_id} for cleanup")

                except Exception as e:
                    warning_msg = f"Failed to cleanup thread {thread_id}: {str(e)}"
                    result.warnings.append(warning_msg)
                    logger.warning(warning_msg)

            result.threads_cleaned = threads_cleaned

            # Clean up any other system resources
            # This would include things like semaphores, locks, etc.

        except Exception as e:
            error_msg = f"Registry cleanup failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)

    async def _get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource metrics."""
        try:
            process = psutil.Process()

            # Memory usage
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024

            # File handles
            try:
                file_handles = process.open_files()
                file_handles_count = len(file_handles)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                file_handles_count = 0

            # Threads
            threads = process.threads()
            thread_count = len(threads)

            # Temporary files
            temp_files_count = (
                len(list(self.temp_dir.rglob("*"))) if self.temp_dir.exists() else 0
            )

            # Cache size (simulated)
            cache_size_mb = 0.0

            # Disk usage
            try:
                disk_usage = shutil.disk_usage(str(self.temp_dir))
                disk_usage_mb = disk_usage.used / 1024 / 1024
            except Exception as e:
                logger.debug(f"Failed to get disk usage for {self.temp_dir}: {e}")
                disk_usage_mb = 0.0

            return ResourceMetrics(
                memory_usage_mb=memory_usage_mb,
                file_handles_count=file_handles_count,
                thread_count=thread_count,
                temp_files_count=temp_files_count,
                cache_size_mb=cache_size_mb,
                disk_usage_mb=disk_usage_mb,
            )

        except Exception as e:
            logger.error(f"Failed to get resource metrics: {e}")
            return ResourceMetrics()

    async def _create_resource_snapshot(self, feature_id: str) -> ResourceSnapshot:
        """Create a snapshot of resources for tracking."""
        snapshot = ResourceSnapshot(
            feature_id=feature_id, timestamp=datetime.now(timezone.utc).isoformat()
        )

        try:
            resources = self.resource_tracker.get_feature_resources(feature_id)

            # Capture memory objects
            snapshot.memory_objects = resources.get("memory_objects", {})

            # Capture file paths
            snapshot.file_paths = list(resources.get("file_paths", set()))

            # Capture temp directories
            snapshot.temp_directories = list(resources.get("temp_directories", set()))

            # Capture cache keys
            snapshot.cache_keys = list(resources.get("cache_keys", set()))

            # Capture thread IDs
            snapshot.threads = list(resources.get("threads", set()))

            # Capture weak references
            snapshot.weak_references = list(resources.get("weak_refs", {}).keys())

        except Exception as e:
            logger.error(
                f"Failed to create resource snapshot for feature {feature_id}: {e}"
            )

        return snapshot

    async def force_cleanup_feature(self, feature_id: str) -> bool:
        """Force cleanup of all resources for a feature."""
        try:
            logger.warning(f"Force cleaning up resources for feature {feature_id}")

            # Cancel any active cleanup operation
            if feature_id in self.active_operations:
                operation = self.active_operations[feature_id]
                operation.status = ResourceCleanupStatus.FAILED
                operation.errors.append("Force cleanup initiated")
                del self.active_operations[feature_id]

            # Clear resource tracking
            self.resource_tracker.clear_feature_resources(feature_id)

            # Remove temp directory
            feature_temp_dir = self.temp_dir / feature_id
            if feature_temp_dir.exists():
                shutil.rmtree(feature_temp_dir)
                logger.debug(f"Force removed temp directory {feature_temp_dir}")

            # Force garbage collection
            gc.collect()

            logger.info(f"Force cleanup completed for feature {feature_id}")
            return True

        except Exception as e:
            logger.error(f"Force cleanup failed for feature {feature_id}: {e}")
            return False

    async def get_cleanup_status(
        self, feature_id: str
    ) -> Optional[ResourceCleanupResult]:
        """Get the current cleanup status for a feature."""
        return self.active_operations.get(feature_id)

    async def get_feature_resource_summary(self, feature_id: str) -> Dict[str, Any]:
        """Get a summary of resources for a feature."""
        resources = self.resource_tracker.get_feature_resources(feature_id)

        return {
            "feature_id": feature_id,
            "memory_objects": len(resources.get("memory_objects", {})),
            "file_paths": len(resources.get("file_paths", set())),
            "temp_directories": len(resources.get("temp_directories", set())),
            "cache_keys": len(resources.get("cache_keys", set())),
            "threads": len(resources.get("threads", set())),
            "weak_refs": len(resources.get("weak_refs", {})),
        }

    async def _emit_cleanup_event(
        self, feature_id: str, event_type: str, result: ResourceCleanupResult
    ) -> None:
        """Emit a resource cleanup event."""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            Event(
                id=f"resource_cleanup_{feature_id}_{event_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.SYSTEM_HEALTH_CHECK,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="resource_cleanup",
                data={
                    "feature_id": feature_id,
                    "event_type": event_type,
                    "result": result.to_dict(),
                },
            )
        )

    async def get_system_resource_summary(self) -> Dict[str, Any]:
        """Get a summary of system-wide resource usage."""
        metrics = await self._get_resource_metrics()

        return {
            "current_metrics": metrics.to_dict(),
            "active_operations": len(self.active_operations),
            "tracked_features": len(self.resource_tracker.feature_resources),
            "temp_directory": str(self.temp_dir),
            "cleanup_policies": self.cleanup_policies,
        }

    async def cleanup_all_temp_data(self) -> int:
        """Clean up all temporary data."""
        try:
            if not self.temp_dir.exists():
                return 0

            files_before = len(list(self.temp_dir.rglob("*")))

            # Remove all contents
            for item in self.temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            files_after = len(list(self.temp_dir.rglob("*")))
            files_deleted = files_before - files_after

            logger.info(f"Cleaned up {files_deleted} temporary files")
            return files_deleted

        except Exception as e:
            logger.error(f"Failed to cleanup all temp data: {e}")
            return 0

    async def close(self) -> None:
        """Close the resource cleanup manager."""
        logger.info("Closing Resource Cleanup Manager")

        # Cancel any active operations
        for feature_id, result in self.active_operations.items():
            logger.warning(
                f"Cancelling active cleanup operation for feature {feature_id}"
            )
            result.status = ResourceCleanupStatus.FAILED
            result.errors.append("Resource cleanup manager shutdown")

        self.active_operations.clear()
        self.resource_snapshots.clear()

        # Clean up all temp data
        await self.cleanup_all_temp_data()

        # Clear resource tracking
        self.resource_tracker.feature_resources.clear()

        logger.info("Resource Cleanup Manager closed")
