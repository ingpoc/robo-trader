"""
Shared Data Models
Common models used across all microservices
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Health check response"""

    status: str = "healthy"
    service: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Optional[Dict[str, str]] = None


class ServiceError(BaseModel):
    """Error response"""

    error: str
    code: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None
    details: Optional[Dict] = None


class Holding(BaseModel):
    """Portfolio holding"""

    symbol: str
    quantity: int
    avg_price: float
    current_value: float
    pnl: float
    pnl_percentage: float


class Order(BaseModel):
    """Order object"""

    order_id: str
    symbol: str
    quantity: int
    price: float
    status: str
    order_type: str  # BUY or SELL
    created_at: datetime
    updated_at: datetime


class RiskAssessment(BaseModel):
    """Risk assessment for a potential trade"""

    symbol: str
    quantity: int
    price: float
    exposure_percentage: float
    approved: bool
    reason: Optional[str] = None


class Recommendation(BaseModel):
    """AI recommendation"""

    recommendation_id: str
    symbol: str
    action: str  # BUY, SELL, HOLD
    reason: str
    target_price: Optional[float] = None
    status: str  # PENDING, APPROVED, REJECTED, EXECUTED
    created_at: datetime


class AnalysisResult(BaseModel):
    """Analytics analysis result"""

    symbol: str
    score: float
    reason: str
    created_at: datetime


class Event(BaseModel):
    """Event message"""

    id: str
    type: str
    data: Dict
    source: str
    timestamp: datetime
    correlation_id: Optional[str] = None
