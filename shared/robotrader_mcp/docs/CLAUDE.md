# Robo-Trader MCP Server

Progressive disclosure pattern for 15+ monitoring tools with 92-97% token reduction.

## Quick Start
```bash
# Discovery (optional but recommended)
CallTool("list_categories", {})      # 5 categories
CallTool("load_category", {"category": "system"})

# Direct execution (also works)
CallTool("queue_status", {})         # Real-time queue health
CallTool("coordinator_status", {})   # System initialization status
CallTool("task_execution_metrics", {})  # 24h task statistics
```

## Tool Categories
| Category | Tools | Token Reduction |
|----------|-------|-----------------|
| logs | analyze_logs | 98%+ |
| database | query_portfolio, verify_configuration_integrity | 98%+ |
| system | check_system_health, diagnose_database_locks, queue_status, coordinator_status | 96-97%+ |
| optimization | differential_analysis, smart_cache, context_aware_summarize | 99%+ |
| performance | real_time_performance_monitor, task_execution_metrics | 95-97%+ |

## New Monitoring Tools

### queue_status
Real-time queue health (60s cache). Returns: status, pending/active counts, insights, recommendations.

### coordinator_status
Initialization verification (45s cache). Returns: healthy/degraded/critical status, coordinator details, critical notes.

### task_execution_metrics
24-hour statistics (120s cache). Returns: task counts, success rates, task types, error trends.

## Architecture
```
TypeScript Server (server.ts)
    ↓
executeTool(toolName, args)
    ↓
execSync(python3 tools/{toolName}.py '{args}')
    ↓
Python Tool: Check cache (TTL) → Fetch (API/DB) → Transform → Cache → Return
```

## Caching
- Coordinator: 45s TTL (rarely changes)
- Queues: 60s TTL (frequently updated)
- Metrics: 120s TTL (hourly updates)
- Location: `~/.robo_trader_mcp_cache/`

## Rules
| Rule | Requirement |
|------|-------------|
| Timeout | <30s per tool (SRT constraint) |
| Network | Localhost only (http://localhost:8000) |
| Filesystem | Cache only (~/.robo_trader_mcp_cache/) |
| Error handling | Graceful degradation with meaningful suggestions |
| Validation | Zod schemas for all inputs |
