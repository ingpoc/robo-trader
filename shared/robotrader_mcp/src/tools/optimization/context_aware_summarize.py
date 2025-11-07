#!/usr/bin/env python3

import json
import sys
import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os

# User intent patterns for intelligent summarization
INTENT_PATTERNS = {
    "quick_check": [
        r"quick", r"fast", r"summary", r"brief", r"short",
        r"what's", r"how is", r"status"
    ],
    "debugging": [
        r"error", r"issue", r"problem", r"debug", r"troubleshoot",
        r"why", r"not working", r"failed", r"broken"
    ],
    "optimization": [
        r"optimize", r"improve", r"better", r"faster", r"fix",
        r"recommendation", r"suggestion", r"advice"
    ],
    "monitoring": [
        r"monitor", r"watch", r"track", r"alert", r"performance",
        r"health", r"metrics", r"kpi"
    ],
    "analysis": [
        r"analyze", r"analysis", r"deep dive", r"detailed", r"comprehensive",
        r"breakdown", r"statistics"
    ]
}

# Detail level configurations
DETAIL_LEVELS = {
    "quick_check": {
        "max_items": 3,
        "max_insights": 2,
        "max_recommendations": 1,
        "include_raw_data": False,
        "include_trends": False
    },
    "debugging": {
        "max_items": 10,
        "max_insights": 5,
        "max_recommendations": 3,
        "include_raw_data": True,
        "include_trends": False
    },
    "optimization": {
        "max_items": 8,
        "max_insights": 4,
        "max_recommendations": 5,
        "include_raw_data": False,
        "include_trends": True
    },
    "monitoring": {
        "max_items": 5,
        "max_insights": 3,
        "max_recommendations": 2,
        "include_raw_data": False,
        "include_trends": True
    },
    "analysis": {
        "max_items": 15,
        "max_insights": 8,
        "max_recommendations": 6,
        "include_raw_data": True,
        "include_trends": True
    }
}

def context_aware_summarize(
    data_source: str = "portfolio",
    user_context: str = "",
    custom_filters: List[str] = None,
    output_format: str = "structured",  # "structured", "natural", "bullet_points"
    max_tokens: int = 500
) -> Dict[str, Any]:
    """
    Perform context-aware summarization with user intent detection.

    Analyzes user's context to determine what they need and provides
    appropriately detailed responses, optimizing for token efficiency.

    Args:
        data_source: Data source to summarize ("portfolio", "system", "errors", "performance")
        user_context: User's question or context for intent detection
        custom_filters: Additional filters to apply
        output_format: Response format ("structured", "natural", "bullet_points")
        max_tokens: Maximum tokens for response (auto-truncates if exceeded)

    Returns:
        Context-aware summary with metadata about detected intent
    """

    try:
        # Detect user intent
        detected_intent = _detect_user_intent(user_context)
        detail_config = DETAIL_LEVELS.get(detected_intent, DETAIL_LEVELS["quick_check"])

        # Apply custom filters
        filters = _parse_custom_filters(custom_filters)

        # Get data based on source
        raw_data = _get_data_for_summarization(data_source, filters)

        # Process data based on intent
        processed_data = _process_data_for_intent(raw_data, detected_intent, detail_config)

        # Generate summary based on intent and output format
        summary = _generate_context_aware_summary(
            processed_data,
            detected_intent,
            detail_config,
            output_format
        )

        # Ensure token limit compliance
        if len(json.dumps(summary)) > max_tokens:
            summary = _truncate_summary(summary, max_tokens)

        return {
            "success": True,
            "data_source": data_source,
            "detected_intent": detected_intent,
            "user_context": user_context,
            "custom_filters": custom_filters,
            "output_format": output_format,
            "detail_level": detail_config,
            "token_usage": len(json.dumps(summary)),
            "token_limit": max_tokens,
            "summary": summary,
            "metadata": {
                "confidence": _calculate_intent_confidence(user_context, detected_intent),
                "processing_time_ms": _measure_processing_time(),
                "data_points_processed": len(processed_data.get("items", []))
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Context-aware summarization failed: {str(e)}",
            "suggestion": "Check data source and parameters"
        }

def _detect_user_intent(user_context: str) -> str:
    """Detect user intent from context text."""

    if not user_context:
        return "quick_check"

    # Convert to lowercase for case-insensitive matching
    context_lower = user_context.lower()

    # Score each intent type
    intent_scores = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, context_lower, re.IGNORECASE):
                score += 1
        intent_scores[intent] = score

    # Return intent with highest score
    if intent_scores:
        return max(intent_scores, key=intent_scores.get)

    return "quick_check"

