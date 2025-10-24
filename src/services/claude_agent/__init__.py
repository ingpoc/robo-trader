"""
Claude Agent Services Package

Provides comprehensive AI trading transparency and visibility services.
"""

from .research_tracker import ResearchTracker, ResearchSession, DataSourceUsage
from .analysis_logger import AnalysisLogger, AnalysisStep, TradeDecisionLog, StrategyEvaluation
from .execution_monitor import ExecutionMonitor, ExecutionStep, TradeExecutionLog, RiskCheckResult
from .daily_strategy_evaluator import DailyStrategyEvaluator, StrategyPerformanceMetrics, StrategyRefinement, DailyStrategyReport
from .activity_summarizer import ActivitySummarizer, DailyActivitySummary, WeeklyActivitySummary
from .trade_decision_logger import TradeDecisionLogger

__all__ = [
    # Research tracking
    "ResearchTracker",
    "ResearchSession",
    "DataSourceUsage",

    # Analysis logging
    "AnalysisLogger",
    "AnalysisStep",
    "TradeDecisionLog",
    "StrategyEvaluation",

    # Execution monitoring
    "ExecutionMonitor",
    "ExecutionStep",
    "TradeExecutionLog",
    "RiskCheckResult",

    # Strategy evaluation
    "DailyStrategyEvaluator",
    "StrategyPerformanceMetrics",
    "StrategyRefinement",
    "DailyStrategyReport",

    # Activity summarization
    "ActivitySummarizer",
    "DailyActivitySummary",
    "WeeklyActivitySummary",

    # Trade decision logging
    "TradeDecisionLogger",
]