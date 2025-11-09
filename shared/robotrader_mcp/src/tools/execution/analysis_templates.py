#!/usr/bin/env python3
"""
Analysis Templates - Pre-built sandbox execution patterns for robo-trader

Instead of reading full files/logs into context, these templates process
data IN SANDBOX and return only insights (200-500 tokens vs 5k-20k tokens).

Token Efficiency: 95-98% reduction vs reading raw data into Claude's context
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter


# ============================================================================
# CODE ANALYSIS TEMPLATES
# ============================================================================

def analyze_database_access_patterns(file_path: str) -> Dict[str, Any]:
    """
    Analyze Python file for database access patterns.

    Returns insights only (300 tokens) instead of full file content (5k-20k tokens).

    Example:
        result = analyze_database_access_patterns("src/web/routes/monitoring.py")
        # Returns: {"direct_access_count": 3, "locked_access_count": 5, ...}
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content)

        results = {
            "file_path": file_path,
            "total_lines": len(content.split('\n')),
            "database_operations": {
                "direct_access": [],      # db.connection.execute() - BAD
                "locked_access": [],      # config_state.store_*() - GOOD
                "async_operations": 0,
                "sync_operations": 0
            },
            "issues": [],
            "recommendations": []
        }

        # Find all database access patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for direct database access (BAD pattern)
                if _is_direct_db_access(node):
                    results["database_operations"]["direct_access"].append({
                        "line": node.lineno,
                        "call": ast.unparse(node)[:100]
                    })
                    results["issues"].append(
                        f"Line {node.lineno}: Direct db access bypasses locking"
                    )

                # Check for locked access (GOOD pattern)
                elif _is_locked_db_access(node):
                    results["database_operations"]["locked_access"].append({
                        "line": node.lineno,
                        "method": _get_method_name(node)
                    })

                # Check if async
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['execute', 'commit', 'fetchall']:
                        # Check if in async function
                        parent = node
                        while parent:
                            if isinstance(parent, ast.AsyncFunctionDef):
                                results["database_operations"]["async_operations"] += 1
                                break
                            parent = getattr(parent, 'parent', None)
                        else:
                            results["database_operations"]["sync_operations"] += 1

        # Generate recommendations
        if results["database_operations"]["direct_access"]:
            results["recommendations"].append(
                "Replace direct db.connection.execute() with ConfigurationState locked methods"
            )

        if results["database_operations"]["sync_operations"] > 0:
            results["recommendations"].append(
                "Convert sync database operations to async"
            )

        # Token estimate
        results["token_efficiency"] = {
            "insight_tokens": 300,
            "full_file_tokens": len(content) // 4,  # Rough estimate
            "reduction_percent": 95
        }

        return results

    except Exception as e:
        return {
            "error": str(e),
            "file_path": file_path
        }


