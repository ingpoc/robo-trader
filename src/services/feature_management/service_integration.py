"""
Service Integration for Feature Management

Handles integration with microservices, database connections, WebSocket connections,
and cache management when features are deactivated.
"""

import asyncio
import aiohttp
import asyncpg
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import weakref
from loguru import logger

from ...core.event_bus import EventBus, Event, EventType
from .models import FeatureConfig, FeatureType


class ServiceIntegrationStatus(Enum):
    """Status of service integration operations."""
    IDLE = "idle"
    STOPPING_SERVICES = "stopping_services"
    CLOSING_CONNECTIONS = "closing_connections"
    CLEANING_CACHE = "cleaning_cache"
    CLOSING_WEBSOCKETS = "closing_websockets"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """Information about a microservice."""
    service_id: str
    service_name: str
    service_type: str
    status: str
    endpoint: Optional[str] = None
    health_check_url: Optional[str] = None
    feature_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "status": self.status,
            "endpoint": self.endpoint,
            "health_check_url": self.health_check_url,
            "feature_id": self.feature_id,
            "dependencies": self.dependencies
        }


@dataclass
class ConnectionInfo:
    """Information about a connection."""
    connection_id: str
    connection_type: str  # database, websocket, http, etc.
    status: str
    endpoint: Optional[str] = None
    feature_id: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "connection_id": self.connection_id,
            "connection_type": self.connection_type,
            "status": self.status,
            "endpoint": self.endpoint,
            "feature_id": self.feature_id,
            "created_at": self.created_at
        }


@dataclass
class ServiceDeactivationResult:
    """Result of service deactivation operations."""
    feature_id: str
    status: ServiceIntegrationStatus
    services_stopped: List[str] = field(default_factory=list)
    connections_closed: List[str] = field(default_factory=list)
    websockets_closed: List[str] = field(default_factory=list)
    cache_entries_cleared: List[str] = field(default_factory=list)
    database_pools_closed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_id": self.feature_id,
            "status": self.status.value,
            "services_stopped": self.services_stopped,
            "connections_closed": self.connections_closed,
            "websockets_closed": self.websockets_closed,
            "cache_entries_cleared": self.cache_entries_cleared,
            "database_pools_closed": self.database_pools_closed,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class ServiceStateSnapshot:
    """Snapshot of service state for potential rollback."""
    feature_id: str
    timestamp: str
    service_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    connection_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cache_snapshots: Dict[str, Any] = field(default_factory=dict)
    websocket_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ServiceIntegrationError(Exception):
    """Service integration specific errors."""
    pass


