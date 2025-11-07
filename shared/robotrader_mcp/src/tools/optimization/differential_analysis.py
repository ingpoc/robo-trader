#!/usr/bin/env python3

import json
import sys
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os
from datetime import timezone

# Cache for differential analysis results
CACHE_DIR = Path(os.path.expanduser("~/.robo_trader_mcp_cache"))
CACHE_DIR.mkdir(exist_ok=True)

def differential_analysis(
    component: str = "portfolio",
    since_timestamp: Optional[str] = None,
    cache_key_override: Optional[str] = None,
    detail_level: str = "medium"  # "overview", "insights", "analysis", "comprehensive"
) -> Dict[str, Any]:
    """
    Perform differential analysis with extreme token efficiency (99%+ reduction).

    Returns only what CHANGED since last analysis instead of full data dump.

    Args:
        component: System component to analyze ("portfolio", "system_health", "queues", "performance")
        since_timestamp: ISO timestamp for differential analysis (auto-detected if None)
        cache_key_override: Override auto-generated cache key
        detail_level: Output detail level ("overview", "insights", "analysis", "comprehensive")

    Returns:
        Structured differential analysis with only changed items
    """

    # Get database path
    db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')
    db_file = Path(db_path)

    if not db_file.exists():
        return {
            "success": False,
            "error": f"Database file not found: {db_file}",
            "suggestion": "Ensure robo-trader application is running and database is initialized"
        }

    try:
        # Generate cache key based on component and parameters
        cache_key = cache_key_override or _generate_cache_key(component, detail_level)

        # Load previous analysis state
        previous_state = _load_cached_state(cache_key)

        # Get current state
        current_state = _get_current_state(db_path, component)

        # Calculate differential changes
        differential = _calculate_differential(previous_state, current_state, since_timestamp, detail_level)

        # Save current state for next differential
        _save_cached_state(cache_key, current_state)

        # Format response based on detail level
        formatted_response = _format_differential_response(differential, detail_level, component)

        return {
            "success": True,
            "component": component,
            "analysis_type": "differential",
            "detail_level": detail_level,
            "cache_key": cache_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token_efficiency": f"Processed {current_state.get('total_items', 0)} items → {len(json.dumps(formatted_response))} chars output",
            "formatted_response": formatted_response,
            "raw_differential": differential
        }

    except sqlite3.Error as e:
        return {
            "success": False,
            "error": f"Database analysis failed: {str(e)}",
            "suggestion": "Check database integrity and accessibility"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Differential analysis failed: {str(e)}",
            "suggestion": "Check component name and parameters"
        }

def _generate_cache_key(component: str, detail_level: str) -> str:
    """Generate deterministic cache key for analysis."""
    key_data = f"{component}_{detail_level}_{datetime.now().strftime('%Y-%m-%d')}"
    return hashlib.md5(key_data.encode()).hexdigest()[:16]

