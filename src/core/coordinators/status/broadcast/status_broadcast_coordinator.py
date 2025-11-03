"""
Status Broadcast Coordinator

Focused coordinator for status broadcasting and change tracking.
Extracted from StatusCoordinator for single responsibility.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any

from src.config import Config
from ...base_coordinator import BaseCoordinator


class StatusBroadcastCoordinator(BaseCoordinator):
    """
    Coordinates status broadcasting and change detection.
    
    Responsibilities:
    - Track broadcast state changes
    - Handle status broadcasting
    - Compute state hashes for change detection
    """
    
    def __init__(self, config, broadcast_coordinator=None):
        super().__init__(config)
        self._broadcast_coordinator = broadcast_coordinator
        self._last_broadcast_state = {}
        self._broadcast_metrics = {
            "total_broadcasts": 0,
            "successful_broadcasts": 0,
            "failed_broadcasts": 0,
            "state_changes": 0,
            "last_broadcast_time": None,
            "last_error": None
        }
    
    async def initialize(self) -> None:
        """Initialize status broadcast coordinator."""
        self._log_info("Initializing StatusBroadcastCoordinator")
        self._initialized = True
    
    def set_broadcast_coordinator(self, broadcast_coordinator) -> None:
        """Set broadcast coordinator."""
        self._broadcast_coordinator = broadcast_coordinator
    
    def has_state_changed(self, components: Dict[str, Any]) -> bool:
        """Check if state has changed since last broadcast."""
        current_state_hash = self.compute_state_hash(components)
        return current_state_hash != self._last_broadcast_state.get("hash")
    
    def compute_state_hash(self, components: Dict[str, Any]) -> str:
        """Compute hash of component states for change detection."""
        normalized = json.dumps(components, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def compute_overall_status(self, components: Dict[str, Any]) -> str:
        """Compute overall system status from component statuses."""
        status_counts = {"healthy": 0, "degraded": 0, "error": 0, "stopped": 0, "inactive": 0, "idle": 0}
        
        for component in components.values():
            status = component.get("status", "unknown")
            if status in status_counts:
                status_counts[status] += 1
        
        if status_counts["error"] > 0:
            return "error"
        elif status_counts["stopped"] > 0:
            return "degraded"
        elif status_counts["inactive"] > 0:
            return "degraded"
        elif status_counts["healthy"] > 0:
            return "healthy"
        else:
            return "idle"
    
    async def broadcast_system_health(self, components: Dict[str, Any], timestamp: str, force: bool = False) -> bool:
        """Broadcast system health with error tracking."""
        if not self._broadcast_coordinator:
            return False
        
        state_changed = self.has_state_changed(components)
        if not (state_changed or force):
            return False
        
        try:
            self._broadcast_metrics["total_broadcasts"] += 1
            self._broadcast_metrics["last_broadcast_time"] = datetime.now(timezone.utc).isoformat()
            
            health_data = {
                "status": self.compute_overall_status(components),
                "components": components,
                "timestamp": timestamp,
                "metrics": self._broadcast_metrics
            }
            
            await self._broadcast_coordinator.broadcast_system_health_update(health_data)
            
            if state_changed:
                self._last_broadcast_state = {
                    "hash": self.compute_state_hash(components),
                    "timestamp": timestamp,
                    "components": components
                }
                self._broadcast_metrics["state_changes"] += 1
            
            self._broadcast_metrics["successful_broadcasts"] += 1
            self._broadcast_metrics["last_error"] = None
            return True
            
        except Exception as e:
            self._broadcast_metrics["failed_broadcasts"] += 1
            self._broadcast_metrics["last_error"] = str(e)
            self._log_error(f"Failed to broadcast system health: {e}")
            return False
    
    def get_broadcast_metrics(self) -> Dict[str, Any]:
        """Get broadcast metrics."""
        return self._broadcast_metrics.copy()
    
    async def cleanup(self) -> None:
        """Cleanup status broadcast coordinator resources."""
        self._log_info("StatusBroadcastCoordinator cleanup complete")

