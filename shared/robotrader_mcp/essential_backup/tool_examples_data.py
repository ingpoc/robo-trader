"""
Comprehensive tool examples data for Robo-Trader MCP Tools.

Real-world usage examples demonstrating how to effectively use each tool
for improved agent success rates following Anthropic's guidance.
"""

from .examples import ToolExample, ExampleComplexity, ExampleCategory, ExamplesRegistry


# High-frequency tool examples
SYSTEM_HEALTH_EXAMPLES = [
    ToolExample(
        name="Quick Health Check",
        description="Basic system health verification before making changes",
        complexity=ExampleComplexity.MINIMAL,
        category=ExampleCategory.MONITORING,
        input_parameters={
            "components": ["database", "queues", "api_endpoints"],
            "verbose": False,
            "include_recommendations": True
        },
        input_context={
            "role": "monitoring",
            "component": "system",
            "operation": "health_check"
        },
        expected_output={
            "status": "healthy",
            "components": {
                "database": {"status": "healthy", "response_time": 0.045},
                "queues": {"status": "healthy", "active_tasks": 3},
                "api_endpoints": {"status": "healthy", "uptime": "99.9%"}
            },
            "recommendations": ["System running optimally"]
        },
        output_highlights=[
            "Overall system status",
            "Individual component health",
            "Performance metrics",
            "Actionable recommendations"
        ],
        use_case="Quick verification before deploying changes or during routine monitoring",
        best_practices=[
            "Run health checks before making system changes",
            "Monitor component response times",
            "Act on recommendations promptly",
            "Include recommendations for proactive maintenance"
        ],
        common_pitfalls=[
            "Ignoring recommendations even when system is healthy",
            "Not checking all critical components",
            "Running health checks too frequently (can impact performance)"
        ],
        success_indicators=[
            "status returns 'healthy' or 'degraded'",
            "All critical components have non-null status",
            "Response times are under 1 second for all components"
        ],
        performance_notes="Typical response time: 200-500ms. Cache duration: 30 seconds."
    ),

    ToolExample(
        name="Comprehensive System Diagnosis",
        description="Detailed health analysis for troubleshooting complex issues",
        complexity=ExampleComplexity.ADVANCED,
        category=ExampleCategory.DEBUGGING,
        input_parameters={
            "components": ["database", "queues", "api_endpoints", "disk_space", "backup_status"],
            "verbose": True,
            "include_recommendations": True
        },
        input_context={
            "role": "debugging",
            "component": "system",
            "operation": "comprehensive_diagnosis"
        },
        expected_output={
            "status": "degraded",
            "components": {
                "database": {
                    "status": "healthy",
                    "response_time": 0.089,
                    "details": {"connections": 12, "queries_per_second": 45}
                },
                "queues": {
                    "status": "degraded",
                    "backlog_count": 15,
                    "details": {"ai_analysis": 8, "portfolio_sync": 7}
                },
                "api_endpoints": {
                    "status": "healthy",
                    "uptime": "99.5%",
                    "details": {"requests_per_minute": 120, "error_rate": 0.02}
                }
            },
            "recommendations": [
                "Clear AI analysis queue backlog",
                "Monitor portfolio sync performance",
                "Consider scaling queue workers"
            ]
        },
        output_highlights=[
            "Detailed component analysis",
            "Performance metrics and bottlenecks",
            "Specific degradation indicators",
            "Targeted remediation steps"
        ],
        use_case="Investigating performance issues or system degradation in production",
        best_practices=[
            "Include all components for comprehensive diagnosis",
            "Use verbose mode for detailed metrics",
            "Focus on the first 2-3 recommendations based on severity",
            "Document findings for trend analysis"
        ],
        common_pitfalls=[
            "Getting overwhelmed by verbose output data",
            "Missing critical issues in the noise",
            "Not prioritizing recommendations by impact"
        ],
        success_indicators=[
            "Identifies root cause of performance issues",
            "Provides actionable next steps",
            "Metrics show clear problem areas",
            "Recommendations are specific and implementable"
        ],
        performance_notes="Comprehensive analysis may take 1-3 seconds depending on system load."
    )
]


