---
name: use-mcp-performance-monitoring
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (find\s+.*\*\.py.*-exec.*grep.*wc\s+-l|awk\s+\{.*print.*\}|for\s+.*in.*\{.*\}.*grep.*-r.*src)
action: block
---

🚫 BLOCKED: Use MCP for performance monitoring.
Run `search_tools(query="performance", category_filter="monitoring")` to discover tools.
