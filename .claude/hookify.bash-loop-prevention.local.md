---
name: bash-loop-prevention
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: for\s+\w+\s+in\s+.*\.(txt|log|csv|json|py).*do.*(cat|grep|awk|sed)
action: block
---

🚫 BLOCKED: File processing loop detected.

Instead of: `for file in *.log; do cat $file | grep ERROR; done`

Use MCP tools:
- `mcp__robo-trader-dev__analyze_logs(patterns=["ERROR"], time_window="24h")` (98% token savings)
- `mcp__robo-trader-dev__execute_analysis(analysis_type="aggregate", data={...})` (99% savings)
- `mcp__robo-trader-dev__workflow_orchestrator(steps=[...])` to chain operations (87% savings)

These handle batch processing efficiently with caching.
