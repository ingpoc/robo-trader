"""
Pydantic schemas for MCP Resources.

These models provide input validation and response structures for MCP Resources,
which enable direct data access patterns alongside tools.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from .base import BaseToolInput, BaseToolOutput


class ResourceReadInput(BaseModel):
    """Input for reading MCP Resources."""
    uri: str = Field(
        description="Resource URI to read (e.g., 'robo://system/health')"
    )
    use_cache: Optional[bool] = Field(
        default=True,
        description="Whether to use cached resource data"
    )
    max_age_seconds: Optional[int] = Field(
        default=60,
        ge=0,
        le=3600,
        description="Maximum age for cached data in seconds"
    )

    @validator('uri')
    def validate_uri(cls, v):
        """Validate URI format."""
        if not v.startswith(('robo://', 'file://')):
            raise ValueError("URI must start with 'robo://' or 'file://'")
        return v


class ResourceListInput(BaseModel):
    """Input for listing available Resources."""
    category_filter: Optional[str] = Field(
        description="Filter by resource category"
    )
    include_metadata: Optional[bool] = Field(
        default=True,
        description="Include resource metadata"
    )
    show_hidden: Optional[bool] = Field(
        default=False,
        description="Include hidden resources"
    )


class ResourceMetadata(BaseModel):
    """Metadata for MCP Resources."""
    uri: str = Field(description="Resource URI")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Resource description")
    category: str = Field(description="Resource category")
    mime_type: Optional[str] = Field(description="MIME type of resource content")
    cache_ttl: Optional[int] = Field(description="Cache TTL in seconds")
    last_modified: Optional[datetime] = Field(description="Last modification timestamp")
    size_bytes: Optional[int] = Field(description="Size in bytes")
    access_count: Optional[int] = Field(description="Number of times accessed")


class ResourceContent(BaseModel):
    """Content of an MCP Resource."""
    uri: str = Field(description="Resource URI")
    mime_type: str = Field(description="MIME type of content")
    text: Optional[str] = Field(description="Text content")
    blob: Optional[bytes] = Field(description="Binary content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ResourceListOutput(BaseModel):
    """Output for resource listing."""
    resources: List[ResourceMetadata] = Field(description="Available resources")
    total_count: int = Field(description="Total number of resources")
    categories: List[str] = Field(description="Available categories")


class ResourceReadOutput(BaseModel):
    """Output for resource reading."""
    contents: List[ResourceContent] = Field(description="Resource contents")
    success: bool = Field(description="Whether read was successful")
    cache_hit: Optional[bool] = Field(description="Whether result came from cache")
    error: Optional[str] = Field(description="Error message if read failed")


# Predefined Resource URIs for robo-trader

class ResourceURIs:
    """Centralized definition of all available Resource URIs."""

    # System Resources
    SYSTEM_HEALTH = "robo://system/health"
    SYSTEM_METRICS = "robo://system/metrics"
    SYSTEM_STATUS = "robo://system/status"

    # Queue Resources
    QUEUES_ALL = "robo://queues/all"
    QUEUES_STATUS = "robo://queues/status"
    QUEUE_PORTFOLIO_SYNC = "robo://queues/portfolio_sync"
    QUEUE_DATA_FETCHER = "robo://queues/data_fetcher"
    QUEUE_AI_ANALYSIS = "robo://queues/ai_analysis"

    # Database Resources
    DATABASE_STATUS = "robo://database/status"
    DATABASE_BACKUPS = "robo://database/backups"
    DATABASE_SCHEMA = "robo://database/schema"

    # Portfolio Resources
    PORTFOLIO_SUMMARY = "robo://portfolio/summary"
    PORTFOLIO_HOLDINGS = "robo://portfolio/holdings"
    PORTFOLIO_PERFORMANCE = "robo://portfolio/performance"
    PORTFOLIO_ANALYSIS = "robo://portfolio/analysis"

    # Analysis Resources
    ANALYSIS_RECENT = "robo://analysis/recent"
    ANALYSIS_ERRORS = "robo://analysis/errors"
    ANALYSIS_RECOMMENDATIONS = "robo://analysis/recommendations"

    # Log Resources
    LOGS_RECENT = "robo://logs/recent"
    LOGS_ERRORS = "robo://logs/errors"
    LOGS_PERFORMANCE = "robo://logs/performance"

    # Config Resources
    CONFIG_SYSTEM = "robo://config/system"
    CONFIG_FEATURES = "robo://config/features"
    CONFIG_ENVIRONMENT = "robo://config/environment"