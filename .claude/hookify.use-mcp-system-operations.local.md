---
name: use-mcp-system-operations
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: ps\s+aux|top\s|htop|iostat|vmstat|df\s+-|free\s|du\s+-
action: block
---

🚫 BLOCKED: Use MCP for system monitoring.
Run `search_tools(query="health", category_filter="system")` to discover available tools.
92%+ token savings with structured health data.
