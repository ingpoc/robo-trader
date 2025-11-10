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


# Execution Tools (Token Efficiency: 95-98% reduction)

class ExecutePythonInput(BaseToolInput):
    """Input for sandboxed Python code execution."""
    code: str = Field(
        description="Python code to execute (must assign result to 'result' variable)"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Variables to inject into execution context (must be JSON-serializable)"
    )
    timeout_seconds: Optional[int] = Field(
        default=30,
        ge=1,
        le=120,
        description="Execution timeout in seconds (1-120, default 30)"
    )
    isolation_level: Optional[str] = Field(
        default="production",
        description="Security isolation level: production (default) or hardened"
    )

    @validator('isolation_level')
    def validate_isolation_level(cls, v):
        """Validate isolation level."""
        if v not in ["production", "hardened", "development"]:
            raise ValueError("isolation_level must be 'production', 'hardened', or 'development'")
        return v

    @validator('code')
    def validate_code(cls, v):
        """Validate code is not empty."""
        if not v or not isinstance(v, str):
            raise ValueError("code must be non-empty string")
        return v


class ExecuteAnalysisInput(BaseToolInput):
    """Input for pre-configured data analysis."""
    analysis_type: str = Field(
        description="Type of analysis: filter, aggregate, transform, validate"
    )
    data: Dict[str, Any] = Field(
        description="Data to analyze (can be nested structures)"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Analysis-specific parameters"
    )

    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        """Validate analysis type."""
        if v not in ["filter", "aggregate", "transform", "validate"]:
            raise ValueError("analysis_type must be 'filter', 'aggregate', 'transform', or 'validate'")
        return v

    @validator('data')
    def validate_data(cls, v):
        """Validate data is not empty."""
        if not v:
            raise ValueError("data is required")
        return v


# Execution Tool Outputs

class ExecutionOutput(BaseToolOutput):
    """Base output for execution tools."""
    success: bool = Field(description="Whether execution succeeded")
    result: Optional[Any] = Field(default=None, description="Execution result")
    stdout: Optional[str] = Field(default="", description="Standard output")
    stderr: Optional[str] = Field(default="", description="Standard error")
    execution_time_ms: int = Field(description="Execution time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    token_efficiency: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token savings information"
    )


class PythonExecutionOutput(ExecutionOutput):
    """Output for Python code execution."""
    token_efficiency: Dict[str, Any] = Field(
        default_factory=lambda: {
            "compression_ratio": "98%+",
            "note": "Code executed directly instead of multi-turn reasoning",
            "estimated_traditional_tokens": "7600+",
            "estimated_sandbox_tokens": "200-300"
        },
        description="Token savings vs traditional reasoning"
    )


class AnalysisExecutionOutput(ExecutionOutput):
    """Output for pre-configured analysis."""
    analysis_type: str = Field(description="Type of analysis performed")
    data_count: Optional[int] = Field(default=None, description="Number of items processed")
    token_efficiency: Dict[str, Any] = Field(
        default_factory=lambda: {
            "compression_ratio": "99%+",
            "note": "Pre-configured analysis with minimal tokens",
            "estimated_traditional_tokens": "5000+",
            "estimated_sandbox_tokens": "100-200"
        },
        description="Token savings vs traditional reasoning"
    )


# Token Optimization Tools

class SmartFileReadInput(BaseToolInput):
    """Input for smart file reading with progressive context loading."""
    file_path: str = Field(
        description="Path to file relative to project root (e.g., 'src/services/analyzer.py')"
    )
    context: str = Field(
        default="summary",
        description="Context level: 'summary' (150 tokens), 'targeted' (800 tokens), or 'full' (complete file)"
    )
    search_term: Optional[str] = Field(
        default=None,
        description="Optional search term to focus on (for targeted mode)"
    )
    line_range: Optional[List[int]] = Field(
        default=None,
        description="Optional [start, end] line range for full mode"
    )

    @validator('context')
    def validate_context(cls, v):
        """Validate context level."""
        if v not in ["summary", "targeted", "full"]:
            raise ValueError("context must be 'summary', 'targeted', or 'full'")
        return v

    @validator('line_range')
    def validate_line_range(cls, v):
        """Validate line range format."""
        if v is not None:
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("line_range must be [start, end]")
            if v[0] < 1 or v[1] < v[0]:
                raise ValueError("Invalid line range: start must be >= 1, end must be >= start")
        return v