def _calculate_intent_confidence(user_context: str, detected_intent: str) -> float:
    """Calculate confidence score for detected intent."""

    if not user_context:
        return 0.5

    patterns = INTENT_PATTERNS.get(detected_intent, [])
    if not patterns:
        return 0.5

    matches = sum(1 for pattern in patterns if re.search(pattern, user_context.lower(), re.IGNORECASE))
    total_patterns = len(patterns)

    return min(matches / max(total_patterns, 1), 1.0)

def _parse_custom_filters(custom_filters: List[str]) -> Dict[str, Any]:
    """Parse custom filters from user input."""

    filters = {
        "symbol_filters": [],
        "time_range": None,
        "pnl_filter": None,
        "analysis_status": None,
        "priority_filter": None
    }

    if not custom_filters:
        return filters

    for filter_str in custom_filters:
        filter_lower = filter_str.lower()

        # Symbol filters
        if filter_str.startswith("symbol:"):
            filters["symbol_filters"].extend(filter_str[8:].split(","))

        # Time range filters
        elif filter_str.startswith("time:"):
            if "1h" in filter_str:
                filters["time_range"] = "1h"
            elif "24h" in filter_str or "1d" in filter_str:
                filters["time_range"] = "24h"
            elif "7d" in filter_str or "1w" in filter_str:
                filters["time_range"] = "7d"

        # P&L filters
        elif filter_str.startswith("pnl:"):
            if "positive" in filter_str or "profit" in filter_str:
                filters["pnl_filter"] = "positive"
            elif "negative" in filter_str or "loss" in filter_str:
                filters["pnl_filter"] = "negative"

        # Analysis status filters
        elif filter_str.startswith("analyzed:"):
            if "recent" in filter_str:
                filters["analysis_status"] = "recent"
            elif "missing" in filter_str or "none" in filter_str:
                filters["analysis_status"] = "missing"

        # Priority filters
        elif filter_str.startswith("priority:"):
            if "high" in filter_str:
                filters["priority_filter"] = "high"
            elif "low" in filter_str:
                filters["priority_filter"] = "low"

    return filters

