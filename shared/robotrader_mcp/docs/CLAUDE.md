# Robo-Trader MCP Server Documentation

> **Last Updated**: 2025-11-07 | **Status**: Production Ready | **Tier**: Reference + How-To
> **Version**: 1.0.0 | **Architecture**: Progressive Disclosure with SRT Security

## Quick Start

### Using the MCP Server

**Recommended: Progressive Discovery Pattern**

All 15 tools are immediately callable, but discovery helps agents find them efficiently:

```bash
# Step 1: List available tool categories (efficient discovery)
CallTool("list_categories", {})
# Returns 5 categories: logs, database, system, optimization, performance

# Step 2: Load specific category to see tools (progressive disclosure)
CallTool("load_category", {"category": "system"})
# Returns 4 system tools: check_system_health, diagnose_database_locks, queue_status, coordinator_status

# Step 3: Execute any tool immediately (no blocking)
CallTool("queue_status", {})               # ✅ Works
CallTool("coordinator_status", {})         # ✅ Works
CallTool("task_execution_metrics", {})     # ✅ Works
```

**Direct Tool Calls (Also Works)**

You can skip discovery and call tools directly:
```bash
CallTool("queue_status", {})  # ✅ Works immediately (no discovery needed)
CallTool("analyze_logs", {"patterns": ["ERROR"]})  # ✅ Works immediately
```

**Alternative: Direct Python Tool Calls**

If you need to bypass MCP entirely:
```bash
python3 shared/robotrader_mcp/tools/queue_status.py '{}'
python3 shared/robotrader_mcp/tools/coordinator_status.py '{}'
python3 shared/robotrader_mcp/tools/task_execution_metrics.py '{}'
```

Note: Direct Python calls bypass the MCP server and do NOT require discovery.

### Tool Locations

- **TypeScript Server**: `src/server.ts` (main MCP server logic)
- **Zod Schemas**: `src/schemas.ts` (input validation)
- **Python Tools**: `tools/*.py` (actual tool implementations)
- **Build Output**: `dist/` (compiled server)

---

## Architecture Overview

### Progressive Disclosure Pattern (Anthropic Approach)

