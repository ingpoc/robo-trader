"""
Workflow State Tracker for Progressive Discovery.

Tracks workflow stages, tool usage patterns, and provides intelligent
context management for progressive tool discovery in the trading system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum

from src.core.di import DependencyContainer
from src.core.event_bus import EventBus, Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Workflow stages for tracking progression."""
    IDLE = "idle"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    OPTIMIZATION = "optimization"


class WorkflowActivity(Enum):
    """Types of workflow activities."""
    TOOL_CALL = "tool_call"
    TASK_CREATION = "task_creation"
    TASK_COMPLETION = "task_completion"
    WORKFLOW_TRANSITION = "workflow_transition"
    PORTFOLIO_UPDATE = "portfolio_update"
    MARKET_EVENT = "market_event"


@dataclass
class WorkflowState:
    """Current workflow state information."""
    stage: WorkflowStage
    substage: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    duration_minutes: int = 0
    completed_stages: Set[WorkflowStage] = field(default_factory=set)
    stage_transitions: List[Dict[str, Any]] = field(default_factory=list)
    active_tools: Set[str] = field(default_factory=set)
    tool_usage_count: Dict[str, int] = field(default_factory=dict)
    session_id: Optional[str] = None
    user_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolUsageRecord:
    """Record of tool usage for pattern analysis."""
    tool_name: str
    stage: WorkflowStage
    timestamp: datetime
    success: bool
    duration_ms: int
    parameters: Dict[str, Any]
    result_summary: str
    suggested_next_tools: List[str] = field(default_factory=list)
    effectiveness_score: float = 0.0


@dataclass
class WorkflowMetrics:
    """Metrics for workflow analysis."""
    total_sessions: int = 0
    average_session_duration: float = 0.0
    stage_completion_rates: Dict[str, float] = field(default_factory=dict)
    tool_usage_patterns: Dict[str, List[ToolUsageRecord]] = field(default_factory=dict)
    most_effective_tools: List[Dict[str, Any]] = field(default_factory=list)
    workflow_efficiency_score: float = 0.0


