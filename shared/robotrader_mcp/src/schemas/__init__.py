"""
Pydantic schemas for robo-trader MCP server input validation.

This package provides input validation models for all MCP tools, ensuring
type safety and automatic error handling for agent interactions.
"""

from .base import *
from .tools import *
from .resources import *

__all__ = [
    # Base models
    "BaseToolInput",
    "BaseToolOutput",
    "ToolResponse",
    "ErrorResponse",

    # Discovery tools
    "ListDirectoriesInput",
    "ReadFileInput",
    "SearchToolsInput",

    # Analysis tools
    "AnalyzeLogsInput",
    "CheckSystemHealthInput",
    "VerifyConfigurationIntegrityInput",
    "DiagnoseDatabaseLocksInput",
    "QueryPortfolioInput",
    "GetQueueStatusInput",
    "GetCoordinatorStatusInput",
    "RealTimePerformanceMonitorInput",
    "GetTaskExecutionMetricsInput",
    "DifferentialAnalysisInput",
    "SmartCacheAnalyzeInput",
    "ContextAwareSummarizeInput",

    # Resource schemas
    "ResourceReadInput",
    "ResourceListInput",
]