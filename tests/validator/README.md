# System Health Validation Testing Suite

> **Purpose**: Centralized validation testing documentation for Robo-Trader System Health page
> **Testing Methodology**: Backtracking Functional Validation
> **Last Updated**: 2025-11-07

## Overview

This folder contains comprehensive validation testing documentation for the System Health page, organized by component and testing methodology. Each file provides detailed test cases, trigger actions, and verification procedures.

## Validation Documents

### 1. SCHEDULERS_VALIDATION.md

**Focus**: Scheduler Tab Testing
**Scope**: All 7 schedulers in the system
**Tests**: 60+ individual test cases
**Duration**: ~3.5 hours for complete validation

**Covers**:
- Background Scheduler (Event-Driven)
- Portfolio Sync Scheduler (PORTFOLIO_SYNC queue)
- Data Fetcher Scheduler (DATA_FETCHER queue)
- AI Analysis Scheduler (AI_ANALYSIS queue) ⚠️ CRITICAL BUGS
- Portfolio Analysis Scheduler (PORTFOLIO_ANALYSIS queue)
- Paper Trading Research Scheduler (PAPER_TRADING_RESEARCH queue)
- Paper Trading Execution Scheduler (PAPER_TRADING_EXECUTION queue)

**Key Features**:
- Per-scheduler test cases (7-9 tests each)
- Trigger endpoints for each scheduler
- Expected behavior documentation
- Known issues and bugs with evidence
- Cross-scheduler validation tests
- Test execution workflow (4 phases)
- Quick reference guide

**Critical Bugs Documented**:
1. Failed tasks not displayed in UI (CRITICAL)
2. AI Analysis turn limit exhaustion (ARCHITECTURAL)
3. WebSocket message incompleteness (INFORMATIONAL)

**Use This File When**:
- Testing Schedulers tab functionality
- Verifying scheduler trigger actions work
- Checking real-time metric updates
- Debugging scheduler failures
- Validating queue-based execution

---

### 2. UI_FUNCTIONAL_TESTING_REFERENCE.md

**Focus**: Frontend UI Component Testing
**Scope**: Complete System Health page UI
**Tests**: Component rendering, interaction, accessibility
**Duration**: Varies by component

**Key Sections**:
- Component hierarchy and structure
- UI element reference (buttons, cards, tables)
- Accessibility compliance testing
- Visual regression testing
- Interaction pattern testing

**Use This File When**:
- Testing frontend component behavior
- Verifying UI renders correctly
- Checking accessibility standards
- Validating form inputs and interactions
- Testing responsive design

---

### 3. FUNCTIONAL_TESTING_REPORT_20251104.md

**Focus**: Historical Test Execution Report
**Scope**: Test results from 2025-11-04
**Tests**: Previously executed test cases
**Duration**: Reference document

**Key Content**:
- Test execution results
- Pass/fail status for components
- Issues identified during testing
- Recommendations for fixes

**Use This File When**:
- Reviewing historical test results
- Understanding previously found issues
- Tracking regression from past tests
- Comparing current vs. past behavior

---

## Testing Methodology: Backtracking Functional Validation

### Core Principle

**"Every number you see, trigger an action to make it change"**

Instead of static UI inspection, this methodology emphasizes:
1. **Observe** - Note current metric values
2. **Trigger** - Perform action that should change metrics
3. **Verify** - Confirm metrics update in real-time
4. **Validate** - Cross-check with API responses

### Workflow

1. **Identify Metric** - What number/field are you testing?
2. **Understand Change** - What action triggers a change?
3. **Trigger Action** - Execute the trigger (API call, user interaction, etc.)
4. **Observe Result** - Did the metric change as expected?
5. **Verify Backend** - Cross-check with API endpoint
6. **Document** - Record pass/fail and any issues

### Why This Approach?

- ✅ Validates end-to-end functionality (UI → API → Backend → UI)
- ✅ Catches silent failures (metrics unchanged despite action)
- ✅ Detects real-time update issues
- ✅ Ensures UI accurately reflects backend state
- ✅ Uncovers timing/race condition bugs

---

## Test Execution Checklist

### Pre-Testing

- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] System Health page accessible at http://localhost:3000/system-health
- [ ] Browser DevTools open (Console + Network tabs)
- [ ] Network WebSocket connection established
- [ ] Current metric values documented

### During Testing

- [ ] Execute trigger action (curl, UI interaction, etc.)
- [ ] Monitor real-time metric updates
- [ ] Cross-check with API responses
- [ ] Record any unexpected behavior
- [ ] Check for console errors or warnings
- [ ] Verify WebSocket messages received

### Post-Testing