class WorkflowStateTracker:
    """
    Tracks workflow state progression and tool usage patterns.

    Features:
    - Workflow stage tracking with progression logic
    - Tool usage pattern analysis
    - Session management and persistence
    - Metrics calculation and optimization suggestions
    - Event-driven state updates
    """

    def __init__(self, container: DependencyContainer):
        """Initialize workflow state tracker."""
        self.container = container
        self.event_bus = None
        self._initialized = False

        # Current state
        self._current_state: Optional[WorkflowState] = None
        self._session_id: Optional[str] = None
        self._session_start_time: Optional[datetime] = None

        # Historical data
        self._usage_history: List[ToolUsageRecord] = []
        self._workflow_history: List[WorkflowState] = []
        self._metrics: WorkflowMetrics = WorkflowMetrics()

        # Configuration
        self._stage_timeout_minutes = {
            WorkflowStage.RESEARCH: 30,
            WorkflowStage.ANALYSIS: 20,
            WorkflowStage.EXECUTION: 15,
            WorkflowStage.MONITORING: 10,
            WorkflowStage.OPTIMIZATION: 25,
            WorkflowStage.IDLE: 60
        }

        # Stage transition rules
        self._stage_transitions = {
            WorkflowStage.IDLE: [WorkflowStage.RESEARCH],
            WorkflowStage.RESEARCH: [WorkflowStage.ANALYSIS, WorkflowStage.IDLE],
            WorkflowStage.ANALYSIS: [WorkflowStage.EXECUTION, WorkflowStage.OPTIMIZATION, WorkflowStage.RESEARCH],
            WorkflowStage.EXECUTION: [WorkflowStage.MONITORING, WorkflowStage.ANALYSIS],
            WorkflowStage.MONITORING: [WorkflowStage.OPTIMIZATION, WorkflowStage.RESEARCH, WorkflowStage.EXECUTION],
            WorkflowStage.OPTIMIZATION: [WorkflowStage.RESEARCH, WorkflowStage.ANALYSIS, WorkflowStage.IDLE]
        }

    async def initialize(self) -> None:
        """Initialize workflow state tracker."""
        if self._initialized:
            return

        try:
            # Get event bus
            self.event_bus = await self.container.get("event_bus")

            # Subscribe to relevant events
            self.event_bus.subscribe(EventType.MCP_TOOL_CALLED, self)
            self.event_bus.subscribe(EventType.TASK_CREATED, self)
            self.event_bus.subscribe(EventType.TASK_COMPLETED, self)
            self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
            self.event_bus.subscribe(EventType.PORTFOLIO_PNL_UPDATE, self)

            # Initialize workflow state
            await self._initialize_new_session()

            self._initialized = True
            logger.info("Workflow State Tracker initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Workflow State Tracker: {e}")
            raise TradingError(
                f"Workflow State Tracker initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def _initialize_new_session(self) -> None:
        """Initialize a new workflow session."""
        self._session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self._session_start_time = datetime.utcnow()

        self._current_state = WorkflowState(
            stage=WorkflowStage.IDLE,
            session_id=self._session_id,
            user_context={
                "portfolio_value": 0.0,
                "trades_executed": 0,
                "active_positions": [],
                "user_expertise_level": "intermediate"
            }
        )

        logger.info(f"Initialized new workflow session: {self._session_id}")

    async def get_current_state(self) -> WorkflowState:
        """Get current workflow state."""
        if not self._current_state:
            await self._initialize_new_session()
        return self._current_state

    async def transition_to_stage(self, new_stage: WorkflowStage, substage: Optional[str] = None) -> bool:
        """
        Transition to a new workflow stage.

        Args:
            new_stage: Target workflow stage
            substage: Optional substage within the stage

        Returns:
            True if transition was successful, False otherwise
        """
        if not self._current_state:
            return False

        # Validate transition
        if not self._is_valid_transition(self._current_state.stage, new_stage):
            logger.warning(f"Invalid workflow transition: {self._current_state.stage} -> {new_stage}")
            return False

        # Record transition
        transition_record = {
            "from_stage": self._current_state.stage.value,
            "to_stage": new_stage.value,
            "timestamp": datetime.utcnow(),
            "duration_minutes": self._current_state.duration_minutes,
            "reason": "automatic_transition"
        }

        # Update state
        old_stage = self._current_state.stage
        self._current_state.stage = new_stage
        self._current_state.substage = substage
        self._current_state.start_time = datetime.utcnow()
        self._current_state.last_activity = datetime.utcnow()
        self._current_state.duration_minutes = 0

        # Mark completed stage
        if old_stage != WorkflowStage.IDLE:
            self._current_state.completed_stages.add(old_stage)

        self._current_state.stage_transitions.append(transition_record)

        logger.info(f"Workflow transition: {old_stage.value} -> {new_stage.value}")
        return True

    def _is_valid_transition(self, from_stage: WorkflowStage, to_stage: WorkflowStage) -> bool:
        """Check if transition is valid."""
        return to_stage in self._stage_transitions.get(from_stage, [])

    async def track_tool_usage(self, tool_name: str, parameters: Dict[str, Any],
                              result_data: Dict[str, Any]) -> None:
        """
        Track tool usage for pattern analysis.

        Args:
            tool_name: Name of the tool used
            parameters: Tool parameters
            result_data: Tool result data
        """
        if not self._current_state:
            return

        # Create usage record
        usage_record = ToolUsageRecord(
            tool_name=tool_name,
            stage=self._current_state.stage,
            timestamp=datetime.utcnow(),
            success=result_data.get("success", True),
            duration_ms=result_data.get("duration_ms", 0),
            parameters=parameters.copy(),
            result_summary=result_data.get("summary", ""),
            suggested_next_tools=result_data.get("suggested_tools", [])
        )

        # Update current state
        self._current_state.active_tools.add(tool_name)
        self._current_state.tool_usage_count[tool_name] = self._current_state.tool_usage_count.get(tool_name, 0) + 1
        self._current_state.last_activity = datetime.utcnow()

        # Add to history
        self._usage_history.append(usage_record)

        # Keep history manageable
        if len(self._usage_history) > 1000:
            self._usage_history = self._usage_history[-500:]

        # Update user context if available
        await self._update_user_context_from_tool(tool_name, parameters, result_data)

        logger.debug(f"Tracked tool usage: {tool_name} in {self._current_state.stage.value}")

    async def _update_user_context_from_tool(self, tool_name: str, parameters: Dict[str, Any],
                                          result_data: Dict[str, Any]) -> None:
        """Update user context based on tool usage."""
        if not self._current_state:
            return

        # Update context based on tool type
        if tool_name == "execute_paper_trade":
            self._current_state.user_context["trades_executed"] += 1
        elif tool_name == "check_paper_trading_status":
            # Update portfolio value from status check
            portfolio_data = result_data.get("portfolio_data", {})
            if "portfolio_value" in portfolio_data:
                self._current_state.user_context["portfolio_value"] = portfolio_data["portfolio_value"]
        elif tool_name == "research_symbol":
            # Add researched symbol to active positions
            symbol = parameters.get("symbol", "").upper()
            if symbol and symbol not in self._current_state.user_context.get("active_positions", []):
                self._current_state.user_context.setdefault("active_positions", []).append(symbol)

    async def check_stage_timeout(self) -> Optional[WorkflowStage]:
        """
        Check if current stage has timed out and suggest transition.

        Returns:
            Suggested next stage if timeout detected, None otherwise
        """
        if not self._current_state:
            return None

        current_stage = self._current_state.stage
        timeout_minutes = self._stage_timeout_minutes.get(current_stage, 30)

        if self._current_state.duration_minutes >= timeout_minutes:
            # Suggest next stage based on completed stages and transitions
            suggested_stage = await self._suggest_next_stage()
            logger.info(f"Stage timeout detected: {current_stage.value} ({self._current_state.duration_minutes}min)")
            return suggested_stage

        return None

    async def _suggest_next_stage(self) -> WorkflowStage:
        """Suggest next stage based on context and history."""
        if not self._current_state:
            return WorkflowStage.RESEARCH

        current_stage = self._current_state.stage
        user_context = self._current_state.user_context

        # Suggest based on current stage and user context
        if current_stage == WorkflowStage.RESEARCH:
            if user_context.get("trades_executed", 0) > 0:
                return WorkflowStage.ANALYSIS
            else:
                return WorkflowStage.ANALYSIS
        elif current_stage == WorkflowStage.ANALYSIS:
            if user_context.get("trades_executed", 0) > 5:
                return WorkflowStage.EXECUTION
            else:
                return WorkflowStage.OPTIMIZATION
        elif current_stage == WorkflowStage.EXECUTION:
            return WorkflowStage.MONITORING
        elif current_stage == WorkflowStage.MONITORING:
            if user_context.get("portfolio_value", 0) > 100000:
                return WorkflowStage.OPTIMIZATION
            else:
                return WorkflowStage.RESEARCH
        elif current_stage == WorkflowStage.OPTIMIZATION:
            return WorkflowStage.RESEARCH
        else:
            return WorkflowStage.RESEARCH

    async def update_activity(self) -> None:
        """Update last activity timestamp."""
        if self._current_state:
            self._current_state.last_activity = datetime.utcnow()
            if self._session_start_time:
                self._current_state.duration_minutes = int(
                    (datetime.utcnow() - self._session_start_time).total_seconds() / 60
                )

    async def handle_event(self, event: Event) -> None:
        """Handle events from the event bus."""
        try:
            if event.type == EventType.MCP_TOOL_CALLED:
                await self._handle_tool_called(event)
            elif event.type == EventType.TASK_CREATED:
                await self._handle_task_created(event)
            elif event.type == EventType.TASK_COMPLETED:
                await self._handle_task_completed(event)
            elif event.type == EventType.EXECUTION_ORDER_FILLED:
                await self._handle_trade_executed(event)
            elif event.type == EventType.PORTFOLIO_PNL_UPDATE:
                await self._handle_portfolio_update(event)

        except Exception as e:
            logger.error(f"Error handling workflow event {event.type}: {e}")

    async def _handle_tool_called(self, event: Event) -> None:
        """Handle MCP tool call event."""
        data = event.data
        tool_name = data.get("tool_name")
        parameters = data.get("parameters", {})
        result_data = data.get("result_data", {})

        if tool_name:
            await self.track_tool_usage(tool_name, parameters, result_data)

    async def _handle_task_created(self, event: Event) -> None:
        """Handle task creation event."""
        await self.update_activity()

        # Update workflow stage based on task type
        data = event.data
        task_type = data.get("task_type")

        if task_type == "MARKET_RESEARCH_PERPLEXITY":
            await self.transition_to_stage(WorkflowStage.RESEARCH)
        elif task_type == "PORTFOLIO_INTELLIGENCE_ANALYSIS":
            await self.transition_to_stage(WorkflowStage.ANALYSIS)
        elif task_type == "PAPER_TRADE_EXECUTION":
            await self.transition_to_stage(WorkflowStage.EXECUTION)
        elif task_type == "PROMPT_TEMPLATE_OPTIMIZATION":
            await self.transition_to_stage(WorkflowStage.OPTIMIZATION)

    async def _handle_task_completed(self, event: Event) -> None:
        """Handle task completion event."""
        await self.update_activity()

    async def _handle_trade_executed(self, event: Event) -> None:
        """Handle trade execution event."""
        await self.update_activity()
        await self.transition_to_stage(WorkflowStage.MONITORING)

    async def _handle_portfolio_update(self, event: Event) -> None:
        """Handle portfolio update event."""
        await self.update_activity()

    async def get_workflow_analytics(self) -> Dict[str, Any]:
        """Get comprehensive workflow analytics."""
        if not self._current_state:
            return {"error": "Workflow tracker not initialized"}

        # Calculate session metrics
        session_duration = 0
        if self._session_start_time:
            session_duration = int((datetime.utcnow() - self._session_start_time).total_seconds() / 60)

        # Calculate stage completion rates
        stage_metrics = {}
        total_sessions = len(self._workflow_history) + 1  # +1 for current session

        for stage in WorkflowStage:
            completed_count = sum(1 for state in self._workflow_history if stage in state.completed_stages)
            if self._current_state and stage in self._current_state.completed_stages:
                completed_count += 1
            stage_metrics[stage.value] = {
                "completion_rate": completed_count / total_sessions if total_sessions > 0 else 0,
                "total_transitions": len([t for t in self._current_state.stage_transitions if t["to_stage"] == stage.value]),
                "current_session_completed": stage in self._current_state.completed_stages
            }

        # Calculate tool usage patterns
        tool_patterns = {}
        for tool_name, usage_count in self._current_state.tool_usage_count.items():
            # Get recent usage records for this tool
            recent_records = [r for r in self._usage_history if r.tool_name == tool_name][-10:]

            if recent_records:
                success_rate = sum(1 for r in recent_records if r.success) / len(recent_records)
                avg_duration = sum(r.duration_ms for r in recent_records) / len(recent_records)

                tool_patterns[tool_name] = {
                    "usage_count": usage_count,
                    "success_rate": round(success_rate, 3),
                    "avg_duration_ms": round(avg_duration),
                    "most_used_in_stage": max(set(r.stage.value for r in recent_records), key=list),
                    "suggested_next_tools": list(set(next_tool for r in recent_records for next_tool in r.suggested_next_tools))
                }

        # Calculate workflow efficiency
        completed_stages_count = len(self._current_state.completed_stages)
        total_possible_stages = len([s for s in WorkflowStage if s != WorkflowStage.IDLE])
        workflow_efficiency = completed_stages_count / total_possible_stages if total_possible_stages > 0 else 0

        return {
            "session_info": {
                "session_id": self._session_id,
                "duration_minutes": session_duration,
                "start_time": self._session_start_time.isoformat() if self._session_start_time else None
            },
            "current_state": {
                "stage": self._current_state.stage.value,
                "substage": self._current_state.substage,
                "duration_minutes": self._current_state.duration_minutes,
                "completed_stages": [s.value for s in self._current_state.completed_stages],
                "active_tools": list(self._current_state.active_tools),
                "last_activity": self._current_state.last_activity.isoformat()
            },
            "stage_metrics": stage_metrics,
            "tool_patterns": tool_patterns,
            "workflow_efficiency": round(workflow_efficiency, 3),
            "total_usage_records": len(self._usage_history),
            "user_context": self._current_state.user_context
        }

    async def get_workflow_recommendations(self) -> List[Dict[str, Any]]:
        """Get intelligent workflow recommendations based on current state."""
        if not self._current_state:
            return []

        recommendations = []

        # Stage-based recommendations
        current_stage = self._current_state.stage
        user_context = self._current_state.user_context

        if current_stage == WorkflowStage.RESEARCH:
            if self._current_state.duration_minutes > 15:
                recommendations.append({
                    "type": "stage_transition",
                    "message": "Consider transitioning to analysis stage",
                    "confidence": 0.8,
                    "action": "transition_to_stage",
                    "parameters": {"stage": "analysis"}
                })

        elif current_stage == WorkflowStage.ANALYSIS:
            if user_context.get("trades_executed", 0) > 3:
                recommendations.append({
                    "type": "stage_transition",
                    "message": "Ready for execution based on your trading history",
                    "confidence": 0.9,
                    "action": "transition_to_stage",
                    "parameters": {"stage": "execution"}
                })

        elif current_stage == WorkflowStage.EXECUTION:
            if self._current_state.duration_minutes > 10:
                recommendations.append({
                    "type": "stage_transition",
                    "message": "Monitor your recent trades",
                    "confidence": 0.8,
                    "action": "transition_to_stage",
                    "parameters": {"stage": "monitoring"}
                })

        # Tool usage recommendations
        most_used_tools = sorted(self._current_state.tool_usage_count.items(),
                                key=lambda x: x[1], reverse=True)[:3]

        if most_used_tools:
            recommendations.append({
                "type": "tool_suggestion",
                "message": f"Your most used tools: {', '.join([t[0] for t in most_used_tools])}",
                "confidence": 0.7,
                "action": "continue_current_workflow"
            })

        # Portfolio complexity recommendations
        if user_context.get("portfolio_value", 0) > 100000:
            recommendations.append({
                "type": "advanced_feature",
                "message": "Consider using advanced analysis tools for your portfolio",
                "confidence": 0.8,
                "action": "enable_advanced_tools"
            })

        return recommendations[:5]  # Return top 5 recommendations

    async def cleanup(self) -> None:
        """Cleanup workflow state tracker resources."""
        if self.event_bus:
            # Unsubscribe from events
            self.event_bus.unsubscribe(EventType.MCP_TOOL_CALLED, self)
            self.event_bus.unsubscribe(EventType.TASK_CREATED, self)
            self.event_bus.unsubscribe(EventType.TASK_COMPLETED, self)
            self.event_bus.unsubscribe(EventType.EXECUTION_ORDER_FILLED, self)
            self.event_bus.unsubscribe(EventType.PORTFOLIO_PNL_UPDATE, self)

        # Save current state to history
        if self._current_state:
            self._workflow_history.append(self._current_state)

        # Clear memory
        self._current_state = None
        self._usage_history.clear()
        self._workflow_history.clear()

        self._initialized = False
        logger.info("Workflow State Tracker cleaned up successfully")