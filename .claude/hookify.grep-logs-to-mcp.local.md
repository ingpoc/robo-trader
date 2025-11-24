---
name: grep-logs-to-mcp
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (tail|head|cat)\s+.*\.(log|txt)|(grep|awk)\s+.*(log|LOG|Error|ERROR|Warning|WARNING)|less\s+.*log
action: warn
---

⚡ Use `analyze_logs(patterns=["ERROR"], time_window="1h")` MCP tool.
Returns structured JSON with 95%+ token savings vs raw log output.