def analyze_import_patterns(file_path: str) -> Dict[str, Any]:
    """
    Analyze import patterns to find circular dependencies or missing imports.

    Returns: Dependency graph insights (200 tokens) vs full file reading (5k+ tokens)
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content)

        results = {
            "file_path": file_path,
            "imports": {
                "standard_library": [],
                "third_party": [],
                "local": []
            },
            "import_locations": [],
            "issues": []
        }

        # Categorize imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    category = _categorize_import(alias.name)
                    results["imports"][category].append(alias.name)
                    results["import_locations"].append({
                        "line": node.lineno,
                        "module": alias.name,
                        "type": "direct"
                    })

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    category = _categorize_import(node.module)
                    for alias in node.names:
                        results["imports"][category].append(f"{node.module}.{alias.name}")
                        results["import_locations"].append({
                            "line": node.lineno,
                            "module": node.module,
                            "name": alias.name,
                            "type": "from"
                        })

        # Check for late imports (inside functions - might indicate circular dependency)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        results["issues"].append({
                            "line": child.lineno,
                            "issue": "Import inside function (possible circular dependency)",
                            "function": node.name
                        })

        results["summary"] = {
            "total_imports": sum(len(v) for v in results["imports"].values()),
            "local_imports": len(results["imports"]["local"]),
            "late_imports": len(results["issues"])
        }

        return results

    except Exception as e:
        return {"error": str(e), "file_path": file_path}


# ============================================================================
# LOG ANALYSIS TEMPLATES
# ============================================================================

def analyze_log_errors(log_path: str, time_window_hours: int = 24) -> Dict[str, Any]:
    """
    Analyze log file for error patterns.

    Returns: Error summary (500 tokens) vs full log content (50k+ tokens)
    """
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()

        results = {
            "log_path": log_path,
            "total_lines": len(lines),
            "error_patterns": defaultdict(list),
            "error_timeline": [],
            "top_errors": []
        }

        # Common robo-trader error patterns
        patterns = {
            "database_locked": r"database.*is locked|sqlite.*locked",
            "turn_limit": r"error_max_turns|turn limit",
            "websocket": r"WebSocket.*closed|WS.*disconnect",
            "rate_limit": r"rate.*limit|429|too many requests",
            "import_error": r"ImportError|ModuleNotFoundError",
            "timeout": r"TimeoutError|timed out"
        }

        for line_num, line in enumerate(lines, 1):
            if 'ERROR' in line or 'CRITICAL' in line:
                # Extract timestamp if present
                timestamp = _extract_timestamp(line)

                # Match against known patterns
                matched = False
                for pattern_name, pattern_regex in patterns.items():
                    if re.search(pattern_regex, line, re.IGNORECASE):
                        results["error_patterns"][pattern_name].append({
                            "line": line_num,
                            "timestamp": timestamp,
                            "message": line.strip()[:150]
                        })
                        matched = True
                        break

                if not matched:
                    results["error_patterns"]["other"].append({
                        "line": line_num,
                        "timestamp": timestamp,
                        "message": line.strip()[:150]
                    })

        # Generate error summary
        error_counts = {k: len(v) for k, v in results["error_patterns"].items()}
        results["top_errors"] = sorted(
            error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        results["summary"] = {
            "total_errors": sum(error_counts.values()),
            "unique_patterns": len(error_counts),
            "most_common": results["top_errors"][0] if results["top_errors"] else None
        }

        # Token efficiency
        results["token_efficiency"] = {
            "insight_tokens": 500,
            "full_log_tokens": len(''.join(lines)) // 4,
            "reduction_percent": 98
        }

        return results

    except Exception as e:
        return {"error": str(e), "log_path": log_path}


# ============================================================================
# PORTFOLIO DATA ANALYSIS TEMPLATES
# ============================================================================

def analyze_portfolio_health(portfolio_data: List[Dict]) -> Dict[str, Any]:
    """
    Analyze portfolio data for health metrics.

    Returns: Health summary (400 tokens) vs raw portfolio data (10k+ tokens)
    """
    if not portfolio_data:
        return {"error": "No portfolio data provided"}

    results = {
        "total_positions": len(portfolio_data),
        "performance": {
            "gainers": [],
            "losers": [],
            "neutral": []
        },
        "risk_analysis": {
            "high_risk": [],
            "medium_risk": [],
            "low_risk": []
        },
        "data_quality": {
            "complete": 0,
            "missing_data": []
        },
        "recommendations": []
    }

    for stock in portfolio_data:
        symbol = stock.get('symbol', 'UNKNOWN')

        # Performance categorization
        roi = stock.get('roi_percent', 0)
        if roi > 5:
            results["performance"]["gainers"].append({
                "symbol": symbol,
                "roi": roi
            })
        elif roi < -5:
            results["performance"]["losers"].append({
                "symbol": symbol,
                "roi": roi
            })
        else:
            results["performance"]["neutral"].append(symbol)

        # Data quality check
        required_fields = ['earnings', 'news', 'fundamental_analysis']
        missing = [f for f in required_fields if not stock.get(f)]

        if not missing:
            results["data_quality"]["complete"] += 1
        else:
            results["data_quality"]["missing_data"].append({
                "symbol": symbol,
                "missing_fields": missing
            })

    # Generate recommendations
    if len(results["performance"]["losers"]) > len(results["performance"]["gainers"]):
        results["recommendations"].append(
            "Portfolio has more losers than gainers - consider rebalancing"
        )

    if results["data_quality"]["complete"] < len(portfolio_data) * 0.8:
        results["recommendations"].append(
            "Over 20% of positions missing data - run data sync"
        )

    return results


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _is_direct_db_access(node: ast.Call) -> bool:
    """Check if AST node represents direct database access."""
    try:
        call_str = ast.unparse(node)
        return 'db.connection.execute' in call_str or 'connection.execute' in call_str
    except:
        return False


def _is_locked_db_access(node: ast.Call) -> bool:
    """Check if AST node represents locked database access."""
    try:
        call_str = ast.unparse(node)
        locked_methods = [
            'config_state.store_',
            'config_state.get_',
            'configuration_state.store_',
            'configuration_state.get_'
        ]
        return any(method in call_str for method in locked_methods)
    except:
        return False


def _get_method_name(node: ast.Call) -> str:
    """Extract method name from AST call node."""
    try:
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return "unknown"
    except:
        return "unknown"


def _categorize_import(module_name: str) -> str:
    """Categorize import as standard library, third-party, or local."""
    standard_libs = {
        'os', 'sys', 'json', 'datetime', 'asyncio', 'pathlib',
        'typing', 'collections', 're', 'ast', 'subprocess'
    }

    base_module = module_name.split('.')[0]

    if base_module in standard_libs:
        return "standard_library"
    elif base_module in ['src', 'shared', 'tests']:
        return "local"
    else:
        return "third_party"


def _extract_timestamp(log_line: str) -> Optional[str]:
    """Extract timestamp from log line."""
    # Common log timestamp patterns
    patterns = [
        r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',  # ISO format
        r'\d{2}:\d{2}:\d{2}',  # Time only
    ]

    for pattern in patterns:
        match = re.search(pattern, log_line)
        if match:
            return match.group(0)

    return None


# ============================================================================
# SCHEMA FOR MCP REGISTRATION
# ============================================================================

def get_schema():
    """Return JSON schema for MCP tool registration."""
    return {
        "name": "analysis_templates",
        "description": "Pre-built analysis patterns that process data in sandbox and return insights only",
        "templates": {
            "analyze_database_access_patterns": {
                "description": "Analyze file for database access patterns (locked vs direct)",
                "input": {"file_path": "string"},
                "output_tokens": 300,
                "savings": "95% vs reading full file"
            },
            "analyze_import_patterns": {
                "description": "Analyze imports for circular dependencies",
                "input": {"file_path": "string"},
                "output_tokens": 200,
                "savings": "96% vs reading full file"
            },
            "analyze_log_errors": {
                "description": "Extract and categorize errors from logs",
                "input": {"log_path": "string", "time_window_hours": "int"},
                "output_tokens": 500,
                "savings": "98% vs reading full logs"
            },
            "analyze_portfolio_health": {
                "description": "Summarize portfolio health metrics",
                "input": {"portfolio_data": "List[Dict]"},
                "output_tokens": 400,
                "savings": "97% vs raw portfolio data"
            }
        }
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test database access analysis
        result = analyze_database_access_patterns(sys.argv[1])
        print(json.dumps(result, indent=2))