This MCP server implements **progressive disclosure for efficient discovery** (following Anthropic's approach):

**How It Works**:
- All 15 tools are immediately callable via `CallTool()`
- No tool blocking or session state tracking
- Discovery tools (`list_categories`, `load_category`) help agents find tools efficiently
- Progressive disclosure is **optional but recommended** for efficiency

**Progressive Discovery Flow** (Recommended):
```
Step 1: list_categories → See 5 categories (~200 tokens)
          ↓
Step 2: load_category("system") → See tools in category (~300 tokens)
          ↓
Step 3: queue_status({}) → Call tool immediately (~1,200 tokens)
          ↓
Total: ~1,700 tokens for discovery + execution
```

**Direct Execution** (Also Valid):
```
queue_status({}) → Call tool directly (~1,200 tokens)
(Skip discovery if you know what tool you need)
```

**Token Efficiency Comparison**:
- Traditional MCP: All 15 tool definitions exposed upfront = 20,000+ tokens
- This MCP (with discovery): Category-based loading = 1,700-2,000 tokens
- This MCP (direct): Skip discovery = 1,200 tokens per tool
- **Reduction: 92-97%** token savings from progressive disclosure

### Tool Categories

| Category | Tools | Use Cases | Token Reduction |
|----------|-------|-----------|-----------------|
| **logs** | analyze_logs | Error analysis, debugging | 98%+ |
| **database** | query_portfolio, verify_configuration_integrity | Portfolio analysis, config validation | 98%+ |
| **system** | check_system_health, diagnose_database_locks, **queue_status**, **coordinator_status** | Health monitoring, lock diagnosis, queue monitoring | 96-97%+ |
| **optimization** | differential_analysis, smart_cache, context_aware_summarize | Token optimization, caching, differential updates | 99%+ |
| **performance** | real_time_performance_monitor, **task_execution_metrics** | Performance monitoring, task metrics | 95-97%+ |

---

## New Monitoring Tools (Phase 2 Enhancement)

### 1. queue_status

**Purpose**: Real-time queue health monitoring with 96% token reduction

**Endpoint**: `/api/queues/status` (proxied from backend)

**Cache Strategy**: 60-second TTL (queues change frequently)

**Input Schema**:
```typescript
QueueStatusInput = {
  use_cache?: boolean    // Use cached data (60s TTL)
  include_details?: boolean  // Include detailed queue information
}
```

**Output Format**:
```json
{
  "success": true,
  "overall_status": "operational|degraded|offline",
  "queue_summary": [
    {
      "queue": "portfolio_sync",
      "health": "healthy|backlog|stalled|idle",
      "pending": 5,
      "active": 2,
      "completed_today": 47,
      "failed_today": 0,
      "avg_time_sec": 3.2
    }
  ],
  "system_stats": {
    "total_pending": 5,
    "total_active": 2,
    "total_completed_today": 47,
    "active_queues": 2
  },
  "insights": [
    "Portfolio sync queue processing efficiently"
  ],
  "recommendations": [
    "Continue monitoring for backlog accumulation"
  ],
  "token_efficiency": {
    "compression_ratio": "96%+",
    "note": "Full queue data aggregated into actionable insights"
  },
  "data_source": "api"
}
```

**Health Determination Logic**:
- `healthy`: Active tasks with normal processing
- `backlog`: >50 pending tasks
- `stalled`: >0 pending + no activity for 30+ minutes
- `idle`: No pending or active tasks
- `active`: 0 active but pending tasks exist

**Use Cases**:
- Monitor queue execution status in real-time
- Detect queue backlog or stalling
- Get system-wide task statistics
- Identify bottlenecks in task processing

---

### 2. coordinator_status

**Purpose**: Verify coordinator initialization and detect silent failures (96.8% token reduction)

**Endpoint**: `/api/coordinators/status` (NEW backend endpoint)

**Cache Strategy**: 45-second TTL (coordinator state rarely changes post-init)

**Input Schema**:
```typescript
CoordinatorStatusInput = {
  use_cache?: boolean      // Use cached data (45s TTL)
  check_critical_only?: boolean  // Check only critical coordinators
}
```

**Output Format**:
```json
{
  "success": true,
  "overall_health": "healthy|degraded|critical",
  "summary": {
    "total_coordinators": 8,
    "healthy": 7,
    "degraded": 1,
    "failed": 0
  },
  "coordinators": {
    "portfolio_analysis_coordinator": {
      "initialized": true,
      "ready": true,
      "error": null,
      "last_checked": "2025-11-07T05:11:39.790516+00:00"
    }
  },
  "failed_coordinators": null,
  "degraded_coordinators": ["portfolio_analysis_coordinator"],
  "insights": [
    "All coordinators initialized successfully"
  ],
  "recommendations": [
    "System is ready for normal operation"
  ],
  "critical_notes": [
    "CRITICAL: portfolio_analysis_coordinator degraded - background analysis disabled"
  ],
  "token_efficiency": {
    "compression_ratio": "96.8%+",
    "note": "Coordinator details aggregated into health summary"
  },
  "data_source": "api"
}
```

**Critical Coordinators Tracked**:
- `portfolio_analysis_coordinator` - Portfolio stock analysis
- `task_coordinator` - Background task coordination
- `queue_coordinator` - Queue management

**Use Cases**:
- Verify system initialization completed successfully
- Detect silent initialization failures
- Monitor critical coordinator health
- Troubleshoot background component issues
- Validate deployment readiness

---

### 3. task_execution_metrics

**Purpose**: Aggregate 24-hour task execution statistics (95.5% token reduction)

**Data Sources**:
- Database: `scheduler_tasks` table (historical data)
- API: `/api/queues/status` (real-time backlog)

**Cache Strategy**: 120-second TTL (historical data changes slowly)

**Input Schema**:
```typescript
TaskExecutionMetricsInput = {
  use_cache?: boolean  // Use cached data (120s TTL)
  time_window_hours?: number  // Time window for analysis (default 24)
  include_trends?: boolean  // Include error trend analysis
}
```

**Output Format**:
```json
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
      "avg_time_ms": 4521,
      "count": 45
    },
    {
      "task_type": "NEWS_ANALYSIS",
      "avg_time_ms": 3200,
      "count": 38
    }
  ],
  "error_trends": [
    {
      "hour": "14",
      "failures": 3
    }
  ],
  "insights": [
    "High processing volume: 156 tasks in 24h",
    "Excellent task success rate: 91.7%",
    "Broad portfolio coverage: 32 stocks analyzed"
  ],
  "recommendations": [
    "Task execution appears healthy - continue monitoring"
  ],
  "token_efficiency": {
    "compression_ratio": "95.5%+",
    "note": "24h of task data aggregated into actionable metrics"
  },
  "data_source": "hybrid"
}
```

**Database Queries Used**:
- Total tasks (24h): Count from `scheduler_tasks`
- Status breakdown: Group by status and count
- Top task types: Group by task_type, average execution time
- Error trends: Group by hour, count failures
- Portfolio coverage: Distinct symbols from `analysis_history`

**Use Cases**:
- Monitor task processing health and efficiency
- Track success rates and failure patterns
- Identify peak processing times
- Measure portfolio coverage
- Detect processing bottlenecks
- Optimize queue concurrency settings

---

## Tool Integration Points

### Backend API Endpoints (NEW)

**File**: `/src/web/routes/coordinators.py` (NEW)

**Endpoint**: `GET /api/coordinators/status`
- Returns initialization status of all coordinators
- Rate limited: 30/minute (configurable)
- Monitors critical coordinators for failures
- Helps detect silent initialization failures

**Usage**:
```python
response = requests.get("http://localhost:8000/api/coordinators/status")
coordinator_data = response.json()
```

### Python Tool Implementations

**Cache Directory**: `~/.robo_trader_mcp_cache/`
- `coordinator_status.json` (45s TTL)
- `queue_status.json` (60s TTL)
- `task_execution_metrics.json` (120s TTL)

**Database Path**: Environment variable `ROBO_TRADER_DB`
- Default: `./state/robo_trader.db`
- Falls back to API when database unavailable

### TypeScript Integration

**Categories Updated**:
```typescript
"system": {
  tools: ["check_system_health", "diagnose_database_locks", "queue_status", "coordinator_status"],
  token_efficiency: "96-97%+"
}

"performance": {
  tools: ["real_time_performance_monitor", "task_execution_metrics"],
  token_efficiency: "95-97%+"
}
```

**Token Estimation** (for UI feedback):
- queue_status: Traditional 30,000 tokens → MCP 1,200 tokens (96% reduction)
- coordinator_status: Traditional 25,000 tokens → MCP 800 tokens (96.8% reduction)
- task_execution_metrics: Traditional 40,000 tokens → MCP 1,800 tokens (95.5% reduction)

---

## Error Handling & Resilience

### Graceful Degradation

All tools implement fallback strategies:

**Coordinator Status**:
- API timeout → Use cache if available
- No cache → Return generic "API unreachable" error
- Recommendations guide troubleshooting

**Queue Status**:
- API unreachable → Suggest checking backend
- Connection timeout → Recommend verifying network
- Invalid response → Log and return standard error

**Task Metrics**:
- Database not found → Suggest ensuring backend is running
- No scheduler_tasks table → Graceful error with helpful message
- API timeout → Fall back to database-only metrics

### Error Response Format

```json
{
  "success": false,
  "error": "Failed to fetch data from API",
  "suggestion": "Check backend server health or network connectivity",
  "execution_time_ms": 5023,
  "token_efficiency": {
    "error": "Execution failed - token efficiency not measured"
  }
}
```

---

## Security & Sandbox Compliance

### Anthropic Sandbox Runtime (SRT) Constraints

All tools comply with SRT security:

| Constraint | Value | Status |
|-----------|-------|--------|
| Execution timeout | 30 seconds | ✅ All tools complete in <5s |
| Memory limit | 256 MB | ✅ No large data structures |
| Filesystem | Read-only (cache only) | ✅ Write only to `~/.robo_trader_mcp_cache/` |
| Network | Localhost only | ✅ Connect to http://localhost:8000 |

**Implementation Details**:
- No external API calls (only localhost:8000)
- Cache files stored in user home directory
- Database read-only access (no writes)
- All operations complete well under timeout

---

## Performance Characteristics

### Cache Behavior

**Cache Hit Rates** (Expected):
- Coordinator status: 90%+ hit rate (rarely changes)
- Queue status: 70-80% hit rate (frequently updated)
- Task metrics: 60-70% hit rate (hourly updates)

**Cache Invalidation**:
- TTL-based expiration (45s, 60s, 120s)
- Manual cache bypass via `use_cache=false`
- Old files automatically cleaned up

### Execution Times

| Tool | Typical Time | Max Time | Data Source |
|------|--------------|----------|-------------|
| coordinator_status | 200-400ms | 800ms | API + cache |
| queue_status | 300-600ms | 1200ms | API + cache |
| task_execution_metrics | 400-800ms | 2000ms | Database + API + cache |

---

## Usage Patterns

### Monitoring Dashboard

Refresh coordinator and queue status every 30-45 seconds:

```typescript
// Check coordinator health
coordinator_status(use_cache=true)  // Returns cached if <45s old

// Check queue status
queue_status(use_cache=true)  // Returns cached if <60s old

// Get task metrics every 2-3 minutes
task_execution_metrics(use_cache=true)  // Returns cached if <120s old
```

### Troubleshooting Flow

**Problem**: "Tasks not executing"

1. Call `coordinator_status()` to verify task_coordinator is healthy
2. Call `queue_status()` to check if queues have pending tasks
3. If tasks pending but not executing, check task_coordinator logs
4. If coordinator degraded, check coordinator initialization logs

**Problem**: "High queue backlog"

1. Call `queue_status()` to identify which queue is backed up
2. Call `task_execution_metrics()` to check success rates
3. If success rate low, investigate error trends (hour column)
4. Check error logs for that time period

**Problem**: "Portfolio analysis not running"

1. Call `coordinator_status()` - check `portfolio_analysis_coordinator`
2. If degraded/failed, check coordinator initialization logs
3. Call `task_execution_metrics()` - check `unique_stocks_analyzed`
4. If count increasing, analysis is running; if not, coordinator is stuck

---

## Implementation Details

### Tool Execution Flow

```
TypeScript Server (server.ts)
    ↓
    executeTool(toolName, args)
    ↓
    execSync(python3 tools/{toolName}.py '{args}')
    ↓
Python Tool (tools/{toolName}.py)
    ↓
    1. Check cache (TTL-based)
    2. Fetch from API/Database if cache miss
    3. Transform raw data → aggregated insights
    4. Cache result
    5. Return response
```

### Data Transformation Pipeline

**Raw Data** (from API/Database)
→ **Aggregation** (Count, average, group, deduplicate)
→ **Insights** (Generate human-readable analysis)
→ **Recommendations** (Actionable suggestions)
→ **Structured Response** (Consistent JSON format)

**Example**: Queue Status
- Raw: 50 individual queue records with detailed metrics
- Aggregated: 3 queue summaries with health status
- Insights: "1 queue has high backlog (>50 tasks)"
- Recommendations: "Increase queue concurrency or investigate delays"

### Zod Validation

All tool inputs validated with Zod schemas:

```typescript
export const QueueStatusSchema = z.object({
  use_cache: z.boolean().optional().default(true),
  include_details: z.boolean().optional().default(false)
});
```

Benefits:
- Type safety for TypeScript
- Runtime validation of inputs
- Automatic error messages for invalid inputs
- Clear schema documentation

---

## Best Practices

### When to Use Each Tool

**queue_status**:
- ✅ Monitor real-time task queue status
- ✅ Detect queue backlog or stalling
- ✅ Verify task concurrency levels
- ❌ Not for historical analysis (use task_execution_metrics instead)

**coordinator_status**:
- ✅ Verify system initialization completed
- ✅ Check critical coordinator health
- ✅ Troubleshoot startup issues
- ❌ Not for detailed coordinator logs (check logs directly)

**task_execution_metrics**:
- ✅ Analyze 24-hour task patterns
- ✅ Check portfolio coverage and success rates
- ✅ Identify peak processing times
- ✅ Measure system efficiency
- ❌ Not for real-time monitoring (use queue_status instead)

### Caching Strategy

```python
# First call: Fetches from API/Database
coordinator_status(use_cache=true)  # 800ms, fresh data

# Immediate follow-up: Returns cached result
coordinator_status(use_cache=true)  # <10ms, cached

# Force refresh:
coordinator_status(use_cache=false) # 800ms, fresh data
```

### Error Handling

All tools return structured errors:

```python
{
  "success": false,
  "error": "Description of what failed",
  "suggestion": "How to troubleshoot",
  "execution_time_ms": 1234
}
```

Always check `success` field before using data.

---

## Development & Debugging

### Testing Individual Tools

```bash
# Test coordinator_status
python3 tools/coordinator_status.py '{}'

# Test with options
python3 tools/coordinator_status.py '{"use_cache": false}'

# Test from project root
cd /robo-trader
python3 shared/robotrader_mcp/tools/coordinator_status.py '{}'
```

### Building the MCP Server

```bash
cd shared/robotrader_mcp
npm run build  # TypeScript compilation
npm run test   # Run tests (if available)
```

### Debugging MCP Server

```bash
# Check compiled server.js
node -c dist/server.js

# Verify tool handlers
grep -n "case 'queue_status'" dist/server.js

# Check cache directory
ls -la ~/.robo_trader_mcp_cache/
```

---

## Future Enhancements

### Priority 1 (Safety Improvements)

- [ ] **Retry Logic**: Add exponential backoff to all API calls
- [ ] **Memory Monitoring**: Prevent OOM errors during large data processing
- [ ] **Fallback Strategy**: Formalize data source fallback (API → Database → Cache)

### Priority 2 (Feature Expansion)

- [ ] **Alert Thresholds**: Configurable warning levels for queue depth
- [ ] **Historical Analysis**: Multi-day trend analysis for metrics
- [ ] **Predictive Metrics**: Forecast queue depth based on trends

### Priority 3 (User Experience)

- [ ] **Interactive Exploration**: Multi-step troubleshooting workflows
- [ ] **Custom Reports**: User-defined metric combinations
- [ ] **Export Functionality**: CSV/JSON export for external analysis

---

## References

### Anthropic Blog: Code Execution with MCP

[Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)

**Guiding Principles**:
1. Progressive disclosure (99%+ token reduction)
2. Information aggregation (raw data → insights)
3. Smart caching (minimize API calls)
4. Graceful error handling (meaningful error messages)
5. SRT security compliance (sandbox safety)

### Related Files

- Root CLAUDE.md: Project architecture and patterns
- src/CLAUDE.md: Backend implementation guidelines
- src/web/routes/coordinators.py: Backend API endpoint
- src/core/coordinators/: Coordinator implementations

---

**Last Updated**: 2025-11-07
**Status**: Production Ready
**Version**: 1.0.0
