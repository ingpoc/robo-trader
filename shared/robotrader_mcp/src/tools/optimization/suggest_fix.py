#!/usr/bin/env python3
"""
Suggest Fix Tool - Pattern-Based Fix Recommendations

Analyzes errors and suggests fixes based on:
- Known error patterns in robo-trader codebase
- Architectural guidelines from CLAUDE.md files
- Common fix patterns from git history
- Code pattern matching

Token Savings: Provides targeted fix suggestions instead of full file exploration
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict


# Known error patterns and their fixes
ERROR_PATTERNS = {
    "database_locked": {
        "pattern": r"database.*is locked|sqlite.*locked",
        "category": "database",
        "common_causes": [
            "Direct database access without locking",
            "Long-running transaction blocking other operations",
            "Missing ConfigurationState locked method usage"
        ],
        "fixes": [
            {
                "description": "Use ConfigurationState locked methods instead of direct db access",
                "example": "await config_state.store_analysis_history(...)",
                "file_pattern": "src/web/routes/*.py"
            },
            {
                "description": "Check for missing asyncio.Lock() in state classes",
                "example": "async with self._lock: await self.db.connection.execute(...)",
                "file_pattern": "src/core/state/*.py"
            }
        ]
    },
    "turn_limit": {
        "pattern": r"error_max_turns|turn limit|too many turns",
        "category": "claude_sdk",
        "common_causes": [
            "Analyzing too many stocks in single session",
            "Direct analysis call instead of queue-based batching",
            "Recursive optimization loops"
        ],
        "fixes": [
            {
                "description": "Use AI_ANALYSIS queue for batched processing",
                "example": "await task_service.create_task(QueueName.AI_ANALYSIS, TaskType.RECOMMENDATION_GENERATION, ...)",
                "file_pattern": "src/services/*.py"
            },
            {
                "description": "Reduce batch size in analyzer",
                "example": "batch_size = min(3, len(remaining_stocks))",
                "file_pattern": "src/services/portfolio_intelligence_analyzer.py"
            }
        ]
    },
    "import_error": {
        "pattern": r"ImportError|ModuleNotFoundError|cannot import",
        "category": "imports",
        "common_causes": [
            "Circular imports between modules",
            "Missing __init__.py in package",
            "Incorrect relative import path"
        ],
        "fixes": [
            {
                "description": "Move import inside function to break circular dependency",
                "example": "def func():\n    from module import thing",
                "file_pattern": "**/*.py"
            },
            {
                "description": "Use absolute imports from project root",
                "example": "from src.core.di import DependencyContainer",
                "file_pattern": "**/*.py"
            }
        ]
    },
    "attribute_error": {
        "pattern": r"AttributeError|has no attribute",
        "category": "type_safety",
        "common_causes": [
            "Missing null/None check before attribute access",
            "Incorrect response structure assumption",
            "API response format mismatch"
        ],
        "fixes": [
            {
                "description": "Add null safety check",
                "example": "if obj and hasattr(obj, 'attribute'):",
                "file_pattern": "**/*.py"
            },
            {
                "description": "Check API response structure matches frontend expectation",
                "example": "return {'analysis': analysis_data}  # Frontend expects nested",
                "file_pattern": "src/web/routes/*.py"
            }
        ]
    },
    "websocket_error": {
        "pattern": r"WebSocket.*closed|websocket.*failed|WS.*disconnect",
        "category": "websocket",
        "common_causes": [
            "Backend not running or health check failed",
            "Frontend trying to connect before backend ready",
            "CORS configuration issue"
        ],
        "fixes": [
            {
                "description": "Check backend health endpoint first",
                "example": "curl -m 3 http://localhost:8000/api/health",
                "file_pattern": "ui/src/**/*.ts"
            },
            {
                "description": "Add connection retry logic with exponential backoff",
                "example": "retries = 0; while retries < 3: try connect(); break; except: wait(2**retries)",
                "file_pattern": "ui/src/lib/websocket.ts"
            }
        ]
    },
    "rate_limit": {
        "pattern": r"rate.*limit|429|too many requests",
        "category": "api_limits",
        "common_causes": [
            "Too many API calls in short time",
            "Missing rate limit handling",
            "No exponential backoff on retries"
        ],
        "fixes": [
            {
                "description": "Add exponential backoff retry logic",
                "example": "await asyncio.sleep(2 ** attempt)",
                "file_pattern": "src/services/*.py"
            },
            {
                "description": "Implement request batching",
                "example": "batch requests into single API call where possible",
                "file_pattern": "src/services/*.py"
            }
        ]
    }
}


def suggest_fix(
    error_message: str,
    context_file: Optional[str] = None,
    include_examples: bool = True
) -> Dict[str, Any]:
    """Suggest fixes for errors based on known patterns.

    Args:
        error_message: The error message or stack trace
        context_file: File where error occurred (for targeted suggestions)
        include_examples: Include code examples in suggestions

    Returns:
        Structured fix suggestions with examples and file locations

    Token Efficiency:
        Returns focused fix suggestions (300-500 tokens) instead of
        reading multiple files to understand error (5k-10k tokens) = 95% reduction
    """

    project_root = Path(os.getenv('ROBO_TRADER_PROJECT_ROOT', os.getcwd()))

    results = {
        "error_message": error_message[:200],  # Truncate for display
        "matched_patterns": [],
        "suggested_fixes": [],
        "related_files": [],
        "tokens_estimate": 400
    }

    # Match error against known patterns
    for pattern_name, pattern_data in ERROR_PATTERNS.items():
        if re.search(pattern_data["pattern"], error_message, re.IGNORECASE):
            match_info = {
                "pattern_name": pattern_name,
                "category": pattern_data["category"],
                "common_causes": pattern_data["common_causes"]
            }
            results["matched_patterns"].append(match_info)

            # Add fix suggestions
            for fix in pattern_data["fixes"]:
                suggestion = {
                    "description": fix["description"],
                    "category": pattern_data["category"],
                    "file_pattern": fix["file_pattern"]
                }

                if include_examples:
                    suggestion["example"] = fix["example"]

                # Find related files matching pattern
                if context_file:
                    related = _find_related_files_for_fix(
                        context_file,
                        fix["file_pattern"],
                        project_root
                    )
                    suggestion["related_files"] = related[:3]  # Top 3 files

                results["suggested_fixes"].append(suggestion)

    # If no patterns matched, provide generic debugging steps
    if not results["matched_patterns"]:
        results["suggested_fixes"] = _get_generic_debugging_steps(error_message)
        results["note"] = "No specific pattern matched. Generic debugging steps provided."

    # Add architectural guidance
    results["architectural_guidance"] = _get_architectural_guidance(
        results["matched_patterns"]
    )

    return results


def _find_related_files_for_fix(
    context_file: str,
    file_pattern: str,
    project_root: Path
) -> List[str]:
    """Find files matching pattern that are related to context file."""

    related_files = []

    try:
        # Use git to find files that changed together
        result = subprocess.run(
            ["git", "log", "--format=%H", "--", context_file],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            commits = result.stdout.strip().split('\n')[:5]  # Last 5 commits

            # Find files changed in same commits
            co_changed = set()
            for commit in commits:
                if not commit:
                    continue

                result = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    for file in result.stdout.strip().split('\n'):
                        if file and _matches_pattern(file, file_pattern):
                            co_changed.add(file)

            related_files = list(co_changed)[:3]

    except Exception:
        pass  # Silently handle git errors

    return related_files


def _matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if file path matches glob-style pattern."""

    # Convert glob pattern to regex
    pattern_regex = pattern.replace("**", ".*").replace("*", "[^/]*")
    return bool(re.match(pattern_regex, file_path))


