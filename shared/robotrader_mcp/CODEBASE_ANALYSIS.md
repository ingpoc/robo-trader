# Robo-Trader MCP Server - Codebase Analysis

## Executive Summary

The robo-trader MCP server is a **progressive disclosure architecture** built with TypeScript (frontend) and Python (tools) that provides AI agents with token-efficient tools for debugging and monitoring the robo-trader application. It achieves 95-99% token reduction by processing data in a sandbox and returning insights only.

---

## 1. Directory Structure & Organization

### Root Directory Layout
```
shared/robotrader_mcp/
├── src/                          # TypeScript MCP server
│   ├── server.ts                 # Main MCP server entry point (390 lines)
│   ├── schemas.ts                # Zod schemas for tool inputs
│   └── index.ts                  # CLI entry point
├── tools/                        # Python tool implementations (9 tools)
│   ├── query_portfolio.py        # Database queries (478 lines)
│   ├── check_health.py           # System health checks (400+ lines)
│   ├── real_time_performance_monitor.py  # Performance monitoring (400+ lines)
│   ├── smart_cache.py            # Smart caching with TTL (400+ lines)
│   ├── differential_analysis.py  # Differential analysis (400+ lines)
│   ├── context_aware_summarize.py # Context-aware summaries (500+ lines)
│   ├── analyze_logs.py           # Log analysis (400+ lines)
│   ├── diagnose_locks.py         # Database lock diagnosis (400+ lines)
│   └── verify_config.py          # Configuration verification (400+ lines)
├── dist/                         # Compiled JavaScript output
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript configuration
├── README.md                     # User documentation
├── MCP_USECASE.md               # Detailed architecture documentation
└── config/                       # Configuration files
```

### Key Observations
- **TypeScript-based MCP server**: Thin orchestrator (server.ts) that dispatches to Python tools
- **Python tools**: Domain-specific implementations with in-process caching
- **Progressive disclosure**: Categories defined in server.ts, loaded on-demand
- **Security**: Tools run in SRT sandbox with strict resource limits (30s timeout, 256MB memory)

---

## 2. Progressive Disclosure System (Core Architecture)

### How It Works

**Level 1: Discovery** - User discovers tool categories (200 tokens)
```
list_categories → Robo-Trader MCP Server
Returns: {
  "logs": {...},
  "database": {...},
  "system": {...},
  "optimization": {...},
  "performance": {...}
}
```

**Level 2: Category Loading** - User loads specific category (300 tokens)
```
load_category(category="logs") → Robo-Trader MCP Server
Returns: 3-4 tools in "logs" category with descriptions
```

**Level 3: Tool Execution** - User executes tool directly (500-2000 tokens output)
```
analyze_logs(patterns=["database is locked"]) → Python tool
Returns: Structured insights (NOT raw log dump)
```

### Categories Defined in server.ts (Lines 9-44)

| Category | Tools | Purpose | Token Efficiency |
|----------|-------|---------|-----------------|
| **logs** | analyze_logs | Log analysis & error patterns | 98%+ reduction |
| **database** | query_portfolio, verify_configuration_integrity | Portfolio queries, config validation | 98%+ reduction |
| **system** | check_system_health, diagnose_database_locks | System monitoring, troubleshooting | 97%+ reduction |
| **optimization** | differential_analysis, smart_cache, context_aware_summarize | Token optimization & differential analysis | 99%+ reduction |
| **performance** | real_time_performance_monitor | Real-time performance metrics | 97%+ reduction |

---

## 3. How Tools Are Currently Implemented

### Standard Python Tool Pattern

All tools follow this structure:

```python
#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

def main_function(arg1: str, arg2: int = 10) -> Dict[str, Any]:
    """
    Main function with docstring.
    
    Token reduction: Processes XK items → Y tokens of insights
    Achieves X% reduction vs traditional approach
    
    Args:
        arg1: Required argument
        arg2: Optional argument with default
        
    Returns:
        Structured result with success, insights, recommendations
    """
    
    # 1. Get configuration from environment
    db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')
    api_base = os.environ.get('ROBO_TRADER_API', 'http://localhost:8000')
    
    # 2. Validate inputs and check preconditions
    if not Path(db_path).exists():
        return {
            "success": False,
            "error": f"Database file not found: {db_path}",
            "suggestion": "Ensure robo-trader application is running"
        }
    
    try:
        # 3. Execute tool logic (in sandbox)
        result = perform_analysis(...)
        
        # 4. Return structured response
        return {
            "success": True,
            "data": result,
            "insights": generate_insights(result),
            "recommendations": generate_recommendations(result),
            "token_efficiency": "Processed X items → Y tokens"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}",
            "suggestion": "Check input parameters"
        }

def main():
    """Entry point for MCP tool execution."""
    try:
        # Parse input from MCP server (via command line argument)
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            input_data = json.loads(sys.stdin.read())
        
        # Execute tool
        result = main_function(
            arg1=input_data.get("arg1"),
            arg2=input_data.get("arg2", 10)
        )
        
        # Output result (MCP server parses this)
        print(json.dumps(result, indent=2))
        
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Invalid JSON input: {str(e)}"
        }))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }))

if __name__ == "__main__":
    main()
```

