# MCP Tools Integration Guide

## Quick Reference: Problem → Solution

| Problem | Hook (Blocks) | MCP Tool | Skill |
|---------|---------------|----------|-------|
| Analyzing logs | grep-logs-to-mcp | analyze_logs | full-stack-debugger |
| Database locked | db-read-to-mcp | diagnose_database_locks | full-stack-debugger |
| Health checks | curl-health-to-mcp | check_system_health | full-stack-debugger |
| Queue monitoring | use-mcp-system-operations | queue_status | trade-execution |
| Portfolio query | db-read-to-mcp | query_portfolio | portfolio-analysis |
| Coordinator not ready | coordinator-debugging | coordinator_status | full-stack-debugger |
| Error pattern matching | N/A | suggest_fix | full-stack-debugger |
| File code reading | N/A | smart_file_read | full-stack-debugger |

## Common Workflows

### 1. Debugging Scheduler Failures
```
1. analyze_logs(patterns=["ERROR", "scheduler"], time_window="24h")
2. queue_status(queue_filter="AI_ANALYSIS", include_backlog_analysis=True)
3. coordinator_status(include_error_details=True)
4. diagnose_database_locks(time_window="24h", include_code_references=True)
5. suggest_fix(error_message="...", context_file="...")
```

### 2. Database Locked Errors
```
1. diagnose_database_locks(time_window="24h", suggest_fixes=True)
   → Shows code locations using direct connections
2. smart_file_read(file_path="src/path/file.py", context="targeted", search_term="sqlite3")
   → Read code with 85% token savings
3. suggest_fix(error_message="database is locked", context_file="...")
   → Get fix pattern: Use config_state.store_*() methods
```

### 3. Coordinator Not Ready Issues
```
1. coordinator_status(check_critical_only=True, include_error_details=True)
2. smart_file_read(file_path="src/core/coordinators/X.py", context="targeted", search_term="initialize")
3. find_related_files(reference="BroadcastCoordinator", relation_type="imports")
4. suggest_fix(error_message="coordinator not ready")
```

### 4. Portfolio Analysis Tasks
```
1. query_portfolio(aggregation_only=True, include_recommendations=True)
2. enhanced_differential_analysis(component="portfolio", since_timestamp="24h ago")
3. execute_analysis(analysis_type="aggregate", data={...}, parameters={...})
```

## Tool Selection Guide

**When to use what**:
- **Logs analysis**: `analyze_logs` (not tail/grep)
- **System health**: `check_system_health` (not curl loops)
- **Database queries**: `query_portfolio`, `diagnose_database_locks` (not sqlite3)
- **Queue monitoring**: `queue_status` (not API calls)
- **Code reading**: `smart_file_read` with context levels (not cat/grep)
- **Error fixes**: `suggest_fix` with error patterns
- **Change detection**: `enhanced_differential_analysis` (99% token savings)