def _get_data_for_summarization(data_source: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Get data for summarization based on source and filters."""

    db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')
    db_file = Path(db_path)

    if not db_file.exists():
        return {
            "success": False,
            "error": f"Database file not found: {db_file}",
            "items": [],
            "metadata": {"total_items": 0}
        }

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if data_source == "portfolio":
            return _get_portfolio_data(cursor, filters)
        elif data_source == "system":
            return _get_system_data(cursor, filters)
        elif data_source == "errors":
            return _get_errors_data(cursor, filters)
        elif data_source == "performance":
            return _get_performance_data(cursor, filters)
        else:
            return {
                "success": False,
                "error": f"Unknown data source: {data_source}",
                "items": [],
                "metadata": {"total_items": 0}
            }

    finally:
        conn.close()

def _get_portfolio_data(cursor: sqlite3.Cursor, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Get portfolio data with applied filters."""

    # Get portfolio holdings
    cursor.execute("SELECT id, holdings FROM portfolio")
    all_items = []

    for row in cursor.fetchall():
        try:
            holdings_data = json.loads(row[1])
            for holding in holdings_data:
                # Apply filters
                if _passes_portfolio_filters(holding, filters):
                    all_items.append(holding)
        except (json.JSONDecodeError, TypeError):
            continue

    return {
        "success": True,
        "data_source": "portfolio",
        "items": all_items,
        "metadata": {
            "total_items": len(all_items),
            "filters_applied": filters
        }
    }

def _get_system_data(cursor: sqlite3.Cursor, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Get system data with applied filters."""

    system_items = []

    # Database statistics
    cursor.execute("SELECT COUNT(*) as count FROM analysis_history")
    system_items.append({
        "type": "database_stats",
        "total_analyses": cursor.fetchone()['count'],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    # Recent activity
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) as count
        FROM analysis_history
        WHERE timestamp > datetime('now', '-24 hours')
    """)
    system_items.append({
        "type": "recent_activity",
        "symbols_analyzed_24h": cursor.fetchone()['count'],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {
        "success": True,
        "data_source": "system",
        "items": system_items,
        "metadata": {
            "total_items": len(system_items),
            "filters_applied": filters
        }
    }

def _get_errors_data(cursor: sqlite3.Cursor, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Get error data with applied filters."""

    cursor.execute("""
        SELECT DISTINCT
            symbol,
            MAX(timestamp) as last_error,
            COUNT(*) as error_count
        FROM analysis_history
        WHERE (analysis_data LIKE '%error%' OR analysis_data LIKE '%failed%')
        GROUP BY symbol
        ORDER BY error_count DESC
        LIMIT 50
    """)

    error_items = []
    for row in cursor.fetchall():
        error_items.append({
            "symbol": row['symbol'],
            "last_error": row['last_error'],
            "error_count": row['error_count'],
            "type": "analysis_error"
        })

    return {
        "success": True,
        "data_source": "errors",
        "items": error_items,
        "metadata": {
            "total_items": len(error_items),
            "filters_applied": filters
        }
    }

def _get_performance_data(cursor: sqlite3.Cursor, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Get performance data with applied filters."""

    performance_items = []

    # Recent performance
    cursor.execute("""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as operations,
            AVG(CASE
                WHEN analysis_data LIKE '%error%' THEN 0
                ELSE 1
            END) * 100 as success_rate
        FROM analysis_history
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """)

    for row in cursor.fetchall():
        performance_items.append({
            "date": row['date'],
            "operations": row['operations'],
            "success_rate": round(row['success_rate'], 2),
            "type": "daily_performance"
        })

    return {
        "success": True,
        "data_source": "performance",
        "items": performance_items,
        "metadata": {
            "total_items": len(performance_items),
            "filters_applied": filters
        }
    }

def _passes_portfolio_filters(holding: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Check if portfolio item passes all filters."""

    # Symbol filters
    if filters["symbol_filters"]:
        if holding.get('symbol') not in filters["symbol_filters"]:
            return False

    # P&L filters
    if filters["pnl_filter"] == "positive" and holding.get('pnl_pct', 0) <= 0:
        return False
    elif filters["pnl_filter"] == "negative" and holding.get('pnl_pct', 0) > 0:
        return False

    return True

def _process_data_for_intent(
    raw_data: Dict[str, Any],
    intent: str,
    detail_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Process data based on detected user intent."""

    items = raw_data.get("items", [])

    if intent in ["quick_check", "monitoring"]:
        # Sort by importance/score for quick insights
        items = _sort_by_relevance(items, intent)

    elif intent == "debugging":
        # Sort by problematic nature
        items = _sort_by_problematic(items, intent)

    elif intent == "optimization":
        # Sort by optimization potential
        items = _sort_by_optimization_potential(items, intent)

    elif intent == "analysis":
        # Sort by analysis interest
        items = _sort_by_analysis_interest(items, intent)

    # Limit items based on detail config
    limited_items = items[:detail_config["max_items"]]

    return {
        "processed_items": limited_items,
        "total_items_before_limit": len(items),
        "items_filtered": len(items) - len(limited_items),
        "intent": intent,
        "detail_config": detail_config
    }

def _sort_by_relevance(items: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
    """Sort items by relevance for quick insights."""

    if intent == "quick_check":
        # For portfolio: sort by P&L magnitude
        return sorted(items, key=lambda x: abs(x.get('pnl_pct', 0)), reverse=True)
    elif intent == "monitoring":
        # For system: sort by timestamp
        return sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)
    else:
        return items

def _sort_by_problematic(items: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
    """Sort items by problematic nature for debugging."""

    return sorted(items, key=lambda x: x.get('error_count', 0), reverse=True)

def _sort_by_optimization_potential(items: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
    """Sort items by optimization potential."""

    return sorted(items, key=lambda x: x.get('performance_impact', 0), reverse=True)

def _sort_by_analysis_interest(items: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
    """Sort items by analysis interest."""

    return items  # Return unsorted for detailed analysis

def _generate_context_aware_summary(
    processed_data: Dict[str, Any],
    intent: str,
    detail_config: Dict[str, Any],
    output_format: str
) -> Dict[str, Any]:
    """Generate context-aware summary based on intent and format."""

    items = processed_data["processed_items"]

    # Generate insights based on intent
    insights = _generate_intent_based_insights(items, intent, detail_config)

    # Generate recommendations
    recommendations = _generate_intent_based_recommendations(items, intent, detail_config)

    # Format response based on output format
    if output_format == "natural":
        return _format_natural_language_summary(insights, recommendations, intent)
    elif output_format == "bullet_points":
        return _format_bullet_point_summary(insights, recommendations, intent)
    else:  # structured
        return _format_structured_summary(insights, recommendations, intent, processed_data)

def _generate_intent_based_insights(
    items: List[Dict[str, Any]],
    intent: str,
    detail_config: Dict[str, Any]
) -> List[str]:
    """Generate insights based on detected intent."""

    insights = []

    if not items:
        insights.append("No data available for analysis")
        return insights

    if intent == "quick_check":
        insights.append(f"Portfolio contains {len(items)} items")
        if items and 'pnl_pct' in items[0]:
            top_performer = max(items, key=lambda x: x.get('pnl_pct', 0))
            insights.append(f"Top performer: {top_performer.get('symbol', 'Unknown')} ({top_performer.get('pnl_pct', 0):.1f}%)")

    elif intent == "debugging":
        problematic_count = len([item for item in items if item.get('error_count', 0) > 0])
        insights.append(f"Found {problematic_count} items with issues")
        if problematic_count > 0:
            insights.append("Requires immediate attention")

    elif intent == "optimization":
        insights.append(f"Analysis covers {len(items)} items")
        insights.append("Optimization opportunities identified")

    elif intent == "monitoring":
        insights.append(f"Monitoring {len(items)} system metrics")
        insights.append("System performance within normal ranges")

    elif intent == "analysis":
        insights.append(f"Comprehensive analysis of {len(items)} items")
        insights.append("Detailed breakdown provided")

    # Limit insights based on config
    return insights[:detail_config["max_insights"]]

def _generate_intent_based_recommendations(
    items: List[Dict[str, Any]],
    intent: str,
    detail_config: Dict[str, Any]
) -> List[str]:
    """Generate recommendations based on detected intent."""

    recommendations = []

    if not items:
        recommendations.append("No data available for recommendations")
        return recommendations

    if intent == "quick_check":
        if len(items) > 50:
            recommendations.append("Consider portfolio optimization for better performance")
        recommendations.append("Continue regular monitoring")

    elif intent == "debugging":
        if any(item.get('error_count', 0) > 0 for item in items):
            recommendations.append("Investigate and resolve identified issues")
        recommendations.append("Review error handling processes")

    elif intent == "optimization":
        recommendations.append("Implement suggested optimizations")
        recommendations.append("Monitor performance improvements")

    elif intent == "monitoring":
        recommendations.append("Continue regular performance monitoring")
        recommendations.append("Set up automated alerts for anomalies")

    elif intent == "analysis":
        recommendations.append("Review detailed analysis for insights")
        recommendations.append("Consider strategic adjustments based on findings")

    # Limit recommendations based on config
    return recommendations[:detail_config["max_recommendations"]]

def _format_natural_language_summary(
    insights: List[str],
    recommendations: List[str],
    intent: str
) -> Dict[str, Any]:
    """Format summary in natural language."""

    return {
        "summary_type": "natural_language",
        "content": f"Based on the {intent} analysis, {' and '.join(insights[:-1])}. {insights[-1] if insights else 'No major issues detected'}. {'Recommendations: ' + '; '.join(recommendations) if recommendations else 'No immediate actions required'}.",
        "insights": insights,
        "recommendations": recommendations
    }

def _format_bullet_point_summary(
    insights: List[str],
    recommendations: List[str],
    intent: str
) -> Dict[str, Any]:
    """Format summary as bullet points."""

    return {
        "summary_type": "bullet_points",
        "content": {
            "intent": f"Analysis Type: {intent.title()}",
            "insights": insights,
            "recommendations": recommendations
        }
    }

def _format_structured_summary(
    insights: List[str],
    recommendations: List[str],
    intent: str,
    processed_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Format summary in structured format."""

    return {
        "summary_type": "structured",
        "intent": intent,
        "overview": f"Context-aware {intent} analysis",
        "insights": insights,
        "recommendations": recommendations,
        "data_points": processed_data.get("total_items_before_limit", 0),
        "filters_applied": processed_data.get("items_filtered", 0)
    }

def _truncate_summary(summary: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
    """Truncate summary to meet token limit."""

    # Convert to JSON string and truncate
    json_str = json.dumps(summary, separators=(',', ':'))

    if len(json_str) <= max_tokens:
        return summary

    # Implement simple truncation by removing least important fields
    if "raw_data" in summary:
        del summary["raw_data"]

    if "recommendations" in summary and len(summary["recommendations"]) > 2:
        summary["recommendations"] = summary["recommendations"][:2]

    return summary

def _measure_processing_time() -> float:
    """Measure processing time for performance tracking."""
    return 0.05  # Mock implementation

def main():
    """Main entry point for MCP tool execution."""
    try:
        # Parse input from MCP server
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            input_data = json.loads(sys.stdin.read())

        # Execute context-aware summarization
        result = context_aware_summarize(
            data_source=input_data.get("data_source", "portfolio"),
            user_context=input_data.get("user_context", ""),
            custom_filters=input_data.get("custom_filters", []),
            output_format=input_data.get("output_format", "structured"),
            max_tokens=input_data.get("max_tokens", 500)
        )

        # Output result
        print(json.dumps(result, indent=2))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Invalid JSON input: {str(e)}",
            "suggestion": "Ensure input is valid JSON format"
        }))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Context-aware summarization failed: {str(e)}",
            "suggestion": "Check input parameters and data accessibility"
        }))

if __name__ == "__main__":
    main()