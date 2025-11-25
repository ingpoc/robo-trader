---
name: db-read-to-mcp
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: sqlite3\s+.*robo_trader\.db|\.read.*state/|cat\s+.*\.db
action: block
---

🚫 BLOCKED: Use MCP for database reads.
Run `search_tools(query="portfolio", category_filter="data")` to discover tools.
95%+ token reduction with pre-aggregated insights.
