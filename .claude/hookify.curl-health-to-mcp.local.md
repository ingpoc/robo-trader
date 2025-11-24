---
name: curl-health-to-mcp
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: curl\s+.*localhost:(8000|3000).*/api/(health|status)|curl\s+-[sm]\s+\d+\s+http://localhost
action: warn
---

⚡ Use `check_system_health()` MCP tool instead.
Comprehensive health with actionable recommendations.
