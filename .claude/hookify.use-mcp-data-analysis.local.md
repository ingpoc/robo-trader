---
name: use-mcp-data-analysis
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: sqlite3\s+.*(robo_trader|\.db)|python3?\s+.*(-c\s+.*json|pandas|csv)
action: block
---

🚫 BLOCKED: Use MCP for database/data operations.
Run `search_tools(query="portfolio", category_filter="data")` to discover tools.
84%+ token savings with structured JSON output.
