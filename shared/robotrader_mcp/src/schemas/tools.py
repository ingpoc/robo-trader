"""
Pydantic schemas for all analysis tools.

These models provide input validation and response structures for the 12 analysis
tools, ensuring type safety and comprehensive documentation for agents.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
from .base import BaseToolInput, BaseToolOutput, Insight, Recommendation


# Discovery Tools

class ListDirectoriesInput(BaseToolInput):
    """Input for filesystem navigation directory listing."""
    path: str = Field(
        default="/",
        description="Path to explore (e.g., '/', '/system', '/logs')"
    )
    include_hidden: Optional[bool] = Field(
        default=False,
        description="Include hidden directories and files"
    )

    @validator('path')
    def validate_path(cls, v):
        """Validate path format."""
        if not v.startswith('/'):
            raise ValueError("Path must start with '/'")
        # Prevent path traversal attempts
        if '..' in v:
            raise ValueError("Path traversal not allowed")
        return v


class ReadFileInput(BaseToolInput):
    """Input for reading tool definition files."""
    path: str = Field(
        description="Full path to file to read (e.g., '/system/queue_status')"
    )
    max_lines: Optional[int] = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of lines to read"
    )

    @validator('path')
    def validate_path(cls, v):
        """Validate path format."""
        if not v.startswith('/'):
            raise ValueError("Path must start with '/'")
        if '..' in v:
            raise ValueError("Path traversal not allowed")
        if not v.endswith(('.ts', '.py', '.md')):
            raise ValueError("Only .ts, .py, and .md files can be read")
        return v


class SearchToolsInput(BaseToolInput):
    """Input for searching tools by keyword."""
    query: str = Field(
        description="Search query (tool name, keyword, or description fragment)"
    )
    detail_level: Optional[str] = Field(
        default="summary",
        description="Detail level: names_only, summary, or full"
    )
    category_filter: Optional[str] = Field(
        description="Filter by specific category"
    )

    @validator('detail_level')
    def validate_detail_level(cls, v):
        """Validate detail level."""
        if v not in ["names_only", "summary", "full"]:
            raise ValueError("detail_level must be 'names_only', 'summary', or 'full'")
        return v


# Analysis Tools

class AnalyzeLogsInput(BaseToolInput):
    """Input for log analysis tool."""
    patterns: List[str] = Field(
        description="Error patterns to search for (e.g., ['ERROR', 'TIMEOUT', 'DATABASE'])"
    )
    time_window: Optional[str] = Field(
        default="1h",
        description="Time window to analyze (e.g., '1h', '24h', '7d')"
    )
    max_examples: Optional[int] = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum examples per pattern"
    )
    group_by: Optional[str] = Field(
        default="error_type",
        description="How to group results: error_type, time, severity"
    )

    @validator('time_window')
    def validate_time_window(cls, v):
        """Validate time window format."""
        if not v.endswith(('h', 'd', 'm')):
            raise ValueError("Time window must end with 'h', 'd', or 'm'")
        return v


class CheckSystemHealthInput(BaseToolInput):
    """Input for system health checking."""
    components: Optional[List[str]] = Field(
        default=["database", "queues", "api_endpoints", "disk_space", "backup_status"],
        description="Components to check (default: all)"
    )
    verbose: Optional[bool] = Field(
        default=False,
        description="Include detailed status information"
    )
    include_recommendations: Optional[bool] = Field(
        default=True,
        description="Include actionable recommendations"
    )


class VerifyConfigurationIntegrityInput(BaseToolInput):
    """Input for configuration verification."""
    checks: Optional[List[str]] = Field(
        default=["database_paths", "api_endpoints", "queue_settings", "security_settings"],
        description="Configuration checks to perform"
    )
    include_suggestions: Optional[bool] = Field(
        default=True,
        description="Include improvement suggestions"
    )
    strict_mode: Optional[bool] = Field(
        default=False,
        description="Treat warnings as errors in strict mode"
    )


class DiagnoseDatabaseLocksInput(BaseToolInput):
    """Input for database lock diagnosis."""
    time_window: Optional[str] = Field(
        default="24h",
        description="Time window for lock analysis"
    )
    include_code_references: Optional[bool] = Field(
        default=True,
        description="Include source code references in diagnosis"
    )
    suggest_fixes: Optional[bool] = Field(
        default=True,
        description="Suggest specific fixes for identified issues"
    )

    @validator('time_window')
    def validate_time_window(cls, v):
        """Validate time window format."""
        if not v.endswith(('h', 'd')):
            raise ValueError("Time window must end with 'h' or 'd'")
        return v


class QueryPortfolioInput(BaseToolInput):
    """Input for portfolio database queries."""
    filters: Optional[List[str]] = Field(
        default=[],
        description="Filters to apply (e.g., ['stale_analysis', 'error_conditions'])"
    )
    limit: Optional[int] = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return"
    )
    aggregation_only: Optional[bool] = Field(
        default=True,
        description="Return only aggregated insights vs individual records"
    )
    include_recommendations: Optional[bool] = Field(
        default=True,
        description="Include portfolio recommendations"
    )


class GetQueueStatusInput(BaseToolInput):
    """Input for queue status monitoring."""
    include_details: Optional[bool] = Field(
        default=False,
        description="Include detailed queue information"
    )
    queue_filter: Optional[str] = Field(
        description="Filter by specific queue name"
    )
    include_backlog_analysis: Optional[bool] = Field(
        default=True,
        description="Include backlog analysis and recommendations"
    )


class GetCoordinatorStatusInput(BaseToolInput):
    """Input for coordinator status checking."""
    check_critical_only: Optional[bool] = Field(
        default=False,
        description="Check only critical coordinators"
    )
    include_last_check_time: Optional[bool] = Field(
        default=True,
        description="Include last check timestamps"
    )
    include_error_details: Optional[bool] = Field(
        default=True,
        description="Include detailed error information"
    )


class RealTimePerformanceMonitorInput(BaseToolInput):
    """Input for real-time performance monitoring."""
    metrics: Optional[List[str]] = Field(
        default=["cpu", "memory", "disk_io", "network"],
        description="Metrics to monitor"
    )
    duration_seconds: Optional[int] = Field(
        default=30,
        ge=5,
        le=300,
        description="Monitoring duration in seconds"
    )
    sample_interval: Optional[int] = Field(
        default=1,
        ge=1,
        le=10,
        description="Sample interval in seconds"
    )
    include_alerts: Optional[bool] = Field(
        default=True,
        description="Include performance alerts"
    )


class GetTaskExecutionMetricsInput(BaseToolInput):
    """Input for task execution metrics."""
    time_window_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=168,
        description="Time window for analysis in hours"
    )
    include_trends: Optional[bool] = Field(
        default=True,
        description="Include error trend analysis"
    )
    task_type_filter: Optional[str] = Field(
        description="Filter by specific task type"
    )
    include_performance_stats: Optional[bool] = Field(
        default=True,
        description="Include performance statistics"
    )


class DifferentialAnalysisInput(BaseToolInput):
    """Input for differential analysis."""
    component: Optional[str] = Field(
        default="portfolio",
        description="Component to analyze"
    )
    since_timestamp: Optional[str] = Field(
        description="Analysis start point (ISO timestamp or '24h ago')"
    )
    cache_key_override: Optional[str] = Field(
        description="Custom cache key"
    )
    include_delta_analysis: Optional[bool] = Field(
        default=True,
        description="Include delta analysis between snapshots"
    )


class SmartCacheAnalyzeInput(BaseToolInput):
    """Input for smart cache analysis."""
    query_type: Optional[str] = Field(
        default="portfolio_health",
        description="Type of cache query to analyze"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default={},
        description="Query parameters"
    )
    force_refresh: Optional[bool] = Field(
        default=False,
        description="Force cache refresh"
    )
    include_performance_metrics: Optional[bool] = Field(
        default=True,
        description="Include cache performance metrics"
    )


class ContextAwareSummarizeInput(BaseToolInput):
    """Input for context-aware data summarization."""
    data_source: Optional[str] = Field(
        default="all",
        description="Data source to summarize"
    )
    user_context: Optional[str] = Field(
        description="User intent or context for summarization"
    )
    max_tokens: Optional[int] = Field(
        default=500,
        ge=100,
        le=2000,
        description="Maximum tokens in summary"
    )
    focus_areas: Optional[List[str]] = Field(
        description="Specific areas to focus on in summary"
    )
    custom_filters: Optional[List[str]] = Field(
        description="Custom filters for data selection"
    )


# Output Models

class AnalysisOutput(BaseToolOutput):
    """Base output model for analysis tools."""
    insights: List[Insight] = Field(
        default=[],
        description="Extracted insights from the analysis"
    )
    recommendations: List[Recommendation] = Field(
        default=[],
        description="Actionable recommendations"
    )
    summary: Optional[str] = Field(
        description="Executive summary of findings"
    )


class SystemHealthOutput(AnalysisOutput):
    """Output for system health checks."""
    overall_status: str = Field(description="Overall system health status")
    component_status: Dict[str, Any] = Field(description="Individual component status")
    critical_issues: List[str] = Field(default=[], description="Critical issues found")


class QueueStatusOutput(AnalysisOutput):
    """Output for queue status monitoring."""
    overall_status: str = Field(description="Overall queue status")
    queue_summary: List[Dict[str, Any]] = Field(description="Summary of each queue")
    system_stats: Dict[str, Any] = Field(description="System-wide statistics")
    active_queues: int = Field(description="Number of active queues")


class PortfolioQueryOutput(AnalysisOutput):
    """Output for portfolio database queries."""
    query_results: List[Dict[str, Any]] = Field(description="Query results")
    aggregation_stats: Dict[str, Any] = Field(description="Aggregated statistics")
    data_quality_score: Optional[float] = Field(description="Data quality score")


class TaskMetricsOutput(AnalysisOutput):
    """Output for task execution metrics."""
    summary: Dict[str, Any] = Field(description="24-hour summary statistics")
    top_task_types: List[Dict[str, Any]] = Field(description="Most frequent task types")
    error_trends: List[Dict[str, Any]] = Field(description="Error trends over time")
    performance_stats: Dict[str, Any] = Field(description="Performance metrics")