#!/usr/bin/env python3
"""Token Metrics Collector - Real-time token usage tracking and efficiency measurement.

This tool provides:
- Real-time token usage metrics
- Token efficiency measurements (actual vs traditional approaches)
- Cost savings calculations
- Performance benchmarks for MCP tools

Token efficiency is the core value proposition - this tool quantifies it.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Metrics storage
METRICS_DIR = Path(os.path.expanduser("~/.robo_trader_mcp_cache/metrics"))
METRICS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_FILE = METRICS_DIR / "token_metrics.json"

# Token cost estimates (per 1M tokens)
COST_PER_MILLION_INPUT = 3.00  # $3 per 1M input tokens (Sonnet)
COST_PER_MILLION_OUTPUT = 15.00  # $15 per 1M output tokens (Sonnet)


def record_tool_usage(
    tool_name: str,
    tokens_used: int,
    traditional_tokens_estimate: int,
    execution_time_ms: int,
    success: bool = True
) -> Dict[str, Any]:
    """Record a tool usage event with token metrics.

    Args:
        tool_name: Name of the tool that was executed
        tokens_used: Actual tokens used by the tool
        traditional_tokens_estimate: Estimated tokens for traditional approach
        execution_time_ms: Execution time in milliseconds
        success: Whether the operation was successful
    """

    metrics = _load_metrics()

    # Create usage record
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "tokens_used": tokens_used,
        "traditional_tokens_estimate": traditional_tokens_estimate,
        "token_savings": traditional_tokens_estimate - tokens_used,
        "efficiency_pct": ((traditional_tokens_estimate - tokens_used) / traditional_tokens_estimate * 100) if traditional_tokens_estimate > 0 else 0,
        "execution_time_ms": execution_time_ms,
        "success": success
    }

    # Add to history
    if "usage_history" not in metrics:
        metrics["usage_history"] = []

    metrics["usage_history"].append(record)

    # Keep only last 1000 entries
    metrics["usage_history"] = metrics["usage_history"][-1000:]

    # Update aggregates
    _update_aggregates(metrics)

    # Save metrics
    _save_metrics(metrics)

    return {
        "success": True,
        "record_saved": True,
        "token_savings": record["token_savings"],
        "efficiency_pct": round(record["efficiency_pct"], 1)
    }


def get_token_metrics(
    time_window_hours: int = 24,
    group_by_tool: bool = True,
    include_cost_analysis: bool = True
) -> Dict[str, Any]:
    """Get token usage metrics and efficiency analysis.

    Args:
        time_window_hours: Time window for analysis (default: 24 hours)
        group_by_tool: Group metrics by tool name (default: True)
        include_cost_analysis: Include cost savings analysis (default: True)
    """

    metrics = _load_metrics()
    usage_history = metrics.get("usage_history", [])

    # Filter by time window
    cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
    recent_usage = [
        u for u in usage_history
        if datetime.fromisoformat(u["timestamp"]) > cutoff
    ]

    if not recent_usage:
        return {
            "success": True,
            "summary": {
                "total_tool_calls": 0,
                "total_tokens_used": 0,
                "total_tokens_saved": 0,
                "average_efficiency_pct": 0,
                "total_cost_savings_usd": 0
            },
            "insights": ["No tool usage in the specified time window"],
            "recommendations": ["Start using MCP tools to track token efficiency"]
        }

    # Calculate overall metrics
    total_tokens_used = sum(u["tokens_used"] for u in recent_usage)
    total_traditional = sum(u["traditional_tokens_estimate"] for u in recent_usage)
    total_savings = total_traditional - total_tokens_used
    avg_efficiency = (total_savings / total_traditional * 100) if total_traditional > 0 else 0

    summary = {
        "total_tool_calls": len(recent_usage),
        "total_tokens_used": total_tokens_used,
        "total_traditional_tokens": total_traditional,
        "total_tokens_saved": total_savings,
        "average_efficiency_pct": round(avg_efficiency, 1),
        "success_rate_pct": round(sum(1 for u in recent_usage if u["success"]) / len(recent_usage) * 100, 1)
    }

    # Group by tool if requested
    by_tool = None
    if group_by_tool:
        by_tool = defaultdict(lambda: {
            "calls": 0,
            "tokens_used": 0,
            "tokens_saved": 0,
            "avg_execution_ms": 0
        })

        for usage in recent_usage:
            tool = usage["tool_name"]
            by_tool[tool]["calls"] += 1
            by_tool[tool]["tokens_used"] += usage["tokens_used"]
            by_tool[tool]["tokens_saved"] += usage["token_savings"]
            by_tool[tool]["avg_execution_ms"] += usage["execution_time_ms"]

        # Calculate averages
        for tool, stats in by_tool.items():
            stats["avg_execution_ms"] = round(stats["avg_execution_ms"] / stats["calls"])
            stats["efficiency_pct"] = round(
                (stats["tokens_saved"] / (stats["tokens_used"] + stats["tokens_saved"]) * 100)
                if (stats["tokens_used"] + stats["tokens_saved"]) > 0 else 0,
                1
            )

    # Cost analysis
    cost_analysis = None
    if include_cost_analysis:
        # Simplified: assume 50/50 input/output split
        actual_cost = (total_tokens_used / 2 * COST_PER_MILLION_INPUT / 1_000_000 +
                      total_tokens_used / 2 * COST_PER_MILLION_OUTPUT / 1_000_000)
        traditional_cost = (total_traditional / 2 * COST_PER_MILLION_INPUT / 1_000_000 +
                           total_traditional / 2 * COST_PER_MILLION_OUTPUT / 1_000_000)
        cost_savings = traditional_cost - actual_cost

        cost_analysis = {
            "actual_cost_usd": round(actual_cost, 4),
            "traditional_cost_usd": round(traditional_cost, 4),
            "cost_savings_usd": round(cost_savings, 4),
            "annual_savings_projection_usd": round(cost_savings * 365 / (time_window_hours / 24), 2)
        }

        summary["total_cost_savings_usd"] = round(cost_savings, 4)

    # Generate insights
    insights = []
    recommendations = []

    if avg_efficiency > 95:
        insights.append(f"Exceptional token efficiency: {avg_efficiency:.1f}% reduction")
    elif avg_efficiency > 85:
        insights.append(f"Excellent token efficiency: {avg_efficiency:.1f}% reduction")
    elif avg_efficiency > 70:
        insights.append(f"Good token efficiency: {avg_efficiency:.1f}% reduction")
    else:
        insights.append(f"Moderate token efficiency: {avg_efficiency:.1f}% reduction")
        recommendations.append("Consider using more token-efficient MCP tools")

    if cost_analysis and cost_analysis["cost_savings_usd"] > 1:
        insights.append(f"Cost savings: ${cost_analysis['cost_savings_usd']} in {time_window_hours}h")
        insights.append(f"Annual projection: ${cost_analysis['annual_savings_projection_usd']}")

    if len(recent_usage) > 100:
        insights.append(f"High tool usage: {len(recent_usage)} calls in {time_window_hours}h")
    elif len(recent_usage) < 10:
        recommendations.append("Increase MCP tool adoption to maximize token savings")

    if not recommendations:
        recommendations.append("Continue leveraging MCP tools for token efficiency")

    result = {
        "success": True,
        "summary": summary,
        "insights": insights,
        "recommendations": recommendations,
        "token_efficiency": {
            "note": "Real-time token usage tracking with 0 token overhead",
            "tracking_period": f"{time_window_hours}h"
        }
    }

    if by_tool:
        result["by_tool"] = dict(by_tool)

    if cost_analysis:
        result["cost_analysis"] = cost_analysis

    return result


def reset_metrics() -> Dict[str, Any]:
    """Reset all token metrics (use with caution)."""

    metrics = {
        "usage_history": [],
        "aggregates": {
            "all_time": {
                "total_calls": 0,
                "total_tokens_saved": 0,
                "total_cost_saved_usd": 0
            }
        },
        "reset_at": datetime.now(timezone.utc).isoformat()
    }

    _save_metrics(metrics)

    return {
        "success": True,
        "message": "Token metrics reset successfully",
        "reset_at": metrics["reset_at"]
    }


def _load_metrics() -> Dict[str, Any]:
    """Load metrics from disk."""

    if not METRICS_FILE.exists():
        return {
            "usage_history": [],
            "aggregates": {
                "all_time": {
                    "total_calls": 0,
                    "total_tokens_saved": 0,
                    "total_cost_saved_usd": 0
                }
            }
        }

    try:
        with open(METRICS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"usage_history": [], "aggregates": {}}


def _save_metrics(metrics: Dict[str, Any]) -> None:
    """Save metrics to disk."""

    try:
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass  # Metrics collection shouldn't break tool execution


def _update_aggregates(metrics: Dict[str, Any]) -> None:
    """Update aggregate statistics."""

    if "aggregates" not in metrics:
        metrics["aggregates"] = {}

    if "all_time" not in metrics["aggregates"]:
        metrics["aggregates"]["all_time"] = {
            "total_calls": 0,
            "total_tokens_saved": 0,
            "total_cost_saved_usd": 0
        }

    usage = metrics.get("usage_history", [])
    total_savings = sum(u["token_savings"] for u in usage)
    total_traditional = sum(u["traditional_tokens_estimate"] for u in usage)
    total_used = sum(u["tokens_used"] for u in usage)

    # Cost calculation
    actual_cost = (total_used / 2 * COST_PER_MILLION_INPUT / 1_000_000 +
                  total_used / 2 * COST_PER_MILLION_OUTPUT / 1_000_000)
    traditional_cost = (total_traditional / 2 * COST_PER_MILLION_INPUT / 1_000_000 +
                       total_traditional / 2 * COST_PER_MILLION_OUTPUT / 1_000_000)

    metrics["aggregates"]["all_time"] = {
        "total_calls": len(usage),
        "total_tokens_saved": total_savings,
        "total_cost_saved_usd": round(traditional_cost - actual_cost, 4)
    }


def token_metrics_collector(
    operation: str = "get_metrics",
    tool_name: Optional[str] = None,
    tokens_used: int = 0,
    traditional_tokens_estimate: int = 0,
    execution_time_ms: int = 0,
    success: bool = True,
    time_window_hours: int = 24,
    group_by_tool: bool = True,
    include_cost_analysis: bool = True,
    use_cache: bool = True,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """Unified MCP tool interface for token metrics collection."""

    if operation == "record":
        return record_tool_usage(
            tool_name=tool_name or "unknown",
            tokens_used=tokens_used,
            traditional_tokens_estimate=traditional_tokens_estimate,
            execution_time_ms=execution_time_ms,
            success=success
        )
    elif operation == "reset":
        return reset_metrics()
    else:
        return get_token_metrics(
            time_window_hours=time_window_hours,
            group_by_tool=group_by_tool,
            include_cost_analysis=include_cost_analysis
        )


def main():
    """Main entry point for MCP tool execution."""
    try:
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            input_data = {}

        result = token_metrics_collector(**input_data)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Token metrics tool failed: {str(e)}",
            "suggestion": "Check input parameters and try again"
        }))


if __name__ == "__main__":
    main()
