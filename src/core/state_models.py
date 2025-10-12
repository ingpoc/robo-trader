"""
State data models for Robo Trader

Contains dataclasses and models used across the system.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


@dataclass
class PortfolioState:
    """Current portfolio snapshot."""
    as_of: str
    cash: Dict[str, float]
    holdings: List[Dict[str, Any]]
    exposure_total: float
    risk_aggregates: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict) -> "PortfolioState":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Signal:
    """Technical analysis signal."""
    symbol: str
    timeframe: str
    indicators: Dict[str, float]
    entry: Optional[Dict[str, Any]] = None
    stop: Optional[Dict[str, Any]] = None
    targets: Optional[List[Dict[str, Any]]] = None
    confidence: float = 0.0
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> "Signal":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskDecision:
    """Risk assessment result."""
    symbol: str
    decision: str  # "approve", "deny", "defer"
    size_qty: Optional[int] = None
    max_risk_inr: Optional[float] = None
    stop: Optional[Dict[str, Any]] = None
    targets: Optional[List[Dict[str, Any]]] = None
    constraints: List[str] = None
    reasons: List[str] = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []
        if self.reasons is None:
            self.reasons = []

    @classmethod
    def from_dict(cls, data: Dict) -> "RiskDecision":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OrderCommand:
    """Order execution command."""
    type: str  # "place", "modify", "cancel"
    side: str  # "BUY", "SELL"
    symbol: str
    qty: Optional[int] = None
    order_type: str = "MARKET"
    product: str = "CNC"
    variety: str = "REGULAR"
    tif: str = "DAY"
    client_tag: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "OrderCommand":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExecutionReport:
    """Order execution result."""
    broker_order_id: str
    status: str  # "COMPLETE", "PENDING", "REJECTED", etc.
    fills: List[Dict[str, Any]] = None
    avg_price: Optional[float] = None
    slippage_bps: Optional[float] = None
    received_at: str = ""

    def __post_init__(self):
        if self.fills is None:
            self.fills = []
        if not self.received_at:
            self.received_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "ExecutionReport":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Intent:
    """Trading intent record."""
    id: str
    symbol: str
    created_at: str
    signal: Optional[Signal] = None
    risk_decision: Optional[RiskDecision] = None
    order_commands: List[OrderCommand] = None
    execution_reports: List[ExecutionReport] = None
    status: str = "pending"  # "pending", "approved", "executed", "rejected"
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    source: str = "system"

    def __post_init__(self):
        if self.order_commands is None:
            self.order_commands = []
        if self.execution_reports is None:
            self.execution_reports = []
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "Intent":
        # Handle nested objects
        if 'signal' in data and data['signal']:
            data['signal'] = Signal.from_dict(data['signal'])
        if 'risk_decision' in data and data['risk_decision']:
            data['risk_decision'] = RiskDecision.from_dict(data['risk_decision'])
        if 'order_commands' in data:
            data['order_commands'] = [OrderCommand.from_dict(cmd) for cmd in data['order_commands']]
        if 'execution_reports' in data:
            data['execution_reports'] = [ExecutionReport.from_dict(rep) for rep in data['execution_reports']]
        return cls(**data)

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.signal:
            data['signal'] = self.signal.to_dict()
        if self.risk_decision:
            data['risk_decision'] = self.risk_decision.to_dict()
        data['order_commands'] = [cmd.to_dict() for cmd in self.order_commands]
        data['execution_reports'] = [rep.to_dict() for rep in self.execution_reports]
        return data


@dataclass
class FundamentalAnalysis:
    """Fundamental analysis results for a stock."""
    symbol: str
    analysis_date: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    profit_margins: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[float] = None
    sector_pe: Optional[float] = None
    industry_rank: Optional[int] = None
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None
    analysis_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "FundamentalAnalysis":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Recommendation:
    """Trading recommendation record."""
    symbol: str
    recommendation_type: str  # BUY/SELL/HOLD
    confidence_score: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    quantity: Optional[int] = None
    reasoning: Optional[str] = None
    analysis_type: Optional[str] = None
    time_horizon: Optional[str] = None
    risk_level: Optional[str] = None
    potential_impact: Optional[str] = None
    alternative_suggestions: Optional[List[str]] = None
    executed_at: Optional[str] = None
    outcome: Optional[str] = None
    actual_return: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "Recommendation":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MarketConditions:
    """Market conditions and macro factors."""
    date: str
    vix_index: Optional[float] = None
    nifty_50_level: Optional[float] = None
    market_sentiment: Optional[str] = None
    interest_rates: Optional[float] = None
    inflation_rate: Optional[float] = None
    gdp_growth: Optional[float] = None
    sector_performance: Optional[Dict[str, Any]] = None
    global_events: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "MarketConditions":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AnalysisPerformance:
    """Performance tracking for analysis recommendations."""
    symbol: str
    prediction_date: str
    recommendation_id: Optional[int] = None
    execution_date: Optional[str] = None
    predicted_direction: Optional[str] = None
    actual_direction: Optional[str] = None
    predicted_return: Optional[float] = None
    actual_return: Optional[float] = None
    accuracy_score: Optional[float] = None
    model_version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "AnalysisPerformance":
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)