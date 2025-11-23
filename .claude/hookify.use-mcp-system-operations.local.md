---
name: use-mcp-system-operations
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (ps\s+aux|top\s+-n\s+\d+|iostat|vmstat|watch\s+|strace|lsof\s+-.*p\s+\d+)
action: warn
---

⚠️ **System monitoring via bash detected**

Use MCP tools for system inspection - they're designed for robo-trader:

- `check_system_health` - Database, queues, API, disk, backups
- `coordinator_status` - Coordinator initialization status
- `queue_status` - Queue depth and task analysis
- `diagnose_database_locks` - Lock issues with code references
- `real_time_performance_monitor` - CPU, memory, disk I/O monitoring

MCP tools save tokens (95%+ reduction) and provide structured insights.
