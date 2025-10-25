"""Data models for Claude Agent SDK integration."""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


class SessionType(str, Enum):
    """Claude session types."""
    MORNING_PREP = "morning_prep"
    EVENING_REVIEW = "evening_review"
    INTRADAY_ANALYSIS = "intraday_analysis"


class ToolCallType(str, Enum):
    """Tool call identifiers."""
    EXECUTE_TRADE = "execute_trade"
    CLOSE_POSITION = "close_position"
    CHECK_BALANCE = "check_balance"
    FETCH_MARKET_CONTEXT = "fetch_market_context"
    GENERATE_RECOMMENDATION = "generate_recommendation"


@dataclass
class ToolCall:
    """Record of a single tool call."""
    tool_name: ToolCallType
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['tool_name'] = self.tool_name.value
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ToolCall':
        """Create from dictionary."""
        data = data.copy()
        data['tool_name'] = ToolCallType(data['tool_name'])
        return ToolCall(**data)


@dataclass
class StrategyLearning:
    """Learning extracted from strategy session."""
    what_worked: List[str]  # Strategies that succeeded
    what_failed: List[str]  # Strategies that failed
    strategy_changes: List[str]  # Adjustments for next session
    research_topics: List[str]  # Topics to research
    confidence_level: float  # 0-1, confidence in learnings


@dataclass
class ClaudeSessionResult:
    """Result of a Claude Agent session."""
    session_id: str
    session_type: SessionType
    account_type: str  # 'swing' or 'options'
    context_provided: Dict[str, Any]  # Input context
    claude_response: str  # Full response text
    tool_calls: List[ToolCall]  # All tools called during session
    decisions_made: List[Dict[str, Any]]  # Parsed decisions
    learnings: Optional[StrategyLearning] = None
    token_input: int = 0
    token_output: int = 0
    total_cost_usd: float = 0.0
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['session_type'] = self.session_type.value
        d['tool_calls'] = [tc.to_dict() for tc in self.tool_calls]
        if self.learnings:
            d['learnings'] = asdict(self.learnings)
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ClaudeSessionResult':
        """Create from dictionary."""
        data = data.copy()
        data['session_type'] = SessionType(data['session_type'])
        data['tool_calls'] = [ToolCall.from_dict(tc) for tc in data.get('tool_calls', [])]
        if data.get('learnings'):
            learning_data = data['learnings']
            data['learnings'] = StrategyLearning(
                what_worked=learning_data.get('what_worked', []),
                what_failed=learning_data.get('what_failed', []),
                strategy_changes=learning_data.get('strategy_changes', []),
                research_topics=learning_data.get('research_topics', []),
                confidence_level=learning_data.get('confidence_level', 0.5)
            )
        return ClaudeSessionResult(**data)


@dataclass
class TradeDecision:
    """Decision to execute a trade."""
    symbol: str
    action: str  # 'buy', 'sell'
    quantity: int
    reason: str
    confidence: float  # 0-1
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    strategy_tag: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeDecision':
        """Create from dictionary."""
        return TradeDecision(**data)


@dataclass
class AnalysisRecommendation:
    """Stock analysis recommendation."""
    symbol: str
    recommendation: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0-1
    fair_value: Optional[float] = None
    rationale: str = ""
    risk_factors: List[str] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AnalysisRecommendation':
        """Create from dictionary."""
        return AnalysisRecommendation(**data)
