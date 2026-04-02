"""
Research Ledger Models

Structured feature extraction models for the deterministic trading core.
LLMs extract features into these models; scoring is deterministic from features.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid


class ManagementFeatures(BaseModel):
    """Management and governance signals extracted from filings, news, and announcements."""
    guidance_raised: Optional[bool] = Field(None, description="Did management raise forward guidance?")
    guidance_lowered: Optional[bool] = Field(None, description="Did management lower forward guidance?")
    promoter_pledge_change_pct: Optional[float] = Field(None, description="Change in promoter pledge as % of holding")
    dilution_signal: Optional[bool] = Field(None, description="QIP, warrant conversion, OFS, or other dilution signal?")
    insider_buying_net_90d: Optional[float] = Field(None, description="Net insider buying in last 90 days (INR crores)")
    ceo_cfo_change_recent: Optional[bool] = Field(None, description="CEO or CFO change in last 6 months?")
    auditor_flags: Optional[bool] = Field(None, description="Any auditor qualifications or flags?")


class FinancialFeatures(BaseModel):
    """Financial metrics extracted from quarterly/annual results."""
    revenue_growth_yoy_pct: Optional[float] = Field(None, description="YoY revenue growth %")
    eps_growth_yoy_pct: Optional[float] = Field(None, description="YoY EPS growth %")
    operating_margin_trend: Optional[str] = Field(None, description="expanding, stable, or contracting")
    free_cash_flow_positive: Optional[bool] = Field(None, description="Is FCF positive in latest period?")
    debt_equity_ratio: Optional[float] = Field(None, description="Current debt-to-equity ratio")
    return_on_equity_pct: Optional[float] = Field(None, description="Return on equity %")
    revenue_surprise_pct: Optional[float] = Field(None, description="Revenue surprise vs consensus %")
    eps_surprise_pct: Optional[float] = Field(None, description="EPS surprise vs consensus %")


class CatalystFeatures(BaseModel):
    """Catalyst and event-driven signals."""
    results_date_in_window: Optional[bool] = Field(None, description="Earnings date within next 30 days?")
    order_book_win: Optional[bool] = Field(None, description="Recent order/book win or contract announcement?")
    regulatory_approval: Optional[bool] = Field(None, description="Recent regulatory approval or license?")
    sector_tailwind: Optional[bool] = Field(None, description="Favorable sector policy or macro tailwind?")
    story_crowded: Optional[bool] = Field(None, description="Is the narrative already well-known and priced in?")
    demerger_or_restructuring: Optional[bool] = Field(None, description="Active demerger/restructuring catalyst?")


class MarketFeatures(BaseModel):
    """Market and technical context signals."""
    relative_strength_vs_nifty_90d: Optional[float] = Field(None, description="90-day RS vs Nifty 50 (positive = outperforming)")
    sector_momentum: Optional[str] = Field(None, description="expanding, stable, or contracting")
    institutional_holding_change_pct: Optional[float] = Field(None, description="QoQ change in FII+DII holding %")
    delivery_pct_avg_20d: Optional[float] = Field(None, description="Average delivery % over 20 trading days")
    base_breakout_setup: Optional[bool] = Field(None, description="Price consolidating near breakout level?")
    volume_expansion: Optional[bool] = Field(None, description="Recent volume expansion vs 50-day average?")


class ResearchLedgerEntry(BaseModel):
    """
    A single point-in-time research snapshot for a symbol.

    This is the structured output of LLM feature extraction.
    The deterministic scorer converts this into a score — the LLM never decides buy/sell.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Structured feature groups
    management: ManagementFeatures = Field(default_factory=ManagementFeatures)
    financial: FinancialFeatures = Field(default_factory=FinancialFeatures)
    catalyst: CatalystFeatures = Field(default_factory=CatalystFeatures)
    market: MarketFeatures = Field(default_factory=MarketFeatures)

    # Metadata
    sources: List[str] = Field(default_factory=list, description="Data sources used for extraction")
    extraction_model: str = Field(default="gpt-5.4", description="Model used for extraction")
    extraction_duration_ms: Optional[int] = Field(None, description="Total extraction time in ms")

    # Scoring (filled by DeterministicScorer, not by LLM)
    score: Optional[float] = Field(None, description="Deterministic score from features")
    action: Optional[str] = Field(None, description="BUY, HOLD, or AVOID — determined by scorer, not LLM")
    feature_confidence: Optional[float] = Field(None, description="% of features successfully extracted (0-1)")

    def count_extracted_features(self) -> tuple[int, int]:
        """Count how many features were successfully extracted vs total possible."""
        extracted = 0
        total = 0
        for group in [self.management, self.financial, self.catalyst, self.market]:
            for field_name, field_value in group.model_dump().items():
                total += 1
                if field_value is not None:
                    extracted += 1
        return extracted, total

    def to_flat_features(self) -> Dict[str, Any]:
        """Flatten all features into a single dict for storage/analysis."""
        flat = {}
        for group_name, group in [
            ("mgmt", self.management),
            ("fin", self.financial),
            ("cat", self.catalyst),
            ("mkt", self.market),
        ]:
            for field_name, field_value in group.model_dump().items():
                flat[f"{group_name}_{field_name}"] = field_value
        return flat

    def to_store_dict(self) -> Dict[str, Any]:
        """Convert to dict suitable for database storage."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "features_json": self.model_dump_json(),
            "score": self.score,
            "action": self.action,
            "feature_confidence": self.feature_confidence,
            "sources": self.sources,
            "extraction_model": self.extraction_model,
        }
