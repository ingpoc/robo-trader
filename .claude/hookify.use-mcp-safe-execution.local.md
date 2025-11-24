---
name: use-mcp-safe-execution
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (pkill|killall).*-f.*python.*src|(xargs.*)?kill.*-9.*(python|src)|(sqlite3.*robo_trader\.db.*(INSERT|UPDATE|DELETE))
action: warn
---

⚡ Use `execute_python` or `execute_analysis` MCP tools for safer operations.
For processes: Kill specific ports only (`lsof -ti:8000 | xargs kill -9`)
