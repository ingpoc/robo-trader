"""
Progressive Discovery Manager for MCP Tools.

Manages dynamic tool discovery based on workflow context, user behavior,
and system state to provide Claude with the most relevant tools at each stage.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from src.core.di import DependencyContainer
from src.core.event_bus import EventBus, Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Workflow stages for progressive discovery."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    OPTIMIZATION = "optimization"


class ToolCategory(Enum):
    """Tool categories for organization."""
    CORE = "core"
    CONTEXTUAL = "contextual"
    ADVANCED = "advanced"
    SUGGESTED = "suggested"


@dataclass
class DiscoveryContext:
    """Context for tool discovery."""
    workflow_stage: WorkflowStage
    portfolio_value: float = 0.0
    trades_executed: int = 0
    current_positions: List[str] = None
    active_strategies: List[str] = None
    last_activity: Optional[datetime] = None
    user_expertise_level: str = "intermediate"  # beginner, intermediate, advanced
    session_duration_minutes: int = 0

    def __post_init__(self):
        if self.current_positions is None:
            self.current_positions = []
        if self.active_strategies is None:
            self.active_strategies = []


@dataclass
class ToolMetadata:
    """Metadata for discovered tools."""
    name: str
    category: ToolCategory
    description: str
    required_stage: WorkflowStage
    dependencies: List[str] = None
    usage_count: int = 0
    last_used: Optional[datetime] = None
    effectiveness_score: float = 0.0  # 0-1 based on user feedback

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class DiscoverySuggestion:
    """Tool discovery suggestion."""
    tool_name: str
    reason: str
    confidence: float  # 0-1
    priority: int  # 1-10


class ProgressiveDiscoveryManager:
    """
    Manages progressive discovery of MCP tools based on context and behavior.

    Features:
    - Tool categorization (core, contextual, advanced)
    - Workflow stage-based discovery
    - Usage pattern tracking
    - Contextual suggestions
    - Learning from user behavior
    """

    def __init__(self, container: DependencyContainer):
        """Initialize discovery manager."""
        self.container = container
        self.event_bus = None
        self._initialized = False

        # Discovery state
        self._current_context: Optional[DiscoveryContext] = None
        self._discovered_tools: Set[str] = set()
        self._tool_metadata: Dict[str, ToolMetadata] = {}
        self._usage_history: List[Dict[str, Any]] = []
        self._suggestions_cache: Dict[str, List[DiscoverySuggestion]] = {}

        # Tool definitions
        self._initialize_tool_metadata()

    async def initialize(self) -> None:
        """Initialize discovery manager."""
        if self._initialized:
            return

        try:
            # Get event bus
            self.event_bus = await self.container.get("event_bus")

            # Subscribe to relevant events
            self.event_bus.subscribe(EventType.MCP_TOOL_CALLED, self)
            self.event_bus.subscribe(EventType.TASK_COMPLETED, self)
            self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)

            # Initialize default context
            self._current_context = DiscoveryContext(
                workflow_stage=WorkflowStage.RESEARCH,
                portfolio_value=0.0,
                trades_executed=0,
                session_duration_minutes=0
            )

            self._initialized = True
            logger.info("Progressive Discovery Manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Progressive Discovery Manager: {e}")
            raise TradingError(
                f"Discovery Manager initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    def _initialize_tool_metadata(self) -> None:
        """Initialize tool metadata."""

        # Core tools - always available
        core_tools = {
            "research_symbol": ToolMetadata(
                name="research_symbol",
                category=ToolCategory.CORE,
                description="Research stock symbols using Perplexity API",
                required_stage=WorkflowStage.RESEARCH,
                effectiveness_score=0.8
            ),
            "check_paper_trading_status": ToolMetadata(
                name="check_paper_trading_status",
                category=ToolCategory.CORE,
                description="Get current account status and positions",
                required_stage=WorkflowStage.MONITORING,
                effectiveness_score=0.9
            ),
            "get_market_status": ToolMetadata(
                name="get_market_status",
                category=ToolCategory.CORE,
                description="Get current market status and trading hours",
                required_stage=WorkflowStage.RESEARCH,
                effectiveness_score=0.7
            )
        }

        # Contextual tools - available based on workflow stage
        contextual_tools = {
            "analyze_portfolio_data": ToolMetadata(
                name="analyze_portfolio_data",
                category=ToolCategory.CONTEXTUAL,
                description="Analyze portfolio and generate insights",
                required_stage=WorkflowStage.ANALYSIS,
                dependencies=["research_symbol"],
                effectiveness_score=0.8
            ),
            "execute_paper_trade": ToolMetadata(
                name="execute_paper_trade",
                category=ToolCategory.CONTEXTUAL,
                description="Execute paper trades with strategy tracking",
                required_stage=WorkflowStage.EXECUTION,
                dependencies=["research_symbol"],
                effectiveness_score=0.9
            ),
            "get_strategy_performance": ToolMetadata(
                name="get_strategy_performance",
                category=ToolCategory.CONTEXTUAL,
                description="Get strategy performance metrics",
                required_stage=WorkflowStage.MONITORING,
                dependencies=["execute_paper_trade"],
                effectiveness_score=0.8
            ),
            "optimize_prompt_template": ToolMetadata(
                name="optimize_prompt_template",
                category=ToolCategory.CONTEXTUAL,
                description="Optimize prompts for better data quality",
                required_stage=WorkflowStage.OPTIMIZATION,
                dependencies=["analyze_portfolio_data"],
                effectiveness_score=0.7
            )
        }

        # Advanced tools - available based on context and expertise
        advanced_tools = {
            "calculate_monthly_pnl": ToolMetadata(
                name="calculate_monthly_pnl",
                category=ToolCategory.ADVANCED,
                description="Calculate monthly P&L and performance metrics",
                required_stage=WorkflowStage.MONITORING,
                dependencies=["execute_paper_trade", "get_strategy_performance"],
                effectiveness_score=0.9
            ),
            "risk_assessment": ToolMetadata(
                name="risk_assessment",
                category=ToolCategory.ADVANCED,
                description="Comprehensive portfolio risk analysis",
                required_stage=WorkflowStage.ANALYSIS,
                dependencies=["analyze_portfolio_data"],
                effectiveness_score=0.8
            ),
            "correlation_analysis": ToolMetadata(
                name="correlation_analysis",
                category=ToolCategory.ADVANCED,
                description="Analyze portfolio correlations and diversification",
                required_stage=WorkflowStage.ANALYSIS,
                dependencies=["analyze_portfolio_data"],
                effectiveness_score=0.7
            ),
            "sector_rotation": ToolMetadata(
                name="sector_rotation",
                category=ToolCategory.ADVANCED,
                description="Analyze sector rotation opportunities",
                required_stage=WorkflowStage.ANALYSIS,
                dependencies=["research_symbol", "analyze_portfolio_data"],
                effectiveness_score=0.6
            )
        }

        # Combine all tools
        self._tool_metadata = {**core_tools, **contextual_tools, **advanced_tools}

    async def get_available_tools(self, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Get list of available tools based on context.

        Args:
            context: Optional context override

        Returns:
            List of available tool names
        """
        if context:
            self._update_context(context)

        if not self._current_context:
            return self.get_core_tools()

        available_tools = []

        # Always include core tools
        available_tools.extend(self.get_core_tools())

        # Add contextual tools based on workflow stage
        available_tools.extend(self.get_contextual_tools(self._current_context.workflow_stage))

        # Add advanced tools based on context
        advanced_tools = self.get_advanced_tools(self._current_context)
        available_tools.extend(advanced_tools)

        # Add suggested tools based on usage patterns
        suggested_tools = self.get_suggested_tools(self._current_context)
        available_tools.extend(suggested_tools)

        # Remove duplicates and maintain order
        seen = set()
        unique_tools = []
        for tool in available_tools:
            if tool not in seen:
                seen.add(tool)
                unique_tools.append(tool)

        # Update discovered tools set
        self._discovered_tools.update(unique_tools)

        return unique_tools

    def get_core_tools(self) -> List[str]:
        """Get core tools always available."""
        return [
            tool_name for tool_name, metadata in self._tool_metadata.items()
            if metadata.category == ToolCategory.CORE
        ]

    def get_contextual_tools(self, workflow_stage: WorkflowStage) -> List[str]:
        """Get tools available for specific workflow stage."""
        available = []

        for tool_name, metadata in self._tool_metadata.items():
            if (metadata.category == ToolCategory.CONTEXTUAL and
                metadata.required_stage == workflow_stage):
                available.append(tool_name)

        return available

    def get_advanced_tools(self, context: DiscoveryContext) -> List[str]:
        """Get advanced tools based on context."""
        available = []

        for tool_name, metadata in self._tool_metadata.items():
            if metadata.category == ToolCategory.ADVANCED:
                # Check if requirements are met
                if self._meets_advanced_requirements(tool_name, context):
                    available.append(tool_name)

        return available

    def get_suggested_tools(self, context: DiscoveryContext) -> List[str]:
        """Get suggested tools based on usage patterns."""
        # Generate cache key
        cache_key = f"{context.workflow_stage.value}_{context.trades_executed}_{len(context.current_positions)}"

        if cache_key in self._suggestions_cache:
            suggestions = self._suggestions_cache[cache_key]
        else:
            suggestions = self._generate_suggestions(context)
            self._suggestions_cache[cache_key] = suggestions

        # Return only high-confidence suggestions
        return [s.tool_name for s in suggestions if s.confidence > 0.6]

    def _meets_advanced_requirements(self, tool_name: str, context: DiscoveryContext) -> bool:
        """Check if advanced tool requirements are met."""
        metadata = self._tool_metadata.get(tool_name)
        if not metadata:
            return False

        # Portfolio value requirements
        if tool_name in ["calculate_monthly_pnl", "risk_assessment"]:
            return context.portfolio_value > 50000  # Require significant portfolio

        # Trading experience requirements
        if tool_name in ["correlation_analysis", "sector_rotation"]:
            return context.trades_executed > 10  # Require trading experience

        # Position requirements
        if tool_name == "risk_assessment":
            return len(context.current_positions) > 5  # Require diverse portfolio

        # Strategy requirements
        if tool_name == "calculate_monthly_pnl":
            return len(context.active_strategies) > 0  # Require active strategies

        return False

    def _generate_suggestions(self, context: DiscoveryContext) -> List[DiscoverySuggestion]:
        """Generate tool suggestions based on context and patterns."""
        suggestions = []

        # Analyze recent usage patterns
        recent_tools = self._get_recently_used_tools(minutes=30)

        # Suggest based on workflow progression
        if context.workflow_stage == WorkflowStage.RESEARCH:
            if "research_symbol" in recent_tools:
                suggestions.append(DiscoverySuggestion(
                    tool_name="analyze_portfolio_data",
                    reason="Research completed, time for portfolio analysis",
                    confidence=0.8,
                    priority=8
                ))

        elif context.workflow_stage == WorkflowStage.ANALYSIS:
            if "analyze_portfolio_data" in recent_tools:
                suggestions.append(DiscoverySuggestion(
                    tool_name="execute_paper_trade",
                    reason="Analysis complete, consider executing trades",
                    confidence=0.7,
                    priority=9
                ))

        elif context.workflow_stage == WorkflowStage.EXECUTION:
            if "execute_paper_trade" in recent_tools and context.trades_executed > 0:
                suggestions.append(DiscoverySuggestion(
                    tool_name="get_strategy_performance",
                    reason="Trades executed, review strategy performance",
                    confidence=0.9,
                    priority=7
                ))

        # Suggest based on portfolio complexity
        if len(context.current_positions) > 10:
            suggestions.append(DiscoverySuggestion(
                tool_name="risk_assessment",
                reason="Large portfolio, consider risk assessment",
                confidence=0.7,
                priority=6
            ))

        # Suggest based on trading frequency
        if context.trades_executed > 5:
            suggestions.append(DiscoverySuggestion(
                tool_name="calculate_monthly_pnl",
                reason="Active trading, track monthly performance",
                confidence=0.8,
                priority=5
            ))

        # Sort by priority and confidence
        suggestions.sort(key=lambda x: (x.priority, x.confidence), reverse=True)

        return suggestions[:5]  # Return top 5 suggestions

    def _get_recently_used_tools(self, minutes: int = 30) -> List[str]:
        """Get list of recently used tools."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        recent_tools = []
        for usage in self._usage_history:
            if usage.get("timestamp") > cutoff_time:
                recent_tools.append(usage.get("tool_name"))

        return list(set(recent_tools))

    async def update_discovery_context(self, context_updates: Dict[str, Any]) -> None:
        """Update discovery context."""
        if not self._current_context:
            self._current_context = DiscoveryContext(
                workflow_stage=WorkflowStage.RESEARCH
            )

        # Update context fields
        for key, value in context_updates.items():
            if hasattr(self._current_context, key):
                if key == "workflow_stage" and isinstance(value, str):
                    value = WorkflowStage(value)
                setattr(self._current_context, key, value)

        logger.debug(f"Updated discovery context: {context_updates}")

    def _update_context(self, context: Dict[str, Any]) -> None:
        """Update context from external source."""
        asyncio.create_task(self.update_discovery_context(context))

    async def track_tool_usage(self, tool_name: str, result_data: Dict[str, Any]) -> None:
        """Track tool usage for learning and optimization."""
        usage_record = {
            "tool_name": tool_name,
            "timestamp": datetime.utcnow(),
            "context": asdict(self._current_context) if self._current_context else {},
            "result_summary": result_data.get("summary", ""),
            "success": result_data.get("success", True)
        }

        self._usage_history.append(usage_record)

        # Update tool metadata
        if tool_name in self._tool_metadata:
            metadata = self._tool_metadata[tool_name]
            metadata.usage_count += 1
            metadata.last_used = datetime.utcnow()

        # Keep usage history manageable
        if len(self._usage_history) > 1000:
            self._usage_history = self._usage_history[-500:]

        logger.debug(f"Tracked tool usage: {tool_name}")

    async def handle_event(self, event: Event) -> None:
        """Handle events from the event bus."""
        try:
            if event.type == EventType.MCP_TOOL_CALLED:
                await self._handle_mcp_tool_called(event)
            elif event.type == EventType.TASK_COMPLETED:
                await self._handle_task_completed(event)
            elif event.type == EventType.EXECUTION_ORDER_FILLED:
                await self._handle_trade_executed(event)

        except Exception as e:
            logger.error(f"Error handling discovery event {event.type}: {e}")

    async def _handle_mcp_tool_called(self, event: Event) -> None:
        """Handle MCP tool call event."""
        data = event.data
        tool_name = data.get("tool_name")
        result_data = data.get("result_data", {})

        if tool_name:
            await self.track_tool_usage(tool_name, result_data)

    async def _handle_task_completed(self, event: Event) -> None:
        """Handle task completion event."""
        data = event.data
        task_type = data.get("task_type")

        # Update context based on completed tasks
        if task_type == "PAPER_TRADE_EXECUTION":
            await self.update_discovery_context({
                "trades_executed": self._current_context.trades_executed + 1 if self._current_context else 1
            })

    async def _handle_trade_executed(self, event: Event) -> None:
        """Handle trade execution event."""
        data = event.data
        symbol = data.get("symbol")

        if symbol and self._current_context:
            # Update positions
            if symbol not in self._current_context.current_positions:
                self._current_context.current_positions.append(symbol)

    async def get_discovery_analytics(self) -> Dict[str, Any]:
        """Get discovery analytics and metrics."""
        if not self._current_context:
            return {"error": "Discovery manager not initialized"}

        # Tool usage statistics
        tool_usage = {}
        for tool_name, metadata in self._tool_metadata.items():
            tool_usage[tool_name] = {
                "usage_count": metadata.usage_count,
                "last_used": metadata.last_used.isoformat() if metadata.last_used else None,
                "effectiveness_score": metadata.effectiveness_score,
                "category": metadata.category.value
            }

        # Discovery statistics
        total_tools = len(self._tool_metadata)
        discovered_tools = len(self._discovered_tools)
        discovery_rate = discovered_tools / total_tools if total_tools > 0 else 0

        # Context information
        context_info = asdict(self._current_context)

        # Recent activity
        recent_usage = self._get_recently_used_tools(minutes=60)

        return {
            "total_tools": total_tools,
            "discovered_tools": discovered_tools,
            "discovery_rate": round(discovery_rate, 3),
            "current_context": context_info,
            "tool_usage": tool_usage,
            "recently_used_tools": recent_usage,
            "total_usage_records": len(self._usage_history),
            "suggestions_cache_size": len(self._suggestions_cache)
        }

    async def cleanup(self) -> None:
        """Cleanup discovery manager resources."""
        if self.event_bus:
            # Unsubscribe from events
            self.event_bus.unsubscribe(EventType.MCP_TOOL_CALLED, self)
            self.event_bus.unsubscribe(EventType.TASK_COMPLETED, self)
            self.event_bus.unsubscribe(EventType.EXECUTION_ORDER_FILLED, self)

        # Clear caches
        self._suggestions_cache.clear()
        self._usage_history.clear()
        self._discovered_tools.clear()

        self._initialized = False
        logger.info("Progressive Discovery Manager cleaned up successfully")