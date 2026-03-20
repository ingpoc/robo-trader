# Robo Trader - Task Completion Checklist

## After completing any feature/fix:

### 1. Update Progress
- Update `.claude/progress/feature-list.json` with completed status
- Update `.claude/progress/session-state.json` if active session
- Write summary to `.claude/progress/claude-progress.txt`

### 2. Test
```bash
# Run backend tests
pytest

# Run frontend tests
cd ui && npm test

# Check health endpoints
curl -m 3 http://localhost:8000/api/health
curl -m 3 http://localhost:3000
```

### 3. Verify
- Check logs for ERROR/exceptions: `tail -f logs/*.log`
- Test in UI if applicable
- Verify no database locks
- Verify queue processing (if queue-related)

### 4. Restart
```bash
# Restart backend after code changes
lsof -ti:8000 | xargs kill -9
python -m src.main --command web
```

### 5. Commit
- Use conventional commits: `feat:`, `fix:`, `refactor:`
- Reference feature from feature-list if applicable

## Common Issues to Check
- [ ] No "database is locked" errors
- [ ] Event loop is running correctly
- [ ] Services are registered with correct names
- [ ] SDK client is properly initialized
- [ ] No import errors
- [ ] UI connects to WebSocket
