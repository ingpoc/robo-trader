---
name: use-mcp-performance-monitoring
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (find\s+.*\*\.py.*-exec.*grep.*wc\s+-l|awk\s+\{.*print.*\}|for\s+.*in.*\{.*\}.*grep.*-r.*src)
action: warn
---

⚠️ **Code analysis/metrics via bash detected**

Use MCP performance tools for structured insights:

- `task_execution_metrics` - Task stats, error trends (95%+ token reduction)
- `token_metrics_collector` - Token usage efficiency tracking
- `real_time_performance_monitor` - Live CPU, memory, disk I/O metrics
- `smart_cache` - Cache analysis with TTL and refresh strategies

These tools replace manual analysis (find, grep, awk, for loops) with optimized queries.