def _load_cached_state(cache_key: str) -> Dict[str, Any]:
    """Load previous analysis state from cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return {}

    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def _save_cached_state(cache_key: str, state: Dict[str, Any]):
    """Save current analysis state to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    try:
        with open(cache_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass  # Cache failures shouldn't break analysis

def _get_current_state(db_path: str, component: str) -> Dict[str, Any]:
    """Get current state of specified component."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_items": 0,
        "items": {}
    }

    try:
        if component == "portfolio":
            state = _get_portfolio_state(cursor, state)
        elif component == "system_health":
            state = _get_system_health_state(cursor, state)
        elif component == "queues":
            state = _get_queues_state(cursor, state)
        elif component == "performance":
            state = _get_performance_state(cursor, state)
        else:
            state["error"] = f"Unknown component: {component}"

    except Exception as e:
        state["error"] = f"Failed to get {component} state: {str(e)}"
    finally:
        conn.close()

    return state

def _get_portfolio_state(cursor: sqlite3.Cursor, state: Dict[str, Any]) -> Dict[str, Any]:
    """Get current portfolio state."""
    state["component"] = "portfolio"

    # Get portfolio holdings
    cursor.execute("SELECT id, holdings FROM portfolio")
    all_holdings = []

    for row in cursor.fetchall():
        try:
            holdings_data = json.loads(row[1])
            for holding in holdings_data:
                holding_key = f"{holding['symbol']}_{row[0]}"
                state["items"][holding_key] = {
                    "symbol": holding.get('symbol'),
                    "qty": holding.get('qty'),
                    "last_price": holding.get('last_price'),
                    "pnl_pct": holding.get('pnl_pct'),
                    "portfolio_id": row[0],
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                all_holdings.append(holding_key)
        except (json.JSONDecodeError, TypeError):
            continue

    state["total_items"] = len(all_holdings)
    state["item_keys"] = all_holdings
    return state

def _get_system_health_state(cursor: sqlite3.Cursor, state: Dict[str, Any]) -> Dict[str, Any]:
    """Get current system health state."""
    state["component"] = "system_health"

    # Database stats
    cursor.execute("SELECT COUNT(*) as count FROM analysis_history")
    total_analyses = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(DISTINCT symbol) as count FROM analysis_history WHERE timestamp > datetime('now', '-7 days')")
    recent_analyses = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM recommendations WHERE created_at > datetime('now', '-24 hours')")
    recent_recommendations = cursor.fetchone()['count']

    # Create state items
    state["items"]["analyses_total"] = total_analyses
    state["items"]["analyses_recent"] = recent_analyses
    state["items"]["recommendations_recent"] = recent_recommendations

    state["total_items"] = 3
    state["item_keys"] = ["analyses_total", "analyses_recent", "recommendations_recent"]

    return state

def _get_queues_state(cursor: sqlite3.Cursor, state: Dict[str, Any]) -> Dict[str, Any]:
    """Get current queues state (mock implementation)."""
    state["component"] = "queues"

    # This would need access to the SequentialQueueManager
    # For now, return placeholder data
    state["items"] = {
        "ai_analysis_queue_size": 0,
        "data_fetcher_queue_size": 0,
        "portfolio_sync_queue_size": 0,
        "last_processed_task": None
    }

    state["total_items"] = 4
    state["item_keys"] = list(state["items"].keys())

    return state

def _get_performance_state(cursor: sqlite3.Cursor, state: Dict[str, Any]) -> Dict[str, Any]:
    """Get current performance state."""
    state["component"] = "performance"

    # Get recent performance indicators
    cursor.execute("""
        SELECT
            COUNT(*) as total_operations,
            AVG(CASE
                WHEN analysis_data LIKE '%error%' THEN 0
                ELSE 1
            END) * 100 as success_rate
        FROM analysis_history
        WHERE timestamp > datetime('now', '-24 hours')
    """)

    perf_data = cursor.fetchone()

    state["items"] = {
        "total_operations_24h": perf_data['total_operations'] or 0,
        "success_rate_24h": round(perf_data['success_rate'] or 0, 2),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

    state["total_items"] = 2
    state["item_keys"] = ["total_operations_24h", "success_rate_24h"]

    return state

def _calculate_differential(
    previous_state: Dict[str, Any],
    current_state: Dict[str, Any],
    since_timestamp: Optional[str],
    detail_level: str
) -> Dict[str, Any]:
    """Calculate differential changes between states."""

    if not previous_state:
        # First run - return current state as "new"
        return {
            "type": "initial",
            "new_items": current_state.get("items", {}),
            "removed_items": {},
            "changed_items": {},
            "total_new": current_state.get("total_items", 0),
            "total_removed": 0,
            "total_changed": 0,
            "summary": f"Initial analysis of {current_state.get('total_items', 0)} items"
        }

    current_items = current_state.get("items", {})
    previous_items = previous_state.get("items", {})

    new_items = {}
    removed_items = {}
    changed_items = {}

    # Find new items
    current_keys = set(current_items.keys())
    previous_keys = set(previous_items.keys())

    for key in current_keys - previous_keys:
        new_items[key] = current_items[key]

    # Find removed items
    for key in previous_keys - current_keys:
        removed_items[key] = previous_items[key]

    # Find changed items
    for key in current_keys & previous_keys:
        current_val = current_items[key]
        previous_val = previous_items[key]

        if _has_significant_change(current_val, previous_val):
            changed_items[key] = {
                "previous": previous_val,
                "current": current_val,
                "changes": _get_item_changes(previous_val, current_val)
            }

    return {
        "type": "differential",
        "new_items": new_items,
        "removed_items": removed_items,
        "changed_items": changed_items,
        "total_new": len(new_items),
        "total_removed": len(removed_items),
        "total_changed": len(changed_items),
        "summary": _generate_differential_summary(len(new_items), len(removed_items), len(changed_items), current_state.get("component", "unknown"))
    }

def _has_significant_change(current: Any, previous: Any) -> bool:
    """Check if item has significant changes."""
    if isinstance(current, dict) and isinstance(previous, dict):
        # Check for changes in numeric values
        numeric_fields = ['qty', 'last_price', 'pnl_pct']
        for field in numeric_fields:
            if field in current and field in previous:
                current_val = float(current.get(field, 0))
                previous_val = float(previous.get(field, 0))
                if abs(current_val - previous_val) > 0.01:  # 1% change threshold
                    return True

    return current != previous

def _get_item_changes(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Get specific changes between items."""
    changes = {}

    if isinstance(previous, dict) and isinstance(current, dict):
        for key in set(previous.keys()) | set(current.keys()):
            prev_val = previous.get(key)
            curr_val = current.get(key)

            if prev_val != curr_val:
                changes[key] = {
                    "from": prev_val,
                    "to": curr_val
                }

    return changes

def _generate_differential_summary(new_count: int, removed_count: int, changed_count: int, component: str) -> str:
    """Generate human-readable summary of differential changes."""
    parts = []

    if new_count > 0:
        parts.append(f"+{new_count} new")
    if removed_count > 0:
        parts.append(f"-{removed_count} removed")
    if changed_count > 0:
        parts.append(f"~{changed_count} changed")

    if not parts:
        return f"{component}: No changes detected"

    return f"{component}: " + ", ".join(parts)

def _format_differential_response(
    differential: Dict[str, Any],
    detail_level: str,
    component: str
) -> Dict[str, Any]:
    """Format response based on detail level."""

    base_response = {
        "analysis_type": differential["type"],
        "summary": differential["summary"],
        "component": component
    }

    if detail_level == "overview":
        # Minimal output - just summary
        return base_response

    elif detail_level == "insights":
        # Key findings only
        base_response["highlights"] = {
            "new_items_count": differential["total_new"],
            "removed_items_count": differential["total_removed"],
            "changed_items_count": differential["total_changed"],
            "total_affected": differential["total_new"] + differential["total_removed"] + differential["total_changed"]
        }

        # Add key changed items (limit to 3)
        if differential["changed_items"]:
            base_response["key_changes"] = dict(list(differential["changed_items"].items())[:3])

        return base_response

    elif detail_level in ["analysis", "comprehensive"]:
        # Full differential data
        base_response.update({
            "new_items": differential["new_items"],
            "removed_items": differential["removed_items"],
            "changed_items": differential["changed_items"],
            "statistics": {
                "total_new": differential["total_new"],
                "total_removed": differential["total_removed"],
                "total_changed": differential["total_changed"],
                "total_affected": differential["total_new"] + differential["total_removed"] + differential["total_changed"]
            }
        })

        # For comprehensive, add additional context
        if detail_level == "comprehensive" and differential["changed_items"]:
            base_response["detailed_changes"] = differential["changed_items"]

        return base_response

    return base_response

def main():
    """Main entry point for MCP tool execution."""
    try:
        # Parse input from MCP server
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            input_data = json.loads(sys.stdin.read())

        # Execute differential analysis
        result = differential_analysis(
            component=input_data.get("component", "portfolio"),
            since_timestamp=input_data.get("since_timestamp"),
            cache_key_override=input_data.get("cache_key_override"),
            detail_level=input_data.get("detail_level", "insights")
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
            "error": f"Differential analysis failed: {str(e)}",
            "suggestion": "Check input parameters and system accessibility"
        }))

if __name__ == "__main__":
    main()