class FindRelatedFilesInput(BaseToolInput):
    """Input for finding files related to a reference file or concept."""
    reference: str = Field(
        description="File path or concept name (e.g., 'BroadcastCoordinator' or 'src/core/di.py')"
    )
    relation_type: str = Field(
        default="all",
        description="Type of relation: 'imports', 'similar', 'git_related', or 'all'"
    )
    max_results: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results per category"
    )
    include_tests: Optional[bool] = Field(
        default=False,
        description="Include test files in results"
    )

    @validator('relation_type')
    def validate_relation_type(cls, v):
        """Validate relation type."""
        if v not in ["imports", "similar", "git_related", "all"]:
            raise ValueError("relation_type must be 'imports', 'similar', 'git_related', or 'all'")
        return v


class SuggestFixInput(BaseToolInput):
    """Input for suggesting fixes based on error patterns."""
    error_message: str = Field(
        description="The error message or stack trace to analyze"
    )
    context_file: Optional[str] = Field(
        default=None,
        description="Optional file where error occurred for targeted suggestions"
    )
    include_examples: Optional[bool] = Field(
        default=True,
        description="Include code examples in suggestions"
    )

    @validator('error_message')
    def validate_error_message(cls, v):
        """Validate error message is not empty."""
        if not v or not v.strip():
            raise ValueError("error_message must not be empty")
        return v


class KnowledgeQueryInput(BaseToolInput):
    """Input for unified knowledge query (session cache + sandbox analysis)."""
    query_type: str = Field(
        description="Type of query: 'error', 'file', 'logs', 'workflow', 'insights'"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message to analyze (for query_type='error')"
    )
    context_file: Optional[str] = Field(
        default=None,
        description="File where error occurred (for query_type='error')"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="File to analyze (for query_type='file')"
    )
    analysis_type: Optional[str] = Field(
        default="structure",
        description="Type of file analysis: 'structure', 'database', 'imports'"
    )
    log_path: Optional[str] = Field(
        default="logs/robo-trader.log",
        description="Path to log file (for query_type='logs')"
    )
    time_window_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=168,
        description="Time window in hours for log analysis"
    )
    issue_type: Optional[str] = Field(
        default=None,
        description="Issue type for debugging workflow (for query_type='workflow')"
    )

    @validator('query_type')
    def validate_query_type(cls, v):
        """Validate query type."""
        valid_types = ["error", "file", "logs", "workflow", "insights"]
        if v not in valid_types:
            raise ValueError(f"query_type must be one of: {', '.join(valid_types)}")
        return v

    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        """Validate analysis type."""
        if v and v not in ["structure", "database", "imports"]:
            raise ValueError("analysis_type must be 'structure', 'database', or 'imports'")
        return v


# High-Impact Token Optimization Tools

class TokenMetricsCollectorInput(BaseToolInput):
    """Input for token metrics collection and efficiency analysis."""
    operation: str = Field(
        default="get_metrics",
        description="Operation: 'record', 'get_metrics', or 'reset'"
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Tool name for recording usage"
    )
    tokens_used: Optional[int] = Field(
        default=0,
        ge=0,
        description="Actual tokens used"
    )
    traditional_tokens_estimate: Optional[int] = Field(
        default=0,
        ge=0,
        description="Estimated tokens for traditional approach"
    )
    execution_time_ms: Optional[int] = Field(
        default=0,
        ge=0,
        description="Execution time in milliseconds"
    )
    success: Optional[bool] = Field(
        default=True,
        description="Whether operation succeeded"
    )
    time_window_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=720,
        description="Time window for metrics analysis (hours)"
    )
    group_by_tool: Optional[bool] = Field(
        default=True,
        description="Group metrics by tool name"
    )
    include_cost_analysis: Optional[bool] = Field(
        default=True,
        description="Include cost savings analysis"
    )

    @validator('operation')
    def validate_operation(cls, v):
        """Validate operation type."""
        if v not in ["record", "get_metrics", "reset"]:
            raise ValueError("operation must be 'record', 'get_metrics', or 'reset'")
        return v


