---
name: use-mcp-safe-execution
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (pkill|killall).*-f.*python.*src|(xargs.*)?kill.*-9.*(python|src)|(sqlite3.*robo_trader\.db.*(INSERT|UPDATE|DELETE))
action: block
---

Run `search_tools(query="execute", category_filter="sandbox")` for safer alternatives.
For processes: Kill specific ports only (`lsof -ti:8000 | xargs kill -9`)
