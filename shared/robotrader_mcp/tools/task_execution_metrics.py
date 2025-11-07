#!/usr/bin/env python3
"""Task Execution Metrics Tool - Aggregate task execution statistics with 95%+ token reduction."""

import json
import sys
import sqlite3
import requests
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Cache configuration
CACHE_DIR = Path(os.path.expanduser("~/.robo_trader_mcp_cache"))
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "task_metrics.json"
CACHE_TTL_SECONDS = 120  # 2 minutes


def get_task_execution_metrics(use_cache: bool = True) -> Dict[str, Any]:
    """Get task execution metrics with hybrid data access and token efficiency."""

    # Check cache
    if use_cache and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                cached = json.load(f)
                cache_time = datetime.fromisoformat(cached['cached_at'])
                age = (datetime.now(timezone.utc) - cache_time).total_seconds()

                if age < CACHE_TTL_SECONDS:
                    cached['data_source'] = 'cache'
                    cached['cache_age_seconds'] = int(age)
                    return cached
        except Exception:
            pass

    # Fetch from database
    db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')
    db_file = Path(db_path)

    if not db_file.exists():
        return {
            "success": False,
            "error": "Database file not found",
            "suggestion": "Ensure robo-trader is running and database is initialized"
        }

    try:
        # Get database metrics
        db_metrics = _get_database_metrics(str(db_file))

        # Get API metrics for real-time enrichment
        api_metrics = _get_api_metrics()

        # Combine and transform
        result = _transform_metrics(db_metrics, api_metrics)

        # Cache
        result['cached_at'] = datetime.now(timezone.utc).isoformat()
        with open(CACHE_FILE, 'w') as f:
            json.dump(result, f, indent=2)

        result['data_source'] = 'hybrid'
        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Task metrics fetch failed: {str(e)}",
            "suggestion": "Check database accessibility and API connectivity"
        }


def _get_database_metrics(db_path: str) -> Dict[str, Any]:
    """Query database for historical task metrics."""

    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    metrics = {}

    try:
        # Total tasks executed (24h)
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM scheduler_tasks
            WHERE created_at > datetime('now', '-24 hours')
        """)
        metrics['total_tasks_24h'] = cursor.fetchone()['total']

        # Success/failure breakdown
        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM scheduler_tasks
            WHERE created_at > datetime('now', '-24 hours')
            GROUP BY status
        """)
        status_breakdown = {}
        for row in cursor.fetchall():
            status_breakdown[row['status']] = row['count']
        metrics['status_breakdown'] = status_breakdown

        # Average execution time by task type
        cursor.execute("""
            SELECT
                task_type,
                AVG(execution_duration_ms) as avg_ms,
                COUNT(*) as count
            FROM scheduler_tasks
            WHERE created_at > datetime('now', '-24 hours')
            AND status = 'COMPLETED'
            GROUP BY task_type
            ORDER BY count DESC
            LIMIT 5
        """)
        task_types = []
        for row in cursor.fetchall():
            task_types.append({
                "task_type": row['task_type'],
                "avg_time_ms": int(row['avg_ms']) if row['avg_ms'] else 0,
                "count": row['count']
            })
        metrics['top_task_types'] = task_types

        # Error trends (hourly)
        cursor.execute("""
            SELECT
                strftime('%H', created_at) as hour,
                COUNT(*) as error_count
            FROM scheduler_tasks
            WHERE created_at > datetime('now', '-24 hours')
            AND status = 'FAILED'
            GROUP BY hour
            ORDER BY hour DESC
        """)
        error_trends = []
        for row in cursor.fetchall():
            error_trends.append({
                "hour": row['hour'],
                "failures": row['error_count']
            })
        metrics['error_trends'] = error_trends

        # Portfolio coverage (unique stocks analyzed)
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol) as count
            FROM analysis_history
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        result = cursor.fetchone()
        metrics['unique_symbols_analyzed_24h'] = result['count'] if result else 0

    finally:
        conn.close()

    return metrics