LOG_ANALYSIS_EXAMPLES = [
    ToolExample(
        name="Recent Error Detection",
        description="Find and analyze recent errors in application logs",
        complexity=ExampleComplexity.COMMON,
        category=ExampleCategory.DEBUGGING,
        input_parameters={
            "patterns": ["ERROR", "CRITICAL", "EXCEPTION"],
            "time_window": "2h",
            "group_by": "error_type",
            "max_examples": 5
        },
        input_context={
            "role": "debugging",
            "component": "logs",
            "operation": "error_analysis"
        },
        expected_output={
            "patterns_found": {
                "ERROR": 3,
                "CRITICAL": 1,
                "EXCEPTION": 2
            },
            "error_groups": {
                "DatabaseConnectionError": {
                    "count": 2,
                    "first_occurrence": "2025-01-15T10:15:30Z",
                    "last_occurrence": "2025-01-15T10:22:15Z",
                    "examples": [
                        "[2025-01-15 10:15:30] ERROR: DatabaseConnectionError: Connection timeout after 30s",
                        "[2025-01-15 10:22:15] ERROR: DatabaseConnectionError: Too many connections"
                    ]
                },
                "QueueProcessingException": {
                    "count": 2,
                    "first_occurrence": "2025-01-15T10:18:45Z",
                    "last_occurrence": "2025-01-15T10:25:30Z",
                    "examples": [
                        "[2025-01-15 10:18:45] ERROR: QueueProcessingException: Task timeout in AI_ANALYSIS",
                        "[2025-01-15 10:25:30] ERROR: QueueProcessingException: Dead letter queue exceeded"
                    ]
                }
            },
            "insights": [
                "Database connection issues suggest pool exhaustion",
                "Queue processing timeouts indicate resource bottlenecks",
                "Errors clustered around 10:15-10:25 suggest related incidents"
            ]
        },
        output_highlights=[
            "Error frequency and patterns",
            "Grouped similar errors for analysis",
            "Time-based error clustering",
            "Specific log examples for each error type"
        ],
        use_case="Investigating recent system issues or monitoring error trends",
        best_practices=[
            "Start with shorter time windows for recent issues",
            "Use specific error patterns to filter noise",
            "Focus on the most frequent error types first",
            "Check error timestamps for correlation with events"
        ],
        common_pitfalls=[
            "Using too broad time windows that hide recent issues",
            "Missing error patterns due to case sensitivity",
            "Overlooking timestamps and error correlations"
        ],
        success_indicators=[
            "Clear error groupings with counts",
            "Actionable insights about error causes",
            "Specific log lines for debugging",
            "Time-based patterns are evident"
        ],
        performance_notes="Search performance depends on log size. 1-2 second response typical for 2h windows."
    ),

    ToolExample(
        name="Performance Issue Investigation",
        description="Analyze logs for performance bottlenecks and slow operations",
        complexity=ExampleComplexity.ADVANCED,
        category=ExampleCategory.DEBUGGING,
        input_parameters={
            "patterns": ["SLOW", "TIMEOUT", "PERFORMANCE_WARNING", "LATENCY"],
            "time_window": "6h",
            "group_by": "time",
            "max_examples": 10
        },
        input_context={
            "role": "debugging",
            "component": "logs",
            "operation": "performance_analysis"
        },
        expected_output={
            "patterns_found": {
                "SLOW": 8,
                "TIMEOUT": 3,
                "PERFORMANCE_WARNING": 5
            },
            "time_groups": {
                "2025-01-15T08:00:00Z": {
                    "SLOW": 2,
                    "TIMEOUT": 1,
                    "examples": [
                        "[2025-01-15 08:15:23] SLOW: Portfolio analysis took 45.2s (threshold: 30s)",
                        "[2025-01-15 08:17:45] TIMEOUT: Database query timeout after 60s"
                    ]
                },
                "2025-01-15T10:30:00Z": {
                    "SLOW": 4,
                    "PERFORMANCE_WARNING": 3,
                    "examples": [
                        "[2025-01-15 10:32:12] SLOW: AI analysis processing 120s",
                        "[2025-01-15 10:35:45] PERFORMANCE_WARNING: Memory usage at 85%"
                    ]
                }
            },
            "insights": [
                "Performance issues concentrated during peak trading hours",
                "AI analysis tasks showing consistent slowdown",
                "Memory usage warnings correlate with slow operations"
            ]
        },
        output_highlights=[
            "Time-based performance clustering",
            "Performance threshold violations",
            "Resource usage correlations",
            "Specific slow operation identification"
        ],
        use_case="Diagnosing performance degradation or system slowness during peak usage",
        best_practices=[
            "Include performance-related keywords in patterns",
            "Use longer time windows to identify patterns",
            "Look for correlations with business hours or events",
            "Focus on consistent performance issues vs one-time spikes"
        ],
        common_pitfalls=[
            "Missing performance patterns due to insufficient time windows",
            "Not correlating performance with system load",
            "Overlooking gradual performance degradation"
        ],
        success_indicators=[
            "Clear time-based performance patterns identified",
            "Specific operations flagged as consistently slow",
            "Performance correlates with system events or load",
            "Actionable performance insights provided"
        ],
        performance_notes="6h analysis may take 2-5 seconds. Consider 24h for trend analysis."
    )
]


