---
name: grep-logs-to-mcp
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (tail|head|cat)\s+.*\.(log|txt)|(grep|awk)\s+.*(log|LOG|Error|ERROR|Warning|WARNING)|less\s+.*log
action: block
---

🚫 BLOCKED: Use MCP for log analysis.
Run `search_tools(query="logs", category_filter="monitoring")` to discover tools.
95%+ token savings with structured JSON output.
