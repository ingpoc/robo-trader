# MCP Tools: Practical Debugging Examples

> Real-world examples showing how each robo-trader-dev MCP tool is used for debugging

## Table of Contents
1. [System Tools](#system-tools) - Health, queues, coordinators
2. [Log Analysis](#log-analysis) - Error patterns and debugging
3. [Database Queries](#database-queries) - Portfolio and configuration
4. [Optimization Tools](#optimization-tools) - Differential analysis, caching
5. [Performance Monitoring](#performance-monitoring) - Task metrics and execution

---

## System Tools

### Tool: `queue_status` - Monitor Background Scheduler

**When to Use**: You want to check if background scheduler tasks are executing properly.

**Example 1: Initial Health Check**
```python
# Call the tool
queue_status(use_cache=True)

# Response:
{
  "overall_status": "operational",
  "queue_summary": [
    {
      "queue": "PORTFOLIO_SYNC",
      "health": "healthy",
      "pending": 0,
      "active": 2,
      "completed_today": 47,
      "failed_today": 0,
      "avg_time_sec": 3.2
    },
    {
      "queue": "DATA_FETCHER",
      "health": "idle",
      "pending": 0,
      "active": 0,
      "completed_today": 23,
      "failed_today": 1,
      "avg_time_sec": 8.5
    },
    {
      "queue": "AI_ANALYSIS",
      "health": "healthy",
      "pending": 5,
      "active": 1,
      "completed_today": 12,
      "failed_today": 0,
      "avg_time_sec": 45.2
    }
  ],
  "system_stats": {
    "total_pending": 5,
    "total_active": 3,
    "total_completed_today": 82,
    "active_queues": 2
  },
  "insights": [
    "Portfolio sync queue processing efficiently (3.2s avg)",
    "AI analysis queue has 5 pending tasks (45s avg analysis)",
    "Data fetcher idle with 1 failure today"
  ],
  "recommendations": [
    "AI analysis queue appears healthy - 5 pending tasks processing normally",
    "Investigate DATA_FETCHER failure from earlier today"
  ]
}
```

**What You Learn**:
- ✅ 3 queues are running
- ✅ 82 tasks completed today
- ⚠️ 5 tasks pending in AI_ANALYSIS queue (normal for analysis)
- ⚠️ 1 failure in DATA_FETCHER (investigate)

**Next Steps**:
```python
# If there are failures, check logs
analyze_logs(patterns=["ERROR", "DATA_FETCHER"], time_window="24h")

# If AI_ANALYSIS queue is stalling:
diagnose_database_locks(time_window="1h")
```

---

### Tool: `coordinator_status` - Verify System Components

**When to Use**: System won't start, or you suspect an initialization failure.

**Example 1: Healthy System**
```python
coordinator_status(use_cache=False)  # Force fresh check

# Response:
{
  "overall_health": "healthy",
  "summary": {
    "total_coordinators": 8,
    "healthy": 8,
    "degraded": 0,
    "failed": 0
  },
  "coordinators": {
    "SessionCoordinator": {
      "initialized": true,
      "ready": true,
      "error": null,
      "last_checked": "2025-11-21T12:30:00Z"
    },
    "PortfolioAnalysisCoordinator": {
      "initialized": true,
      "ready": true,
      "error": null,
      "last_checked": "2025-11-21T12:30:00Z"
    },
    "TaskCoordinator": {
      "initialized": true,
      "ready": true,
      "error": null,
      "last_checked": "2025-11-21T12:30:00Z"
    },
    "QueueCoordinator": {
      "initialized": true,
      "ready": true,
      "error": null,
      "last_checked": "2025-11-21T12:30:00Z"
    }
    # ... 4 more coordinators
  },
  "insights": ["All coordinators initialized successfully"],
  "recommendations": ["System is ready for normal operation"],
  "critical_notes": []
}
```

**Example 2: Degraded System (Portfolio Analysis Failed)**
```python
coordinator_status(use_cache=False)

# Response:
{
  "overall_health": "degraded",
  "summary": {
    "total_coordinators": 8,
    "healthy": 7,
    "degraded": 1,
    "failed": 0
  },
  "coordinators": {
    # ... other coordinators healthy ...
    "PortfolioAnalysisCoordinator": {
      "initialized": true,
      "ready": false,
      "error": "Failed to initialize state_manager dependency",
      "last_checked": "2025-11-21T12:30:00Z"
    }
  },
  "degraded_coordinators": ["PortfolioAnalysisCoordinator"],
  "critical_notes": [
    "CRITICAL: portfolio_analysis_coordinator degraded - background analysis disabled"
  ],
  "insights": ["Portfolio analysis coordinator failed during initialization"],
  "recommendations": [
    "Check logs for state_manager initialization error",
    "Verify database connection is working",
    "Restart backend server to retry initialization"
  ]
}
```

**What You Learn**:
- ✅ All 8 coordinators started
- ❌ PortfolioAnalysisCoordinator ready=false
- 🔍 Error: "Failed to initialize state_manager dependency"

**Next Steps**:
```python
# Check what went wrong during startup
analyze_logs(patterns=["ERROR", "state_manager", "initialization"], time_window="5m")

# Verify database is accessible
verify_configuration_integrity(checks=["database_paths"])

# Restart backend and check again
coordinator_status(use_cache=False)
```

---

### Tool: `check_system_health` - Overall System Status

**When to Use**: Quick health check of all system components.

**Example 1: All Systems Operational**
```python
check_system_health()

# Response:
{
  "status": "healthy",
  "timestamp": "2025-11-21T12:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "message": "SQLite database connected",
      "size_mb": 2.4,
      "tables": 18
    },
    "queues": {
      "status": "healthy",
      "message": "All 3 queues operational",
      "details": {
        "portfolio_sync": "healthy",
        "data_fetcher": "idle",
        "ai_analysis": "healthy"
      }
    },
    "api_endpoints": {
      "status": "healthy",
      "message": "All endpoints responding",
      "endpoints": 45,
      "latency_ms": 12
    },
    "disk_space": {
      "status": "healthy",
      "available_gb": 150,
      "logs_gb": 0.5
    },
    "backup_status": {
      "status": "healthy",
      "latest_backup": "2025-11-21T06:59:00Z",
      "backups_available": 7
    }
  },
  "insights": ["All systems operating normally"],
  "recommendations": ["Continue normal operation"],
  "initialization_errors": []
}
```

**Example 2: Database Issues**
```python
check_system_health()

# Response:
{
  "status": "degraded",
  "components": {
    "database": {
      "status": "warning",
      "message": "Database file age: 45 minutes",
      "last_modified": "2025-11-21T11:45:00Z",
      "age_minutes": 45
    },
    # ... other components healthy ...
  },
  "insights": ["Database has not been updated in 45 minutes"],
  "recommendations": [
    "Check if backend scheduler is running",
    "Verify no long-running database locks"
  ]
}
```

---

## Log Analysis

### Tool: `analyze_logs` - Find Error Patterns

**When to Use**: Error occurred, need to understand it or find related issues.

**Example 1: Find All DATABASE LOCK Errors**
```python
analyze_logs(
  patterns=["database is locked", "LOCK"],
  time_window="24h",
  max_examples=5
)

# Response:
{
  "success": true,
  "time_window": "24h",
  "patterns_found": [
    {
      "pattern": "database is locked",
      "count": 12,
      "severity": "high",
      "frequency": "every ~2 hours",
      "examples": [
        {
          "timestamp": "2025-11-21T08:30:00Z",
          "log": "[ERROR] database is locked - ConfigurationState.get_analysis_history()",
          "context": "During portfolio analysis - 30 second analysis took 40s"
        },
        {
          "timestamp": "2025-11-21T06:45:00Z",
          "log": "[ERROR] database is locked - direct db.connection.execute()",
          "context": "From src/web/routes/monitoring.py:450"
        }
      ],
      "likely_cause": "Direct database access in web endpoint (bypasses ConfigurationState lock)",
      "architecture_violation": "Web endpoints should use ConfigurationState.get_*() locked methods"
    }
  ],
  "insights": [
    "12 'database is locked' errors in last 24h",
    "Pattern 1 (blocking analysis): Uses ConfigurationState correctly",
    "Pattern 2 (web endpoint): Bypasses ConfigurationState locking"
  ],
  "recommendations": [
    "Update monitoring.py:450 to use ConfigurationState.get_analysis_history()",
    "Review all web endpoint database access patterns"
  ],
  "token_efficiency": "98% reduction - processed 5,000 lines → actionable patterns"
}
```

**What You Learn**:
- 12 errors occurred (vs looking through 5,000+ log lines manually)
- Error has 2 patterns (architecture violation + blocking operations)
- Specific files to fix (monitoring.py:450)

**Next Steps**:
```python
# Get the specific file to fix
smart_file_read(
  file_path="src/web/routes/monitoring.py",
  context="targeted",
  search_term="database"
)

# Get fix suggestions
suggest_fix(error_message="database is locked", context_file="src/web/routes/monitoring.py")
```

**Example 2: Find TIMEOUT Errors**
```python
analyze_logs(
  patterns=["timeout", "Timeout", "exceeded"],
  time_window="1h",
  max_examples=3
)

# Response shows if Claude SDK timeout, API timeout, or database timeout
# and gives recommendations for each
```

---

## Database Queries

### Tool: `query_portfolio` - Check Portfolio Analysis Status

**When to Use**: Need to understand which stocks have been analyzed and which are stale.

**Example 1: Find Stocks Needing Analysis**
```python
query_portfolio(
  filters=["stale_analysis"],  # Only unanalyzed or old analysis
  aggregation_only=True,        # Return summary, not raw records
  limit=20
)

# Response:
{
  "success": true,
  "query_filters": ["stale_analysis"],
  "summary": {
    "total_holdings": 81,
    "matching_filters": 12,
    "analyzed_stocks": 69,
    "stale_stocks": 12,
    "avg_analysis_age_days": 5.3,
    "oldest_analysis_days": 14
  },
  "stale_stocks": [
    {"symbol": "AAPL", "shares": 150, "last_analyzed": "14 days ago", "analysis_age_days": 14},
    {"symbol": "MSFT", "shares": 75, "last_analyzed": "10 days ago", "analysis_age_days": 10},
    {"symbol": "NVDA", "shares": 50, "last_analyzed": "9 days ago", "analysis_age_days": 9},
    # ... 9 more stocks
  ],
  "insights": [
    "12 stocks (14.8%) have stale analysis (>7 days old)",
    "AAPL analysis is 14 days old - highest priority",
    "69 stocks analyzed recently"
  ],
  "recommendations": [
    "Queue 12 stale stocks for analysis refresh",
    "Prioritize AAPL, MSFT, NVDA (oldest analysis)"
  ],
  "token_efficiency": "98% reduction - portfolio with 81 holdings → 12 recommendation items"
}
```

**What You Learn**:
- 12 stocks need re-analysis
- AAPL is 14 days old (priority)
- 69 stocks already analyzed

**Use Case Example**:
In your background scheduler, you can use this to trigger analysis:
```python
# Get stale stocks
stale_stocks = query_portfolio(filters=["stale_analysis"])

# Queue them for analysis
for stock in stale_stocks["stale_stocks"]:
  await task_service.create_task(
    queue_name=QueueName.AI_ANALYSIS,
    task_type=TaskType.RECOMMENDATION_GENERATION,
    payload={"agent_name": "scan", "symbols": [stock["symbol"]]},
    priority=7
  )
```

---

### Tool: `verify_configuration_integrity` - Validate System Setup

**When to Use**: Before deployment, or if system behaves unexpectedly.

**Example 1: Successful Verification**
```python
verify_configuration_integrity(
  checks=["database_paths", "api_endpoints", "queue_settings", "security_settings"],
  include_suggestions=True
)

# Response:
{
  "success": true,
  "checks_performed": 4,
  "issues_found": 0,
  "all_checks_passed": true,
  "check_results": {
    "database_paths": {
      "passed": true,
      "message": "Database path valid: /robo-trader/state/robo_trader.db",
      "database_exists": true,
      "is_writable": true
    },
    "api_endpoints": {
      "passed": true,
      "message": "All 45 API endpoints responding",
      "latency_ms": 12,
      "endpoints_checked": 45
    },
    "queue_settings": {
      "passed": true,
      "message": "3 queues configured correctly",
      "queue_count": 3,
      "concurrency": "optimal"
    },
    "security_settings": {
      "passed": true,
      "message": "Claude SDK authentication configured",
      "auth_method": "oauth_token",
      "token_valid": true
    }
  },
  "insights": ["All configuration checks passed - system is ready"],
  "recommendations": ["Proceed with deployment"]
}
```

**Example 2: Configuration Issues**
```python
verify_configuration_integrity()

# Response:
{
  "success": false,
  "checks_performed": 4,
  "issues_found": 2,
  "check_results": {
    "database_paths": {
      "passed": false,
      "message": "Database backup directory not writable",
      "issue": "/robo-trader/state/backups/ permission denied",
      "suggestion": "Run: chmod 755 /robo-trader/state/backups/"
    },
    "api_endpoints": {
      "passed": false,
      "message": "Backend API not responding",
      "issue": "Connection refused on http://localhost:8000",
      "suggestion": "Start backend server: python -m src.main --command web"
    }
    # ... other checks
  },
  "recommendations": [
    "Fix directory permissions",
    "Start backend server",
    "Run verification again"
  ]
}
```

---

## Optimization Tools

### Tool: `differential_analysis` - Show Only Changes

**When to Use**: You want to understand what changed since last check (99% token reduction).

**Example 1: Portfolio Changes in Last 24 Hours**
```python
differential_analysis(
  component="portfolio",
  since_timestamp="24h ago"
)

# Response:
{
  "success": true,
  "analysis_type": "differential",
  "time_window": "24h",
  "summary": {
    "items_added": 2,
    "items_removed": 0,
    "items_modified": 5,
    "total_changes": 7
  },
  "changes": {
    "added": [
      {"symbol": "NVDA", "shares": 100, "added_at": "2025-11-21T10:30:00Z"},
      {"symbol": "TSLA", "shares": 50, "added_at": "2025-11-21T08:00:00Z"}
    ],
    "removed": [],
    "modified": [
      {
        "symbol": "AAPL",
        "changes": {
          "shares": {"old": 100, "new": 150, "change": "+50"},
          "last_analysis": {"old": "2025-11-19", "new": "2025-11-21", "change": "updated"}
        }
      },
      # ... 4 more modified stocks
    ]
  },
  "insights": [
    "2 new positions added (NVDA, TSLA)",
    "5 existing positions modified (share count or analysis)",
    "No positions removed"
  ],
  "token_efficiency": "99% reduction - showing only deltas, not full portfolio"
}
```

**Use Case**: Monitor portfolio mutations without reading full database.

---

### Tool: `smart_file_read` - Read with Progressive Context

**When to Use**: Need to understand a file but don't want to load it all (87-95% token reduction).

**Example 1: Summary Mode - Get File Structure**
```python
smart_file_read(
  file_path="src/services/portfolio_intelligence_analyzer.py",
  context="summary"  # Just imports, classes, methods
)

# Response: ~150 tokens
{
  "file_path": "src/services/portfolio_intelligence_analyzer.py",
  "mode": "summary",
  "total_lines": 850,
  "file_type": ".py",
  "imports": [
    "asyncio", "json", "sqlite3", "Claude SDK from src.core.claude_sdk_client_manager",
    "BroadcastCoordinator from src.core.coordinators"
  ],
  "classes": [
    "PortfolioIntelligenceAnalyzer (main service)"
  ],
  "class_methods": [
    "analyze_portfolio_intelligence() - main analysis method",
    "_broadcast_analysis_status() - broadcasts to UI",
    "get_active_analysis_status() - class method for tracking"
  ],
  "key_patterns": [
    "Uses Claude SDK for analysis",
    "Tracks active analysis tasks in class variable",
    "Broadcasts status updates via BroadcastCoordinator"
  ],
  "tokens_estimate": 150
}
```

**What You Learn** (without reading 850 lines):
- Main classes and methods
- Key dependencies
- Architecture patterns

**Example 2: Targeted Mode - Focus on Specific Term**
```python
smart_file_read(
  file_path="src/services/portfolio_intelligence_analyzer.py",
  context="targeted",
  search_term="_broadcast_analysis_status"
)

# Response: ~800 tokens - shows the method and surrounding code
{
  "mode": "targeted",
  "search_term": "_broadcast_analysis_status",
  "matches": [
    {
      "line": 762,
      "method": "_broadcast_analysis_status",
      "signature": "async def _broadcast_analysis_status(self, status: str, message: str)",
      "key_code": [
        "if status == 'analyzing':",
        "  broadcast_coordinator.broadcast_claude_status_update(...)",
        "if status == 'idle':",
        "  broadcast_coordinator.broadcast_claude_status_update(...)"
      ],
      "purpose": "Broadcasts Claude analysis status to UI"
    }
  ],
  "recommendations": [
    "Method broadcasts both 'analyzing' and 'idle' statuses",
    "Uses BroadcastCoordinator for WebSocket updates"
  ],
  "tokens_estimate": 800
}
```

---

### Tool: `suggest_fix` - Get Fix Recommendations

**When to Use**: You have an error and want fix suggestions based on known patterns.

**Example 1: Database Lock Error**
```python
suggest_fix(
  error_message="database is locked",
  context_file="src/web/routes/monitoring.py"
)

# Response:
{
  "success": true,
  "error": "database is locked",
  "context_file": "src/web/routes/monitoring.py",
  "confidence": 0.95,
  "fixes": [
    {
      "fix_number": 1,
      "title": "Use ConfigurationState locked methods instead of direct access",
      "description": "Database lock errors often come from bypassing ConfigurationState locking",
      "code_example": [
        "# ❌ WRONG - causes database lock",
        "config_data = await config_state.db.connection.execute(...)",
        "",
        "# ✅ CORRECT - uses built-in locking",
        "config_data = await config_state.get_analysis_history()"
      ],
      "applies_to": ["web endpoints", "routes"],
      "success_rate": 0.98,
      "files_to_update": ["src/web/routes/monitoring.py:450"]
    },
    {
      "fix_number": 2,
      "title": "Add timeout to database operations",
      "description": "Long-running operations without timeout can block other operations",
      "code_example": [
        "# Add timeout for database calls",
        "try:",
        "  result = await asyncio.wait_for(db_call(), timeout=5.0)",
        "except asyncio.TimeoutError:",
        "  handle_timeout()"
      ],
      "applies_to": ["long-running analysis"],
      "success_rate": 0.85
    }
  ],
  "recommendations": [
    "Primary fix: Use ConfigurationState.get_*() methods (98% success rate)",
    "Secondary: Add timeout protection to long operations"
  ],
  "token_efficiency": "95% reduction - instant pattern matching vs manual code review"
}
```

---

## Performance Monitoring

### Tool: `task_execution_metrics` - 24-Hour Task Analysis

**When to Use**: Monitor if background scheduler is healthy and productive.

**Example 1: Healthy System**
```python
task_execution_metrics(
  time_window_hours=24,
  include_trends=True
)

# Response:
{
  "success": true,
  "summary": {
    "total_tasks_24h": 156,
    "success_rate_pct": 91.7,
    "completed_tasks": 143,
    "failed_tasks": 13,
    "unique_stocks_analyzed": 32,
    "current_backlog": 5,
    "active_tasks": 2
  },
  "top_task_types": [
    {
      "task_type": "RECOMMENDATION_GENERATION",
      "count": 45,
      "avg_time_ms": 4521,
      "success_rate": 100
    },
    {
      "task_type": "NEWS_ANALYSIS",
      "count": 38,
      "avg_time_ms": 3200,
      "success_rate": 89.5
    },
    {
      "task_type": "DATA_FETCH",
      "count": 73,
      "avg_time_ms": 2100,
      "success_rate": 90
    }
  ],
  "error_trends": [
    {"hour": "14", "failures": 3, "type": "TIMEOUT"},
    {"hour": "18", "failures": 2, "type": "API_ERROR"},
    {"hour": "02", "failures": 8, "type": "NETWORK_ERROR"}
  ],
  "insights": [
    "High execution volume: 156 tasks in 24 hours",
    "Excellent success rate: 91.7% (143/156 tasks)",
    "Good portfolio coverage: 32 unique stocks analyzed",
    "Peak failures at 02:00 UTC (night backups running)"
  ],
  "recommendations": [
    "System health excellent - continue current schedule",
    "Night failures (02:00) likely due to backup operations (acceptable)",
    "Monitor TIMEOUT errors at 14:00 - may need longer timeout"
  ],
  "token_efficiency": "95.5% reduction - 24h of task history → actionable metrics"
}
```

**What You Learn**:
- 156 tasks executed (healthy volume)
- 91.7% success rate (excellent)
- 32 stocks analyzed (good coverage)
- Peak failure times identified

**Example 2: Problem Detection**
```python
task_execution_metrics(time_window_hours=24, include_trends=True)

# Unhealthy Response:
{
  "success": true,
  "summary": {
    "total_tasks_24h": 12,       # ⚠️ Very low - only 12 tasks
    "success_rate_pct": 58.3,    # ⚠️ Poor - 58% success rate
    "completed_tasks": 7,
    "failed_tasks": 5,
    "unique_stocks_analyzed": 3, # ⚠️ Very low - only 3 stocks
    "current_backlog": 127,      # ⚠️ Critical - 127 pending tasks!
    "active_tasks": 0            # ⚠️ No tasks running
  },
  "error_trends": [
    {"hour": "every_hour", "failures": 5, "type": "TASK_TIMEOUT"}
  ],
  "insights": [
    "CRITICAL: Only 12 tasks completed in 24h (should be 100+)",
    "CRITICAL: 127 tasks in backlog (processing stalled)",
    "CRITICAL: 0 active tasks (queue stopped?)",
    "Low success rate: 58.3% (5/8 tasks failing)"
  ],
  "recommendations": [
    "Check TaskCoordinator - appears to be stalled",
    "Call coordinator_status() to verify task_coordinator health",
    "Check queue_status() - AI_ANALYSIS queue may be stuck",
    "Analyze error logs - all 5 failures are TASK_TIMEOUT"
  ]
}
```

**Next Steps**:
```python
# If metrics show problems, follow this workflow:
1. coordinator_status(use_cache=False)  # Check coordinator health
2. queue_status(use_cache=False)         # Check queue status
3. analyze_logs(patterns=["TIMEOUT"], time_window="1h")  # Find error details
4. diagnose_database_locks()             # Check for lock contention
```

---

## Real-World Debugging Workflow

### Scenario: "Background scheduler stopped working"

**Step 1: Get Quick Health Check** (~1,200 tokens)
```python
coordinator_status()
# ✅ All coordinators healthy

queue_status()
# ⚠️ AI_ANALYSIS queue: 127 pending, 0 active, health='stalled'
```

**Step 2: Get Historical Context** (~1,800 tokens)
```python
task_execution_metrics(time_window_hours=24)
# Shows: Tasks were working yesterday (45/day), now 0 in last 2 hours
```

**Step 3: Find Root Cause** (~300 tokens)
```python
analyze_logs(patterns=["ERROR", "AI_ANALYSIS"], time_window="2h", max_examples=3)
# Shows: "database is locked" errors starting 2 hours ago
```

**Step 4: Get Fix Recommendation** (~800 tokens)
```python
suggest_fix(error_message="database is locked")
# Recommends: Use ConfigurationState.get_*() instead of direct db access
```

**Step 5: Identify File to Fix** (~150 tokens)
```python
smart_file_read(file_path="src/web/routes/analysis.py", context="summary")
# Shows: analyze_route() uses direct db.connection.execute()
```

**Total Tokens**: ~4,250 tokens
**Traditional Debugging**: 50,000+ tokens
**Token Savings**: 91%

---

## Summary

Each tool serves a specific debugging purpose:

| Tool | Token Reduction | Use For |
|------|-----------------|---------|
| `queue_status` | 96% | Monitor scheduler execution |
| `coordinator_status` | 96.8% | Verify system initialization |
| `task_execution_metrics` | 95.5% | Check task success rates |
| `analyze_logs` | 98% | Find error patterns |
| `query_portfolio` | 98% | Check analysis status |
| `smart_file_read` | 87-95% | Understand code (progressive) |
| `suggest_fix` | 95% | Get fix recommendations |
| `differential_analysis` | 99% | Track only changes |

**Typical Debugging Session**: 4-5 tool calls = 4,000-5,000 tokens (vs 40,000+ traditional)
