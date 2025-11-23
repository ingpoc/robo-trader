---
name: use-mcp-safe-execution
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (pkill|killall).*-f.*python.*src|(xargs.*)?kill.*-9.*(python|src)|(sqlite3.*robo_trader\.db.*(INSERT|UPDATE|DELETE))|(db\.connection\.execute.*(INSERT|UPDATE|DELETE|CREATE))
action: warn
---

⚠️ **Direct database/process manipulation detected**

This pattern bypasses safety mechanisms:
- **Processes**: Use `lsof -ti:PORT | xargs kill -9` for port cleanup only
- **Database**: Use `config_state.store_*()` methods (locked state management)
- **Direct writes**: Never use sqlite3 CLI or direct connection.execute() for data modifications

Why? Locked state methods prevent "database is locked" errors and maintain consistency.