def _get_generic_debugging_steps(error_message: str) -> List[Dict[str, str]]:
    """Provide generic debugging steps when no pattern matches."""

    steps = [
        {
            "description": "Check server logs for full stack trace",
            "example": "tail -f logs/robo-trader.log | grep ERROR",
            "category": "debugging"
        },
        {
            "description": "Verify backend health endpoint",
            "example": "curl -m 3 http://localhost:8000/api/health",
            "category": "debugging"
        },
        {
            "description": "Check for recent code changes",
            "example": "git log --oneline -5",
            "category": "debugging"
        },
        {
            "description": "Review CLAUDE.md for architectural patterns",
            "example": "Read CLAUDE.md, src/CLAUDE.md for guidance",
            "category": "architecture"
        }
    ]

    # Add error-specific steps
    if "syntax" in error_message.lower():
        steps.insert(0, {
            "description": "Check for Python syntax errors",
            "example": "python -m py_compile <file>",
            "category": "syntax"
        })

    if "timeout" in error_message.lower():
        steps.insert(0, {
            "description": "Increase timeout values in config",
            "example": "Check src/core/sdk_helpers.py for timeout settings",
            "category": "performance"
        })

    return steps


def _get_architectural_guidance(matched_patterns: List[Dict]) -> List[str]:
    """Provide architectural guidance based on matched patterns."""

    guidance = []

    categories = {p["category"] for p in matched_patterns}

    if "database" in categories:
        guidance.append(
            "Database Access Pattern: Always use ConfigurationState locked methods "
            "instead of direct db.connection access to prevent locks"
        )
        guidance.append(
            "See CLAUDE.md section 'Database & State Management' for locking patterns"
        )

    if "claude_sdk" in categories:
        guidance.append(
            "Claude SDK Pattern: Use AI_ANALYSIS queue for batched processing "
            "to prevent turn limit exhaustion"
        )
        guidance.append(
            "See CLAUDE.md section 'Sequential Queue Architecture' for queue usage"
        )

    if "websocket" in categories:
        guidance.append(
            "WebSocket Pattern: Check backend health before establishing connection"
        )
        guidance.append(
            "See ui/src/CLAUDE.md for WebSocket integration patterns"
        )

    if not guidance:
        guidance.append(
            "Review CLAUDE.md files for architectural patterns and best practices"
        )

    return guidance


# Schema for MCP integration
def get_schema():
    """Return JSON schema for MCP tool registration."""
    return {
        "name": "suggest_fix",
        "description": "Suggest fixes for errors based on known patterns and architectural guidelines",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_message": {
                    "type": "string",
                    "description": "The error message or stack trace to analyze"
                },
                "context_file": {
                    "type": "string",
                    "description": "Optional file where error occurred for targeted suggestions"
                },
                "include_examples": {
                    "type": "boolean",
                    "description": "Include code examples in suggestions (default: true)"
                }
            },
            "required": ["error_message"]
        }
    }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        result = suggest_fix(sys.argv[1])
        print(json.dumps(result, indent=2))