- [ ] Document all findings
- [ ] Note any failed tests
- [ ] Record performance metrics
- [ ] Create issue tickets for bugs found
- [ ] Mark tests as pass/fail
- [ ] Summarize test execution

---

## API Endpoints Reference

### Health & Status

```bash
# Overall system health
curl -s 'http://localhost:8000/api/health'

# All schedulers status
curl -s 'http://localhost:8000/api/monitoring/scheduler'

# All queues status
curl -s 'http://localhost:8000/api/queues/status'

# Specific queue status
curl -s 'http://localhost:8000/api/queues/status' | jq '.[] | select(.name=="ai_analysis")'
```

### Scheduler Triggers

```bash
# Portfolio Sync
curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_sync_scheduler/execute'

# Data Fetcher
curl -X POST 'http://localhost:8000/api/configuration/schedulers/data_fetcher_scheduler/execute'

# AI Analysis (LONG DURATION - 30-60+ sec)
curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'

# Portfolio Analysis
curl -X POST 'http://localhost:8000/api/configuration/schedulers/portfolio_analysis_scheduler/execute'

# Paper Trading Research
curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_research_scheduler/execute'

# Paper Trading Execution
curl -X POST 'http://localhost:8000/api/configuration/schedulers/paper_trading_execution_scheduler/execute'
```

### Transparency APIs

```bash
# Claude research activities
curl -s 'http://localhost:8000/api/claude/transparency/research'

# Claude analysis activities
curl -s 'http://localhost:8000/api/claude/transparency/analysis'

# Claude execution activities
curl -s 'http://localhost:8000/api/claude/transparency/execution'
```

---

## Known Critical Issues

### Issue #1: Failed Tasks Not Visible in UI

**Severity**: CRITICAL
**Impact**: System appears healthy when tasks are failing
**Evidence**: Backend tracks `failed_tasks` but UI doesn't display
**Status**: DOCUMENTED - Needs Fix

### Issue #2: AI Analysis Turn Limit on Large Portfolios

**Severity**: HIGH
**Impact**: Analysis fails for 81+ stock portfolios
**Root Cause**: Architectural - should use queue batching
**Status**: WORKAROUND - Use queue submission instead of direct call

### Issue #3: WebSocket Message Incompleteness

**Severity**: MEDIUM
**Impact**: Some metrics not available in real-time
**Status**: DOCUMENTED - Monitoring

---

## Next Steps

1. **Execute Scheduler Tests** (SCHEDULERS_VALIDATION.md)
   - Test each of 7 schedulers individually
   - Estimated: 3.5 hours for complete validation

2. **Fix Critical Bugs**
   - Display `failed_tasks` in UI Errors tab
   - Add failed queue task alerts
   - Update WebSocket message format

3. **Create Automated Tests**
   - Convert manual tests to pytest framework
   - Playwright tests for UI validation
   - API endpoint integration tests

4. **Performance Baseline**
   - Record typical execution times
   - Monitor queue throughput
   - Track scheduler resource usage

5. **Documentation**
   - Create scheduler configuration guide
   - Document troubleshooting procedures
   - Add operational runbooks

---

## File Organization

```
tests/validator/
├── README.md (this file)
├── SCHEDULERS_VALIDATION.md (Scheduler testing guide - 60+ tests)
├── UI_FUNCTIONAL_TESTING_REFERENCE.md (UI component reference)
└── FUNCTIONAL_TESTING_REPORT_20251104.md (Historical test results)
```

---

## Quick Start: Test Your First Scheduler

### 1. Trigger AI Analysis Scheduler

```bash
curl -X POST 'http://localhost:8000/api/configuration/schedulers/ai_analysis_scheduler/execute'
```

### 2. Watch System Health Page

Go to: http://localhost:3000/system-health
Tab: **Schedulers**

### 3. Monitor Queue Status

```bash
curl -s 'http://localhost:8000/api/queues/status' | jq '.[] | select(.name=="ai_analysis")'
```

### 4. Observe Changes

- Watch `pending_tasks` change to `active_tasks`
- Monitor execution duration (30-60+ seconds typical)
- Check if `failed_tasks` appears when task fails
- Verify metrics update in UI without page refresh

### 5. Verify in Backend

Check if failure is tracked:
```bash
# Should see: "failed_tasks": 1 if analysis failed
curl -s 'http://localhost:8000/api/queues/status' | jq '.[] | select(.name=="ai_analysis")'
```

---

## Contact & Issues

Found a bug? Document it and add to SCHEDULERS_VALIDATION.md "Known Issues" section with:
- Bug title
- Reproduction steps
- Expected vs actual behavior
- Screenshots/logs if applicable
- Severity level

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Status**: Active - Ready for Testing
