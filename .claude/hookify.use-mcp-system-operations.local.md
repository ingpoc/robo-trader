---
name: use-mcp-system-operations
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (watch\s+-n|top\s+-b|iostat\s+-x|vmstat\s+\d+|strace\s+-p|htop|nmon|dstat)
action: warn
---

⚠️ **Continuous system monitoring via bash detected**

For sustained monitoring, use MCP tools (they're token-optimized):

- `check_system_health` - Database, queues, API, disk, backups
- `coordinator_status` - Coordinator initialization status
- `real_time_performance_monitor` - CPU, memory, disk I/O metrics

Quick commands like `ps aux`, `top`, `lsof` are fine for debugging.
