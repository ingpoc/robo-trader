---
name: use-mcp-data-analysis
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (sqlite3\s+.*robo_trader\.db.*(SELECT|JOIN|GROUP\s+BY))|((python|python3)\s+-c.*(json\.load|pandas|pd\.read))
action: warn
---

⚠️ **Data analysis via bash detected**

Use MCP data analysis tools - they're token-optimized for robo-trader:

- `query_portfolio` - Portfolio database queries with aggregation
- `analyze_logs` - Log analysis with error pattern grouping
- `execute_analysis` - Pre-configured filters, aggregation, transforms, validation
- `execute_python` - Sandboxed Python execution with context injection

These tools reduce token overhead by 95%+ vs manual queries.
