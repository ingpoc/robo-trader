# Robo Trader - UI Functional Testing Reference

> **Last Updated**: 2025-11-04 | **Status**: Authoritative Reference | **Purpose**: Complete UI → Database → UI verification mapping

This document is the definitive reference for functional testing the Robo Trader UI. It maps every UI interaction to its expected database updates and UI reflections across the system.

**Use This Document For**:
- Manual UI testing workflows
- Creating automated test cases
- Debugging UI-backend mismatches
- Verifying data persistence after code changes
- Understanding complete system data flows

---

## Table of Contents

1. [Configuration Tab](#1-configuration-tab)
2. [System Health Page](#2-system-health-page)
3. [AI Transparency Page](#3-ai-transparency-page)
4. [Paper Trading Page](#4-paper-trading-page)
5. [News & Earnings Page](#5-news--earnings-page)
6. [Dashboard Page](#6-dashboard-page)
7. [Critical Data Flows](#7-critical-data-flows)
8. [Database Reference](#8-database-reference)
9. [WebSocket Events](#9-websocket-events)
10. [API Endpoints](#10-api-endpoints)
11. [Testing Scenarios](#11-testing-scenarios)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Configuration Tab

The Configuration tab allows users to manage AI agents, background schedulers, data sources, and system prompts.

### 1.1 AI Agents Section

#### Action: Portfolio Analyzer - Run Now

**UI Path**: Configuration → AI Agents Tab → Portfolio Analyzer Card → "Run Now" button

**Trigger Element**: Button labeled "Run Now"

**API Endpoint**: `POST /api/configuration/ai-agents/portfolio_analyzer/execute`

**Queue Task Created**:
- **Queue Name**: `AI_ANALYSIS`
- **Task Type**: `RECOMMENDATION_GENERATION`
- **Payload**: `{"agent_name": "portfolio_analyzer", "symbols": null}`
- **Priority**: 7 (high)

**Expected Database Updates**:

1. **Table**: `scheduler_tasks`
   - **Operation**: INSERT
   - **Fields Updated**: task_id, queue_name, task_type, payload, status, priority, created_at, updated_at
   - **Example Values**:
     - task_id: `550e8400-e29b-41d4-a716-446655440000`
     - queue_name: `AI_ANALYSIS`
     - task_type: `RECOMMENDATION_GENERATION`
     - status: `PENDING` (initially), then `RUNNING`, then `COMPLETED`
     - priority: 7
     - created_at: `2025-11-04T12:30:00Z`

2. **Table**: `analysis_history` (after task execution completes, typically 5-10 minutes later)
   - **Operation**: INSERT (multiple rows, one per stock analyzed)
   - **Fields Updated**: symbol, timestamp, analysis, created_at
   - **Example Values**:
     - symbol: `AAPL`
     - timestamp: `2025-11-04T12:35:00Z`
     - analysis: `{full_claude_response_json_object}`
     - created_at: `2025-11-04T12:35:45Z`

3. **Table**: `recommendations` (after analysis completes)
   - **Operation**: INSERT (multiple rows, 1-2 per stock)
   - **Fields Updated**: symbol, recommendation_type, confidence_score, reasoning, analysis_type, created_at
   - **Example Values**:
     - symbol: `AAPL`
     - recommendation_type: `BUY`
     - confidence_score: 0.85
     - reasoning: `"Strong fundamentals with positive earnings outlook..."`
     - analysis_type: `portfolio_intelligence`
     - created_at: `2025-11-04T12:35:45Z`

**Expected UI Reflections**:

1. **Toast Notification** (Immediate):
   - **Message**: "AI Agent execution initiated. Check System Health for progress."
   - **How to Verify**: Green notification appears at top right

2. **System Health → Queues Tab** (Within 1-2 seconds, via WebSocket):
   - **What Updates**: AI_ANALYSIS queue "Pending Tasks" count increases by 1
   - **How to Verify**:
     - Navigate to System Health → Queues Tab
     - Look for "AI_ANALYSIS Queue" card
     - Check "Pending Tasks" shows correct count
     - Check "In Progress" field shows task_id or null
   - **WebSocket Event Triggered**: `queue_status_update`

3. **System Health → Schedulers Tab** (After execution completes, 5-10 minutes later):
   - **What Updates**:
     - "Total Executions" count increases
     - "Completed Today" count increases
     - "Last Execution Time" updates to current timestamp
   - **How to Verify**:
     - Navigate to System Health → Schedulers Tab
     - Scroll to "AI Analysis Agents" section
     - Verify statistics updated

4. **AI Transparency → Recommendations Tab** (After execution completes):
   - **What Updates**: New recommendation cards appear with:
     - Stock symbol
     - Recommendation type (BUY/SELL/HOLD)
     - Confidence score (as percentage, e.g., 85%)
     - Detailed reasoning text from Claude
     - Analysis type ("portfolio_intelligence")
     - Timestamp of when analysis was created
   - **How to Verify**:
     - Navigate to AI Transparency → Recommendations Tab
     - Look for new entries at top of list (sorted by created_at DESC)
     - Click on recommendation card to expand and view full Claude reasoning

5. **AI Transparency → Sessions Tab** (If sessions are tracked):
   - **What Updates**: New session entry appears showing:
     - Session ID
     - Session type: "portfolio_analyzer"
     - Timestamp of when analysis started
     - Token usage (input + output)
     - Cost in USD
   - **How to Verify**:
     - Navigate to AI Transparency → Sessions Tab
     - Look for new session entry matching execution time

**Verification Steps**:

1. Click "Run Now" button on Portfolio Analyzer
2. Verify green toast notification appears: "AI Agent execution initiated..."
3. Navigate to System Health → Queues Tab
4. Verify AI_ANALYSIS queue shows task in "Pending Tasks" or "In Progress"
5. Wait 5-10 minutes for AI analysis to complete (Claude analysis is slow)
6. Check System Health → Schedulers Tab → Statistics show execution
7. Navigate to AI Transparency → Recommendations Tab
8. Verify new recommendations appear with your portfolio symbols
9. Click on a recommendation to verify Claude analysis content is present

**Database Verification Query**:
```sql
-- Check that analysis was created
SELECT symbol, created_at, LENGTH(analysis) as analysis_length
FROM analysis_history
WHERE created_at > datetime('now', '-15 minutes')
ORDER BY created_at DESC;

-- Check recommendations were created
SELECT symbol, recommendation_type, confidence_score, reasoning
FROM recommendations
WHERE created_at > datetime('now', '-15 minutes')
ORDER BY created_at DESC;

-- Check task status in queue
SELECT task_id, status, created_at, updated_at
FROM scheduler_tasks
WHERE task_type = 'RECOMMENDATION_GENERATION' AND queue_name = 'AI_ANALYSIS'
ORDER BY created_at DESC LIMIT 1;
```

**Expected Timeline**:
- Task creation: <1 second
- Task queuing: Instant
- Task execution: 5-10 minutes (Claude analysis with timeout protection)
- Database write: <1 second after execution
- UI update via WebSocket: <1 second
- UI update via polling: <5 seconds

**Common Issues & Solutions**:

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Task timeout after 15 minutes | Analyzing too many stocks in one session | Queue system batches stocks (2-3 per task), each in separate Claude session |
| No recommendations appear | Database write failed or analysis error | Check backend logs for Claude SDK errors or database lock issues |
| UI doesn't update after execution | WebSocket disconnected | Refresh page to trigger API polling, or check WebSocket connection |
| "Database is locked" error | Direct database access bypassing locks | Verify ConfigurationState uses async locks, all web endpoints use locked methods |
| Task marked FAILED | Execution error in Claude analysis | Check execution_history table for error_message field |

---

#### Action: Portfolio Analyzer - View Status

**UI Path**: Configuration → AI Agents Tab → Portfolio Analyzer Card → Status Indicator

**Trigger Element**: Status dot (green=enabled, gray=disabled)

**Display Information**:
- Current status (enabled/disabled)
- Claude usage: Yes/No
- Response frequency: Time interval
- Scope: Portfolio-wide or specific symbols
- Last execution: Timestamp (from execution_history table)

**No Database Write** - This is a read-only action displaying configuration

**Expected Database Query**:
```sql
SELECT enabled, use_claude, response_frequency, response_frequency_unit, scope, last_execution_time
FROM ai_agents_config
WHERE agent_name = 'portfolio_analyzer';
```

---

### 1.2 Background Tasks (Schedulers) Section

#### Action: News Processor - Run Now

**UI Path**: Configuration → Background Tasks Tab → News Processor Card → "Run Now" button

**Trigger Element**: Button labeled "Run Now"

**API Endpoint**: `POST /api/configuration/schedulers/news_processor/execute`

**Queue Task Created**:
- **Queue Name**: `DATA_FETCHER`
- **Task Type**: `NEWS_PROCESSOR_RUN` (or `FUNDAMENTALS_UPDATE`)
- **Payload**: `{"symbols": null, "manual_trigger": true}`
- **Priority**: 8 (higher priority for manual triggers)

**Expected Database Updates**:

1. **Table**: `scheduler_tasks`
   - **Operation**: INSERT
   - **Fields**: task_id, queue_name, task_type, payload, status, priority, created_at, updated_at
   - **Example Values**:
     - queue_name: `DATA_FETCHER`
     - task_type: `NEWS_PROCESSOR_RUN`
     - status: `PENDING` → `RUNNING` → `COMPLETED`

2. **Table**: `execution_history`
   - **Operation**: INSERT (after task completion)
   - **Fields**: task_name, task_type, status, execution_time_seconds, data_fetched_count, error_message, created_at
   - **Example Values**:
     - task_name: `news_processor`
     - status: `COMPLETED`
     - execution_time_seconds: 45.5
     - data_fetched_count: 25 (number of articles fetched)

3. **Table**: `news_earnings_data`
   - **Operation**: INSERT/UPDATE (multiple rows)
   - **Fields**: symbol, news_title, news_source, news_content, sentiment_score, published_at, fetched_at
   - **Example Values**:
     - symbol: `AAPL`
     - news_title: `"Apple Announces Record Quarterly Results"`
     - news_source: `Reuters`
     - sentiment_score: 0.78 (positive)
     - published_at: `2025-11-04T10:00:00Z`
     - fetched_at: `2025-11-04T12:35:00Z`

**Expected UI Reflections**:

1. **Toast Notification** (Immediate):
   - **Message**: "News Processor execution initiated..."
   - **How to Verify**: Green notification at top right

2. **System Health → Schedulers Tab** (After execution):
   - **What Updates**:
     - News Processor "Jobs Processed" count increases
     - "Last Run" timestamp updates
     - "Status" shows completed with green checkmark
   - **How to Verify**: Navigate to System Health → Schedulers → look for News Processor card

3. **News & Earnings Page** (If news fetched successfully):
   - **What Updates**:
     - News tab populates with fresh articles
     - Article timestamps show recent fetch time
     - Sentiment scores display for each article
   - **How to Verify**:
     - Navigate to News & Earnings page
     - Select a symbol from dropdown (or view all)
     - Click News tab
     - Verify recent articles appear with timestamps

**Verification Steps**:

1. Click "Run Now" on News Processor
2. Verify toast notification appears
3. Navigate to System Health → Schedulers Tab
4. Verify News Processor shows recent execution
5. Wait 30-60 seconds for task to complete
6. Navigate to News & Earnings page
7. Verify new articles appear with recent timestamps
8. Check sentiment scores are populated (0.0-1.0 range)

**Database Verification Query**:
```sql
-- Check execution history
SELECT task_name, status, execution_time_seconds, data_fetched_count, created_at
FROM execution_history
WHERE task_name = 'news_processor' AND created_at > datetime('now', '-5 minutes')
ORDER BY created_at DESC LIMIT 1;

-- Check new news articles
SELECT symbol, news_title, sentiment_score, fetched_at
FROM news_earnings_data
WHERE fetched_at > datetime('now', '-5 minutes')
ORDER BY fetched_at DESC
LIMIT 10;

-- Check task in queue
SELECT task_id, queue_name, status, created_at
FROM scheduler_tasks
WHERE queue_name = 'DATA_FETCHER' AND created_at > datetime('now', '-10 minutes')
ORDER BY created_at DESC LIMIT 1;
```

**Expected Timeline**:
- Task creation: <1 second
- Task execution: 30-60 seconds (depends on number of symbols and API response time)
- Database write: <1 second after execution
- UI update: <5 seconds (polling)
- News & Earnings page: Manual refresh needed or WebSocket update if implemented

**Common Issues**:

| Issue | Solution |
|-------|----------|
| No news articles fetched | Check Perplexity API credentials, verify symbols in portfolio |
| Execution timeout (>90 seconds) | Reduce number of symbols to analyze, or increase timeout |
| News source attribution missing | Verify source parsing in news processor, check API response format |

---

#### Action: Save Configuration Changes

**UI Path**: Configuration → [Any Tab] → "Save Configuration" button (top right)

**Trigger Element**: Button labeled "Save Configuration"

**API Endpoints** (multiple calls):
- `PUT /api/configuration/background-tasks/{task_name}` (for each modified scheduler)
- `PUT /api/configuration/ai-agents/{agent_name}` (for each modified AI agent)
- `PUT /api/configuration/global-settings` (if global settings changed)

**Request Body Example** (for scheduler):
```json
{
  "enabled": true,
  "frequency_seconds": 3600,
  "frequency_unit": "hours",
  "use_claude": true,
  "priority": "high"
}
```

**Expected Database Updates**:

1. **Table**: `background_tasks_config`
   - **Operation**: UPDATE (all fields for specified task)
   - **Fields**: enabled, frequency_seconds, frequency_unit, use_claude, priority, updated_at
   - **Example Values**:
     - enabled: true
     - frequency_seconds: 7200 (2 hours)
     - use_claude: false
     - priority: "high"
     - updated_at: 2025-11-04T12:45:00Z

2. **Table**: `ai_agents_config`
   - **Operation**: UPDATE (all fields for specified agent)
   - **Fields**: enabled, use_claude, response_frequency, response_frequency_unit, scope, max_tokens_per_request, updated_at
   - **Example Values**:
     - enabled: false
     - scope: "portfolio"
     - max_tokens_per_request: 2048
     - updated_at: 2025-11-04T12:45:00Z

3. **JSON Backup Files** (in `config/backups/`):
   - **Operation**: CREATE
   - **Files Created**:
     - `config/backups/config_background_tasks_config_20251104_124500.json`
     - `config/backups/config_ai_agents_config_20251104_124500.json`
   - **Content**: Previous configuration values (before update)

4. **Main Config File** (in `config/`):
   - **Operation**: REPLACE
   - **File**: `config/config.json`
   - **Content**: Full updated configuration snapshot (atomic write pattern)

**Expected UI Reflections**:

1. **Toast Notification** (Immediate):
   - **Message**: "All configuration changes have been saved successfully"
   - **How to Verify**: Green success notification at top right

2. **Configuration Tab** (After save):
   - **What Updates**:
     - Form fields revert to read-only display
     - Save button becomes disabled
     - Updated values persist
   - **How to Verify**: Fields no longer show as modified, save button grayed out

3. **Page Persistence** (After browser refresh):
   - **What Updates**: All configuration changes remain visible
   - **How to Verify**: Refresh page (Cmd+R), verify all changes are still present

4. **Server Persistence** (After backend restart):
   - **What Updates**: Configuration changes survive server restart
   - **How to Verify**: Stop backend, restart it, configuration changes still present

**Verification Steps**:

1. Navigate to Configuration tab (any sub-tab)
2. Make a change (e.g., toggle scheduler enabled status, change frequency)
3. Observe field highlights in yellow/different color (indicating modified state)
4. Click "Save Configuration" button
5. Verify green success toast appears
6. Verify form fields return to normal display (non-modified state)
7. Refresh page (Cmd+R)
8. Verify configuration changes persist
9. Database check: Query the config tables to verify updated_at timestamp

**Database Verification Query**:
```sql
-- Check configuration was updated
SELECT task_name, enabled, frequency_seconds, use_claude, updated_at
FROM background_tasks_config
WHERE updated_at > datetime('now', '-5 minutes')
ORDER BY updated_at DESC;

-- Check backup file was created (verify in file system)
SELECT COUNT(*) as backup_count
FROM sqlite_master
WHERE type='file' AND name LIKE 'config/backups/%';
```

**Verification - File System**:
```bash
# Check that backup files were created
ls -lh config/backups/config_*_*.json | tail -5
```

**Common Issues**:

| Issue | Solution |
|-------|----------|
| Changes lost after refresh | Verify API returned success (HTTP 200), check database updated_at |
| Backup file not created | Ensure config/backups/ directory exists, check backend logs |
| Partial save | If only some fields updated, some APIs may have failed - check response codes |
| Configuration reverted after restart | Check if JSON backup created successfully, verify atomic write pattern |

---

### 1.3 View/Edit AI Prompts

#### Action: View Prompt for Scheduler/Agent

**UI Path**: Configuration → [Background Tasks or AI Agents] → Card → "View Prompt" button

**Trigger Element**: Button labeled "View Prompt" or "Edit Prompt"

**API Endpoint**: `GET /api/configuration/prompts/{task_name}`

**Expected Database Query**:
```sql
SELECT prompt_name, prompt_content, description, created_at, updated_at
FROM ai_prompts_config
WHERE prompt_name = '{task_name}';
```

**Expected UI Display**:

1. **Prompt Modal/Expandable Section**:
   - **Title**: "{Task Name} Prompt"
   - **Read-only Display**: Prompt content shown in text area (readonly initially)
   - **Description**: Helper text explaining what this prompt does
   - **Updated At**: Timestamp of last modification
   - **Buttons**: "Edit", "Copy to Clipboard", "Close"

**No Database Write** - This is a read-only action

---

#### Action: Edit and Save Prompt

**UI Path**: Configuration → [Background Tasks or AI Agents] → Card → "Edit Prompt" button

**Trigger Element**: Button labeled "Edit Prompt"

**API Endpoint** (on save): `PUT /api/configuration/prompts/{task_name}`

**Request Body**:
```json
{
  "prompt_content": "Updated prompt text here...",
  "description": "Updated description of what this prompt does"
}
```

**Expected Database Updates**:

1. **Table**: `ai_prompts_config`
   - **Operation**: UPDATE
   - **Fields**: prompt_content, description, updated_at
   - **Example Values**:
     - prompt_content: `"You are an expert financial analyst..."`
     - updated_at: `2025-11-04T12:50:00Z`

2. **JSON Backup Files** (in `config/backups/`):
   - **Operation**: CREATE (backup of previous prompt)
   - **Files Created**:
     - `config/backups/config_ai_prompts_{task_name}_{timestamp}.json`
   - **Example**: `config/backups/config_ai_prompts_news_processor_20251104_125000.json`
   - **Content**: Previous prompt content (before update)

**Expected UI Reflections**:

1. **Toast Notification**:
   - **Message**: "Prompt for {task_name} saved successfully"
   - **How to Verify**: Green success notification

2. **Prompt Modal**:
   - **What Updates**:
     - Text area returns to read-only mode
     - "Updated At" timestamp changes
   - **How to Verify**: Modal shows confirmation, timestamp updated

3. **Backup Verification**:
   - **What Created**: Backup file in `config/backups/`
   - **How to Verify**: Check file system for new backup file

**Verification Steps**:

1. Click "Edit Prompt" on any task
2. Modal/section opens with editable text area
3. Modify prompt text (change a word or add a sentence)
4. Click "Save Prompt"
5. Verify green success toast: "Prompt for [task name] saved successfully"
6. Verify text area returns to read-only
7. Verify timestamp updated to current time
8. Database check: Query ai_prompts_config for updated_at
9. File check: Verify backup file created in config/backups/

**Database Verification Query**:
```sql
SELECT prompt_name, updated_at, LENGTH(prompt_content) as content_length
FROM ai_prompts_config
WHERE prompt_name = 'news_processor' AND updated_at > datetime('now', '-5 minutes');
```

---

## 2. System Health Page

System Health page provides real-time monitoring of:
- Queue status (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS queues)
- Scheduler execution history
- Database statistics and backups
- System errors and alerts

### 2.1 Queues Tab

**UI Path**: System Health → Queues Tab (auto-loads on page mount)

**Trigger Element**: Tab navigation (no button click required, auto-loads)

**API Endpoint**: `GET /api/monitoring/scheduler` (or similar queue status endpoint)

**Expected Database Queries**:

1. **Queue Statistics** (per queue):
```sql
SELECT
  queue_name,
  SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_count,
  SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running_count,
  SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
  AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_execution_time_seconds
FROM scheduler_tasks
WHERE created_at > datetime('now', '-24 hours')
GROUP BY queue_name;
```

**Expected UI Display**:

1. **Queue Cards** (3 cards, one per queue):

   **Card 1: PORTFOLIO_SYNC Queue**
   - Title: "Portfolio Sync Queue"
   - Pending Tasks: Integer count (e.g., "3")
   - In Progress: Task ID or null (e.g., "550e8400..." or "--")
   - Completed Today: Integer count (e.g., "12")
   - Failed: Integer count (e.g., "0")
   - Avg Task Time: Duration (e.g., "2.5s")
   - Success Rate: Percentage (e.g., "100%")

   **Card 2: DATA_FETCHER Queue**
   - Same structure as above
   - Example values: 1 pending, 45 completed, 0 failed, 45.2s avg time

   **Card 3: AI_ANALYSIS Queue**
   - Same structure as above
   - Example values: 0 pending, 3 completed, 0 failed, 120.5s avg time

2. **Queue Statistics Summary** (below cards):
   - Total tasks across all queues: Integer (e.g., "50")
   - Total completed: Integer (e.g., "47")
   - Success rate: Percentage (e.g., "94%")
   - Failed tasks: Integer (e.g., "3")

**WebSocket Updates**:
- **Event Type**: `queue_status_update`
- **Frequency**: Real-time (whenever task status changes)
- **Payload**:
```json
{
  "queue_name": "AI_ANALYSIS",
  "pending_count": 0,
  "running_count": 0,
  "completed_count": 3,
  "failed_count": 0
}
```

**UI Update Mechanism**:
- **Real-time**: WebSocket event triggers immediate UI update (no delay)
- **Fallback**: If WebSocket unavailable, API polling every 5 seconds
- **Visual Indicator**: Small indicator shows "Live" (green) or "Polling" (yellow) status

**Verification Steps**:

1. Navigate to System Health → Queues Tab
2. Observe 3 queue cards displayed with current statistics
3. Trigger a task execution (e.g., run News Processor from Configuration)
4. Watch Queues Tab in real-time:
   - DATA_FETCHER queue pending count increases by 1
   - "In Progress" field shows task_id
   - Within 30-60 seconds, task moves to "Completed Today"
5. Verify success rate calculation (completed / (completed + failed) * 100)

**Database Verification Query**:
```sql
-- Check current queue status
SELECT queue_name, status, COUNT(*) as count
FROM scheduler_tasks
WHERE created_at > datetime('now', '-24 hours')
GROUP BY queue_name, status
ORDER BY queue_name, status;

-- Check task details
SELECT task_id, queue_name, status, created_at, updated_at,
       CAST((julianday(updated_at) - julianday(created_at)) * 86400 AS INTEGER) as execution_seconds
FROM scheduler_tasks
ORDER BY created_at DESC
LIMIT 10;
```

---

### 2.2 Schedulers Tab

**UI Path**: System Health → Schedulers Tab

**Trigger Element**: Tab navigation

**API Endpoint**: `GET /api/monitoring/scheduler`

**Expected Database Queries**:

```sql
-- Get execution history for each scheduler
SELECT
  task_name,
  COUNT(*) as total_executions,
  SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as successful,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
  AVG(execution_time_seconds) as avg_execution_time,
  MAX(created_at) as last_execution
FROM execution_history
WHERE created_at > datetime('now', '-7 days')
GROUP BY task_name
ORDER BY MAX(created_at) DESC;
```

**Expected UI Display**:

1. **Scheduler Cards** (for each configured scheduler):

   **News Processor Card**:
   - Name: "News Processor"
   - Status: "Running" (green dot) or "Stopped" (gray dot)
   - Jobs Processed: Integer (e.g., "47")
   - Jobs Failed: Integer (e.g., "0")
   - Success Rate: Percentage (e.g., "100%")
   - Last Run: Relative time (e.g., "2 minutes ago")
   - Last Status: "Completed" or "Failed"

   Similar cards for:
   - Earnings Processor
   - Fundamentals Processor
   - (Any other configured schedulers)

2. **Execution Timeline** (below cards):
   - Recent executions listed chronologically (newest first)
   - Each entry shows: scheduler name, status icon, timestamp, duration
   - Example: "News Processor ✅ 2 min ago (45s)"

**Verification Steps**:

1. Navigate to System Health → Schedulers Tab
2. See list of configured schedulers with statistics
3. Trigger a scheduler execution from Configuration tab
4. Watch Schedulers Tab update:
   - "Last Run" changes to "now" or "a few seconds ago"
   - "Jobs Processed" count increases
   - Execution timeline shows new entry at top
5. Database check: Query execution_history table

**Database Verification Query**:
```sql
-- Check execution history
SELECT task_name, status, execution_time_seconds, data_fetched_count, created_at
FROM execution_history
ORDER BY created_at DESC
LIMIT 20;

-- Aggregate statistics
SELECT
  task_name,
  COUNT(*) as total_runs,
  SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as successful,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed
FROM execution_history
WHERE created_at > datetime('now', '-7 days')
GROUP BY task_name;
```

---

## 3. AI Transparency Page

AI Transparency page shows complete visibility into Claude's decisions, analyses, and trading logic.

### 3.1 Recommendations Tab

**UI Path**: AI Transparency → Recommendations Tab

**Trigger Element**: Tab navigation

**API Endpoint**: `GET /api/claude/transparency/analysis`

**Expected Database Queries**:

```sql
-- Get latest analysis records
SELECT symbol, timestamp, analysis, created_at
FROM analysis_history
ORDER BY created_at DESC
LIMIT 50;

-- Get recommendations for display
SELECT symbol, recommendation_type, confidence_score, reasoning, analysis_type, created_at
FROM recommendations
ORDER BY created_at DESC
LIMIT 100;
```

**Expected API Response Format**:
```json
{
  "analysis": {
    "portfolio_analyses": [
      {
        "symbol": "AAPL",
        "timestamp": "2025-11-04T12:35:00Z",
        "analysis_type": "portfolio_intelligence",
        "confidence_score": 0.85,
        "recommendation_type": "BUY",
        "reasoning": "Strong fundamentals with positive earnings outlook. Technical analysis shows bullish trend...",
        "analysis_summary": "Summary of Claude analysis",
        "analysis_content": "Full Claude response JSON object",
        "data_quality": {
          "news": "available",
          "earnings": "available",
          "fundamentals": "available"
        },
        "created_at": "2025-11-04T12:35:45Z"
      },
      {
        "symbol": "MSFT",
        "timestamp": "2025-11-04T12:35:00Z",
        "analysis_type": "portfolio_intelligence",
        "confidence_score": 0.72,
        "recommendation_type": "HOLD",
        "reasoning": "Stable company with moderate growth prospects...",
        ...
      }
    ],
    "portfolio_stats": {
      "total_analyses": 15,
      "symbols_analyzed": 10,
      "avg_confidence": 0.78,
      "total_recommendations": 23,
      "buy_count": 8,
      "sell_count": 3,
      "hold_count": 12
    }
  }
}
```

**Expected UI Display**:

1. **Statistics Summary** (at top):
   - Total Analyses: 15
   - Symbols Analyzed: 10
   - Average Confidence: 78%
   - Buy Recommendations: 8
   - Sell Recommendations: 3
   - Hold Recommendations: 12

2. **Recommendation Cards** (grouped by symbol, sorted by created_at DESC):

   **Card Example - AAPL**:
   - Symbol: "AAPL"
   - Recommendation: "BUY" (with color: green for BUY, red for SELL, yellow for HOLD)
   - Confidence: "85%"
   - Analysis Type: "portfolio_intelligence"
   - Reasoning: "Strong fundamentals with positive earnings outlook..." (expandable)
   - Timestamp: "Nov 4, 2025 12:35 PM"
   - Data Quality Badge: Shows checkmarks for available data sources (earnings ✓, news ✓, fundamentals ✓)

3. **Expandable Details**:
   - Click on card to expand → Shows full Claude analysis
   - Full text of reasoning
   - Data quality breakdown (which sources were available)
   - Timestamp of when analysis was created

**Verification Steps**:

1. Navigate to AI Transparency → Recommendations Tab
2. See statistics summary at top (must have values ≥ 0)
3. Verify recommendation cards appear (should have at least 3 from portfolio analysis)
4. Check each card shows:
   - Symbol ✓
   - Recommendation type (BUY/SELL/HOLD) ✓
   - Confidence score (0-100%) ✓
   - Reasoning text ✓
   - Timestamp ✓
5. Click on a card to expand and view full Claude analysis
6. Verify data quality indicators show which sources were available

**Database Verification Query**:
```sql
-- Check recommendations exist
SELECT symbol, recommendation_type, confidence_score, reasoning, created_at
FROM recommendations
ORDER BY created_at DESC
LIMIT 10;

-- Check analysis records
SELECT symbol, LENGTH(analysis) as analysis_length, created_at
FROM analysis_history
ORDER BY created_at DESC
LIMIT 10;

-- Get statistics matching UI display
SELECT
  COUNT(DISTINCT symbol) as symbols_analyzed,
  COUNT(*) as total_recommendations,
  AVG(confidence_score) as avg_confidence,
  SUM(CASE WHEN recommendation_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
  SUM(CASE WHEN recommendation_type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
  SUM(CASE WHEN recommendation_type = 'HOLD' THEN 1 ELSE 0 END) as hold_count
FROM recommendations;
```

---

### 3.2 Trades Tab

**UI Path**: AI Transparency → Trades Tab

**Trigger Element**: Tab navigation

**API Endpoint**: `GET /api/claude/transparency/execution`

**Expected Database Queries**:

```sql
-- Get trade execution records
SELECT symbol, side, quantity, entry_price, exit_price, status, created_at
FROM paper_trades
ORDER BY created_at DESC
LIMIT 50;
```

**Expected UI Display**:

1. **Trade Cards** (sorted by created_at DESC):

   **Card Example**:
   - Symbol: "AAPL"
   - Side: "BUY" (displayed in green) or "SELL" (in red)
   - Quantity: "10"
   - Entry Price: "₹150.50"
   - Exit Price: "₹152.00" (or "--" if position still open)
   - P&L: "₹15.00" (calculated: (exit - entry) * quantity)
   - P&L %: "0.99%"
   - Status: "OPEN" (green) or "CLOSED" (gray)
   - Timestamp: "Nov 4, 2025 12:35 PM"

2. **Trade Statistics** (if implemented):
   - Total Trades: Integer count
   - Win Rate: Percentage of profitable trades
   - Total P&L: Sum of all trade profits/losses
   - Avg Win Size: Average profit per winning trade
   - Avg Loss Size: Average loss per losing trade

**Verification Steps**:

1. Navigate to AI Transparency → Trades Tab
2. Execute a paper trade from Paper Trading page
3. Return to Trades Tab (may need to refresh)
4. Verify new trade appears in the list
5. Check all fields populated correctly:
   - Symbol ✓
   - Side (BUY/SELL) ✓
   - Quantity ✓
   - Entry Price ✓
   - Status ✓
   - Timestamp ✓

---

### 3.3 Sessions Tab

**UI Path**: AI Transparency → Sessions Tab

**Trigger Element**: Tab navigation

**API Endpoint**: `GET /api/claude/transparency/execution`

**Expected Database Query**:
```sql
SELECT session_id, session_type, success, decisions_made, token_input, token_output,
       ROUND(token_input * 0.003 / 1000 + token_output * 0.006 / 1000, 4) as cost_usd,
       created_at
FROM claude_strategy_logs
ORDER BY created_at DESC
LIMIT 50;
```

**Expected UI Display**:

1. **Session Cards** (sorted by created_at DESC):

   **Card Example**:
   - Session ID: "550e8400-e29b-41d4..."
   - Session Type: "portfolio_analyzer" or "news_processor"
   - Account Type: "paper"
   - Success: "✓ Yes" (green) or "✗ No" (red)
   - Trades Executed: "2"
   - Token Usage: "Input: 5,000 | Output: 2,500"
   - Cost: "$0.09 USD"
   - Timestamp: "Nov 4, 2025 12:35 PM"

2. **Session Statistics** (if implemented):
   - Total Sessions: Integer count
   - Successful Rate: Percentage
   - Total Tokens Used: Integer sum
   - Total Cost: Sum in USD
   - Avg Token Usage: Average tokens per session

**Expected Timeline**:
- Session created when Claude analysis starts
- Token usage recorded during Claude interaction
- Session marked COMPLETED when analysis finishes
- Cost calculated: (input_tokens * 0.003/1000) + (output_tokens * 0.006/1000)

**Verification Steps**:

1. Navigate to AI Transparency → Sessions Tab
2. Trigger Portfolio Analysis from Configuration
3. Wait for analysis to complete (5-10 minutes)
4. Refresh Sessions Tab (or rely on WebSocket update)
5. Verify new session appears with:
   - Matching session type ✓
   - Success marked as yes ✓
   - Token usage shows non-zero values ✓
   - Cost shows in USD ✓
   - Recent timestamp ✓

**Database Verification Query**:
```sql
-- Check session logs
SELECT session_id, session_type, success, token_input, token_output, created_at
FROM claude_strategy_logs
ORDER BY created_at DESC
LIMIT 10;

-- Calculate average cost
SELECT
  AVG((token_input * 0.003 / 1000) + (token_output * 0.006 / 1000)) as avg_cost_usd,
  SUM((token_input * 0.003 / 1000) + (token_output * 0.006 / 1000)) as total_cost_usd,
  COUNT(*) as total_sessions
FROM claude_strategy_logs;
```

---

## 4. Paper Trading Page

Paper Trading page allows users to:
- Execute buy/sell trades
- Manage paper trading accounts
- View positions and history
- Track P&L

### 4.1 Execute Trade

**UI Path**: Paper Trading → Execute Trade Tab (or Trade Form)

**Trigger Element**: "Execute BUY" or "Execute SELL" button (disabled until all fields filled)

**API Endpoint**: `POST /api/paper-trading/execute` *(Note: Currently returns 404, not fully implemented)*

**Expected Request Body**:
```json
{
  "account_type": "paper",
  "symbol": "AAPL",
  "side": "BUY",
  "quantity": 10,
  "order_type": "MARKET",
  "price": null,
  "stop_loss": 148.50,
  "target_price": 155.00
}
```

**Expected Database Updates** (when fully implemented):

1. **Table**: `paper_trades`
   - **Operation**: INSERT
   - **Fields**: trade_id, account_type, symbol, side, quantity, entry_price, stop_loss, target_price, status, created_at
   - **Example Values**:
     - trade_id: `550e8400-e29b-41d4-a716-446655440000`
     - account_type: `paper`
     - symbol: `AAPL`
     - side: `BUY`
     - quantity: 10
     - entry_price: 150.50
     - status: `OPEN`
     - created_at: `2025-11-04T12:50:00Z`

2. **Table**: `paper_accounts`
   - **Operation**: UPDATE
   - **Fields**: cash_balance (decrease), total_positions_value, updated_at
   - **Example Values**:
     - cash_balance: 100000.00 - (10 * 150.50) = 98,495.00
     - updated_at: `2025-11-04T12:50:00Z`

3. **Table**: `portfolio_state`
   - **Operation**: INSERT or UPDATE
   - **Fields**: symbol, quantity, avg_price, current_price, unrealized_pnl, updated_at
   - **Example Values**:
     - symbol: `AAPL`
     - quantity: 10
     - avg_price: 150.50
     - updated_at: `2025-11-04T12:50:00Z`

**Expected UI Reflections**:

1. **Toast Notification** (Immediate):
   - **Message**: "Trade executed successfully"
   - **How to Verify**: Green notification at top

2. **Paper Trading Page Updates** (Immediate or after refresh):

   **Positions Tab**:
   - **What Updates**: New position appears (or existing position quantity increases)
   - **How to Verify**: See position card for AAPL with quantity 10
   - **Fields Visible**: Symbol, Quantity, Avg Price, Current Price, P&L, P&L%

   **Account Balance Summary**:
   - **What Updates**: Cash balance decreases
   - **How to Verify**: Account selector at top shows updated balance
   - **Example**: "Available Cash: ₹98,495.00" (was ₹100,000.00)

   **History Tab**:
   - **What Updates**: New trade entry appears in history list
   - **How to Verify**: See new row at top of history with trade details
   - **Fields**: Symbol, Side, Quantity, Entry Price, Timestamp, Status

**Verification Steps**:

1. Navigate to Paper Trading → Execute Trade Tab
2. Fill in form fields:
   - Symbol: "AAPL" (or any valid symbol)
   - Quantity: 10
   - Leave Price empty for MARKET order
3. Set Stop Loss and Target Price (optional but recommended)
4. Verify "Execute BUY" button becomes enabled (all required fields filled)
5. Click "Execute BUY" button
6. Verify green success toast appears
7. Check Positions Tab → See new AAPL position with quantity 10
8. Check Account Summary → Cash balance decreased by trade cost
9. Check History Tab → New trade entry appears
10. Database check: Query paper_trades table

**Database Verification Query** (when implemented):
```sql
-- Check trade was created
SELECT trade_id, symbol, side, quantity, entry_price, status, created_at
FROM paper_trades
WHERE created_at > datetime('now', '-1 minute')
ORDER BY created_at DESC
LIMIT 1;

-- Check account balance was updated
SELECT account_type, cash_balance, updated_at
FROM paper_accounts
WHERE updated_at > datetime('now', '-1 minute')
ORDER BY updated_at DESC
LIMIT 1;

-- Check position was created/updated
SELECT symbol, quantity, avg_price, unrealized_pnl
FROM portfolio_state
WHERE symbol = 'AAPL';
```

**Common Issues**:

| Issue | Solution |
|-------|----------|
| Execute button disabled | Not all required fields filled, check form validation |
| No confirmation after click | API endpoint not implemented (returns 404) |
| Balance doesn't update | Trade backend not connected to account service |
| Position doesn't appear | Portfolio_state table not updated by trade service |

---

### 4.2 View Positions

**UI Path**: Paper Trading → Positions Tab

**Trigger Element**: Tab navigation (auto-loads)

**API Endpoint**: `GET /api/paper-trading/positions` (or similar)

**Expected Database Query**:
```sql
SELECT symbol, quantity, avg_price, current_price,
       ROUND((current_price - avg_price) * quantity, 2) as unrealized_pnl,
       ROUND(((current_price - avg_price) / avg_price) * 100, 2) as pnl_percent
FROM portfolio_state
WHERE quantity > 0
ORDER BY symbol;
```

**Expected UI Display**:

1. **Positions Table/Cards**:

   **Example Row**:
   - Symbol: "AAPL"
   - Quantity: 10
   - Avg Price: "₹150.50"
   - Current Price: "₹152.00"
   - P&L: "₹15.00" (green, positive)
   - P&L %: "0.99%" (green)
   - Exit Button: "Sell" or "Close Position"

2. **Position Summary**:
   - Total Positions: Integer count (e.g., "5")
   - Total Invested: Sum of (quantity * avg_price) (e.g., "₹1,50,000")
   - Current Value: Sum of (quantity * current_price) (e.g., "₹1,52,500")
   - Total P&L: Sum of unrealized P&L (e.g., "₹2,500")
   - Total P&L %: Percentage of gains (e.g., "1.67%")

**Verification Steps**:

1. Navigate to Paper Trading → Positions Tab
2. See list of open positions
3. Verify each position shows:
   - Symbol ✓
   - Quantity ✓
   - Avg Price ✓
   - Current Price ✓
   - P&L calculations ✓
4. Verify summary totals are correct (sum of quantities, values, etc.)

---

## 5. News & Earnings Page

News & Earnings page displays market news and earnings data for portfolio companies.

### 5.1 View News for Symbol

**UI Path**: News & Earnings → Symbol Selector → Select symbol → News Tab

**Trigger Element**: Symbol dropdown selection

**API Endpoint**: `GET /api/news-earnings/news?symbol={symbol}` (or similar)

**Expected Database Query**:
```sql
SELECT news_id, symbol, news_title, news_source, news_content,
       sentiment_score, published_at, fetched_at
FROM news_earnings_data
WHERE symbol = '{symbol}' AND type = 'news'
ORDER BY published_at DESC
LIMIT 50;
```

**Expected UI Display**:

1. **News Feed**:

   **News Card Example**:
   - Title: "Apple Announces Record Quarterly Results"
   - Source: "Reuters" (with source logo if available)
   - Content: "Truncated article text... [Read More]"
   - Sentiment Score: "78%" (green for positive, red for negative)
   - Published: "Nov 4, 2025 10:00 AM"
   - Fetched: "Nov 4, 2025 10:05 AM" (shown as relative time: "5 minutes after publication")

2. **Sentiment Indicators**:
   - Green indicator: Sentiment score > 0.6 (positive)
   - Yellow indicator: 0.4 < Sentiment score < 0.6 (neutral)
   - Red indicator: Sentiment score < 0.4 (negative)

3. **Filter/Sort Options** (if implemented):
   - Sort by: "Most Recent" or "Most Relevant"
   - Filter by Sentiment: "All", "Positive", "Neutral", "Negative"
   - Date Range: "Last 7 days", "Last 30 days", etc.

**Verification Steps**:

1. Navigate to News & Earnings page
2. Select a symbol from dropdown (e.g., "AAPL")
3. Click News tab
4. Verify news articles appear:
   - Title ✓
   - Source ✓
   - Sentiment score ✓
   - Published timestamp ✓
5. Verify sentiment indicators use correct colors
6. Verify articles sorted by published_at (most recent first)

**Database Verification Query**:
```sql
-- Check news for symbol
SELECT news_title, sentiment_score, published_at, fetched_at
FROM news_earnings_data
WHERE symbol = 'AAPL' AND type = 'news'
ORDER BY published_at DESC
LIMIT 10;

-- Check data freshness (when last fetched)
SELECT symbol, MAX(fetched_at) as last_fetch
FROM news_earnings_data
WHERE type = 'news'
GROUP BY symbol;
```

---

## 6. Dashboard Page

Dashboard provides overview of portfolio status and performance.

### 6.1 View Portfolio Overview

**UI Path**: Dashboard (home page, auto-loads on mount)

**Trigger Element**: Page load (no specific button, API called automatically)

**API Endpoint**: `GET /api/dashboard` or `GET /api/portfolio/overview`

**Expected Database Queries**:

1. **Portfolio Summary**:
```sql
SELECT
  COUNT(DISTINCT symbol) as total_holdings,
  SUM(quantity * current_price) as total_value,
  SUM(quantity * avg_price) as total_invested,
  SUM((current_price - avg_price) * quantity) as total_unrealized_pnl
FROM portfolio_state
WHERE quantity > 0;
```

2. **Account Summary**:
```sql
SELECT cash_balance, total_value
FROM paper_accounts
WHERE account_type = 'paper'
LIMIT 1;
```

3. **Holdings List**:
```sql
SELECT symbol, quantity, avg_price, current_price,
       (current_price - avg_price) * quantity as unrealized_pnl,
       ((current_price - avg_price) / avg_price) * 100 as pnl_percent
FROM portfolio_state
WHERE quantity > 0
ORDER BY symbol;
```

**Expected UI Display**:

1. **Portfolio Summary Cards**:

   **Total Value**:
   - Label: "Total Portfolio Value"
   - Value: "₹1,52,500"
   - Subtext: "Includes cash: ₹2,500"

   **Cash Balance**:
   - Label: "Available Cash"
   - Value: "₹2,500"
   - Subtext: "Buying Power"

   **Total P&L**:
   - Label: "Total P&L"
   - Value: "₹2,500" (green if positive, red if negative)
   - Percentage: "+1.67%" (green if positive)

   **Holdings Count**:
   - Label: "Total Positions"
   - Value: "5"
   - Subtext: "5 stocks held"

2. **Holdings Table**:

   | Symbol | Quantity | Avg Price | Current Price | P&L | P&L % |
   |--------|----------|-----------|---------------|-----|-------|
   | AAPL | 10 | ₹150.50 | ₹152.00 | ₹15 | +0.99% |
   | MSFT | 5 | ₹380.00 | ₹385.00 | ₹25 | +1.31% |
   | GOOGL | 2 | ₹2,800.00 | ₹2,850.00 | ₹100 | +1.79% |

   - Sortable by each column
   - Color-coded (green for positive P&L, red for negative)
   - Click row to see position details

3. **Performance Metrics** (if implemented):

   **Win Rate**:
   - Label: "Win Rate"
   - Value: "60.0%"
   - Calculation: (Winning positions / Total positions) * 100

   **Sharpe Ratio**:
   - Label: "Risk-Adjusted Return"
   - Value: "1.25"
   - Indicates portfolio efficiency

   **Max Drawdown**:
   - Label: "Maximum Drawdown"
   - Value: "-8.5%"
   - Largest peak-to-trough decline

**WebSocket Updates**:
- **Event**: `portfolio_update`
- **Frequency**: Real-time whenever price updates or trade executed
- **Payload**:
```json
{
  "holdings": [
    {
      "symbol": "AAPL",
      "quantity": 10,
      "current_price": 152.00,
      "unrealized_pnl": 15.00,
      "pnl_percent": 0.99
    }
  ],
  "total_value": 152500.00,
  "total_pnl": 2500.00
}
```

**Verification Steps**:

1. Navigate to Dashboard (home page)
2. Verify portfolio overview loads:
   - Total value displays ✓
   - Cash balance shows ✓
   - Holdings table populates ✓
3. Check calculations:
   - P&L = (current_price - avg_price) * quantity ✓
   - P&L % = (P&L / invested) * 100 ✓
4. Verify color coding (green for positive, red for negative) ✓
5. Watch real-time updates:
   - Execute a trade from Paper Trading
   - Return to Dashboard
   - New position appears or existing position updates
6. Database check: Verify values match queries

**Database Verification Query**:
```sql
-- Check portfolio summary
SELECT
  COUNT(DISTINCT symbol) as total_holdings,
  SUM(quantity) as total_quantity,
  ROUND(SUM(quantity * current_price), 2) as total_value,
  ROUND(SUM((current_price - avg_price) * quantity), 2) as total_pnl
FROM portfolio_state
WHERE quantity > 0;

-- Check top holdings
SELECT symbol, quantity, avg_price, current_price,
       ROUND((current_price - avg_price) * quantity, 2) as pnl
FROM portfolio_state
WHERE quantity > 0
ORDER BY quantity * current_price DESC
LIMIT 10;
```

---

## 7. Critical Data Flows

### 7.1 Portfolio Intelligence Analysis - End-to-End

This is the complete flow from user trigger to UI display.

**Flow Overview**:
```
User clicks "Run Now" in Configuration
        ↓
API creates task in AI_ANALYSIS queue
        ↓
Task queued (status: PENDING)
        ↓
Queue manager picks up task (status: RUNNING)
        ↓
Claude SDK analyzes 2-3 stocks per task
        ↓
Analysis results saved to analysis_history table
        ↓
Recommendations extracted and saved to recommendations table
        ↓
Task marked COMPLETED
        ↓
WebSocket event: queue_status_update
        ↓
System Health page updates (if open)
        ↓
AI Transparency page updates (if open)
```

**Step-by-Step Execution**:

1. **Trigger** (User Action)
   - Navigate to Configuration → AI Agents
   - Click "Run Now" button on Portfolio Analyzer
   - UI shows loading indicator

2. **API Call**
   - Frontend: `POST /api/configuration/ai-agents/portfolio_analyzer/execute`
   - Backend: Validates request, creates task object
   - Response: `{"status": "success", "task_id": "550e8400...", "message": "AI Agent execution queued"}`

3. **Task Creation**
   - Task service: Creates task record in `scheduler_tasks` table
   - Fields: task_id, queue_name='AI_ANALYSIS', task_type='RECOMMENDATION_GENERATION', status='PENDING'
   - Timestamp: created_at = current timestamp

4. **Queue Submission**
   - Queue manager: Adds task to AI_ANALYSIS queue
   - Queue broadcasts WebSocket event: `queue_status_update`
   - **UI Impact**: If System Health is open, queue count updates immediately

5. **Task Execution** (takes 5-10 minutes)
   - Queue manager: Picks up task from queue, marks status='RUNNING'
   - Handler called: `handle_recommendation_generation()`
   - PortfolioIntelligenceAnalyzer:
     - Retrieves portfolio from database
     - For each stock (batched 2-3 per task):
       - Calls Claude SDK with analysis prompt
       - Claude analyzes news, earnings, fundamentals
       - Returns recommendations
     - All analysis stored in memory until completion

6. **Database Persistence** (after analysis completes)
   - Analysis stored: `INSERT INTO analysis_history (symbol, timestamp, analysis, created_at) VALUES (...)`
   - Recommendations stored: `INSERT INTO recommendations (symbol, recommendation_type, confidence_score, reasoning, ...) VALUES (...)`
   - Task marked: `UPDATE scheduler_tasks SET status='COMPLETED', updated_at=NOW() WHERE task_id=...`

7. **WebSocket Event Broadcasting**
   - Queue manager: Broadcasts `queue_status_update` event
   - Payload: `{queue_name: 'AI_ANALYSIS', completed_count: 1, ...}`
   - **UI Impact**: System Health updates in real-time

8. **UI Display Updates**
   - Option A (Real-time): WebSocket listener updates System Health and AI Transparency
   - Option B (Polling): Front-end polls `/api/claude/transparency/analysis` every 5 seconds
   - **Result**: New recommendations visible in AI Transparency → Recommendations Tab

**Timeline Metrics**:
- API call → Task created: <1 second
- Task queued → Execution starts: <5 seconds (if queue idle) or variable (if other tasks in queue)
- Execution time: 5-10 minutes (Claude analysis with multiple stocks)
- Database write: <1 second
- UI update via WebSocket: <1 second
- Total end-to-end: 5-10 minutes

**Verification Checklist**:
- [ ] Toast notification appears immediately
- [ ] System Health → Queues shows task in "Pending Tasks" within 2 seconds
- [ ] Task status transitions: PENDING → RUNNING → COMPLETED (observe in backend logs)
- [ ] After 5-10 minutes, queue shows task COMPLETED
- [ ] System Health → Schedulers shows execution count increased
- [ ] AI Transparency → Recommendations shows new entries
- [ ] Each recommendation has symbol, type, confidence score, reasoning ✓
- [ ] Database queries return correct values ✓
- [ ] All timestamps are recent (created_at within last 10 minutes) ✓

**Common Failure Points**:

| Failure Point | Symptom | Root Cause | Fix |
|---------------|---------|-----------|-----|
| Toast doesn't appear | No user feedback | Frontend API call failed | Check network tab in DevTools |
| Queue never starts | Task stuck in PENDING | Queue manager not running | Restart backend server |
| Analysis incomplete | Task times out after 15 min | Analyzing too many stocks (81+) | Solution built-in: queue batches 2-3 per task |
| No recommendations appear | Analysis completes but nothing in UI | Database write failed | Check ConfigurationState.store_recommendation() logged correctly |
| UI doesn't update | Manual refresh needed to see changes | WebSocket disconnected | Check WebSocket connection in browser DevTools |
| Analysis shows errors | Claude SDK timeout or turn limit | Analysis ran out of turns or took too long | Ensure queue batcher working, check Claude timeout settings |

---

### 7.2 News Processor Execution

**Flow Overview**:
```
User clicks "Run Now" in News Processor
        ↓
Task created in DATA_FETCHER queue
        ↓
Task executes: Perplexity API fetches news
        ↓
News articles parsed and sentiment analyzed
        ↓
Results saved to news_earnings_data table
        ↓
Execution logged to execution_history table
        ↓
WebSocket: scheduler_execution event
        ↓
System Health page updates
```

**Step-by-Step Execution**:

1. **Trigger**
   - Navigate to Configuration → Background Tasks
   - Click "Run Now" on News Processor

2. **Task Creation**
   - Task: queue_name='DATA_FETCHER', task_type='NEWS_PROCESSOR_RUN'
   - Status: PENDING

3. **Queue Execution** (30-60 seconds)
   - For each portfolio symbol:
     - Call Perplexity API: GET latest news articles
     - Parse response: Extract title, content, source
     - Sentiment analysis: Classify article sentiment (0.0-1.0)
     - Insert into database

4. **Database Updates**
   ```sql
   INSERT INTO news_earnings_data
   (symbol, news_title, news_source, sentiment_score, published_at, fetched_at)
   VALUES ('AAPL', 'Apple Announces...', 'Reuters', 0.78, '2025-11-04T10:00:00', NOW())
   ```

5. **Execution History**
   ```sql
   INSERT INTO execution_history
   (task_name, task_type, status, execution_time_seconds, data_fetched_count, created_at)
   VALUES ('news_processor', 'NEWS_PROCESSOR_RUN', 'COMPLETED', 45.5, 25, NOW())
   ```

6. **WebSocket Event**
   - Event: `scheduler_execution`
   - Triggers System Health → Schedulers Tab to refresh

**Timeline**:
- Task creation: <1 second
- Task execution: 30-60 seconds
- Database write: <1 second
- UI update: <5 seconds

**Verification Checklist**:
- [ ] Toast notification appears
- [ ] System Health → Queues shows DATA_FETCHER queue with task
- [ ] After 30-60 seconds, task marked COMPLETED
- [ ] System Health → Schedulers shows News Processor execution updated
- [ ] Database contains new news articles with recent fetched_at timestamp
- [ ] News & Earnings page shows new articles (may need refresh)

---

### 7.3 Configuration Persistence

**Flow Overview**:
```
User changes configuration (toggle, select, type)
        ↓
Form field marked as modified (UI highlight)
        ↓
User clicks "Save Configuration"
        ↓
Frontend collects all changes
        ↓
Multiple API calls: PUT /api/configuration/{resource}/{name}
        ↓
Backend validates and updates database
        ↓
JSON backup files created in config/backups/
        ↓
Config file (config/config.json) updated atomically
        ↓
Toast notification: "Configuration saved"
        ↓
Backend broadcasts event: configuration_updated
        ↓
All components using config reload values
```

**Step-by-Step Execution**:

1. **User Changes**
   - Example: Toggle "News Processor" enabled from true to false
   - Form field highlights (yellow or different color)
   - "Save Configuration" button becomes enabled

2. **Save Triggered**
   - User clicks "Save Configuration"
   - Frontend collects all modified fields
   - Groups by resource type (background_tasks_config, ai_agents_config, etc.)

3. **API Calls**
   ```
   PUT /api/configuration/background-tasks/news_processor
   {
     "enabled": false,
     "frequency_seconds": 3600,
     "use_claude": true,
     "priority": "high"
   }
   ```

4. **Backend Processing**
   - Validate request
   - Update `background_tasks_config` table
   - Create backup file: `config/backups/config_background_tasks_config_20251104_125000.json`
   - Update main config file: `config/config.json`
   - Atomic write: Write to temp file, then `os.replace()` to live file

5. **Database Update**
   ```sql
   UPDATE background_tasks_config
   SET enabled=false, updated_at=NOW()
   WHERE task_name='news_processor'
   ```

6. **UI Confirmation**
   - Toast appears: "All configuration changes have been saved successfully"
   - Form fields return to normal display (non-modified state)
   - Save button becomes disabled

7. **Persistence Verification**
   - User refreshes page: Changes persist ✓
   - Backend restarts: Changes persist (loaded from config.json) ✓
   - Backup files created: Can restore to previous state ✓

**Verification Checklist**:
- [ ] Modified field highlights during edit
- [ ] Save button enabled when changes exist
- [ ] Toast notification appears on save
- [ ] Form returns to normal display
- [ ] Database updated (query config table)
- [ ] Backup file created in config/backups/
- [ ] Changes persist after browser refresh
- [ ] Changes persist after backend restart

---

## 8. Database Reference

### Core Configuration Tables

| Table | Primary Key | Purpose | When Updated | Key Fields |
|-------|------------|---------|--------------|-----------|
| `background_tasks_config` | id, task_name (UNIQUE) | Scheduler configuration | PUT /api/configuration/background-tasks | enabled, frequency_seconds, frequency_unit, use_claude, priority |
| `ai_agents_config` | id, agent_name (UNIQUE) | AI agent configuration | PUT /api/configuration/ai-agents | enabled, use_claude, response_frequency, scope, max_tokens_per_request |
| `global_settings_config` | id, setting_key (UNIQUE) | System-wide settings | PUT /api/configuration/global-settings | setting_value |
| `ai_prompts_config` | id, prompt_name (UNIQUE) | AI prompts for tasks/agents | PUT /api/configuration/prompts | prompt_content, description, updated_at |

### Task Management Tables

| Table | Primary Key | Purpose | When Updated | Key Fields |
|-------|------------|---------|--------------|-----------|
| `scheduler_tasks` | id, task_id (UNIQUE) | Queue task records | Task service (create, update status) | queue_name, task_type, status (PENDING/RUNNING/COMPLETED/FAILED), payload, priority, created_at, updated_at |
| `execution_history` | id | Task execution records | After task completion | task_name, task_type, status, execution_time_seconds, data_fetched_count, error_message, created_at |

### AI Analysis Tables

| Table | Primary Key | Purpose | When Updated | Key Fields |
|-------|------------|---------|--------------|-----------|
| `analysis_history` | id | Claude analysis results | After Portfolio Analyzer completes | symbol, timestamp, analysis (JSON), created_at |
| `recommendations` | id | Trading recommendations | After analysis completes | symbol, recommendation_type (BUY/SELL/HOLD), confidence_score, reasoning, analysis_type, created_at |
| `claude_strategy_logs` | id, session_id (UNIQUE) | Claude session tracking | After Claude analysis | session_id, session_type, success, decisions_made, token_input, token_output, created_at |

### Portfolio & Trading Tables

| Table | Primary Key | Purpose | When Updated | Key Fields |
|-------|------------|---------|--------------|-----------|
| `portfolio_state` | symbol (UNIQUE) | Current holdings | After trade execution | symbol, quantity, avg_price, current_price, unrealized_pnl, updated_at |
| `paper_trades` | id, trade_id (UNIQUE) | Trade execution records | When user executes trade | trade_id, account_type, symbol, side (BUY/SELL), quantity, entry_price, status, created_at |
| `paper_accounts` | id, account_type (UNIQUE) | Paper trading accounts | When trade executes | account_type, cash_balance, total_value, updated_at |

### News & Earnings Tables

| Table | Primary Key | Purpose | When Updated | Key Fields |
|-------|------------|---------|--------------|-----------|
| `news_earnings_data` | id | News and earnings articles | News/Earnings Processor executes | symbol, news_title, news_source, sentiment_score, published_at, fetched_at |

---

## 9. WebSocket Events

WebSocket provides real-time updates without page refresh.

| Event Type | Payload | Triggered By | UI Components Listening |
|------------|---------|--------------|------------------------|
| `queue_status_update` | `{queue_name, pending_count, running_count, completed_count, failed_count}` | Task status changes in queue | System Health → Queues Tab |
| `scheduler_execution` | `{task_name, status, execution_time_seconds, timestamp}` | Scheduler task completes | System Health → Schedulers Tab |
| `recommendation_update` | `{symbol, recommendation_type, confidence_score, timestamp}` | New recommendation created | AI Transparency → Recommendations Tab |
| `portfolio_update` | `{symbol, quantity, current_price, unrealized_pnl, pnl_percent}` | Position changes or price updates | Dashboard → Portfolio Table |
| `configuration_updated` | `{resource_type, timestamp}` | Configuration saved | Any component using config |
| `error_alert` | `{error_type, message, timestamp, component}` | System errors occur | System Health → Errors Tab |

**Example: Real-Time Queue Updates**

```javascript
// Frontend WebSocket listener (pseudocode)
socket.on('queue_status_update', (payload) => {
  const { queue_name, pending_count, running_count, completed_count } = payload;

  // Update System Health → Queues Tab
  updateQueueCard(queue_name, {
    pending: pending_count,
    inProgress: running_count,
    completed: completed_count
  });
});
```

---

## 10. API Endpoints

### Configuration Endpoints

| Method | Endpoint | Purpose | Request | Response |
|--------|----------|---------|---------|----------|
| GET | `/api/configuration/background-tasks` | Get all scheduler configs | N/A | `{background_tasks: {...}}` |
| PUT | `/api/configuration/background-tasks/{task_name}` | Update scheduler config | `{enabled, frequency_seconds, priority, useClaude}` | `{status: "updated"}` |
| GET | `/api/configuration/ai-agents` | Get all AI agent configs | N/A | `{ai_agents: {...}}` |
| PUT | `/api/configuration/ai-agents/{agent_name}` | Update AI agent config | `{enabled, useClaude, responseFrequency, scope, maxTokens}` | `{status: "updated"}` |
| GET | `/api/configuration/prompts/{prompt_name}` | Get prompt | N/A | `{prompt_name, content, description, updated_at}` |
| PUT | `/api/configuration/prompts/{prompt_name}` | Update prompt | `{content, description}` | `{status: "success"}` |
| POST | `/api/configuration/schedulers/{task_name}/execute` | Execute scheduler manually | `{symbols: []}` (optional) | `{status: "success", task_id}` |
| POST | `/api/configuration/ai-agents/{agent_name}/execute` | Execute AI agent | N/A | `{status: "queued", task_id, message}` |

### Monitoring Endpoints

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | `/api/monitoring/scheduler` | Get scheduler status and queue stats | `{status, schedulers: [...], queues: [...]}` |
| GET | `/api/health` | System health check | `{status: "healthy", timestamp}` |

### AI Transparency Endpoints

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | `/api/claude/transparency/analysis` | Get analysis activity | `{analysis: {portfolio_analyses, portfolio_stats}}` |
| GET | `/api/claude/transparency/execution` | Get trade execution transparency | `{execution: {total_sessions, successful_count, recent_sessions}}` |
| GET | `/api/claude/transparency/trade-decisions` | Get trade decision log | `{decisions: [...]}}` |

### Paper Trading Endpoints

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| POST | `/api/paper-trading/execute` | Execute trade | ❌ Not implemented (404) |
| GET | `/api/paper-trading/positions` | Get open positions | ⚠️ Partially implemented |
| GET | `/api/paper-trading/history` | Get trade history | ⚠️ Partially implemented |

---

## 11. Testing Scenarios

### Scenario 1: Complete Portfolio Analysis Workflow

**Objective**: Verify portfolio analysis from trigger to UI display

**Duration**: ~12 minutes

**Steps**:
1. Open browser to http://localhost:3000/configuration
2. Ensure backend is running: `curl -m 3 http://localhost:8000/api/health`
3. Navigate to Configuration → AI Agents Tab
4. Click "Run Now" on Portfolio Analyzer
5. Verify green toast: "AI Agent execution initiated"
6. Open second browser tab: System Health → Queues Tab
7. Verify AI_ANALYSIS queue shows task queued
8. Wait 5-10 minutes for Claude analysis to complete
9. Watch AI_ANALYSIS queue status change: PENDING → RUNNING → COMPLETED
10. Navigate to AI Transparency → Recommendations Tab
11. Verify new recommendations appear for portfolio stocks
12. Click on recommendation card to view full Claude reasoning
13. Verify data quality indicators show available sources

**Expected Results**:
- ✅ Task queued successfully
- ✅ Queue status updates in real-time
- ✅ Recommendations display after execution
- ✅ Confidence scores between 0.0-1.0
- ✅ Reasoning text present and substantial
- ✅ Data quality indicators accurate

**Database Verification**:
```sql
-- Should return recent analysis records
SELECT symbol, confidence_score, recommendation_type
FROM recommendations
WHERE created_at > datetime('now', '-15 minutes')
LIMIT 5;
```

---

### Scenario 2: News Processor Execution with Data Verification

**Objective**: Verify news data flows from processor to UI

**Duration**: ~2 minutes

**Steps**:
1. Navigate to Configuration → Background Tasks
2. Click "Run Now" on News Processor
3. Verify toast notification
4. Navigate to System Health → Schedulers Tab
5. Verify News Processor execution history updated
6. Wait 30-60 seconds for completion
7. Navigate to News & Earnings page
8. Select a symbol from dropdown
9. Click News tab
10. Verify new articles appear with recent timestamps

**Expected Results**:
- ✅ Task execution logged
- ✅ News articles appear in UI
- ✅ Sentiment scores present (0.0-1.0)
- ✅ Articles sorted by publication date (newest first)
- ✅ Source attribution displayed

**Database Verification**:
```sql
-- Check news articles fetched in last 5 minutes
SELECT symbol, COUNT(*) as article_count, MAX(fetched_at) as last_fetch
FROM news_earnings_data
WHERE fetched_at > datetime('now', '-5 minutes')
GROUP BY symbol;
```

---

### Scenario 3: Configuration Persistence Across Restarts

**Objective**: Verify configuration changes survive server restart

**Duration**: ~5 minutes

**Steps**:
1. Navigate to Configuration → Background Tasks
2. Change News Processor frequency from 1 hour to 2 hours
3. Toggle "Use Claude AI" OFF
4. Click "Save Configuration"
5. Verify toast: "Configuration saved successfully"
6. Refresh browser page (Cmd+R)
7. Verify changes persist (frequency still 2 hours, Claude still OFF)
8. Stop backend: `lsof -ti:8000 | xargs kill -9`
9. Start backend: `python -m src.main --command web`
10. Navigate back to Configuration
11. Verify changes still present after server restart

**Expected Results**:
- ✅ Toast confirms save
- ✅ Changes visible after browser refresh
- ✅ Changes visible after backend restart
- ✅ JSON backup file created

**Database Verification**:
```sql
-- Check configuration values
SELECT task_name, frequency_seconds, use_claude, updated_at
FROM background_tasks_config
WHERE task_name = 'news_processor';
```

**File System Verification**:
```bash
# Check backup file created
ls -lh config/backups/config_background_tasks_config_*.json | tail -1
```

---

### Scenario 4: Real-Time Queue Monitoring

**Objective**: Verify queue status updates in real-time via WebSocket

**Duration**: ~3 minutes

**Steps**:
1. Open System Health → Queues Tab
2. Open browser DevTools → Network → WS (WebSocket filter)
3. Trigger task execution (e.g., run News Processor)
4. Watch WebSocket messages in Network tab
5. Verify `queue_status_update` event appears
6. Watch Queues Tab UI update in real-time
7. Verify pending count increases immediately
8. Wait for task execution to complete
9. Verify completed count increases
10. Verify pending returns to 0

**Expected Results**:
- ✅ WebSocket messages sent in real-time
- ✅ UI updates immediately (no page refresh needed)
- ✅ Queue counts accurate
- ✅ Task progression visible: PENDING → RUNNING → COMPLETED

**WebSocket Verification** (in DevTools):
```
> {"type": "queue_status_update", "queue_name": "DATA_FETCHER", "pending_count": 1}
> {"type": "queue_status_update", "queue_name": "DATA_FETCHER", "running_count": 1, "pending_count": 0}
> {"type": "queue_status_update", "queue_name": "DATA_FETCHER", "completed_count": 1, "running_count": 0}
```

---

## 12. Troubleshooting

### Issue: "Database is locked" error appears during analysis

**Symptoms**:
- Page freezes during AI analysis
- Error in browser console: "database is locked"
- Backend logs show SQLite locking errors

**Root Cause**:
- Direct database connection access bypasses `asyncio.Lock()` protection
- Multiple async operations accessing database concurrently
- ConfigurationState.store_analysis_history() not using proper locking

**Diagnosis**:
1. Check backend logs: `tail -f logs/backend.log | grep -i lock`
2. Check database file locks: `lsof | grep robo_trader.db`
3. Query database directly: `sqlite3 state/robo_trader.db "PRAGMA busy_timeout;"`

**Fix**:
1. Verify all web endpoints use ConfigurationState locked methods:
   ```python
   # ✅ CORRECT - Uses internal locking
   success = await config_state.store_analysis_history(symbol, timestamp, analysis_json)

   # ❌ WRONG - Direct connection access bypasses locking
   await config_state.db.connection.execute(...)
   ```

2. Update any direct database access to use locked methods
3. Increase timeout protection if analysis legitimately takes >15 minutes:
   ```python
   # In src/services/scheduler/queue_manager.py
   timeout = 900.0  # Increase from 300 to 900 seconds (15 minutes)
   ```

**Prevention**:
- Always use ConfigurationState public methods in web endpoints
- Never access `db.connection.execute()` directly outside database_state classes
- Use `async with self._lock:` pattern in state classes

**Verification**:
```bash
# Check for database lock issues
sqlite3 state/robo_trader.db "SELECT * FROM pragma_integrity_check;"

# Should return: ok
```

---

### Issue: Portfolio analysis task times out after 15 minutes

**Symptoms**:
- Task status changes to FAILED
- Error message: "Task execution timeout (>900s)"
- Analysis never appears in UI

**Root Cause**:
- Timeout set too low for large portfolios
- Claude analysis on 81+ stocks requires multiple turns
- Each stock needs separate Claude session (queue batcher should handle this)

**Diagnosis**:
1. Check backend logs: `grep -i "timeout" logs/backend.log`
2. Check task status: `SELECT status, error_message FROM scheduler_tasks WHERE task_id='...';`
3. Monitor execution time: `SELECT execution_time_seconds FROM execution_history WHERE task_name='portfolio_analyzer';`

**Fix**:
1. Verify queue batcher is working (should batch 2-3 stocks per task):
   ```bash
   # Check logs for batch messages
   grep "Batch.*stocks" logs/backend.log
   ```

2. If needed, increase timeout in `src/services/scheduler/queue_manager.py`:
   ```python
   # Current: 900 seconds (15 minutes)
   # Increase to: 1200 seconds (20 minutes) for large portfolios
   timeout = 1200.0
   ```

3. Alternatively, reduce batch size to speed up individual tasks:
   ```python
   BATCH_SIZE = 2  # Analyze 2 stocks per task instead of 3
   ```

**Prevention**:
- Monitor average execution times for your portfolio
- Set timeout = observed_time + 50% buffer
- Keep batch size reasonable (2-3 stocks)

---

### Issue: No recommendations appear in UI after analysis completes

**Symptoms**:
- Portfolio Analyzer runs without errors
- Task marked COMPLETED
- AI Transparency → Recommendations Tab shows no new entries
- System Health shows execution completed

**Root Cause**:
- Database write failed silently
- ConfigurationState.store_recommendation() not called
- Analysis data format incorrect (JSON parsing failed)

**Diagnosis**:
1. Check backend logs for errors: `grep -i "recommendation\|analysis" logs/backend.log`
2. Query database directly:
   ```sql
   SELECT COUNT(*) as recommendation_count FROM recommendations
   WHERE created_at > datetime('now', '-30 minutes');
   ```
3. Check analysis_history for records:
   ```sql
   SELECT symbol, LENGTH(analysis) FROM analysis_history
   WHERE created_at > datetime('now', '-30 minutes');
   ```

**Fix**:
1. Verify PortfolioIntelligenceAnalyzer calls store methods correctly:
   ```python
   # Check that both methods are called
   await config_state.store_analysis_history(symbol, timestamp, analysis_json)
   await config_state.store_recommendation(symbol, rec_type, confidence, reasoning, analysis_type)
   ```

2. Check database for partial data:
   ```sql
   -- Check if analysis_history has entries but recommendations don't
   SELECT ah.symbol, COUNT(r.id) as rec_count
   FROM analysis_history ah
   LEFT JOIN recommendations r ON ah.symbol = r.symbol
   WHERE ah.created_at > datetime('now', '-30 minutes')
   GROUP BY ah.symbol;
   ```

3. If analysis_history exists but recommendations don't, the issue is in recommendation extraction logic

**Prevention**:
- Add logging to track recommendation extraction:
   ```python
   logger.info(f"Storing {len(recommendations)} recommendations for {symbol}")
   ```
- Verify response from store_recommendation():
   ```python
   success = await config_state.store_recommendation(...)
   if not success:
       logger.error(f"Failed to store recommendation for {symbol}")
   ```

---

### Issue: WebSocket updates not working, UI requires manual refresh

**Symptoms**:
- Queue status doesn't update automatically
- Must refresh page to see new recommendations
- System Health page shows "Polling" instead of "Live"

**Root Cause**:
- WebSocket connection dropped or never established
- Backend not emitting events
- Frontend listeners not registered

**Diagnosis**:
1. Check browser DevTools → Network → WS (WebSocket tab)
2. Look for connection: Should show `ws://localhost:8000/ws`
3. Check connection status: Should show "101 Switching Protocols"
4. Monitor messages: Should see periodic `queue_status_update` events

**Fix**:
1. Check backend WebSocket server is running:
   ```bash
   # Should see ConnectionManager logs
   grep -i "websocket\|ws://" logs/backend.log
   ```

2. Verify frontend WebSocket initialization (check console):
   ```javascript
   // In browser console
   console.log("WebSocket status:", systemStatusStore.isConnected)
   ```

3. Manually reconnect WebSocket:
   ```javascript
   // In browser console
   window.location.reload()  // Hard refresh to reinitialize
   ```

4. If still not working, check firewall/proxy settings preventing WebSocket

**Prevention**:
- Implement automatic reconnection logic
- Add fallback to API polling (already implemented as fallback)
- Monitor WebSocket connection health

**Verification**:
```javascript
// In browser console, should return true
document.querySelector('[data-websocket-status]')?.textContent === 'Connected'
```

---

### Issue: Configuration changes not saving or not persisting

**Symptoms**:
- Save button clicked but no toast appears
- Changes lost after page refresh
- Changes reverted after server restart

**Root Cause**:
- API request failed (network error or backend issue)
- Database write succeeded but JSON file not updated
- File write failed (permissions issue, disk full)

**Diagnosis**:
1. Check browser DevTools → Network tab
2. Look for PUT requests to `/api/configuration/*`
3. Check response status: Should be 200 OK
4. Check response body: Should include `{"status": "success"}`

**Fix**:
1. If API call fails (non-200 status):
   - Check backend logs: `grep -i "error\|exception" logs/backend.log`
   - Verify API endpoint exists
   - Check request body JSON syntax

2. If API succeeds but changes don't persist:
   - Check JSON file creation: `ls -lh config/config.json`
   - Check file permissions: `stat config/config.json`
   - Check database update: Query config tables

3. Verify atomic write pattern working:
   ```bash
   # Should see temp file → replace pattern
   ls -lh config/config.json*
   ```

**Prevention**:
- Add request/response logging
- Monitor file write operations
- Set appropriate file permissions (644)

---

## Summary

This comprehensive functional testing reference document covers:

1. **Configuration Tab**: AI agents, schedulers, prompts with database updates
2. **System Health Page**: Queue monitoring, scheduler execution tracking
3. **AI Transparency Page**: Recommendations, sessions, trade logs
4. **Paper Trading Page**: Trade execution, position management
5. **News & Earnings Page**: News display, sentiment analysis
6. **Dashboard Page**: Portfolio overview, performance metrics
7. **Critical Flows**: End-to-end workflows for major features
8. **Database Reference**: All tables, fields, and update triggers
9. **WebSocket Events**: Real-time update mechanism
10. **API Endpoints**: All REST endpoints with request/response formats
11. **Testing Scenarios**: Step-by-step verification procedures
12. **Troubleshooting**: Common issues with diagnosis and fixes

Use this document to:
- Manually test UI functionality
- Verify data flows from UI → Database → UI
- Create automated test cases
- Debug issues systematically
- Understand complete system architecture
- Verify configuration persistence
- Monitor real-time updates

---

**Last Updated**: 2025-11-04
**Version**: 1.0
**Status**: Production Ready - Use for all UI functional testing
