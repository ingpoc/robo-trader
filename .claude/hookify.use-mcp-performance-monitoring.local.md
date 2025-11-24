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

⚡ Use `real_time_performance_monitor` or `task_execution_metrics` MCP tools instead.
