---
name: curl-health-to-mcp
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: ^curl\s+.*localhost:(8000|3000).*/api/(health|status)|^curl\s+-[sm]\s+\d+\s+http://localhost
action: block
---

🚫 BLOCKED: Use MCP for standalone health checks.
Run `search_tools(query="health", category_filter="system")` to discover tools.
Note: curl is allowed in compound commands (e.g., server restart && curl).
