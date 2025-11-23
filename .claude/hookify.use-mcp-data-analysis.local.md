---
name: use-mcp-data-analysis
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (sqlite3\s+.*robo_trader\.db.*(SELECT.*JOIN|SELECT.*GROUP\s+BY|SELECT.*WHERE.*AND.*AND))|((python|python3)\s+-c.*(pandas|pd\.read|DataFrame))
action: warn
---

⚠️ **Complex data analysis via bash detected**

For multi-table or aggregated queries, use MCP tools (token-optimized):

- `query_portfolio` - Portfolio database queries with aggregation
- `analyze_logs` - Log analysis with error pattern grouping
- `execute_analysis` - Pre-configured filters, aggregation, transforms
- `execute_python` - Sandboxed Python with context injection

Simple queries like `SELECT count(*) FROM table` are fine.