### Input/Output Flow

**TypeScript Server (server.ts)**:
```typescript
async function executeTool(toolName: string, args: any): Promise<any> {
    // 1. Estimate input tokens
    const inputTokens = Math.ceil(JSON.stringify(args).length / 4);
    
    // 2. Execute Python tool via child_process
    const result = execSync(
        `python3 ./tools/${toolName}.py '${JSON.stringify(args)}'`,
        { timeout: 30000 }
    );
    
    // 3. Parse response
    const response = JSON.parse(result);
    
    // 4. Calculate token efficiency (output vs traditional approach)
    const outputTokens = Math.ceil(JSON.stringify(response).length / 4);
    const traditionalTokens = TRADITIONAL_TOKEN_ESTIMATES[toolName];
    const actualReduction = ((traditionalTokens - outputTokens) / traditionalTokens) * 100;
    
    // 5. Add metadata and return
    response.execution_time_ms = executionTime;
    response.token_efficiency = { ... };
    return response;
}
```

### Environment Variables Used

Tools access backend state via environment variables:

| Variable | Default | Usage |
|----------|---------|-------|
| `ROBO_TRADER_DB` | `./state/robo_trader.db` | SQLite database path (read-only in sandbox) |
| `ROBO_TRADER_API` | `http://localhost:8000` | Backend API base URL (for health checks, queue status) |
| `LOG_DIR` | `./logs` | Application logs directory |

---

## 4. Tool Implementation Patterns

### Pattern 1: Database Access (query_portfolio.py)

```python
def query_portfolio(filters: List[str] = None, limit: int = 20, aggregation_only: bool = True):
    """Query portfolio database and return structured insights."""
    
    db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')
    db_file = Path(db_path)
    
    if not db_file.exists():
        return {"success": False, "error": "Database not found"}
    
    try:
        # Connect to database (SRT ensures read-only)
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Execute queries
        portfolio_stats = get_portfolio_stats(cursor)
        results = apply_filters_and_query(cursor, filters, limit)
        health_metrics = calculate_portfolio_health(cursor, portfolio_stats)
        
        # Generate insights (not raw data)
        insights = generate_portfolio_insights(results, portfolio_stats, health_metrics)
        recommendations = generate_portfolio_recommendations(results, health_metrics)
        
        conn.close()
        
        return {
            "success": True,
            "portfolio_stats": portfolio_stats,
            "health_metrics": health_metrics,
            "analysis": {...},
            "insights": insights,
            "recommendations": recommendations,
            "token_efficiency": "Processed X stocks → Y chars output"
        }
        
    except sqlite3.Error as e:
        return {"success": False, "error": f"Database query failed: {str(e)}"}
```

