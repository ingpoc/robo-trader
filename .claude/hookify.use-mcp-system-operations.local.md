---
name: use-mcp-system-operations
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: ps\s+aux|top\s|htop|iostat|vmstat|df\s+-|free\s|du\s+-
action: warn
---

⚡ Use `check_system_health()` or `coordinator_status()` MCP tools.
Comprehensive health data with 92%+ token savings.