class WorkflowOrchestratorInput(BaseToolInput):
    """Input for workflow orchestration and tool chaining."""
    operation: str = Field(
        default="execute",
        description="Operation: 'execute', 'save_template', 'load_template', 'list_templates'"
    )
    steps: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Workflow steps with tool, params, condition, context_mapping"
    )
    initial_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Initial context for workflow"
    )
    stop_on_error: Optional[bool] = Field(
        default=True,
        description="Stop workflow on first error"
    )
    template_name: Optional[str] = Field(
        default=None,
        description="Template name for save/load operations"
    )
    description: Optional[str] = Field(
        default=None,
        description="Template description for save operation"
    )

    @validator('operation')
    def validate_operation(cls, v):
        """Validate operation type."""
        valid_ops = ["execute", "save_template", "load_template", "list_templates"]
        if v not in valid_ops:
            raise ValueError(f"operation must be one of: {', '.join(valid_ops)}")
        return v


class EnhancedDifferentialAnalysisInput(BaseToolInput):
    """Input for enhanced differential analysis showing only changes."""
    component: str = Field(
        default="portfolio",
        description="Component to analyze: portfolio, queues, config, metrics, analysis"
    )
    since_timestamp: Optional[str] = Field(
        default=None,
        description="Analysis start point (ISO timestamp or '24h ago')"
    )
    include_delta_analysis: Optional[bool] = Field(
        default=True,
        description="Include detailed delta breakdown"
    )
    cache_key_override: Optional[str] = Field(
        default=None,
        description="Custom cache key for specific use cases"
    )

    @validator('component')
    def validate_component(cls, v):
        """Validate component type."""
        valid_components = ["portfolio", "queues", "config", "metrics", "analysis"]
        if v not in valid_components:
            raise ValueError(f"component must be one of: {', '.join(valid_components)}")
        return v


class SessionContextInjectionInput(BaseToolInput):
    """Input for session context injection and progress tracking."""
    operation: str = Field(
        default="inject_progress",
        description="Operation: inject_progress, get_context, clear_context, track_workflow, create_operation, complete_operation"
    )
    operation_id: Optional[str] = Field(
        default=None,
        description="Unique operation identifier"
    )
    status: Optional[str] = Field(
        default="running",
        description="Operation status: pending, running, completed, failed"
    )
    progress_pct: Optional[int] = Field(
        default=0,
        ge=0,
        le=100,
        description="Progress percentage (0-100)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable progress message"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )
    include_all: Optional[bool] = Field(
        default=False,
        description="Include all operations (not just active)"
    )
    clear_completed: Optional[bool] = Field(
        default=False,
        description="Clear only completed/failed operations"
    )
    workflow_id: Optional[str] = Field(
        default=None,
        description="Workflow identifier for multi-step tracking"
    )
    total_steps: Optional[int] = Field(
        default=1,
        ge=1,
        description="Total steps in workflow"
    )
    current_step: Optional[int] = Field(
        default=1,
        ge=1,
        description="Current step number"
    )
    step_name: Optional[str] = Field(
        default="Unknown",
        description="Name of current step"
    )
    step_status: Optional[str] = Field(
        default="running",
        description="Status of current step"
    )
    step_result: Optional[Any] = Field(
        default=None,
        description="Result from completed step"
    )
    operation_type: Optional[str] = Field(
        default="generic",
        description="Type of operation being tracked"
    )
    description: Optional[str] = Field(
        default="Operation in progress",
        description="Operation description"
    )
    estimated_duration_sec: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated duration in seconds"
    )
    success: Optional[bool] = Field(
        default=True,
        description="Whether operation succeeded"
    )
    result: Optional[Any] = Field(
        default=None,
        description="Operation result"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )

    @validator('operation')
    def validate_operation(cls, v):
        """Validate operation type."""
        valid_ops = ["inject_progress", "get_context", "clear_context", "track_workflow", "create_operation", "complete_operation"]
        if v not in valid_ops:
            raise ValueError(f"operation must be one of: {', '.join(valid_ops)}")
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate status."""
        if v and v not in ["pending", "running", "completed", "failed"]:
            raise ValueError("status must be 'pending', 'running', 'completed', or 'failed'")
        return v