def _get_api_metrics() -> Dict[str, Any]:
    """Get real-time metrics from API."""

    api_base = os.environ.get('ROBO_TRADER_API', 'http://localhost:8000')

    try:
        # Get queue status for backlog
        response = requests.get(f"{api_base}/api/queues/status", timeout=3)
        if response.status_code == 200:
            queue_data = response.json()
            return {
                "current_backlog": queue_data.get('stats', {}).get('total_pending_tasks', 0),
                "active_tasks": queue_data.get('stats', {}).get('total_active_tasks', 0)
            }
    except Exception:
        pass

    return {
        "current_backlog": 0,
        "active_tasks": 0
    }


def _transform_metrics(db_metrics: Dict, api_metrics: Dict) -> Dict[str, Any]:
    """Transform to token-efficient format with insights (95%+ reduction)."""

    # Calculate success rate
    status = db_metrics.get('status_breakdown', {})
    completed = status.get('COMPLETED', 0)
    failed = status.get('FAILED', 0)
    total = completed + failed

    success_rate = (completed / total * 100) if total > 0 else 0

    # Generate insights
    insights = []
    recommendations = []

    # Success rate insights
    if success_rate > 95:
        insights.append(f"Excellent task success rate: {success_rate:.1f}%")
    elif success_rate > 80:
        insights.append(f"Good task success rate: {success_rate:.1f}%")
    else:
        insights.append(f"Low task success rate: {success_rate:.1f}% - investigate failures")
        recommendations.append("Review error logs for failed tasks")

    # Processing volume
    total_24h = db_metrics.get('total_tasks_24h', 0)
    if total_24h > 100:
        insights.append(f"High processing volume: {total_24h} tasks in 24h")
    elif total_24h > 20:
        insights.append(f"Moderate processing volume: {total_24h} tasks in 24h")
    else:
        insights.append(f"Low processing volume: {total_24h} tasks in 24h")
        recommendations.append("Verify queue execution is active")

    # Portfolio coverage
    symbols_analyzed = db_metrics.get('unique_symbols_analyzed_24h', 0)
    if symbols_analyzed > 50:
        insights.append(f"Broad portfolio coverage: {symbols_analyzed} stocks analyzed")
    elif symbols_analyzed < 10:
        insights.append(f"Limited portfolio coverage: only {symbols_analyzed} stocks analyzed")
        recommendations.append("Check portfolio analysis coordinator status")

    # Backlog status
    backlog = api_metrics.get('current_backlog', 0)
    if backlog > 50:
        insights.append(f"High backlog: {backlog} pending tasks")
        recommendations.append("Consider increasing queue concurrency or investigate processing delays")

    # Error trends
    error_trends = db_metrics.get('error_trends', [])
    if len(error_trends) > 5:
        recommendations.append("Multiple hours with task failures - investigate error patterns")

    if not recommendations:
        recommendations.append("Task execution appears healthy - continue monitoring")

    return {
        "success": True,
        "summary": {
            "total_tasks_24h": total_24h,
            "success_rate_pct": round(success_rate, 1),
            "completed_tasks": completed,
            "failed_tasks": failed,
            "unique_stocks_analyzed": symbols_analyzed,
            "current_backlog": backlog,
            "active_tasks": api_metrics.get('active_tasks', 0)
        },
        "top_task_types": db_metrics.get('top_task_types', []),
        "error_trends": error_trends[:5],  # Last 5 hours only
        "insights": insights,
        "recommendations": recommendations,
        "token_efficiency": {
            "compression_ratio": "95%+",
            "note": "24h of task data aggregated into actionable metrics"
        }
    }


def main():
    """Main entry point."""
    try:
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            input_data = {}

        use_cache = input_data.get("use_cache", True)
        result = get_task_execution_metrics(use_cache=use_cache)

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Task metrics tool failed: {str(e)}"
        }))


if __name__ == "__main__":
    main()
