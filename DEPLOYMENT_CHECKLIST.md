# AnalysisScheduler Deployment Checklist

This document provides a step-by-step guide for deploying the smart periodic analysis scheduler that replaces event-driven task creation.

## Pre-Deployment Verification (Phase 5 Complete)

- [x] **Phase 1**: Database helper methods added to `AnalysisStateManager`
  - `get_last_analysis_timestamp(symbol)`
  - `get_last_recommendation_timestamp(symbol)`
  - `get_stocks_needing_analysis(symbols, hours=24)`

- [x] **Phase 2**: AnalysisScheduler module created
  - `src/core/background_scheduler/analysis_scheduler.py`
  - Runs every 5 minutes to check stocks needing analysis
  - Implements deduplication logic

- [x] **Phase 3**: Comprehensive analysis handler created
  - `src/services/portfolio_intelligence/comprehensive_analyzer.py`
  - Analyzes news + earnings + fundamentals in single Claude session
  - Stores results and creates recommendation

- [x] **Phase 4**: Event handlers modified
  - `handle_news_fetched()` - Now just updates state, doesn't create task
  - `handle_earnings_fetched()` - Now just updates state, doesn't create task
  - `handle_fundamentals_updated()` - Now just updates state, doesn't create task
  - `_trigger_ai_analysis()` method removed

- [x] **Phase 5**: Integration with BackgroundScheduler
  - AnalysisScheduler integrated into BackgroundScheduler lifecycle
  - Task handler registered in DI container
  - Container passed to BackgroundScheduler for initialization

## Pre-Deployment Steps

### 1. Database Verification

```bash
# Check current queue status
curl -s http://localhost:8000/api/system-health | jq '.scheduler_status.ai_analysis_queue'

# Expected output (high numbers before cleanup):
# {
#   "queue_name": "ai_analysis",
#   "pending": 4731,
#   "processing": 0,
#   "completed": 0,
#   "failed": 121,
#   "success_rate": "0.00%"
# }
```

### 2. Backup Database

```bash
# Manual backup before cleanup
curl -X POST 'http://localhost:8000/api/backups/create?label=pre_cleanup'

# Verify backup was created
curl 'http://localhost:8000/api/backups/list?hours=24'
```

### 3. Review Queue Content

```bash
# Dry-run to see what will be deleted
python scripts/clear_ai_analysis_queue.py --dry-run

# Output will show:
# Found 4731 pending AI_ANALYSIS tasks
# Found 121 failed AI_ANALYSIS tasks
# Total: 4852 tasks to delete
```

## Deployment Steps

### Step 1: Verify Backend is Running

```bash
# Check health endpoint
curl -m 3 http://localhost:8000/api/health

# Should return: {"status": "healthy"}
```

### Step 2: Clean the Queue

```bash
# Clear existing pending and failed tasks
# This prepares queue for fresh AnalysisScheduler operation
python scripts/clear_ai_analysis_queue.py --confirm

# Output will show:
# Pending tasks deleted: 4731/4731
# Failed tasks deleted: 121/121
# Total deleted: 4852/4852
```

### Step 3: Verify Queue is Empty

```bash
# Check queue status - should show 0 pending
curl -s http://localhost:8000/api/system-health | jq '.scheduler_status.ai_analysis_queue'

# Expected output:
# {
#   "queue_name": "ai_analysis",
#   "pending": 0,
#   "processing": 0,
#   "completed": 0,
#   "failed": 0,
#   "success_rate": "0.00%"
# }
```

### Step 4: Restart Backend

```bash
# Kill existing backend process
lsof -ti:8000 | xargs kill -9
sleep 2

# Start fresh backend (will initialize AnalysisScheduler)
python -m src.main --command web

# Wait for startup (30-60 seconds)
sleep 30

# Verify health
curl -m 3 http://localhost:8000/api/health
```

### Step 5: Verify AnalysisScheduler Started

```bash
# Check backend logs for AnalysisScheduler startup messages
tail -f logs/robo-trader.log | grep -i "analysis_scheduler"

# Expected log messages:
# [INIT] Initializing AnalysisScheduler
# [INIT] AnalysisScheduler initialized - OK
# [INIT] Starting AnalysisScheduler
# [INIT] AnalysisScheduler started - OK
# AnalysisScheduler started
```

## Post-Deployment Validation (48 Hours)

### Monitor Queue Health

```bash
# Check queue status every 5-10 minutes
curl -s http://localhost:8000/api/system-health | jq '.scheduler_status'

# Verify:
# 1. pending < 30 (AnalysisScheduler creates ~1-5 tasks per 5-minute cycle)
# 2. No spike in failed tasks
# 3. Success rate improving (was 0%, should increase)
```

### Monitor Analysis Results

```bash
# Check AI Transparency to see analysis being stored
curl -s http://localhost:8000/api/claude/transparency/analysis | jq '.analysis | keys' | wc -l

# Should see increasing number of analyzed stocks
```

### Monitor Logs for Errors

```bash
# Check for errors or warnings in AnalysisScheduler
tail -f logs/robo-trader.log | grep -E "ERROR|WARNING|analysis_scheduler"

# Watch for:
# 1. Database lock errors (should be none with proper locking)
# 2. Analysis failures (check if model fails, API issues)
# 3. Queue buildup (pending count increasing too fast)
```

