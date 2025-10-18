# BackgroundScheduler Refactoring Analysis

## Overview
- **Total Lines**: 2348
- **Class File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/src/core/background_scheduler.py`
- **Current Responsibilities**: 1 massive class handling 10+ distinct business domains
- **Refactoring Priority**: HIGH - This is a classic "God Object" pattern

## Current Architecture

### Public API (8 methods)
1. `__init__()` - Initialization
2. `start()` - Start scheduler and background loops
3. `stop()` - Stop scheduler
4. `schedule_task()` - Schedule new task
5. `cancel_task()` - Cancel existing task
6. `trigger_event()` - Trigger event-driven tasks
7. `reload_config()` - Update config dynamically
8. `get_scheduler_status()` - Get current status

---

## 1. TASK SCHEDULING DOMAIN (~350 lines)

### Lines: 132-212, 386-418, 420-512
### Responsibilities:
- Task lifecycle management (create, track, execute, cancel)
- Priority-based execution queue
- Concurrent task limiting
- Task timeout handling
- Retry logic with exponential backoff

### Methods:
- `start()` (132-155)
- `stop()` (157-168)
- `schedule_task()` (170-195)
- `cancel_task()` (197-212)
- `get_scheduler_status()` (386-400)
- `_count_tasks_by_type()` (402-409)
- `_count_tasks_by_priority()` (411-418)
- `_scheduling_loop()` (420-428)
- `_execute_due_tasks()` (440-464)
- `_execute_task()` (466-483)
- `_run_task_with_timeout()` (485-512)
- `_handle_task_failure()` (564-578)

### Key State:
- `tasks: Dict[str, BackgroundTask]`
- `running_tasks: Dict[str, asyncio.Task]`
- `is_running: bool`
- `max_concurrent_tasks: int`
- `task_timeout_seconds: int`

### Dependencies:
- BackgroundTask data class
- TaskType, TaskPriority enums
- asyncio

**Extraction Target**: `TaskScheduler` or `BackgroundTaskOrchestrator`

---

## 2. MARKET MONITORING DOMAIN (~100 lines)

### Lines: 580-599, 430-438, 782-836
### Responsibilities:
- Market hours awareness (IST: 9:15 AM - 3:30 PM)
- Market open/close detection
- Market-triggered event handling

### Methods:
- `_check_market_status()` (580-598)
- `_market_monitoring_loop()` (430-438)
- `_handle_market_open_event()` (761-770)
- `_handle_market_close_event()` (771-780)
- `_execute_market_monitoring()` (782-836)

### Key State:
- `market_open: bool`
- `market_open_time: time`
- `market_close_time: time`
- `last_market_check: datetime`

### Dependencies:
- datetime utilities
- State manager (portfolio data)
- Alert manager

**Extraction Target**: `MarketMonitor`

---

## 3. PRICE/RISK MONITORING DOMAIN (~150 lines)

### Lines: 887-946, 725-736, 737-749
### Responsibilities:
- Stop loss breach detection
- Price movement detection and alerts
- Risk thresholds

### Methods:
- `_execute_stop_loss_monitor()` (887-946)
- `_handle_stop_loss_event()` (725-736)
- `_handle_price_movement_event()` (737-749)

### Key State:
- References `config.risk.stop_loss_percent`

### Dependencies:
- Portfolio data from state manager
- Alert manager
- Config (risk parameters)

**Extraction Target**: `RiskMonitor` or `PriceMonitor`

---

## 4. EARNINGS MONITORING & PARSING DOMAIN (~550 lines)

### Lines: 713-724, 838-886, 1958-2056, 2058-2197, 2199-2244, 1763-1779, 1800-1936

### Responsibilities:
- Earnings calendar fetching (Perplexity API)
- Earnings data parsing (multi-strategy)
- Earnings surprise detection
- Earnings event handling
- n+1 business day analysis scheduling

### Methods:
- `_handle_earnings_event()` (713-724)
- `_execute_earnings_check()` (838-886)
- `_execute_earnings_scheduler()` (1958-2056)
- `_fetch_earnings_calendar()` (2058-2197)
- `_check_earnings_surprise()` (2199-2244)
- `_parse_earnings_data()` (1800-1825)
- `_parse_structured_earnings()` (1826-1898)
- `_parse_regex_earnings()` (1901-1916)
- `_basic_earnings_extraction()` (1918-1936)
- `_extract_next_earnings_date()` (1763-1779)
- `_calculate_business_day()` (1938-1956)

### External Dependencies:
- Perplexity API (3 API keys with round-robin)
- Pydantic models for structured output
- Regex parsing

**Extraction Target**: `EarningsProcessor` or `EarningsMonitor`

---

## 5. NEWS MONITORING DOMAIN (~400 lines)

### Lines: 750-760, 948-1118, 1120-1289, 1436-1532, 1533-1628

### Responsibilities:
- Real-time news monitoring (Perplexity API)
- Daily news aggregation
- Batch processing with rate limiting
- API key rotation (round-robin)
- News content parsing and storage
- Sentiment analysis

### Methods:
- `_handle_news_event()` (750-760)
- `_execute_news_monitoring()` (948-1118)
- `_execute_news_daily()` (1120-1289)
- `_parse_and_save_batch_data()` (1436-1532)
- `_parse_and_save_daily_data()` (1533-1628)

### Sub-domain: News Data Processing
- `_is_news_duplicate()` (1671-1710)
- `_extract_news_for_symbol()` (1745-1750)
- `_analyze_sentiment()` (1781-1798)
- `_calculate_news_relevance()` (1630-1669)

### External Dependencies:
- Perplexity API (batch processing, rate limiting)
- State manager (portfolio, news storage)
- Fundamental service

**Extraction Target**: `NewsMonitor`, `NewsProcessor`

---

## 6. FUNDAMENTAL ANALYSIS DOMAIN (~60 lines)

### Lines: 1291-1350

### Responsibilities:
- Fetch fundamental data for portfolio
- Generate fundamental analysis alerts
- Check concerning fundamentals

### Methods:
- `_execute_fundamental_monitoring()` (1291-1350)

### External Dependencies:
- FundamentalService
- State manager (alert manager)

**Extraction Target**: Handled by `FundamentalService` - already extracted

---

## 7. RECOMMENDATIONS DOMAIN (~80 lines)

### Lines: 1352-1433

### Responsibilities:
- Generate bulk recommendations
- Store recommendation results
- Create recommendation alerts

### Methods:
- `_execute_recommendation_generation()` (1352-1433)

### External Dependencies:
- RecommendationEngine
- State manager

**Extraction Target**: Handled by `RecommendationEngine` - already extracted

---

## 8. EVENT HANDLING DOMAIN (~30 lines)

### Lines: 214-230, 761-780

### Responsibilities:
- Event dispatcher (event routing)
- Event handler delegation

### Methods:
- `trigger_event()` (214-230)
- `_handle_market_open_event()` (761-770)
- `_handle_market_close_event()` (771-780)

**Extraction Target**: `EventDispatcher` or merge into domain-specific classes

---

## 9. CONFIGURATION MANAGEMENT DOMAIN (~160 lines)

### Lines: 231-384

### Responsibilities:
- Dynamic config reloading
- Task frequency updates
- Task enabling/disabling
- Schedule time calculation (IST)

### Methods:
- `reload_config()` (231-384)

**Extraction Target**: `SchedulerConfigManager`

---

## 10. PERSISTENCE DOMAIN (~70 lines)

### Lines: 2281-2349

### Responsibilities:
- Load tasks from JSON file
- Save tasks to JSON file
- Async file I/O with aiofiles

### Methods:
- `_load_tasks()` (2281-2313)
- `_save_task()` (2314-2349)

**Extraction Target**: `SchedulerPersistence` or `TaskStore`

---

## 11. HEALTH & SYSTEM DOMAIN (~30 lines)

### Lines: 2246-2278

### Responsibilities:
- System health checks
- Data cleanup

### Methods:
- `_execute_health_check()` (2246-2253)
- `_execute_system_health_check()` (2255-2270)
- `_execute_data_cleanup()` (2272-2278)

**Extraction Target**: `SystemHealthMonitor`

---

## 12. TASK DISPATCH LOGIC (~50 lines)

### Lines: 514-562, 600-712

### Responsibilities:
- Route task execution by type
- Call domain-specific executors
- Invoke callbacks for external tasks

### Methods:
- `_execute_task_logic()` (514-562)
- `_schedule_default_tasks()` (600-712)

---

## Summary of Extracted Modules

### Module 1: TaskScheduler (Core Orchestration)
- Responsibility: Manage task lifecycle, queues, timeouts
- Size: ~350 lines
- Public methods: `start()`, `stop()`, `schedule_task()`, `cancel_task()`, `get_scheduler_status()`
- Dependencies: TaskType, TaskPriority, asyncio

### Module 2: MarketMonitor
- Responsibility: Track market hours, trigger market events
- Size: ~100 lines
- Dependencies: StateManager, AlertManager, datetime

### Module 3: RiskMonitor / PriceMonitor
- Responsibility: Monitor stop loss, price movements
- Size: ~150 lines
- Dependencies: StateManager, AlertManager, Config

### Module 4: EarningsProcessor
- Responsibility: Fetch, parse, analyze earnings data
- Size: ~550 lines
- Sub-components:
  - EarningsCalendarFetcher (API calls)
  - EarningsParser (multi-strategy parsing)
  - EarningsAnalyzer (n+1 scheduling, surprise detection)
- Dependencies: Perplexity API, StateManager, Regex

### Module 5: NewsMonitor
- Responsibility: Fetch news, batch process, detect duplicates
- Size: ~400 lines
- Sub-components:
  - NewsAPIClient (Perplexity integration with rate limiting)
  - NewsProcessor (parse, deduplicate, store)
  - SentimentAnalyzer
- Dependencies: Perplexity API, StateManager, FundamentalService

### Module 6: SchedulerConfigManager
- Responsibility: Reload config, update task frequencies
- Size: ~160 lines
- Dependencies: Config, TaskScheduler reference

### Module 7: TaskPersistence / TaskStore
- Responsibility: Load/save tasks from file
- Size: ~70 lines
- Dependencies: aiofiles, JSON, PathLib

### Module 8: SystemHealthMonitor
- Responsibility: Health checks, data cleanup
- Size: ~30 lines
- Dependencies: StateManager

### Module 9: EventDispatcher
- Responsibility: Route events to handlers
- Size: ~30 lines
- Dependencies: EventHandlers from domain modules

---

## Dependency Flow

```
BackgroundScheduler (MAIN)
├── TaskScheduler (core)
│   └── uses: TaskType, TaskPriority, asyncio
│
├── EventDispatcher (routes to)
│   ├── MarketMonitor
│   ├── RiskMonitor
│   ├── EarningsProcessor
│   ├── NewsMonitor
│   └── others...
│
├── SchedulerConfigManager
│   └── references TaskScheduler
│
└── TaskPersistence
    └── uses aiofiles
