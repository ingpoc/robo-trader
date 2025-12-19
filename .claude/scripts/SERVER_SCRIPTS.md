# Robo Trader Server Management Scripts

These scripts reduce context usage by automating repetitive server tasks consistently.

## Location
All server scripts are now in `.claude/scripts/`

## Available Scripts

### 1. `kill_servers.sh`
Kills any processes running on ports 3000 and 8000.
```bash
./.claude/scripts/kill_servers.sh
```

### 2. `start_servers.sh`
Starts both backend and frontend servers with proper environment variables and logging.
- Backend: Python FastAPI server on port 8000
- Frontend: Node.js dev server on port 3000
- Logs are saved to `logs/backend.log` and `logs/frontend.log`
- PIDs are saved to `.backend_pid` and `.frontend_pid` for tracking

```bash
./.claude/scripts/start_servers.sh
```

### 3. `health_check.sh`
Quick health status of all services:
- Process status (running/stopped)
- API health checks
- Database existence and size
- Recent errors in logs

```bash
./.claude/scripts/health_check.sh
```

### 4. `quick_verification.sh`
Outputs structured JSON for verifier-agent:
- Project health (servers, database, config)
- List of critical issues
- Progress summary from feature-list.json

```bash
./.claude/scripts/quick_verification.sh | jq .
```

## Usage by Agents

### Verifier Agent
The verifier-agent should use `quick_verification.sh` to get a complete system status in a single command:
```bash
# Get full verification as JSON
./.claude/scripts/quick_verification.sh

# Parse specific parts
./.claude/scripts/quick_verification.sh | jq '.issues'
./.claude/scripts/quick_verification.sh | jq '.progress.percentage'
```

### Coding Agent
When starting work:
```bash
# Clean start
./.claude/scripts/kill_servers.sh
./.claude/scripts/start_servers.sh

# Check health
./.claude/scripts/health_check.sh
```

## Context Savings

Using these scripts instead of manual commands:
- **Reduces context usage by ~80%** for server management
- **Standardizes output format** (JSON for structured data)
- **Eliminates variations** in how tasks are performed
- **Provides consistent error handling**

## Example Outputs

### Health Check Output
```
🔍 Robo Trader Health Check
=========================

1. Process Status:
✅ Backend process running (PID: 12345)
❌ Frontend process not running

2. API Health:
✅ Backend API responding
   ok
❌ Frontend not responding
...
```

### Verification JSON Output
```json
{
  "project_health": {
    "servers": {
      "backend": "running",
      "frontend": "stopped"
    },
    "database": {
      "status": "exists",
      "size": "832K",
      "tables": 55
    }
  },
  "issues": [
    {
      "type": "import_error",
      "message": "Tests using wrong import..."
    }
  ],
  "progress": {
    "total": 52,
    "completed": 44,
    "percentage": 84.6
  }
}
```

## Best Practices

1. **Always use scripts** instead of manual commands for repetitive tasks
2. **Check JSON output** for programmatic decisions
3. **Monitor logs** with `tail -f logs/backend.log`
4. **Stop servers** before code changes with `kill_servers.sh`