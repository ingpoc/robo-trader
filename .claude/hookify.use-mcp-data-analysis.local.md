---
name: use-mcp-data-analysis
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: sqlite3\s+.*(robo_trader|\.db)|python3?\s+.*(-c\s+.*json|pandas|csv)
action: warn
---

⚡ Use `query_portfolio` or `execute_analysis` MCP tools.
Structured JSON output with 84%+ token savings.