**Key Patterns**:
- Open connection, query, close immediately (no persistent connections)
- Apply filters WITHIN the tool (don't return raw data)
- Generate insights and recommendations (value-add processing)
- Return structured response with success flag

### Pattern 2: Smart Caching (smart_cache.py)

```python
def smart_cache_analyze(
    query_type: str = "portfolio_health",
    parameters: Dict[str, Any] = None,
    force_refresh: bool = False,
    max_age_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """Perform smart cached analysis with progressive disclosure."""
    
    # Generate deterministic cache key
    cache_key = _generate_smart_cache_key(query_type, parameters)
    
    # Check cache validity
    cache_info = _get_cache_info(cache_key, query_type, max_age_seconds)
    
    if not force_refresh and cache_info["is_valid"]:
        # Cache hit - return cached result with metadata
        return {
            "success": True,
            "query_type": query_type,
            "cache_hit": True,
            "cache_age_seconds": cache_info["age_seconds"],
            "cache_ttl": cache_info["ttl"],
            "data": cache_info["data"],
            "metadata": cache_info["metadata"],
            "token_efficiency": "Cache hit"
        }
    
    # Cache miss or force refresh
    try:
        live_data = _perform_live_analysis(query_type, parameters)
        
        # Save to cache with TTL
        cache_metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "query_type": query_type,
            "parameters": parameters
        }
        _save_to_cache(cache_key, live_data, cache_metadata, query_type)
        
        return {
            "success": True,
            "cache_hit": False,
            "data": live_data,
            "token_efficiency": "Cache miss - performed live analysis"
        }
```

**Cache TTL Configurations** (lines 20-27):
```python
CACHE_TTL = {
    "portfolio": 300,           # 5 minutes
    "system_health": 30,        # 30 seconds (rapid changes)
    "performance": 120,         # 2 minutes
    "queues": 60,              # 1 minute
    "errors": 300,             # 5 minutes
    "recommendations": 600      # 10 minutes
}
```

### Pattern 3: Differential Analysis (differential_analysis.py)

```python
def differential_analysis(
    component: str = "portfolio",
    since_timestamp: Optional[str] = None,
    cache_key_override: Optional[str] = None,
    detail_level: str = "medium"  # "overview", "insights", "analysis", "comprehensive"
) -> Dict[str, Any]:
    """Return only CHANGED items since last analysis (99%+ token reduction)."""
    
    # Load previous state from cache
    previous_state = _load_cached_state(cache_key)
    
    # Get current state
    current_state = _get_current_state(db_path, component)
    
    # Calculate what CHANGED
    differential = _calculate_differential(previous_state, current_state, detail_level)
    
    # Save current state for next differential
    _save_cached_state(cache_key, current_state)
    
    # Format response based on detail level
    formatted_response = _format_differential_response(differential, detail_level, component)
    
    return {
        "success": True,
        "component": component,
        "analysis_type": "differential",
        "detail_level": detail_level,
        "changes": formatted_response,
        "token_efficiency": "Processed X items → Y chars (differential only)"
    }
```

**Detail Levels**: "overview" (minimal), "insights" (medium), "analysis" (full), "comprehensive" (all data + trends)

### Pattern 4: Context-Aware Summarization (context_aware_summarize.py)

```python
def context_aware_summarize(
    data_source: str = "portfolio",
    user_context: str = "",
    custom_filters: List[str] = None,
    output_format: str = "structured",  # "structured", "natural", "bullet_points"
    max_tokens: int = 500
) -> Dict[str, Any]:
    """Intelligently summarize data based on user intent."""
    
    # Detect user intent from context string
    intent = _detect_user_intent(user_context)
    
    # Get detail level config for intent
    detail_config = DETAIL_LEVELS[intent]
    
    # Fetch relevant data
    data = _fetch_data(data_source, custom_filters)
    
    # Summarize based on intent
    summary = _create_summary(data, detail_config, output_format)
    
    return {
        "success": True,
        "data_source": data_source,
        "detected_intent": intent,
        "output_format": output_format,
        "summary": summary,
        "token_efficiency": "Intent-based summarization"
    }
```

**Intent Patterns** (lines 13-34):
```python
INTENT_PATTERNS = {
    "quick_check": [r"quick", r"fast", r"summary", r"status"],
    "debugging": [r"error", r"issue", r"debug", r"why"],
    "optimization": [r"optimize", r"improve", r"fix"],
    "monitoring": [r"monitor", r"track", r"alert"],
    "analysis": [r"analyze", r"detailed", r"comprehensive"]
}
```

### Pattern 5: Real-Time Performance Monitoring

```python
class PerformanceMonitor:
    """Real-time performance monitoring with background sampling."""
    
    def __init__(self):
        self.performance_history = []
        self.monitor_thread = None
        self._load_cached_data()
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            daemon=True
        )
        self.monitor_thread.start()
    
    def _monitor_loop(self):
        """Collect performance samples at intervals."""
        while self.is_monitoring:
            sample = self._collect_performance_sample()
            self.performance_history.append(sample)
            
            # Keep only recent history
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                seconds=MONITORING_CONFIG["history_window"]
            )
            self.performance_history = [
                entry for entry in self.performance_history
                if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
            ]
            
            self._save_cached_data()
            time.sleep(MONITORING_CONFIG["sampling_interval"])
```

---

## 5. TypeScript Server Implementation (server.ts)

### MCP Server Setup (Lines 48-51)
```typescript
const server = new Server({
  name: "robo-trader-dev",
  version: "1.0.0"
});
```

### Tool Execution Orchestration (Lines 54-163)

```typescript
async function executeTool(toolName: string, args: any): Promise<any> {
    const startTime = Date.now();
    
    try {
        // 1. Estimate input tokens (rough approximation)
        const inputSize = JSON.stringify(args).length;
        const inputTokens = Math.ceil(inputSize / 4);
        
        // 2. Execute Python tool in sandbox
        const result = execSync(
            `python3 ./tools/${toolName}.py '${JSON.stringify(args)}'`,
            {
                timeout: 30000,  // 30-second SRT sandbox timeout
                encoding: 'utf8',
                cwd: process.cwd()
            }
        );
        
        const executionTime = Date.now() - startTime;
        const response = JSON.parse(result);
        
        // 3. Calculate output tokens
        const outputSize = JSON.stringify(response).length;
        const outputTokens = Math.ceil(outputSize / 4);
        
        // 4. Estimate traditional approach tokens
        const traditionalTokens = {
            'analyze_logs': 30000,
            'query_portfolio': 15000,
            'check_health': 25000,
            'verify_config': 10000,
            'diagnose_locks': 40000,
            'differential_analysis': 50000,
            'smart_cache': 35000,
            'context_aware_summarize': 40000,
            'real_time_performance_monitor': 20000
        }[toolName] || inputTokens * 10;
        
        // 5. Calculate actual reduction percentage
        const actualReduction = ((traditionalTokens - outputTokens) / traditionalTokens) * 100;
        
        // 6. Add execution metadata to response
        response.execution_time_ms = executionTime;
        response.token_efficiency = {
            input_tokens: inputTokens,
            output_tokens: outputTokens,
            traditional_tokens_estimated: traditionalTokens,
            actual_reduction_percent: Math.round(actualReduction * 10) / 10,
            comparison: `Traditional: ${traditionalTokens} tokens vs MCP: ${outputTokens} tokens`
        };
        
        // 7. Ensure consistent response format
        if (!response.hasOwnProperty('success')) {
            response.success = true;
        }
        if (!response.hasOwnProperty('insights')) {
            response.insights = [];
        }
        if (!response.hasOwnProperty('recommendations')) {
            response.recommendations = [];
        }
        
        return response;
        
    } catch (error: any) {
        // Standardized error response
        return {
            success: false,
            error: error.message || "Tool execution failed",
            execution_time_ms: Date.now() - startTime,
            token_efficiency: {
                error: "Execution failed - token efficiency not measured"
            },
            insights: [`Tool execution failed: ${error.message}`],
            recommendations: ["Check tool input parameters"]
        };
    }
}
```

### Tool Registration Pattern (Lines 208-381)

```typescript
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    
    switch (name) {
        case "list_categories":
            // Return category overview
            return { content: [...] };
        
        case "load_category":
            // Return tools in category
            const { category } = args;
            const cat = toolCategories[category];
            return { content: [...] };
        
        case "analyze_logs":
        case "query_portfolio":
        case "check_system_health":
        // ... other tools
            const result = await executeTool(toolName, args);
            return {
                content: [{
                    type: "text",
                    text: JSON.stringify(result, null, 2)
                }]
            };
        
        default:
            return {
                content: [{
                    type: "text",
                    text: JSON.stringify({
                        success: false,
                        error: `Unknown tool: ${name}`,
                        available_tools: ["list_categories", "load_category", "mcp_info"]
                    })
                }]
            };
    }
});
```

---

## 6. Adding a New Tool - Step-by-Step

### Step 1: Create Python Tool File

Create `tools/my_new_tool.py`:

```python
#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import os

def my_new_tool_analysis(
    param1: str,
    param2: int = 10,
    param3: bool = False
) -> Dict[str, Any]:
    """
    Description of what tool does.
    
    Token reduction: Processes X items → Y tokens
    Achieves X% reduction vs traditional approach
    """
    
    # Get configuration from environment
    db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')
    api_base = os.environ.get('ROBO_TRADER_API', 'http://localhost:8000')
    
    if not Path(db_path).exists():
        return {
            "success": False,
            "error": f"Database file not found: {db_path}"
        }
    
    try:
        # Tool logic here
        result = do_analysis(param1, param2, param3)
        
        insights = generate_insights(result)
        recommendations = generate_recommendations(result)
        
        return {
            "success": True,
            "data": result,
            "insights": insights,
            "recommendations": recommendations,
            "token_efficiency": f"Processed X items → {len(json.dumps(result))} chars"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }

def main():
    """Entry point for MCP tool execution."""
    try:
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            input_data = json.loads(sys.stdin.read())
        
        result = my_new_tool_analysis(
            param1=input_data.get("param1"),
            param2=input_data.get("param2", 10),
            param3=input_data.get("param3", False)
        )
        
        print(json.dumps(result, indent=2))
        
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Invalid JSON input: {str(e)}"
        }))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }))

if __name__ == "__main__":
    main()
```

### Step 2: Add Zod Schema in schemas.ts

```typescript
// schemas.ts - Add new schema
export const MyNewToolSchema = z.object({
    param1: z.string().describe("Description of param1"),
    param2: z.number().optional().default(10).describe("Description of param2"),
    param3: z.boolean().optional().default(false).describe("Description of param3")
});

export type MyNewToolInput = z.infer<typeof MyNewToolSchema>;
```

### Step 3: Register in Tool Categories

```typescript
// server.ts - Add to toolCategories
const toolCategories = {
    // ... existing categories ...
    "custom": {  // New category (or add to existing)
        name: "Custom Tools",
        description: "Custom analysis tools",
        tools: ["my_new_tool"],
        token_efficiency: "95%+ reduction",
        use_cases: ["custom_analysis"]
    }
};
```

### Step 4: Add Tool Execution Case

```typescript
// server.ts - Add case in CallToolRequestSchema handler
case "my_new_tool":
    const customResult = await executeTool("my_new_tool", args);
    return {
        content: [{
            type: "text",
            text: JSON.stringify(customResult, null, 2)
        }]
    };
```

### Step 5: Update Token Estimation

```typescript
// server.ts - Add to traditionalTokens in executeTool()
case 'my_new_tool':
    traditionalTokens = 20000;  // Estimate tokens without tool
    break;
```

### Step 6: Test the Tool

```bash
# Test tool directly
echo '{"param1": "test", "param2": 5}' | python3 tools/my_new_tool.py

# Test via MCP server
# Build TypeScript
npm run build

# Start server
node dist/index.js
```

---

## 7. Database Access Patterns

### Safe Database Access

All tools access database **read-only** via SQLite:

```python
# 1. Get database path from environment
db_path = os.environ.get('ROBO_TRADER_DB', './state/robo_trader.db')

# 2. Validate file exists
if not Path(db_path).exists():
    return {"success": False, "error": "Database not found"}

# 3. Connect (SRT sandbox ensures read-only)
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row  # Enable dict-like access
cursor = conn.cursor()

# 4. Execute queries
cursor.execute("SELECT * FROM portfolio LIMIT 10")
results = cursor.fetchall()

# 5. Close connection immediately
conn.close()
```

### Database Tables Available

Tools can query:
- `portfolio` - Portfolio holdings
- `analysis_history` - Claude analysis records
- `recommendations` - Trading recommendations
- `paper_trading` - Paper trading history (if applicable)
- `configuration` - Configuration state

### API Endpoints Available

Tools can call backend API:

```python
import requests

api_base = os.environ.get('ROBO_TRADER_API', 'http://localhost:8000')

# Health check
response = requests.get(f"{api_base}/api/health", timeout=5)

# Get queue status (if available)
response = requests.get(f"{api_base}/api/system/queues", timeout=5)

# Get analysis transparency
response = requests.get(f"{api_base}/api/claude/transparency/analysis", timeout=5)
```

---

## 8. Caching Architecture

### In-Process Caching

Tools use `.robo_trader_mcp_cache/` directory for caching:

```python
from pathlib import Path

CACHE_DIR = Path(os.path.expanduser("~/.robo_trader_mcp_cache"))
CACHE_DIR.mkdir(exist_ok=True)

# Tools cache:
# - Performance monitoring history (100 samples, ~30KB)
# - Differential analysis state (JSON snapshots)
# - Smart cache entries with TTL
```

### Cache TTL Configurations

```python
CACHE_TTL = {
    "portfolio": 300,              # 5 minutes (volatile)
    "system_health": 30,           # 30 seconds (very volatile)
    "performance": 120,            # 2 minutes
    "queues": 60,                  # 1 minute
    "errors": 300,                 # 5 minutes
    "recommendations": 600         # 10 minutes
}
```

---

## 9. Error Handling Patterns

### Standardized Error Response Format

All tools return this format on error:

```python
{
    "success": False,
    "error": "Human-readable error message",
    "suggestion": "What user should do to fix",
    # Optional additional fields:
    "details": {...}  # Additional context if helpful
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Database file not found" | DB path invalid or app not running | Start backend with `python -m src.main --command web` |
| "API endpoint not responding" | Backend health check failed | Verify backend on port 8000 |
| "Task execution timeout" | Analysis took > 30 seconds | Reduce data scope or increase timeout in server.ts |
| "JSON parsing error" | Invalid input format | Verify input is valid JSON |

---

## 10. Token Efficiency Metrics

### How Token Reduction is Calculated

```typescript
// Traditional approach: Raw data dump to Claude
Traditional tokens = size of full data export / 4

// MCP approach: Insight extraction in sandbox
MCP tokens = size of insight summary / 4

// Reduction percentage
Reduction = (Traditional - MCP) / Traditional * 100
```

### Example: Log Analysis
- **Traditional**: 50K log lines × 4 tokens/line = 200K tokens
- **MCP approach**: Parse, filter, aggregate → 500 tokens
- **Reduction**: (200K - 500) / 200K = 99.75%

### Typical Reductions by Tool

| Tool | Reduction | Input | Output |
|------|-----------|-------|--------|
| analyze_logs | 98.3% | 50K log lines | 500 tokens |
| query_portfolio | 98.7% | 15K database rows | 200 tokens |
| check_system_health | 96.8% | Multiple API calls | 800 tokens |
| diagnose_locks | 97% | Logs + code analysis | 1.2K tokens |
| differential_analysis | 99%+ | Full data dump | Delta only |
| real_time_performance_monitor | 97%+ | Metrics history | Alerts + trends |

---

## 11. Key Takeaways for Enhancement

### For Queue Monitoring Tool

**What's Available**:
- Backend API at `ROBO_TRADER_API` (default: `http://localhost:8000`)
- Database tables: `portfolio`, `analysis_history`, `recommendations`
- Environment: `ROBO_TRADER_DB`, `ROBO_TRADER_API`, `LOG_DIR`
- Caching: Use `~/.robo_trader_mcp_cache/` for tool-specific caches

**Pattern to Follow**:
1. Query API or database to get queue status
2. Process/aggregate data in Python tool
3. Return structured insights (not raw data)
4. Cache frequently accessed data with appropriate TTL
5. Return JSON with success flag, insights, and recommendations

### For Coordinator Status Tool

**Access Pattern**:
- Call `/api/coordinators/status` endpoint (if available)
- OR query database for coordinator-related state
- Cache with 30-60 second TTL (coordinators change frequently)

### For Task Execution Metrics Tool

**Available Data**:
- `SchedulerTask` database table (if exposed via DB)
- `/api/scheduler/tasks` endpoint for live status
- Task execution history in application logs

**Processing**:
- Aggregate task metrics by queue, type, timestamp
- Calculate average execution time, success rate
- Identify bottlenecks and slow tasks
- Generate recommendations for optimization

---

## 12. Security & Sandboxing

### SRT Sandbox Protections

All tools run in **Anthropic Sandbox Runtime (SRT)** with:

- **OS-level isolation**: Seatbelt (macOS) / bubblewrap (Linux)
- **Network restrictions**: Localhost only
- **Filesystem boundaries**: Read-only access
- **Resource limits**: 30-second timeout, 256MB memory limit
- **Process isolation**: Can't access host processes

### Implications for Tools

✅ **Safe**:
- Read-only SQLite database access
- HTTP calls to localhost API
- File I/O within sandbox filesystem
- In-process caching

❌ **Not Allowed**:
- Write to database (read-only)
- Network calls outside localhost
- Executing external binaries
- Accessing host files outside sandbox

---

## Conclusion

The robo-trader MCP server is a well-architected, progressive disclosure system that provides 95-99% token reduction through intelligent data processing and caching. New monitoring tools should follow the established patterns:

1. **Input**: Get parameters via `sys.argv[1]` JSON argument
2. **Access**: Query backend API or database (read-only)
3. **Process**: Aggregate and analyze in Python tool
4. **Cache**: Store frequently-accessed data with TTL
5. **Output**: Return structured JSON with insights/recommendations

This pattern ensures optimal token efficiency while providing actionable insights to AI agents.
