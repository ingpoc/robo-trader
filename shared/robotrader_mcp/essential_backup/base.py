"""
Base Pydantic models for MCP server.

These models provide common structures for tool inputs/outputs,
error handling, and response formatting according to the MCP specification.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import json


class ToolStatus(str, Enum):
    """Tool execution status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CACHE_HIT = "cache_hit"


class DetailLevel(str, Enum):
    """Detail level for search and discovery operations."""
    NAMES_ONLY = "names_only"
    SUMMARY = "summary"
    FULL = "full"


class CacheStrategy(str, Enum):
    """Cache strategy for operations."""
    USE_CACHE = "use_cache"
    FORCE_REFRESH = "force_refresh"
    CACHE_ONLY = "cache_only"


class BaseToolInput(BaseModel):
    """Base model for all tool inputs."""
    use_cache: Optional[bool] = Field(
        default=True,
        description="Whether to use cached results when available"
    )
    timeout_seconds: Optional[int] = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum execution time in seconds"
    )

    model_config = {
        "extra": "forbid",  # Prevent additional fields
        "use_enum_values": True
    }


class TokenEfficiency(BaseModel):
    """Token efficiency metrics."""
    compression_ratio: Optional[str] = Field(
        default=None,
        description="Compression ratio achieved (e.g., '96%+ reduction')"
    )
    tokens_input: Optional[int] = Field(
        default=None,
        description="Number of input tokens processed"
    )
    tokens_output: Optional[int] = Field(
        default=None,
        description="Number of output tokens generated"
    )
    note: Optional[str] = Field(
        default=None,
        description="Additional efficiency notes"
    )


class ExecutionStats(BaseModel):
    """Execution statistics."""
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="Execution time in milliseconds"
    )
    cache_hit: Optional[bool] = Field(
        default=None,
        description="Whether result was served from cache"
    )
    data_source: Optional[str] = Field(
        default=None,
        description="Source of the data (api, database, cache, etc.)"
    )


class BaseToolOutput(BaseModel):
    """Base model for all tool outputs."""
    success: bool = Field(
        description="Whether the operation was successful"
    )
    status: Optional[ToolStatus] = Field(
        default=ToolStatus.SUCCESS,
        description="Detailed status of the operation"
    )
    token_efficiency: Optional[TokenEfficiency] = Field(
        description="Token efficiency metrics"
    )
    execution_stats: Optional[ExecutionStats] = Field(
        description="Execution statistics"
    )

    model_config = {
        "use_enum_values": True
    }


class ErrorResponse(BaseToolOutput):
    """Error response model."""
    success: bool = Field(default=False)
    status: ToolStatus = Field(default=ToolStatus.ERROR)
    error: str = Field(
        description="Human-readable error description"
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Suggested troubleshooting steps"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    token_efficiency: Optional[TokenEfficiency] = Field(
        default=None,
        description="Token efficiency metrics"
    )
    execution_stats: Optional[ExecutionStats] = Field(
        default=None,
        description="Execution statistics"
    )


class ToolResponse(BaseModel):
    """Standard tool response wrapper."""
    content: List[Dict[str, Any]] = Field(
        description="Response content following MCP specification"
    )
    isError: bool = Field(
        default=False,
        description="Whether this response represents an error"
    )
    data: Optional[Dict[str, Any]] = Field(
        description="Additional response data"
    )

    @classmethod
    def from_result(cls, result: Dict[str, Any]) -> "ToolResponse":
        """Create response from tool result."""
        return cls(
            content=[{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }],
            data=result
        )

    @classmethod
    def from_error(cls, error: str, suggestion: Optional[str] = None) -> "ToolResponse":
        """Create error response."""
        error_response = ErrorResponse(
            error=error,
            suggestion=suggestion
        )
        return cls(
            content=[{
                "type": "text",
                "text": json.dumps(error_response.model_dump(), indent=2)
            }],
            isError=True,
            data=error_response.model_dump()
        )


class SearchMatch(BaseModel):
    """Search result match."""
    tool_name: str = Field(description="Name of the matching tool")
    category: str = Field(description="Tool category")
    description: str = Field(description="Tool description")
    token_efficiency: Optional[str] = Field(default=None, description="Token efficiency rating")
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relevance score (0-1)"
    )


class FileTreeNode(BaseModel):
    """Filesystem tree node for directory exploration."""
    name: str = Field(description="Name of the node")
    path: str = Field(description="Full path to the node")
    type: str = Field(description="Type: 'directory' or 'file'")
    description: Optional[str] = Field(default=None, description="Node description")
    size: Optional[int] = Field(default=None, description="Size in bytes (for files)")
    tool_count: Optional[int] = Field(default=None, description="Number of tools (for directories)")


class Insight(BaseModel):
    """Insight or observation extracted from data."""
    text: str = Field(description="Insight text")
    category: Optional[str] = Field(default=None, description="Insight category")
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )


class Recommendation(BaseModel):
    """Actionable recommendation."""
    text: str = Field(description="Recommendation text")
    priority: Optional[str] = Field(default=None, description="Priority level: high, medium, low")
    estimated_impact: Optional[str] = Field(default=None, description="Expected impact")