TOOL_SEARCH_EXAMPLES = [
    ToolExample(
        name="Database Tools Discovery",
        description="Find all database-related tools for portfolio management",
        complexity=ExampleComplexity.MINIMAL,
        category=ExampleCategory.DEVELOPMENT,
        input_parameters={
            "query": "database portfolio query",
            "category_filter": "database",
            "detail_level": "summary"
        },
        expected_output={
            "success": True,
            "query": "database portfolio query",
            "category_filter": "database",
            "detail_level": "summary",
            "matches": 2,
            "tools": [
                {
                    "name": "query_portfolio",
                    "category": "database",
                    "brief": "Query robo-trader portfolio database and return structured insights"
                },
                {
                    "name": "verify_configuration_integrity",
                    "category": "database",
                    "brief": "Verify robo-trader system configuration consistency and integrity"
                }
            ]
        },
        output_highlights=[
            "Relevant tools found for query",
            "Tool categories clearly identified",
            "Brief descriptions for quick understanding",
            "Match count for result validation"
        ],
        use_case="Finding tools for database operations and portfolio management tasks",
        best_practices=[
            "Use specific database-related keywords",
            "Apply category filters to narrow results",
            "Start with summary view before exploring details",
            "Include multiple relevant terms for better matching"
        ],
        common_pitfalls=[
            "Using too generic terms that return many results",
            "Not filtering by category when specific functionality needed",
            "Missing tools due to overly specific queries"
        ],
        success_indicators=[
            "2-5 relevant tools found",
            "Tools match the intended use case",
            "Brief descriptions provide clear understanding",
            "Category filtering works correctly"
        ],
        performance_notes="Typically 100-300ms response time with caching"
    )
]


# Create the comprehensive examples registry
TOOL_EXAMPLES_REGISTRY = ExamplesRegistry(
    tool_examples={
        "check_system_health": SYSTEM_HEALTH_EXAMPLES,
        "analyze_logs": LOG_ANALYSIS_EXAMPLES,
        "search_tools": TOOL_SEARCH_EXAMPLES,

        # Additional tools can have examples added here
        # "query_portfolio": PORTFOLIO_EXAMPLES,
        # "diagnose_database_locks": DATABASE_LOCK_EXAMPLES,
        # "queue_status": QUEUE_STATUS_EXAMPLES,
        # "execute_python": PYTHON_EXECUTION_EXAMPLES,
        # ... etc for all 22 tools
    }
)