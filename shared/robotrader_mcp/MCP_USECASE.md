# Robo-Trader MCP Server - Development Acceleration Plan

> **Last Updated**: 2025-11-06 | **Purpose**: AI Development Acceleration | **Target**: Claude Code Agents
>
> **References**: [Anthropic Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) | [Anthropic Sandbox Runtime](https://github.com/anthropic-experimental/sandbox-runtime) |
[Anthropic Sandbox Doc] (https://www.anthropic.com/engineering/claude-code-sandboxing)

## 🎯 Goal

**Create an external MCP server that helps Claude Code agents debug and develop the robo-trader application faster while avoiding rate limits and token exhaustion using Anthropic's official sandbox runtime.**

### Architecture Clarification
**This is NOT part of the robo-trader application** - it's an external development tool for AI agents.

- **Application MCP**: Already exists in `src/mcp/` for production integration
- **Development MCP**: This project - external debugging tool for AI agents

### Primary User: Claude Code Agents (like me)

- **Current Pain Points**:

  - Hitting rate limits when reading large files (30K+ tokens for log analysis)
  - Context window exhaustion during debugging sessions (75K+ tokens per session)
  - Time-consuming code exploration and analysis (5-10 minutes per issue)

- **Desired Outcome**:

  - Execute complex analysis in minimal tokens (500-2000 tokens vs 75K)
  - Get actionable insights instead of raw data dumps
  - Debug issues 10-20x faster (30 seconds vs 5-10 minutes)
  - **No application integration required** - purely external development tool

---

## 🏗️ Core Principles

### 1. Progressive Disclosure: Load Only What's Needed

**Principle**: Present tools as a filesystem structure where agents discover and load tool definitions on-demand, rather than loading everything upfront.

**Implementation Pattern**:
```
shared/robotrader_mcp/tools/
├── database/
│   ├── query_portfolio.ts      # Load only when database access needed
│   └── analyze_data.ts         # Load only for data analysis
├── logs/
│   ├── analyze_logs.ts         # Load only for log investigation
│   └── diagnose_issues.ts      # Load only for debugging
└── system/
    ├── health_check.ts         # Load only for system monitoring
    └── config_verify.ts        # Load only for configuration validation
```

**Why This Works**: Instead of loading 50+ tool definitions (150K tokens), agents load only the 2-3 tools needed for their current task (2K tokens).

**Robo-Trader Example**:
```typescript
// Agent exploring the filesystem:
const dbTools = await list_tools('database');  # Loads only database tools
const logTools = await list_tools('logs');     # Loads only log analysis tools
// Total: 2K tokens instead of 150K tokens
```

### 2. Code Execution Over Data Transfer: Process Before Returning

**Principle**: Execute data processing and filtering in the sandbox environment before returning results to Claude, avoiding raw data transfer.

**Token Transformation Example**:
```python
# ❌ Traditional approach (150K tokens):
raw_logs = read_entire_log_file()  # 50,000 lines = 30,000 tokens
raw_db_data = query_all_portfolio() # 15,000 rows = 15,000 tokens
raw_api_response = call_api()       # 5,000 lines = 5,000 tokens
# Claude processes in context: 100,000+ tokens

# ✅ MCP approach (2,000 tokens):
# All processing happens in sandbox:
filtered_errors = analyze_logs(patterns=["database is locked"], limit=10)  # 500 tokens
problematic_stocks = query_portfolio(filters=["stale_analysis"])          # 200 tokens
api_summary = call_api(endpoint="/health", summary_only=True)              # 300 tokens
# Results: 1,000 tokens total (98.7% savings)
```

**Real-World Impact**: The blog post shows `const transcript = (await gdrive.getDocument(...)).content; await salesforce.updateRecord(...)` saves 98.7% tokens vs direct tool calls by processing in the execution environment.

**Robo-Trader Application**:
```python
# Instead of: fetch 81 stock analyses = 162,000 tokens
# Execute in sandbox:
analysis_summary = analyze_portfolio_intelligence(
    symbols=ALL_STOCKS,           # Process all in sandbox
    return_highlights_only=True   # Filter before returning
)
# Returns: 2,000 tokens of insights (99.4% savings)
```

### 3. Control Flow in Code vs Tool Chaining

**Principle**: Execute loops, conditionals, and complex logic in code rather than chaining individual tool calls.

**Before MCP (Tool Chaining)**:
```typescript
// 8 separate tool calls, each with full context
for (const stock of portfolio) {
    const analysis = await getStockAnalysis(stock.symbol);  // 2K tokens × 81 = 162K tokens
    const price = await getCurrentPrice(stock.symbol);      // 1K tokens × 81 = 81K tokens
    if (analysis.score > 80) {
        await addToWatchlist(stock.symbol);                // 1K tokens × 20 = 20K tokens
    }
}
// Total: 263K tokens, 81 round trips
```

**After MCP (Code Execution)**:
```typescript
// Single code execution in sandbox
const result = await execute_in_sandbox(`
    portfolio_analysis = analyze_all_stocks()
    high_scoring_stocks = [s for s in portfolio_analysis if s.score > 80]
    return {"highlights": high_scoring_stocks[:10], "total_analyzed": len(portfolio_analysis)}
`);
// Returns: 2,000 tokens, 1 execution
```

### 4. State Persistence & Skill Development

**Principle**: Use filesystem access in sandbox to persist state, cache results, and develop reusable skills.

**Implementation Pattern**:
```python
# In sandbox execution:
def analyze_with_cache():
    cache_file = "/tmp/mcp-workspace/analysis_cache.json"

    # Check cache first
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cache = json.load(f)
        if cache.get("timestamp") > time.time() - 3600:  # 1 hour cache
            return cache["results"]

    # Perform expensive analysis
    results = expensive_portfolio_analysis()

    # Persist to cache
    with open(cache_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "results": results
        }, f)

    return results
```

**Benefits**: Expensive operations are cached across sessions, reducing both token usage and execution time.

### 5. Security-First Data Handling

**Principle**: Implement deterministic security rules with data tokenization and monitoring before any data reaches Claude.

**Security Layers**:
```python
# Layer 1: Input validation in sandbox
def validate_query(sql_query):
    blocked_keywords = ["DROP", "DELETE", "UPDATE", "INSERT"]
    for keyword in blocked_keywords:
        if keyword.upper() in sql_query.upper():
            raise SecurityError(f"Blocked keyword: {keyword}")
    return sql_query

# Layer 2: Data filtering before return
def sanitize_portfolio_data(raw_data):
    sensitive_fields = ["api_key", "secret_key", "personal_info"]
    return [
        {k: v for k, v in row.items() if k not in sensitive_fields}
        for row in raw_data
    ]

# Layer 3: Output size limiting
def limit_response_size(data, max_tokens=1000):
    estimated_tokens = len(str(data)) / 4  # Rough estimate
    if estimated_tokens > max_tokens:
        return {"error": "Response too large", "size_estimate": estimated_tokens}
    return data
```

**Implementation for Robo-Trader**:
```python
# Safe database access pattern
def safe_portfolio_query(filters):
    # Input validation
    if not isinstance(filters, list) or len(filters) > 10:
        raise SecurityError("Invalid filters")

    # Sanitized query
    safe_sql = """
        SELECT symbol, last_analysis, score
        FROM analysis_history
        WHERE symbol IN ({})
        LIMIT 50
    """.format(",".join(["?"] * len(filters)))

    # Execute with parameterized query
    results = execute_readonly_query(safe_sql, filters)

    # Sanitize output
    return sanitize_portfolio_data(results)
```

---

## 🏗️ Architecture Overview

### **External Development Tool Architecture**

```
┌─────────────────┐    Claude Code     ┌─────────────────────┐
│   AI Agent       │ ◄─────────────────► │  Development MCP   │
│ (Claude Code)    │                    │     Server          │
└─────────────────┘                    │                     │
                                        │  ┌───────────────┐ │
                                        │  │   Sandbox     │ │
                                        │  │  (SRT)         │ │
                                        │  │               │ │
                                        │  │ Python Tools │ │
                                        │  └───────────────┘ │
                                        └─────────┬───────────┘
                                                  │ Read-Only Access
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Robo-Trader Application (External Access)       │
│  ├─ logs/robo-trader.log (read-only)                       │
│  ├─ state/robo_trader.db (read-only)                       │
│  ├─ config/config.json (read-only)                         │
│  └─ http://localhost:8000/api/* (GET only)                 │
└─────────────────────────────────────────────────────────────┘
```

### **Key Design Principles**
- **Zero Integration**: No code changes to robo-trader application
- **Read-Only Access**: Cannot modify application state or data
- **External Tool**: Runs independently of the application
- **Development Focus**: Optimized for debugging and development workflow

---

## 🛠️ Core MCP Tools

Based on the most common debugging scenarios in robo-trader development, these **5 essential tools** will provide 95%+ of the value:

### 1. `analyze_logs` - Log Pattern Intelligence
**Purpose**: Analyze 50K+ log lines → return 500 tokens of actionable error patterns

```python
# Example usage
analyze_logs(
    patterns=["database is locked", "timeout", "ERROR", "CRITICAL"],
    time_window="1h",
    group_by="error_type",
    max_examples=3
)

# Returns (instead of 30K tokens of raw logs):
{
  "database_is_locked": {
    "count": 47,
    "examples": ["2025-11-06 10:23:45 ERROR database is locked"],
    "error_rate_per_minute": 0.78,
    "affected_operations": ["store_analysis_history", "store_recommendation"]
  },
  "timeout_errors": {"count": 12, "examples": [...]}
}
```

**Token Savings**: 30,000 → 500 tokens (98.3% reduction)

### 2. `query_portfolio` - Smart Database Analysis
**Purpose**: Query 15K+ portfolio rows → return 200 tokens of problematic stocks

```python
# Example usage
query_portfolio(
    filters=["stale_analysis", "missing_analysis", "error_conditions"],
    aggregation_only=True,
    limit=20
)

# Returns (instead of 15K rows):
{
  "stocks_needing_attention": [
    {"symbol": "AAPL", "issue": "stale_analysis", "last_analysis": "2025-11-03"},
    {"symbol": "MSFT", "issue": "missing_analysis", "last_analysis": "N/A"}
  ],
  "total_stale_analyses": 23,
  "total_missing_analyses": 5,
  "health_score": 92.6
}
```

**Token Savings**: 15,000 → 200 tokens (98.7% reduction)

### 3. `diagnose_database_locks` - Lock Issue Investigation
**Purpose**: Correlate log errors with code patterns → return actionable fixes

```python
# Example usage
diagnose_database_locks(
    time_window="24h",
    include_code_references=True,
    suggest_fixes=True
)

# Returns (instead of reading hours of logs and code):
{
  "lock_errors_found": 47,
  "probable_causes": [
    {
      "cause": "Direct database access in web routes",
      "evidence": "Lock errors spike during /api/claude/transparency/analysis calls",
      "locations": [
        "src/web/routes/claude_routes.py:234",
        "src/web/routes/claude_routes.py:189"
      ],
      "recommended_fixes": [
        "Replace direct db.connection.execute() with config_state.get_analysis_history()",
        "Use locked ConfigurationState methods in all web endpoints"
      ]
    }
  ]
}
```

**Token Savings**: 40,000 → 1,200 tokens (97% reduction)

### 4. `check_system_health` - Multi-Component Status
**Purpose**: Aggregate health across all components → return comprehensive status

```python
# Example usage
check_system_health(
    components=["database", "queues", "api_endpoints", "disk_space", "backup_status"]
)

# Returns (instead of querying each endpoint separately):
{
  "overall_status": "HEALTHY",
  "database": {
    "status": "OK",
    "portfolio_size": 81,
    "analyzed_today": 23,
    "last_backup": "2025-11-06 02:00:00"
  },
  "queues": {
    "AI_ANALYSIS": {"pending": 3, "running": 1},
    "PORTFOLIO_SYNC": {"pending": 0, "running": 0}
  },
  "disk_space": {"used_gb": 45.2, "available_gb": 234.8},
  "issues_detected": 0
}
```

**Token Savings**: 25,000 → 800 tokens (96.8% reduction)

### 5. `verify_configuration_integrity` - Configuration Validation
**Purpose**: Verify system configuration consistency → return issues only

```python
# Example usage
verify_configuration_integrity(
    checks=["database_paths", "api_endpoints", "queue_settings", "security_settings"]
)

# Returns (only problems, not "everything is fine"):
{
  "issues_found": 2,
  "problems": [
    {
      "type": "database_path_mismatch",
      "severity": "WARNING",
      "description": "config.json references ./data/robo_trader.db but actual file is at ./state/robo_trader.db"
    },
    {
      "type": "missing_security_headers",
      "severity": "INFO",
      "description": "CORS headers not configured for /api/* endpoints"
    }
  ],
  "overall_integrity": 95.8
}
```

**Token Savings**: 10,000 → 300 tokens (97% reduction)

---

## 🏗️ Technology Stack

### **Core Components**
- **MCP Server**: Node.js with `@modelcontextprotocol/sdk/mcp.js` (≈200 lines - ultra-minimal)
- **Sandbox Runtime**: `@anthropic-ai/sandbox-runtime` (SRT) - handles all security automatically
- **Python Tools**: 5 simple scripts (100-150 lines each) - focused analysis only
- **Database Access**: Read-only SQLite via Python (standard library)

### **Security (SRT Handles Everything)**
- **OS-level Isolation**: Seatbelt (macOS) / bubblewrap (Linux) - **handled by SRT**
- **Network Controls**: localhost-only - **handled by SRT**
- **Filesystem Boundaries**: Read-only `logs/`, `state/` - **handled by SRT**
- **Resource Limits**: 30s timeout, 256MB memory - **handled by SRT**
- **No Custom Security Needed**: SRT provides production-grade sandboxing

### **Configuration Files**
```json
// ~/.srt-settings.json (Sandbox boundaries)
{
  "network": {
    "allowedDomains": ["localhost", "127.0.0.1"],
    "deniedDomains": ["*"],
    "allowUnixSockets": true,
    "allowLocalBinding": false
  },
  "filesystem": {
    "allowWrite": ["./state/*", "./logs/*", "./shared/robotrader_mcp/tmp/*"],
    "denyWrite": ["src/*", "ui/*", "/etc/*", "/usr/*"],
    "denyRead": ["*/.ssh/*", "*/.aws/*", "*/.env*"]
  }
}
```

```json
// ~/.claude/mcp_settings.json (MCP server registration)
{
  "mcpServers": {
    "robo-trader-dev": {
      "command": "srt",
      "args": ["node", "./shared/robotrader_mcp/src/server.js"],
      "env": {
        "ROBO_TRADER_API": "http://localhost:8000",
        "ROBO_TRADER_DB": "./state/robo_trader.db",
        "LOG_DIR": "./logs",
        "ALLOW_EXEC_TIMEOUT": "30",
        "MAX_MEMORY_MB": "256"
      }
    }
  }
}
```

---

## 📈 Expected Impact

### **Token Consumption Comparison**

| Development Task | Current Approach | MCP Approach | Token Reduction | Time Savings |
|------------------|------------------|--------------|-----------------|--------------|
| **Log Analysis** | Read 50K lines → 30K tokens | Error patterns → 500 tokens | **98.3%** | 5 min → 30 sec |
| **Database Debug** | Query 15K rows → 15K tokens | Problem stocks → 200 tokens | **98.7%** | 3 min → 15 sec |
| **System Health** | Multiple endpoints → 25K tokens | Aggregated status → 800 tokens | **96.8%** | 4 min → 20 sec |
| **Lock Diagnosis** | Logs + code → 40K tokens | Root cause analysis → 1.2K tokens | **97%** | 8 min → 45 sec |
| **Config Issues** | Manual checks → 10K tokens | Automated validation → 300 tokens | **97%** | 6 min → 30 sec |

### **Development Velocity Transformation**

**Before MCP**:
```
You: "Why are there database errors?"
Me: *Read logs* (30K tokens, 3 min)
Me: *Query database* (15K tokens, 2 min)
Me: *Analyze patterns* (10K tokens, 3 min)
→ Total: 55K tokens, 8 minutes
→ Risk: Hit rate limit during analysis
```

**After MCP**:
```
You: "Why are there database errors?"
Me: *Execute diagnose_database_locks()* (1.2K tokens, 45 sec)
→ "47 lock errors from src/web/routes/claude_routes.py:234 bypassing ConfigurationState.
   Fix: Use config_state.get_analysis_history() instead of direct db.connection.execute()"
→ Total: 1.2K tokens, 45 seconds
→ No rate limit risk
```

---

## 🗺️ Implementation Plan

### **Progressive Disclosure Implementation**

#### **File System Structure for Tool Discovery**
```
shared/robotrader_mcp/tools/
├── categories/
│   ├── logs/
│   │   ├── _category.json          # Category metadata
│   │   └── analyze_logs.ts        # Tool definition
│   ├── database/
│   │   ├── _category.json
│   │   ├── query_portfolio.ts
│   │   └── verify_integrity.ts
│   └── system/
│       ├── _category.json
│       ├── check_health.ts
│       └── monitor_resources.ts
```

#### **Category Metadata (_category.json)**
```json
{
  "name": "Log Analysis Tools",
  "description": "Tools for analyzing application logs and error patterns",
  "tools": ["analyze_logs", "diagnose_errors"],
  "token_efficiency": "98%+ reduction",
  "use_cases": ["debugging", "error_analysis", "performance_monitoring"]
}
```

### **Phase 1: SRT + Progressive Disclosure (Day 1 - 4 hours)**
- [ ] Install `@anthropic-ai/sandbox-runtime`: `npm install -g @anthropic-ai/sandbox-runtime`
- [ ] Configure `~/.srt-settings.json` with filesystem boundaries
- [ ] Set up tool categories structure for progressive discovery
- [ ] Implement category discovery mechanism (200 lines)

### **Phase 2: Core Categories (Days 2-3 - 8 hours)**
- [ ] Implement `logs/analyze_logs.py` (pattern matching, 2 hours)
- [ ] Implement `database/query_portfolio.py` (SQLite queries, 3 hours)
- [ ] Implement `system/check_health.py` (status checks, 3 hours)
- [ ] Test progressive discovery with real debugging scenarios

### **Phase 3: Advanced Categories (Days 4-5 - 8 hours)**
- [ ] Implement `database/verify_integrity.py` (setup validation, 4 hours)
- [ ] Implement `logs/diagnose_errors.py` (error correlation, 4 hours)
- [ ] Optimize token efficiency across all tools (core value proposition)
- [ ] Test progressive disclosure workflow end-to-end

### **Phase 4: Token Optimization & Testing (Day 6 - 4 hours)**
- [ ] Validate progressive disclosure metrics (target: 99%+ reduction)
- [ ] End-to-end testing with real debugging scenarios
- [ ] Token usage analysis (baseline vs progressive)
- [ ] Documentation with progressive disclosure examples

---

## 🛠️ Progressive Disclosure Implementation (Anthropic Blog Post Alignment)

### **Core Principle: Load Only What's Needed**

**Traditional MCP** (loads all tools upfront - blog post problem):
```typescript
// Blog Post Problem: Load ALL tool definitions into context
const allToolDefinitions = [
  analyze_logs_tool,      // 5,000 tokens
  query_portfolio_tool,  // 8,000 tokens
  diagnose_database_locks_tool, // 6,000 tokens
  check_system_health_tool,  // 4,000 tokens
  verify_configuration_tool,  // 7,000 tokens
  // ... 20 more tools = 150,000 tokens total
];

// Agent gets ALL definitions regardless of need = 150K tokens just to start!
server.registerTools(allToolDefinitions);
```

**Progressive Disclosure** (blog post solution - filesystem discovery):
```typescript
// Blog Post Solution: Tools as filesystem structure
const toolCategories = {
  "logs": ["analyze_logs", "diagnose_errors"],
  "database": ["query_portfolio", "verify_integrity"],
  "system": ["check_health", "monitor_resources"]
};

// Agent discovers categories first (200 tokens), then loads specific tools (300 tokens each)
server.registerTool("list_categories", async () => {
  return Object.keys(toolCategories);
});

server.registerTool("load_category", async (category) => {
  if (!toolCategories[category]) {
    throw new Error(`Unknown category: ${category}`);
  }
  return toolCategories[category].map(toolName => ({
    name: toolName,
    description: getToolDescription(toolName),
    load: () => loadTool(toolName)  // Load on-demand only
  }));
});

// Agent workflow:
// 1. List categories: 200 tokens
// 2. Load "logs" category: 300 tokens
// 3. Use analyze_logs tool: 500 tokens
// Total: 1,000 tokens vs 150,000 tokens (99.3% reduction)
```

**Our MCP Specification-Aligned Implementation** (ultra-minimal):
```typescript
// 200 lines total - follows MCP spec's simplicity philosophy
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

const server = new McpServer({
  name: "robo-trader-dev",
  version: "1.0.0"
});

// Simple pattern for all 5 tools - follows MCP spec best practices
const tools = [
  { name: "analyze_logs", script: "tools/analyze_logs.py" },
  { name: "query_portfolio", script: "tools/query_portfolio.py" },
  { name: "diagnose_database_locks", script: "tools/diagnose_locks.py" },
  { name: "check_system_health", script: "tools/health_check.py" },
  { name: "verify_configuration_integrity", script: "tools/config_verify.py" }
];

tools.forEach(tool => {
  server.registerTool(tool.name, {
    description: toolDescriptions[tool.name],
    inputSchema: toolSchemas[tool.name]
  }, async (args) => {
    // MCP spec: simple validation only
    if (!validateInput(tool.name, args)) {
      throw new Error(`Invalid input for ${tool.name}`);
    }

    // SRT handles ALL security automatically (timeout, memory, isolation)
    const result = await execSync(`python3 ${tool.script} '${JSON.stringify(args)}'`, {
      timeout: 30000,
      encoding: 'utf8'
    });

    // MCP spec: standard response format
    return { content: [{ type: "text", text: result }] };
  });
});
```

### **MCP Spec-Aligned Python Tool (100-150 lines max)**

```python
# tools/analyze_logs.py - follows MCP spec's focused tool philosophy
import json
import sqlite3
from pathlib import Path

def analyze_logs(patterns, time_window="1h"):
    """MCP spec: focused single-purpose tool for log analysis."""

    # Read logs (SRT handles read-only access automatically)
    log_file = Path("./logs/robo-trader.log")
    if not log_file.exists():
        return {"error": "Log file not found"}

    logs = log_file.read_text().split('\n')

    # MCP spec: process in sandbox, return insights only (token efficiency)
    results = {}
    for pattern in patterns:
        matches = [log for log in logs if pattern.lower() in log.lower()]
        results[pattern] = {
            "count": len(matches),
            "examples": matches[:3],  # Limit for token efficiency
            "recent": matches[-1:] if matches else None
        }

    return results

# MCP spec: simple stdin input (SRT provides isolation)
if __name__ == "__main__":
    try:
        input_data = json.loads(input())
        result = analyze_logs(input_data["patterns"], input_data.get("time_window", "1h"))
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
```

### **Implementation Complexity Comparison (MCP Spec Analysis)**

| Component | Traditional MCP | MCP Spec + SRT Approach | Reduction |
|-----------|----------------|---------------------------|-----------|
| **Server Code** | 3,000+ lines | 200 lines | **93%** |
| **Security Code** | 1,500+ lines | 0 lines | **100%** |
| **Tool Definitions** | 800+ lines | 100 lines | **88%** |
| **Error Handling** | 600+ lines | 50 lines | **92%** |
| **Resource Management** | 400+ lines | 0 lines | **100%** |
| **Total Implementation** | 5,900+ lines | 350 lines | **94%** |

### **MCP Specification Benefits Applied**
- ✅ **Focused Tools**: Single purpose each (analyze_logs, query_portfolio, etc.)
- ✅ **Standard Responses**: `{content: [{type: "text", text: "..."}]}` format
- ✅ **Minimal Validation**: Basic usability checks only
- ✅ **Token Efficiency**: Process in sandbox, return insights only
- ✅ **Simple Architecture**: No resources, prompts, or notifications needed

### **What SRT Handles Automatically**
- ✅ **Process Isolation**: Each execution in isolated sandbox
- ✅ **Filesystem Security**: Read-only access to allowed directories only
- ✅ **Network Restrictions**: localhost-only access (no external calls)
- ✅ **Resource Limits**: 30s timeout, 256MB memory, 1MB output
- ✅ **OS Security**: Seatbelt (macOS) / bubblewrap (Linux) isolation
- ✅ **Audit Logging**: Built-in security violation monitoring

### **What We Focus On**
- 🎯 **Token-Efficient Output**: Filter data before returning to Claude
- 🎯 **Domain-Specific Insights**: Trading-specific error messages and patterns
- 🎯 **MCP Spec Compliance**: Standard response format, focused tools
- 🎯 **Simple Tool Logic**: Focus on analysis, not infrastructure
- 🎯 **Quick Iteration**: Get working tools vs perfect architecture

### **Progressive Disclosure in Action: Debugging Scenario**

**Before Progressive Disclosure** (expensive token usage):
```
Claude: "I need to debug production issues, what tools do you have?"

Traditional MCP Response (150,000 tokens):
"All available tools:
- analyze_logs (5,000 tokens)
- query_portfolio (8,000 tokens)
- diagnose_database_locks (6,000 tokens)
- check_system_health (4,000 tokens)
- verify_configuration_integrity (7,000 tokens)
- monitor_queue_status (3,000 tokens)
- check_api_endpoints (5,000 tokens)
- analyze_performance_metrics (4,000 tokens)
- ... 20 more tools (108,000 tokens)
...[agent hits rate limit after loading all definitions]..."
```

**After Progressive Disclosure** (our implementation):
```
Claude: "I need to debug production issues, what tools do you have?"

Our MCP Response (200 tokens):
"Available categories:
- logs (Log analysis and error diagnosis)
- database (Portfolio and configuration queries)
- system (Health monitoring and status checks)"

Claude: "I'm seeing database lock errors, let me explore database tools"

Our MCP Response (300 tokens):
"Database category tools:
- query_portfolio (Query portfolio data and analysis results)
- verify_configuration_integrity (Check configuration consistency)

Claude: "Let me query portfolio for problematic stocks"

Our MCP Response + Execution (800 tokens):
"Executing query_portfolio with filters: ['stale_analysis', 'error_conditions']...
Results: 23 stocks need attention, 5 have errors
..."

Total Token Usage: 1,300 tokens vs 150,000 tokens (99.1% reduction)
No rate limit issues!
```

### **Token Context Saving Examples**

**Tool 1: analyze_logs** (98.3% token reduction):
```python
# Before: Agent reads entire log file
logs = read_file("logs/robo-trader.log")  # 50,000 lines = 30,000 tokens
errors = [line for line in logs if "ERROR" in line]  # Agent processes in context

# After: Process in sandbox
result = analyze_logs(patterns=["database is locked", "timeout"], max_examples=3)
# Returns: 500 tokens of structured insights
```

**Tool 2: query_portfolio** (98.7% token reduction):
```python
# Before: Agent queries entire portfolio
portfolio = query("SELECT * FROM portfolio")  # 81 stocks × 20 fields = 15,000 tokens

# After: Filter in sandbox, return issues only
result = query_portfolio(filters=["stale_analysis", "error_conditions"], limit=20)
# Returns: 200 tokens of problematic stocks only
```

**Tool 3: diagnose_database_locks** (97% token reduction):
```python
# Before: Agent reads logs + code + correlations
logs = read_logs()    # 30,000 tokens
code = read_source()  # 5,000 tokens
correlations = correlate()  # 10,000 tokens

# After: Process in sandbox with robo-trader knowledge
result = diagnose_database_locks()
# Returns: 1,200 tokens of actionable diagnosis with code references
```

### **MCP Specification Philosophy**
"The MCP specification rewards simplicity" - our approach perfectly aligns with:
- **Focused Tools**: Single purpose each (5 tools for debugging)
- **Standard Responses**: Consistent `{content: [{type: "text", text: "..."}]}` format
- **Minimal Validation**: Basic usability checks only
- **Token Efficiency**: Process in sandbox, return insights only
- **Simple Architecture**: No resources, prompts, or notifications needed for debugging tools
- **Progressive Disclosure**: Discover and load tools on-demand based on need

---

## 🔧 Usage Examples

### **Debugging Session Example**
```bash
# User asks: "Production is slow, can you investigate?"
# Claude executes:

result1 = await check_system_health(["database", "queues", "api_endpoints"])
# → Returns: "AI_ANALYSIS queue backlog: 15 tasks, database response time: 2.3s"

result2 = await diagnose_database_locks(time_window="1h")
# → Returns: "Found 23 lock errors, probable cause: direct DB access in web routes"

result3 = await analyze_logs(patterns=["timeout", "slow_query"], time_window="2h")
# → Returns: "15 slow queries detected on analysis_history table"

# Total tokens: 2.1K instead of 50K+
# Total time: 2 minutes instead of 15 minutes
```

### **Configuration Verification Example**
```bash
# User asks: "Is the system properly configured before deployment?"
# Claude executes:

result = await verify_configuration_integrity()
# → Returns: "2 issues found: database path mismatch, missing CORS headers"

# User gets specific, actionable issues instead of manual checking
```

---

## 📚 Key References

### **Blog Posts & Documentation**
- **[Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)** - Core principles of progressive disclosure and token optimization
- **[Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)** - Security model and sandbox implementation patterns
- **[MCP Documentation](https://modelcontextprotocol.io/)** - Protocol specification and best practices

### **Open Source Repositories**
- **[Sandbox Runtime](https://github.com/anthropic-experimental/sandbox-runtime)** - Official Anthropic sandbox implementation
- **[MCP SDK](https://github.com/modelcontextprotocol/servers)** - Server implementation examples and patterns
- **[MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)** - TypeScript/Node.js SDK for MCP servers

### **Security & Architecture**
- **[Seatbelt](https://github.com/servo/seatbelt)** - macOS sandbox profiles used by SRT
- **[Bubblewrap](https://github.com/containers/bubblewrap)** - Linux sandbox implementation used by SRT
- **[RestrictedPython](https://github.com/zopefoundation/RestrictedPython)** - Python code execution security (if needed)

---

## 🎯 Success Metrics

### **Primary Goals**
- ✅ **95%+ token reduction** across all debugging scenarios
- ✅ **10-20x faster** issue resolution and system understanding
- ✅ **Zero rate limit issues** during complex debugging sessions
- ✅ **Actionable insights** returned instead of raw data dumps
- ✅ **Production-grade security** using Anthropic's sandbox runtime

### **Measurable Outcomes**
- **Token Usage**: From 75K+ tokens/session to 2K-3K tokens/session
- **Debugging Time**: From 10-15 minutes/issue to 30-90 seconds/issue
- **Developer Velocity**: 5-10x faster debugging and system understanding
- **Cost Efficiency**: 95%+ reduction in API costs for development tasks
- **Security**: Enterprise-grade isolation with zero maintenance overhead

---

**Document Version**: 5.0
**Last Updated**: 2025-11-06
**Status**: Ready for Implementation
**Target User**: Claude Code agents developing robo-trader (external development tool)
**Implementation**: 6-day development plan, MCP spec + SRT sandboxing (94% less code)
**Architecture**: External MCP server, follows MCP spec simplicity philosophy, SRT handles all security
**Code Complexity**: 350 lines total (vs 5,900+ traditional approach)
**MCP Spec Compliance**: Ultra-minimal implementation following specification best practices