```

---

## Critical Insights

### Anti-Patterns Found:
1. **API Key Management**: Hard-coded round-robin with instance variable `_perplexity_key_index`
   - Should extract to `APIKeyRotator` utility
2. **Repeated Patterns**: News and Earnings both fetch from Perplexity with similar retry logic
   - Should extract to `PerplexityClient` utility
3. **Mixed Concerns**: `_execute_news_monitoring()` handles API calls, parsing, AND storage
   - Each should be separate class
4. **Config Access Pattern**: Direct attribute access (e.g., `self.config.agents.market_monitoring.enabled`)
   - Should use `SchedulerConfigManager` for abstraction

### Refactoring Sequence (Recommended):

1. **Phase 1**: Extract utilities
   - `PerplexityClient` (handles API calls, retries, rate limiting)
   - `APIKeyRotator` (round-robin key management)
   - `TaskStore` (persistence)

2. **Phase 2**: Extract core scheduler
   - `TaskScheduler` (task lifecycle)
   - `SchedulerConfigManager` (config management)

3. **Phase 3**: Extract monitoring domains
   - `MarketMonitor` (market hours)
   - `RiskMonitor` (stop loss, price movements)
   - `EarningsProcessor` (earnings data)
   - `NewsMonitor` (news data)
   - `SystemHealthMonitor` (health)

4. **Phase 4**: Create facade
   - `BackgroundSchedulerFacade` (thin wrapper, delegates to modules)

### Size Reduction:
- Current: 2348 lines in 1 class
- After refactoring: ~100-200 lines in main class + 10-12 focused modules
- Maintainability improvement: ~80-90%

---

## External Dependencies
- **aiofiles**: Async file operations
- **OpenAI/Perplexity**: News and earnings fetching
- **pydantic**: Structured output validation
- **loguru**: Logging
- **FundamentalService**: Already extracted
- **RecommendationEngine**: Already extracted
- **StateManager**: Database and state access
- **AlertManager**: Alert creation

---

## Testing Implications
- Current: Hard to unit test (2348 line monolith)
- After refactoring: Each module independently testable with mocks
- Example: Can test `EarningsProcessor` without `NewsMonitor`

