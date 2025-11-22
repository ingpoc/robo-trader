"""
AI Status Coordinator

Focused coordinator for AI and Claude agent status.
Extracted from StatusCoordinator for single responsibility.
Now uses event-driven architecture instead of polling.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
import uuid

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType, EventHandler
from ..base_coordinator import BaseCoordinator
from ...ai_planner import AIPlanner
from ..core.session_coordinator import SessionCoordinator


class AIStatusCoordinator(BaseCoordinator, EventHandler):
    """
    Coordinates AI and Claude agent status using event-driven architecture.

    Responsibilities:
    - Get AI status
    - Get Claude agent status
    - Subscribe to Claude analysis events (event-driven instead of polling)
    - Track active analysis sessions
    """

    def __init__(
        self,
        config: Config,
        ai_planner: AIPlanner,
        session_coordinator: SessionCoordinator
    ):
        super().__init__(config)
        self.ai_planner = ai_planner
        self.session_coordinator = session_coordinator
        self.event_bus: Optional[EventBus] = None
        self._active_analyses: Set[str] = set()  # Track active analysis IDs
        self._last_broadcast_status: Optional[str] = None  # Track last broadcast to avoid duplicates

    async def initialize(self) -> None:
        """Initialize AI status coordinator and subscribe to events."""
        self._log_info("Initializing AIStatusCoordinator")

        # Get event bus from container
        self.event_bus = await self.container.get("event_bus")

        # Subscribe to Claude analysis events for event-driven broadcasting
        self.event_bus.subscribe(EventType.CLAUDE_ANALYSIS_STARTED, self)
        self.event_bus.subscribe(EventType.CLAUDE_ANALYSIS_COMPLETED, self)

        self._broadcast_coordinator = None
        self._initialized = True
        self._log_info("AIStatusCoordinator initialized - subscribed to Claude analysis events (event-driven, no polling)")

    def set_broadcast_coordinator(self, broadcast_coordinator) -> None:
        """Set broadcast coordinator for Claude status updates."""
        self._broadcast_coordinator = broadcast_coordinator

    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        return await self.ai_planner.get_current_task_status()

    async def get_claude_agent_status(self) -> Dict[str, Any]:
        """Get Claude agent status."""
        claude_status = await self.session_coordinator.get_claude_status()
        
        if claude_status and claude_status.is_valid:
            sdk_connected = claude_status.account_info.get("sdk_connected", False)
            cli_process_running = claude_status.account_info.get("cli_process_running", False)
            if sdk_connected and cli_process_running:
                return {
                    "status": "active",
                    "authMethod": claude_status.account_info.get("auth_method", "unknown"),
                    "tasksCompleted": claude_status.account_info.get("tasks_completed", 0),
                    "lastActivity": claude_status.account_info.get("last_activity", datetime.now(timezone.utc).isoformat())
                }
            else:
                return {
                    "status": "authenticated",
                    "authMethod": claude_status.account_info.get("auth_method", "unknown"),
                    "tasksCompleted": 0,
                    "lastActivity": datetime.now(timezone.utc).isoformat()
                }
        else:
            return {
                "status": "inactive",
                "authMethod": "none",
                "tasksCompleted": 0,
                "lastActivity": None
            }

    def get_ai_analysis_status(self) -> str:
        """Get current AI analysis scheduler status."""
        try:
            from src.services.portfolio_intelligence import PortfolioIntelligenceAnalyzer
            status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
            return status_info.get("status", "idle")
        except Exception as e:
            self._log_warning(f"Could not get AI analysis status: {e}")
            return "idle"
    
    def get_ai_analysis_last_run(self) -> str:
        """Get last run time for AI analysis."""
        try:
            status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
            last_activity = status_info.get("last_activity")
            if last_activity:
                return last_activity
            from datetime import timedelta
            return (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        except Exception:
            return (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    
    def get_ai_analysis_active_task(self) -> Optional[Dict[str, Any]]:
        """Get active AI analysis task details."""
        try:
            status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
            current_task = status_info.get("current_task")
            if current_task:
                return {
                    "agent_name": current_task.get("agent_name"),
                    "symbols_count": current_task.get("symbols_count", 0),
                    "started_at": current_task.get("started_at")
                }
            return None
        except Exception:
            return None

    async def broadcast_claude_status_based_on_analysis(self) -> None:
        """
        Broadcast Claude status based on active AI analysis tasks.

        This method automatically detects when Claude analysis is running
        (whether manually triggered or via background scheduler) and broadcasts
        the appropriate Claude status to the UI.

        - If analysis is running → broadcast 'CLAUDE_ANALYSIS_STARTED' event
        - If no analysis → broadcast 'CLAUDE_ANALYSIS_COMPLETED' event

        Also ensures Claude is properly authenticated before broadcasting.
        """
        if not self._broadcast_coordinator:
            return

        try:
            # First check if Claude is authenticated
            claude_status = await self.get_claude_agent_status()
            if not claude_status or claude_status.get("status") == "inactive":
                # Don't broadcast if Claude is not authenticated
                self._log_debug("Claude not authenticated, skipping status broadcast")
                return

            from src.services.portfolio_intelligence import PortfolioIntelligenceAnalyzer

            # Get active analysis tasks
            try:
                status_info = PortfolioIntelligenceAnalyzer.get_active_analysis_status()
                has_running_analysis = status_info.get("status") == "running" or len(status_info.get("running_tasks", [])) > 0
            except Exception:
                # If we can't get analysis status, assume no analysis is running
                has_running_analysis = False
                status_info = {"running_tasks": []}

            # Determine auth method from Claude status
            auth_method = claude_status.get("authMethod", claude_status.get("auth_method", "claude_code"))

            if has_running_analysis:
                # Broadcast CLAUDE_ANALYSIS_STARTED when Claude analysis is running
                # This triggers the frontend useClaudeStatus hook to set status to 'analyzing'
                active_task = self.get_ai_analysis_active_task()
                analysis_event_data = {
                    "analysis_id": str(uuid.uuid4()),  # Generate unique analysis ID
                    "agent_name": active_task.get("agent_name") if active_task else "analyzer",
                    "symbols_count": active_task.get("symbols_count", 0) if active_task else 0,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "running",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self._broadcast_coordinator.broadcast_claude_analysis_started(analysis_event_data)
                self._log_debug(f"Broadcast Claude analysis started: {analysis_event_data.get('agent_name')}")
            else:
                # Broadcast CLAUDE_ANALYSIS_COMPLETED when no analysis is running
                # This clears the analyzing status in the frontend
                completed_event_data = {
                    "analysis_id": str(uuid.uuid4()),
                    "agent_name": "analyzer",
                    "symbols_count": 0,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self._broadcast_coordinator.broadcast_claude_analysis_completed(completed_event_data)
                self._log_debug("Broadcast Claude analysis completed")

        except Exception as e:
            self._log_warning(f"Failed to broadcast Claude status based on analysis: {e}")

    async def cleanup(self) -> None:
        """Cleanup AI status coordinator resources and unsubscribe from events."""
        if not self._initialized:
            return

        # Unsubscribe from events
        if self.event_bus:
            self.event_bus.unsubscribe(EventType.CLAUDE_ANALYSIS_STARTED, self)
            self.event_bus.unsubscribe(EventType.CLAUDE_ANALYSIS_COMPLETED, self)

        self._active_analyses.clear()
        self._log_info("AIStatusCoordinator cleanup complete")

    async def handle_event(self, event: Event) -> None:
        """
        Handle Claude analysis events for real-time status tracking.

        Replaces polling-based approach with event-driven updates.
        """
        try:
            if event.type == EventType.CLAUDE_ANALYSIS_STARTED:
                await self._handle_analysis_started(event)
            elif event.type == EventType.CLAUDE_ANALYSIS_COMPLETED:
                await self._handle_analysis_completed(event)
        except Exception as e:
            self._log_error(f"Failed to handle Claude analysis event {event.type}: {e}")

    async def _handle_analysis_started(self, event: Event) -> None:
        """Handle Claude analysis started event."""
        analysis_id = event.data.get("analysis_id")
        if analysis_id:
            self._active_analyses.add(analysis_id)
            self._log_info(f"Claude analysis started: {analysis_id}")

        # Broadcast 'analyzing' status and specific analysis started event
        await self._broadcast_claude_status("analyzing", event.data)

        # Also broadcast the specific analysis started event for granular frontend tracking
        if self._broadcast_coordinator:
            try:
                await self._broadcast_coordinator.broadcast_claude_analysis_started(event.data)
            except Exception as e:
                self._log_warning(f"Failed to broadcast Claude analysis started event: {e}")

    async def _handle_analysis_completed(self, event: Event) -> None:
        """Handle Claude analysis completed event."""
        analysis_id = event.data.get("analysis_id")
        if analysis_id:
            self._active_analyses.discard(analysis_id)
            status = event.data.get("status", "completed")
            self._log_info(f"Claude analysis completed: {analysis_id} ({status})")

        # Broadcast status based on whether other analyses are active
        if self._active_analyses:
            await self._broadcast_claude_status("analyzing", event.data)
        else:
            await self._broadcast_claude_status("connected/idle", event.data)

        # Also broadcast the specific analysis completed event for granular frontend tracking
        if self._broadcast_coordinator:
            try:
                await self._broadcast_coordinator.broadcast_claude_analysis_completed(event.data)
            except Exception as e:
                self._log_warning(f"Failed to broadcast Claude analysis completed event: {e}")

    async def _broadcast_claude_status(self, status: str, event_data: Dict[str, Any]) -> None:
        """
        Broadcast Claude status to UI with change detection to avoid duplicates.
        """
        if not self._broadcast_coordinator:
            return

        # Skip duplicate broadcasts
        if self._last_broadcast_status == status and len(self._active_analyses) > 0:
            return

        try:
            claude_status_data = {
                "status": status,
                "auth_method": "claude_code",
                "sdk_connected": True,
                "cli_process_running": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "analysis_in_progress": status == "analyzing",
                    "active_analyses": len(self._active_analyses),
                    "latest_analysis": {
                        "analysis_id": event_data.get("analysis_id"),
                        "agent_name": event_data.get("agent_name"),
                        "symbols_count": event_data.get("symbols_count", 0),
                        "status": event_data.get("status", "running")
                    }
                }
            }

            await self._broadcast_coordinator.broadcast_claude_status_update(claude_status_data)
            self._last_broadcast_status = status
            self._log_debug(f"Broadcast Claude status: {status}")

        except Exception as e:
            self._log_warning(f"Failed to broadcast Claude status: {e}")