### Verify Event Handlers

```bash
# Check that news/earnings/fundamentals events only update state
tail -f logs/robo-trader.log | grep -E "news_fetched|earnings_fetched|fundamentals_updated"

# Should see:
# "News fetched for AAPL (analysis will be scheduled periodically)"
# NOT: "Creating CLAUDE_NEWS_ANALYSIS task"
```

## Rollback Plan

If issues occur, rollback is simple:

### Quick Rollback (Keep Same Data)

```bash
# Stop backend
lsof -ti:8000 | xargs kill -9

# Restart old backend version (before AnalysisScheduler)
git checkout main~1  # Go back one commit
python -m src.main --command web

# System will revert to event-driven task creation
```

### Full Rollback (Restore from Backup)

```bash
# If you need to restore database state
curl -X POST 'http://localhost:8000/api/backups/restore/robo_trader_pre_cleanup_20251110_144523.db'

# Restart backend
lsof -ti:8000 | xargs kill -9
python -m src.main --command web
```

## Success Criteria

After 24-48 hours of operation, verify:

- ✅ **Queue stays small**: Pending AI_ANALYSIS tasks < 30 consistently
- ✅ **No database locks**: No "database is locked" errors in logs
- ✅ **Analysis executes**: New stocks analyzed within 24 hours
- ✅ **Success rate improves**: From 0% to 80%+ success rate
- ✅ **Event handlers work**: news/earnings events only update state
- ✅ **AnalysisScheduler runs**: New analysis tasks queued every 5 minutes
- ✅ **Analysis results stored**: AI Transparency shows growing analysis history

## Troubleshooting

### Issue: Queue still has high pending count

**Symptoms**: Pending count remains > 100 after 1 hour

**Cause**: AnalysisScheduler not running, or already-queued tasks are still being processed

**Resolution**:
1. Check logs: `tail -f logs/robo-trader.log | grep -i analysis_scheduler`
2. Verify AnalysisScheduler started: Should see `AnalysisScheduler started` message
3. Check if old tasks are still executing: Monitor `queue_executor` logs
4. If needed, manually clear queue again: `python scripts/clear_ai_analysis_queue.py --confirm`

### Issue: Database locked errors increase

**Symptoms**: Logs show "database is locked" errors

**Cause**: Concurrent database access without proper locking during analysis

**Resolution**:
1. Review ConfigurationState locking pattern
2. Verify all database state classes use `asyncio.Lock()`
3. Check if analysis tasks are being analyzed in parallel (should be sequential)
4. May need to increase timeout in queue_manager.py

### Issue: Analysis tasks not being created

**Symptoms**: Queue remains empty, no analysis happening

**Cause**: AnalysisScheduler not finding stocks needing analysis

**Resolution**:
1. Check portfolio has holdings: Portfolio should have > 0 stocks
2. Check stock_scheduler_state table: Should have entries for portfolio stocks
3. Check if `get_stocks_needing_analysis()` query is working
4. Manually run analysis scheduler cycle: Add debug logging in analysis_scheduler.py

### Issue: Analysis results not appearing in AI Transparency

**Symptoms**: Queue shows completed tasks, but no analysis history

**Cause**: Analysis stored but not being retrieved by API endpoint

**Resolution**:
1. Check database: Query analysis_history table directly
2. Verify `store_analysis_history()` is being called in comprehensive_analyzer.py
3. Check `/api/claude/transparency/analysis` endpoint implementation
4. Ensure proper database locking in ConfigurationState

## Performance Expectations

### Before Deployment
- AI_ANALYSIS queue: 4,731 pending tasks
- Success rate: 0% (all failing due to queue congestion)
- Memory usage: High (thousands of pending tasks)

### After Deployment (Steady State)
- AI_ANALYSIS queue: ~5-20 pending tasks
- Success rate: ~85-95%
- Memory usage: Low (only current batch in queue)
- API response times: Sub-second (not blocked by analysis)

### Analysis Frequency
- **First analysis**: 5-10 minutes after AnalysisScheduler starts (backlog catch-up)
- **Subsequent**: Every 24 hours for analyzed stocks, or on-demand for new stocks
- **Max concurrent**: 1 analysis task at a time (sequential queue execution)

## Documentation Updates

After successful deployment:

1. Update `CLAUDE.md` with AnalysisScheduler information
2. Document timeout requirements (15 minutes for comprehensive analysis)
3. Update troubleshooting guide with known issues
4. Add operational monitoring procedures
5. Document queue health baseline metrics

## Sign-Off

- [ ] Pre-deployment verification complete
- [ ] Database backed up
- [ ] Queue cleared successfully
- [ ] AnalysisScheduler initialized
- [ ] No errors in first 1 hour
- [ ] Queue health stable (< 30 pending after 6 hours)
- [ ] Analysis results appearing in AI Transparency
- [ ] Event handlers correctly updated state only
- [ ] No database lock errors

---

**Deployment Date**: [FILL IN]
**Deployed By**: [FILL IN]
**Rollback Date** (if needed): [FILL IN]