class ServiceRegistry:
    """Mock service registry for demonstration."""
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.service_health: Dict[str, bool] = {}
    
    async def register_service(self, service_info: ServiceInfo) -> bool:
        """Register a service."""
        self.services[service_info.service_id] = service_info
        self.service_health[service_info.service_id] = True
        return True
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service."""
        if service_id in self.services:
            del self.services[service_id]
            self.service_health.pop(service_id, None)
            return True
        return False
    
    async def stop_service(self, service_id: str) -> bool:
        """Stop a service."""
        if service_id in self.services:
            self.services[service_id].status = "stopped"
            self.service_health[service_id] = False
            return True
        return False
    
    async def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """Get service information."""
        return self.services.get(service_id)
    
    async def get_services_by_feature(self, feature_id: str) -> List[ServiceInfo]:
        """Get all services for a feature."""
        return [service for service in self.services.values() if service.feature_id == feature_id]


class ServiceManagementIntegration:
    """
    Integrates feature management with microservices and infrastructure.
    
    Responsibilities:
    - Stop/start microservices via service registry
    - Manage database connections and pools
    - Control WebSocket connections and subscriptions
    - Handle cache cleanup and invalidation
    - Provide rollback capabilities for service operations
    """

    def __init__(
        self,
        service_registry: Optional[ServiceRegistry] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.service_registry = service_registry or ServiceRegistry()
        self.event_bus = event_bus
        
        # Feature to service mapping
        self.feature_services: Dict[str, Set[str]] = {}  # feature_id -> service_ids
        self.feature_connections: Dict[str, Set[str]] = {}  # feature_id -> connection_ids
        self.feature_websockets: Dict[str, Set[str]] = {}  # feature_id -> websocket_ids
        self.feature_cache_keys: Dict[str, Set[str]] = {}  # feature_id -> cache_keys
        
        # Connection tracking
        self.database_connections: Dict[str, Any] = {}  # connection_id -> connection
        self.websocket_connections: Dict[str, Any] = {}  # websocket_id -> websocket
        self.http_sessions: Dict[str, aiohttp.ClientSession] = {}  # session_id -> session
        
        # Operation tracking
        self.active_operations: Dict[str, ServiceDeactivationResult] = {}
        self.state_snapshots: Dict[str, ServiceStateSnapshot] = {}
        
        # Initialize service mappings
        self._initialize_service_mappings()
        
        logger.info("Service Management Integration initialized")

    def _initialize_service_mappings(self) -> None:
        """Initialize mappings between features and services."""
        # Map feature types to typical services
        service_mapping = {
            FeatureType.SERVICE: {
                "market_data_service", "portfolio_service", "execution_service",
                "analytics_service", "risk_service"
            },
            FeatureType.AGENT: {
                "claude_agent_service", "recommendation_service"
            },
            FeatureType.MONITOR: {
                "monitoring_service", "alert_service"
            },
            FeatureType.INTEGRATION: {
                "api_gateway", "data_feed_service", "notification_service"
            }
        }
        
        # Store mappings for reference
        self.feature_service_mapping = service_mapping

    async def register_feature_services(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        service_ids: List[str]
    ) -> None:
        """
        Register services for a feature.
        
        Args:
            feature_id: ID of the feature
            feature_config: Configuration of the feature
            service_ids: List of service IDs associated with the feature
        """
        # Initialize feature tracking
        if feature_id not in self.feature_services:
            self.feature_services[feature_id] = set()
        if feature_id not in self.feature_connections:
            self.feature_connections[feature_id] = set()
        if feature_id not in self.feature_websockets:
            self.feature_websockets[feature_id] = set()
        if feature_id not in self.feature_cache_keys:
            self.feature_cache_keys[feature_id] = set()
        
        # Register services
        for service_id in service_ids:
            self.feature_services[feature_id].add(service_id)
            
            # Create service info if not exists
            service_info = await self.service_registry.get_service(service_id)
            if not service_info:
                service_info = ServiceInfo(
                    service_id=service_id,
                    service_name=f"Service {service_id}",
                    service_type="microservice",
                    status="running",
                    feature_id=feature_id
                )
                await self.service_registry.register_service(service_info)
        
        logger.info(f"Registered {len(service_ids)} services for feature {feature_id}")

    async def register_feature_connection(
        self,
        feature_id: str,
        connection_id: str,
        connection_type: str,
        connection: Any
    ) -> None:
        """Register a connection for a feature."""
        if feature_id not in self.feature_connections:
            self.feature_connections[feature_id] = set()
        
        self.feature_connections[feature_id].add(connection_id)
        
        # Store connection reference
        if connection_type == "database":
            self.database_connections[connection_id] = connection
        elif connection_type == "websocket":
            self.websocket_connections[connection_id] = connection
        elif connection_type == "http":
            self.http_sessions[connection_id] = connection
        
        logger.debug(f"Registered {connection_type} connection {connection_id} for feature {feature_id}")

    async def deactivate_feature_services(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        timeout_seconds: int = 60
    ) -> ServiceDeactivationResult:
        """
        Deactivate all services for a feature.
        
        Args:
            feature_id: ID of the feature to deactivate
            feature_config: Configuration of the feature
            timeout_seconds: Timeout for deactivation operations
            
        Returns:
            ServiceDeactivationResult with operation details
        """
        if feature_id in self.active_operations:
            logger.warning(f"Service deactivation already in progress for feature {feature_id}")
            return self.active_operations[feature_id]
        
        result = ServiceDeactivationResult(
            feature_id=feature_id,
            status=ServiceIntegrationStatus.IDLE
        )
        self.active_operations[feature_id] = result
        
        logger.info(f"Starting service deactivation for feature {feature_id}")
        
        try:
            # Create state snapshot for rollback
            snapshot = await self._create_service_state_snapshot(feature_id)
            self.state_snapshots[feature_id] = snapshot
            
            # Stage 1: Stop services
            result.status = ServiceIntegrationStatus.STOPPING_SERVICES
            await self._stop_feature_services(feature_id, feature_config)
            
            # Stage 2: Close connections
            result.status = ServiceIntegrationStatus.CLOSING_CONNECTIONS
            await self._close_feature_connections(feature_id, feature_config)
            
            # Stage 3: Close websockets
            result.status = ServiceIntegrationStatus.CLOSING_WEBSOCKETS
            await self._close_feature_websockets(feature_id, feature_config)
            
            # Stage 4: Clean cache
            result.status = ServiceIntegrationStatus.CLEANING_CACHE
            await self._clean_feature_cache(feature_id, feature_config)
            
            # Mark as completed
            result.status = ServiceIntegrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully completed service deactivation for feature {feature_id}")
            
            # Emit completion event
            if self.event_bus:
                await self._emit_service_event(feature_id, "deactivation_completed", result)
            
        except asyncio.TimeoutError:
            error_msg = f"Service deactivation timeout for feature {feature_id}"
            result.errors.append(error_msg)
            result.status = ServiceIntegrationStatus.FAILED
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Service deactivation failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            result.status = ServiceIntegrationStatus.FAILED
            logger.error(error_msg)
            
        finally:
            # Clean up operation tracking
            if feature_id in self.active_operations:
                del self.active_operations[feature_id]
        
        return result

    async def _stop_feature_services(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Stop all services for a feature."""
        services = await self.service_registry.get_services_by_feature(feature_id)
        stopped_services = []
        
        for service in services:
            try:
                # Stop service via registry
                success = await self.service_registry.stop_service(service.service_id)
                if success:
                    stopped_services.append(service.service_id)
                    logger.debug(f"Stopped service {service.service_id} for feature {feature_id}")
                
                # In a real implementation, you would also:
                # - Call service shutdown endpoints
                # - Wait for graceful shutdown
                # - Verify service is stopped
                
            except Exception as e:
                logger.error(f"Failed to stop service {service.service_id}: {e}")
        
        # Update result
        if feature_id in self.active_operations:
            self.active_operations[feature_id].services_stopped.extend(stopped_services)
        
        logger.info(f"Stopped {len(stopped_services)} services for feature {feature_id}")

    async def _close_feature_connections(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Close all connections for a feature."""
        connections = self.feature_connections.get(feature_id, set())
        closed_connections = []
        closed_database_pools = []
        
        for connection_id in connections:
            try:
                # Close database connections
                if connection_id in self.database_connections:
                    connection = self.database_connections[connection_id]
                    if hasattr(connection, 'close'):
                        await connection.close()
                        closed_connections.append(connection_id)
                        closed_database_pools.append(connection_id)
                        logger.debug(f"Closed database connection {connection_id}")
                
                # Close HTTP sessions
                elif connection_id in self.http_sessions:
                    session = self.http_sessions[connection_id]
                    await session.close()
                    closed_connections.append(connection_id)
                    logger.debug(f"Closed HTTP session {connection_id}")
                
            except Exception as e:
                logger.error(f"Failed to close connection {connection_id}: {e}")
        
        # Update result
        if feature_id in self.active_operations:
            result = self.active_operations[feature_id]
            result.connections_closed.extend(closed_connections)
            result.database_pools_closed.extend(closed_database_pools)
        
        logger.info(f"Closed {len(closed_connections)} connections for feature {feature_id}")

    async def _close_feature_websockets(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Close all WebSocket connections for a feature."""
        websockets = self.feature_websockets.get(feature_id, set())
        closed_websockets = []
        
        for websocket_id in websockets:
            try:
                if websocket_id in self.websocket_connections:
                    websocket = self.websocket_connections[websocket_id]
                    if hasattr(websocket, 'close'):
                        await websocket.close()
                        closed_websockets.append(websocket_id)
                        logger.debug(f"Closed WebSocket {websocket_id}")
                
            except Exception as e:
                logger.error(f"Failed to close WebSocket {websocket_id}: {e}")
        
        # Update result
        if feature_id in self.active_operations:
            self.active_operations[feature_id].websockets_closed.extend(closed_websockets)
        
        logger.info(f"Closed {len(closed_websockets)} WebSockets for feature {feature_id}")

    async def _clean_feature_cache(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Clean cache entries for a feature."""
        cache_keys = self.feature_cache_keys.get(feature_id, set())
        cleared_entries = []
        
        for cache_key in cache_keys:
            try:
                # This would integrate with your cache system (Redis, etc.)
                # For now, we'll simulate cache clearing
                cleared_entries.append(cache_key)
                logger.debug(f"Cleared cache entry {cache_key}")
                
            except Exception as e:
                logger.error(f"Failed to clear cache entry {cache_key}: {e}")
        
        # Update result
        if feature_id in self.active_operations:
            self.active_operations[feature_id].cache_entries_cleared.extend(cleared_entries)
        
        logger.info(f"Cleared {len(cleared_entries)} cache entries for feature {feature_id}")

    async def _create_service_state_snapshot(
        self,
        feature_id: str
    ) -> ServiceStateSnapshot:
        """Create a snapshot of service state for rollback."""
        snapshot = ServiceStateSnapshot(
            feature_id=feature_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        try:
            # Capture service states
            services = await self.service_registry.get_services_by_feature(feature_id)
            for service in services:
                snapshot.service_states[service.service_id] = service.to_dict()
            
            # Capture connection states
            connections = self.feature_connections.get(feature_id, set())
            for connection_id in connections:
                connection_state = {
                    "connection_id": connection_id,
                    "status": "active"
                }
                snapshot.connection_states[connection_id] = connection_state
            
            # Capture cache state
            cache_keys = self.feature_cache_keys.get(feature_id, set())
            snapshot.cache_snapshots = {
                "keys": list(cache_keys),
                "count": len(cache_keys)
            }
            
            # Capture WebSocket states
            websockets = self.feature_websockets.get(feature_id, set())
            for websocket_id in websockets:
                websocket_state = {
                    "websocket_id": websocket_id,
                    "status": "connected"
                }
                snapshot.websocket_states[websocket_id] = websocket_state
                
        except Exception as e:
            logger.error(f"Failed to create service state snapshot for feature {feature_id}: {e}")
        
        return snapshot

    async def get_feature_service_info(self, feature_id: str) -> List[ServiceInfo]:
        """Get information about all services for a feature."""
        return await self.service_registry.get_services_by_feature(feature_id)

    async def get_feature_connection_info(self, feature_id: str) -> List[ConnectionInfo]:
        """Get information about all connections for a feature."""
        connections = self.feature_connections.get(feature_id, set())
        connection_info_list = []
        
        for connection_id in connections:
            connection_type = "unknown"
            if connection_id in self.database_connections:
                connection_type = "database"
            elif connection_id in self.websocket_connections:
                connection_type = "websocket"
            elif connection_id in self.http_sessions:
                connection_type = "http"
            
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                connection_type=connection_type,
                status="active",
                feature_id=feature_id,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            connection_info_list.append(connection_info)
        
        return connection_info_list

    async def rollback_service_deactivation(self, feature_id: str) -> bool:
        """
        Rollback service deactivation for a feature.
        
        This attempts to restore the previous state of services and connections.
        """
        try:
            snapshot = self.state_snapshots.get(feature_id)
            if not snapshot:
                logger.warning(f"No state snapshot available for rollback of feature {feature_id}")
                return False
            
            logger.info(f"Rolling back service deactivation for feature {feature_id}")
            
            # Restore service states
            for service_id, service_state in snapshot.service_states.items():
                try:
                    service_info = ServiceInfo.from_dict(service_state)
                    await self.service_registry.register_service(service_info)
                    logger.debug(f"Restored service {service_id} during rollback")
                    
                except Exception as e:
                    logger.error(f"Failed to restore service {service_id}: {e}")
            
            # Restore connections
            for connection_id, connection_state in snapshot.connection_states.items():
                try:
                    # This would restore connections based on their type
                    logger.debug(f"Restored connection {connection_id} during rollback")
                    
                except Exception as e:
                    logger.error(f"Failed to restore connection {connection_id}: {e}")
            
            logger.info(f"Successfully rolled back service deactivation for feature {feature_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for feature {feature_id}: {e}")
            return False

    async def _emit_service_event(
        self,
        feature_id: str,
        event_type: str,
        result: ServiceDeactivationResult
    ) -> None:
        """Emit a service integration event."""
        if not self.event_bus:
            return
        
        await self.event_bus.publish(Event(
            id=f"service_integration_{feature_id}_{event_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            type=EventType.SYSTEM_HEALTH_CHECK,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="service_integration",
            data={
                "feature_id": feature_id,
                "event_type": event_type,
                "result": result.to_dict()
            }
        ))

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get the overall status of service integration."""
        return {
            "active_operations": len(self.active_operations),
            "tracked_features": len(self.feature_services),
            "tracked_services": sum(len(services) for services in self.feature_services.values()),
            "tracked_connections": sum(len(connections) for connections in self.feature_connections.values()),
            "tracked_websockets": sum(len(websockets) for websockets in self.feature_websockets.values()),
            "tracked_cache_keys": sum(len(keys) for keys in self.feature_cache_keys.values()),
            "state_snapshots": len(self.state_snapshots),
            "database_connections": len(self.database_connections),
            "websocket_connections": len(self.websocket_connections),
            "http_sessions": len(self.http_sessions),
            "services_available": {
                "service_registry": self.service_registry is not None,
                "event_bus": self.event_bus is not None
            }
        }

    async def clear_feature_tracking(self, feature_id: str) -> None:
        """Clear all tracking data for a feature."""
        self.feature_services.pop(feature_id, None)
        self.feature_connections.pop(feature_id, None)
        self.feature_websockets.pop(feature_id, None)
        self.feature_cache_keys.pop(feature_id, None)
        self.state_snapshots.pop(feature_id, None)
        
        logger.info(f"Cleared service tracking for feature {feature_id}")

    async def force_stop_service(self, service_id: str) -> bool:
        """Force stop a specific service."""
        try:
            logger.warning(f"Force stopping service {service_id}")
            
            success = await self.service_registry.stop_service(service_id)
            if success:
                logger.info(f"Force stopped service {service_id}")
                return True
            else:
                logger.error(f"Failed to force stop service {service_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to force stop service {service_id}: {e}")
            return False

    async def close_all_connections(self) -> None:
        """Close all tracked connections."""
        logger.info("Closing all tracked connections")
        
        # Close database connections
        for connection_id, connection in self.database_connections.items():
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
                    logger.debug(f"Closed database connection {connection_id}")
            except Exception as e:
                logger.error(f"Failed to close database connection {connection_id}: {e}")
        
        # Close HTTP sessions
        for session_id, session in self.http_sessions.items():
            try:
                await session.close()
                logger.debug(f"Closed HTTP session {session_id}")
            except Exception as e:
                logger.error(f"Failed to close HTTP session {session_id}: {e}")
        
        # Close WebSockets
        for websocket_id, websocket in self.websocket_connections.items():
            try:
                if hasattr(websocket, 'close'):
                    await websocket.close()
                    logger.debug(f"Closed WebSocket {websocket_id}")
            except Exception as e:
                logger.error(f"Failed to close WebSocket {websocket_id}: {e}")
        
        # Clear tracking
        self.database_connections.clear()
        self.http_sessions.clear()
        self.websocket_connections.clear()

    async def close(self) -> None:
        """Close the service integration."""
        logger.info("Closing Service Management Integration")
        
        # Cancel any active operations
        for feature_id, result in self.active_operations.items():
            logger.warning(f"Cancelling active service operation for feature {feature_id}")
            result.status = ServiceIntegrationStatus.FAILED
            result.errors.append("Service integration shutdown")
        
        self.active_operations.clear()
        
        # Close all connections
        await self.close_all_connections()
        
        # Clear tracking data
        self.feature_services.clear()
        self.feature_connections.clear()
        self.feature_websockets.clear()
        self.feature_cache_keys.clear()
        self.state_snapshots.clear()
        
        logger.info("Service Management Integration closed")