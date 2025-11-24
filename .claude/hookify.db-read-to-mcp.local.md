---
name: db-read-to-mcp
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: sqlite3\s+.*robo_trader\.db|\.read.*state/|cat\s+.*\.db
action: warn
---

⚡ Use `query_portfolio(aggregation_only=True)` MCP tool instead.
Pre-aggregated insights with 95%+ token reduction.
