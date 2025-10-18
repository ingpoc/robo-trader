# Background Scheduler Refactoring Plan

**Goal**: Modularize the 2348-line monolithic BackgroundScheduler class into focused, single-responsibility modules following SOLID principles.

**Current State**: God Object anti-pattern with 12+ mixed concerns
**Target State**: 7-8 focused modules with clear interfaces
**Estimated Duration**: 16-24 hours with full test coverage
**Risk Level**: Low (phased approach with backward compatibility)

---

## Executive Summary

### Current Problems

| Problem | Impact | Severity |
|---------|--------|----------|
| God Object (2348 lines) | Cannot understand entire class at once | Critical |
| 12+ Mixed Concerns | Impossible to test modules independently | Critical |
| Duplicated API Logic | 8+ instances of Perplexity API calls | High |
| Large If-Elif Chains | 15+ branches in `reload_config()` | High |
| High Cyclomatic Complexity | Bug fixes affect unexpected areas | High |
| No Clear Boundaries | Cannot reuse components elsewhere | Medium |

### Expected Improvements

- **Cognitive Load**: 2348 → 350 lines per file (90% reduction)
- **Test Coverage**: 20% → 80%+
- **Bug Fix Time**: 70% reduction
- **Maintainability**: 80-90% improvement
- **Reusability**: Components can be used in other projects

---

## Architecture Overview: New Structure

```
src/core/background_scheduler/
├── __init__.py                    # Public API
├── models.py                      # TaskType, TaskPriority, BackgroundTask
├── stores/
│   └── task_store.py             # Persistence layer (~70 lines)
├── clients/
│   ├── perplexity_client.py       # Unified Perplexity API (~150 lines)
│   └── api_key_rotator.py         # API key management (~50 lines)
├── processors/
│   ├── earnings_processor.py      # Earnings parsing & analysis (~400 lines)
│   ├── news_processor.py          # News fetching & analysis (~300 lines)
│   └── fundamental_analyzer.py    # Fundamental data (~60 lines)
├── monitors/
│   ├── market_monitor.py          # IST market hours detection (~80 lines)
│   ├── risk_monitor.py            # Stop loss & price monitoring (~150 lines)
│   └── health_monitor.py          # System health checks (~30 lines)
├── config/
│   └── task_config_manager.py     # Config reloading & validation (~140 lines)
├── events/
│   └── event_handler.py           # Event routing & dispatch (~50 lines)
├── core/
│   ├── task_scheduler.py          # Core task lifecycle (~250 lines)
│   └── task_executor.py           # Task execution & timeouts (~200 lines)
└── background_scheduler.py        # Facade (~150 lines)
```

---

## Detailed Phase Breakdown

### Phase 1: Extract Utilities (4-6 hours)

**Objective**: Create reusable, independent utility modules with zero cross-dependencies.

#### 1.1 Create `models.py` (~50 lines)
**Extract**: `TaskType` enum, `TaskPriority` enum, `BackgroundTask` dataclass

**Lines to extract from original**: 26-90
**Dependencies**: datetime, dataclasses, typing
**Status**: NO CHANGES to existing code, just organization

**Checklist**:
- [ ] Create `src/core/background_scheduler/models.py`
- [ ] Move enums and dataclass
- [ ] Verify serialization methods still work
- [ ] Update imports in original file

#### 1.2 Create `task_store.py` (~70 lines)
**Extract**: `_load_tasks()`, `_save_task()`, file I/O logic

**Lines to extract from original**: ~900-950 area (persistence methods)
**Dependencies**: aiofiles, Path, BackgroundTask
**Key Methods**:
- `async load_tasks(state_dir: Path) -> Dict[str, BackgroundTask]`
- `async save_task(state_dir: Path, task: BackgroundTask) -> None`
- `async delete_task(state_dir: Path, task_id: str) -> None`

**Checklist**:
- [ ] Create `src/core/background_scheduler/stores/task_store.py`
- [ ] Use aiofiles for all I/O (rule: async-file-operations-rules.md)
- [ ] Implement atomic writes (temp file + rename)
- [ ] Add error handling per error-handling-rules.md
- [ ] Unit test: test_task_store.py

#### 1.3 Create `perplexity_client.py` (~150 lines)
**Extract**: Consolidate 8+ instances of Perplexity API calls

**Current Duplications**:
- News fetching: `_fetch_news()` at lines ~1400
- Earnings fetching: `_fetch_earnings()` at lines ~1500
- Sentiment analysis: `_analyze_sentiment()` at lines ~1781
- Recommendation generation: `_generate_recommendations()` at lines ~1600

**New Interface**:
```python
class PerplexityClient:
    async def fetch_news(self, symbols: List[str], limit: int = 10) -> str
    async def fetch_earnings(self, symbols: List[str]) -> str
    async def analyze_sentiment(self, content: str, context: str) -> str
    async def generate_recommendations(self, context: Dict) -> str
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/clients/perplexity_client.py`
- [ ] Implement centralized API calling with error handling
- [ ] Add logging for all API calls
- [ ] Unit test: test_perplexity_client.py
- [ ] Verify rate limiting considerations

#### 1.4 Create `api_key_rotator.py` (~50 lines)
**Extract**: Hard-coded API key rotation logic

**Current Implementation**: Instance variable with round-robin
**New Interface**:
```python
class APIKeyRotator:
    def __init__(self, api_keys: List[str])
    def get_next_key(self) -> str
    def rotate_on_error(self, key: str) -> str
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/clients/api_key_rotator.py`
- [ ] Implement thread-safe rotation
- [ ] Add error tracking per key
- [ ] Unit test: test_api_key_rotator.py

**Phase 1 Verification**:
- [ ] All utilities are independent modules
- [ ] No circular dependencies
- [ ] Original BackgroundScheduler still imports and works
- [ ] Run: `pytest src/core/background_scheduler/tests/` (Phase 1 subset)

---

### Phase 2: Extract Task Scheduler Core (2-3 hours)

**Objective**: Extract task lifecycle management and execution queuing.

#### 2.1 Create `task_scheduler.py` (~250 lines)
**Extract**: Task scheduling, queuing, priority handling

**Lines to extract from original**:
- `schedule_task()` at lines ~170-195
- `cancel_task()` at lines ~197-212
- `_execute_due_tasks()` at lines ~440-500
- `_scheduling_loop()` at lines ~420-428
- Task queue management logic

**New Interface**:
```python
class TaskScheduler:
    async def schedule_task(
        self,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: int = 0,
        interval_seconds: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> str

    async def cancel_task(self, task_id: str) -> bool

    async def get_due_tasks(self) -> List[BackgroundTask]

    async def update_next_execution(self, task_id: str, interval_seconds: int) -> None
```

**Dependencies**: TaskStore, BackgroundTask models
**No Dependencies On**: Perplexity, News, Earnings, etc.

**Checklist**:
- [ ] Create `src/core/background_scheduler/core/task_scheduler.py`
- [ ] Move scheduling logic
- [ ] Implement task state machine
- [ ] Add logging for task lifecycle events
- [ ] Unit test: test_task_scheduler.py
- [ ] Integration test: scheduler + task_store together

---

### Phase 3: Extract Domain Processors (4-6 hours)

**Objective**: Separate business logic for different data domains.

#### 3.1 Create `earnings_processor.py` (~400 lines)
**Extract**: All earnings-related logic

**Methods to extract**:
- `_fetch_earnings()` (fetch from API)
- `_parse_earnings_data()` (data parsing - lines ~1800-1900)
- `_parse_structured_earnings()` (structured parsing - lines ~1826)
- `_parse_regex_earnings()` (regex parsing - lines ~1901)
- `_basic_earnings_extraction()` (fallback - lines ~1918)
- `_extract_next_earnings_date()` (date extraction - lines ~1763)
- `_handle_earnings_event()` (event handling)
- `_execute_earnings_check_task()` (task execution)

**New Interface**:
```python
class EarningsProcessor:
    async def fetch_latest_earnings(self, symbols: List[str]) -> Dict[str, Any]

    def parse_earnings_data(self, earnings_text: str) -> Dict[str, Any]

    async def process_earnings_event(self, event_data: Dict) -> None

    def extract_next_earnings_date(self, content: str, symbol: str) -> Optional[str]
```

**Dependencies**: PerplexityClient, BackgroundTask
**Responsibilities**:
- Fetching earnings data via API
- Parsing earnings information (3 strategies)
- Extracting structured data
- Event handling for earnings announcements
- Task execution

**Checklist**:
- [ ] Create `src/core/background_scheduler/processors/earnings_processor.py`
- [ ] Extract parsing methods (consolidate 3 strategies)
- [ ] Move event handling for earnings
- [ ] Add comprehensive logging
- [ ] Unit test: test_earnings_processor.py (parsing logic)
- [ ] Mock Perplexity API for tests
- [ ] Test all 3 parsing strategies with real earnings examples

#### 3.2 Create `news_processor.py` (~300 lines)
**Extract**: All news-related logic

**Methods to extract**:
- `_fetch_news()` (fetch from API)
- `_fetch_daily_news()` (daily aggregation)
- `_extract_news_for_symbol()` (extraction - lines ~1745)
- `_calculate_news_relevance()` (scoring - lines ~1630)
- `_handle_news_event()` (event handling)
- `_execute_news_monitoring_task()` (task execution)

**New Interface**:
```python
class NewsProcessor:
    async def fetch_recent_news(self, symbols: List[str], hours: int = 24) -> Dict[str, Any]

    async def fetch_daily_news(self, symbols: List[str]) -> Dict[str, Any]

    def calculate_relevance_score(
        self,
        news_content: str,
        earnings_content: str,
        focus_significant: bool
    ) -> float

    async def process_news_event(self, event_data: Dict) -> None
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/processors/news_processor.py`
- [ ] Extract news fetching logic
- [ ] Extract relevance scoring algorithm
- [ ] Move event handling for news alerts
- [ ] Add comprehensive logging
- [ ] Unit test: test_news_processor.py
- [ ] Test relevance scoring algorithm with real news

#### 3.3 Create `fundamental_analyzer.py` (~60 lines)
**Extract**: Fundamental analysis delegation

**Current State**: Minimal logic, mostly delegates to `FundamentalService`

**New Interface**:
```python
class FundamentalAnalyzer:
    async def analyze_fundamentals(self, symbols: List[str]) -> Dict[str, Any]

    async def process_fundamental_event(self, event_data: Dict) -> None
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/processors/fundamental_analyzer.py`
- [ ] Wrap FundamentalService calls
- [ ] Add error handling
- [ ] Unit test: test_fundamental_analyzer.py

**Phase 3 Verification**:
- [ ] Each processor is independently testable
- [ ] No circular dependencies between processors
- [ ] Perplexity API calls consolidated (no duplicates)
- [ ] Run: `pytest src/core/background_scheduler/tests/processors/`

---

### Phase 4: Extract Monitor Services (3-4 hours)

**Objective**: Separate real-time monitoring logic.

#### 4.1 Create `market_monitor.py` (~80 lines)
**Extract**: Market hours detection and status

**Methods to extract**:
- `_check_market_status()` (IST market hours check)
- `_market_monitoring_loop()` (monitoring loop)
- `_handle_market_open_event()` (event)
- `_handle_market_close_event()` (event)
- `is_market_open()` helper

**New Interface**:
```python
class MarketMonitor:
    async def check_market_status(self) -> Dict[str, Any]

    def is_market_open(self) -> bool

    async def start_monitoring_loop(self, on_market_open: Callable, on_market_close: Callable) -> None
```

**Configuration**:
- Market open: 9:15 AM IST
- Market close: 3:30 PM IST
- Timezone: UTC+5:30

**Checklist**:
- [ ] Create `src/core/background_scheduler/monitors/market_monitor.py`
- [ ] Move market hours logic
- [ ] Add timezone handling (IST vs UTC)
- [ ] Unit test: test_market_monitor.py
- [ ] Test timezone conversions thoroughly

#### 4.2 Create `risk_monitor.py` (~150 lines)
**Extract**: Stop loss and price monitoring

**Methods to extract**:
- `_check_stop_loss()` (price vs stop loss)
- `_handle_stop_loss_event()` (event)
- `_handle_price_movement_event()` (price alerts)
- `_execute_stop_loss_monitor_task()` (task execution)

**New Interface**:
```python
class RiskMonitor:
    async def check_positions_for_stop_loss(self) -> List[Dict[str, Any]]

    async def process_stop_loss_event(self, event_data: Dict) -> None

    async def process_price_movement_event(self, event_data: Dict) -> None

    async def start_monitoring_loop(self, callback: Callable) -> None
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/monitors/risk_monitor.py`
- [ ] Extract stop loss checking logic
- [ ] Extract price monitoring logic
- [ ] Add event handling
- [ ] Unit test: test_risk_monitor.py
- [ ] Integration test: risk monitor with orchestrator

#### 4.3 Create `health_monitor.py` (~30 lines)
**Extract**: System health checks

**Methods to extract**:
- `_execute_health_check_task()` (task execution)
- Health check logic

**New Interface**:
```python
class HealthMonitor:
    async def check_system_health(self) -> Dict[str, Any]

    async def execute_health_check_task(self) -> None
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/monitors/health_monitor.py`
- [ ] Move health check logic
- [ ] Add diagnostics collection
- [ ] Unit test: test_health_monitor.py

**Phase 4 Verification**:
- [ ] Each monitor is independently testable
- [ ] Monitors can be started/stopped independently
- [ ] No cross-monitor dependencies
- [ ] Run: `pytest src/core/background_scheduler/tests/monitors/`

---

### Phase 5: Extract Config and Event Handling (2-3 hours)

**Objective**: Separate configuration management and event routing.

#### 5.1 Create `task_config_manager.py` (~140 lines)
**Extract**: Configuration reloading and task synchronization

**Methods to extract**:
- `reload_config()` (main method - lines ~231-384)
- `_sync_task_with_config()` (helper)
- `_schedule_time_based_tasks()` (time-based scheduling)

**New Interface**:
```python
class TaskConfigManager:
    async def reload_config(self, new_config: Config, scheduler: TaskScheduler) -> None

    async def apply_task_config(self, task: BackgroundTask, config: Any) -> None
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/config/task_config_manager.py`
- [ ] Extract config reload logic
- [ ] Break down 15+ if-elif branches into a config mapping
- [ ] Add validation
- [ ] Unit test: test_task_config_manager.py
- [ ] Test config reload with various scenarios

#### 5.2 Create `event_handler.py` (~50 lines)
**Extract**: Event routing and dispatch

**Methods to extract**:
- `trigger_event()` (main dispatcher - lines ~214-229)
- Event routing logic

**New Interface**:
```python
class EventHandler:
    def register_handler(self, event_type: str, handler: Callable) -> None

    async def trigger_event(self, event_type: str, event_data: Dict) -> None

    def get_registered_events(self) -> List[str]
```

**Event Types Supported**:
- earnings_announced
- stop_loss_triggered
- price_movement
- news_alert
- market_open
- market_close

**Checklist**:
- [ ] Create `src/core/background_scheduler/events/event_handler.py`
- [ ] Implement publish-subscribe pattern
- [ ] Move event routing logic
- [ ] Unit test: test_event_handler.py

**Phase 5 Verification**:
- [ ] Config manager is independent of execution logic
- [ ] Event handler supports dynamic handler registration
- [ ] No magic strings, events are type-safe
- [ ] Run: `pytest src/core/background_scheduler/tests/config/`

---

### Phase 6: Create Facade and Integration (1-2 hours)

**Objective**: Create new BackgroundScheduler facade that coordinates all components.

#### 6.1 Refactor `background_scheduler.py` (~150 lines)
**Transform**: From God Object to Facade

**New Structure**:
```python
class BackgroundScheduler:
    def __init__(self, config: Config, state_manager: DatabaseStateManager, orchestrator=None):
        self.scheduler = TaskScheduler(state_manager)
        self.config_manager = TaskConfigManager()
        self.event_handler = EventHandler()

        self.earnings_processor = EarningsProcessor(PerplexityClient())
        self.news_processor = NewsProcessor(PerplexityClient())
        self.fundamental_analyzer = FundamentalAnalyzer()

        self.market_monitor = MarketMonitor()
        self.risk_monitor = RiskMonitor()
        self.health_monitor = HealthMonitor()

        self._setup_event_handlers()

    async def start(self) -> List[asyncio.Task]:
        # Coordinate component startup
        # Return monitoring tasks

    async def stop(self) -> None:
        # Coordinate graceful shutdown

    # Delegate public methods to components
    async def schedule_task(self, ...): ...
    async def cancel_task(self, ...): ...
    async def trigger_event(self, ...): ...
    async def reload_config(self, ...): ...
    async def get_scheduler_status(self) -> Dict: ...

    def _setup_event_handlers(self) -> None:
        # Register all event handlers
```

**Key Responsibilities**:
- Dependency injection and component initialization
- Lifecycle coordination (start/stop)
- Event routing setup
- Public API delegation

**Checklist**:
- [ ] Refactor `src/core/background_scheduler.py` to facade
- [ ] Remove all business logic (keep only delegation)
- [ ] Maintain backward compatibility (same public API)
- [ ] Add comprehensive docstrings
- [ ] Integration test: test_background_scheduler_facade.py

#### 6.2 Update `__init__.py` (~20 lines)
**Create**: Public API exports

```python
from .models import TaskType, TaskPriority, BackgroundTask
from .background_scheduler import BackgroundScheduler

__all__ = ["BackgroundScheduler", "TaskType", "TaskPriority", "BackgroundTask"]
```

**Checklist**:
- [ ] Create `src/core/background_scheduler/__init__.py`
- [ ] Export public classes
- [ ] Update imports in rest of codebase

**Phase 6 Verification**:
- [ ] All existing imports still work
- [ ] No breaking changes to public API
- [ ] Original file can be safely deprecated
- [ ] Run full integration tests

---

### Phase 7: Update Imports and Verify (1-2 hours)

**Objective**: Update all files importing from BackgroundScheduler.

**Files to Update**:
1. `src/web/app.py` - WebSocket handlers, dependency injection
2. `src/core/robo_trader_orchestrator.py` - Main orchestrator
3. `src/services/` - Any services using scheduler
4. Test files importing from scheduler

**Checklist**:
- [ ] Update all imports to use new module structure
- [ ] Verify no circular imports
- [ ] Run full test suite: `pytest`
- [ ] Run type checking: `mypy src/`
- [ ] Run linting: `ruff check src/`
- [ ] Integration testing with full application

---

## Testing Strategy

### Unit Tests (Per Component)

**Phase 1 Tests** (~2 hours):
- `test_models.py` - Task serialization/deserialization
- `test_task_store.py` - File I/O, atomic writes
- `test_perplexity_client.py` - API mocking, error handling
- `test_api_key_rotator.py` - Key rotation logic

**Phase 2 Tests** (~1 hour):
- `test_task_scheduler.py` - Task queuing, priority ordering, due task detection

**Phase 3 Tests** (~3 hours):
- `test_earnings_processor.py` - 3 parsing strategies, edge cases
- `test_news_processor.py` - Relevance scoring, filtering
- `test_fundamental_analyzer.py` - Service delegation

**Phase 4 Tests** (~2 hours):
- `test_market_monitor.py` - IST timezone handling
- `test_risk_monitor.py` - Stop loss detection
- `test_health_monitor.py` - Health checks

**Phase 5 Tests** (~1.5 hours):
- `test_task_config_manager.py` - Config reload scenarios
- `test_event_handler.py` - Event routing, handler registration

**Phase 6+ Tests** (~1.5 hours):
- `test_background_scheduler_facade.py` - Full integration
- Update existing tests for new import paths

**Total Test Development**: ~11 hours
**Target Coverage**: 80%+

### Integration Tests

**Scenario 1**: Full scheduler lifecycle
```python
async def test_scheduler_start_stop_cycle():
    scheduler = BackgroundScheduler(config, state_manager)
    tasks = await scheduler.start()
    await asyncio.sleep(2)
    await scheduler.stop()
    # Verify all tasks cancelled, no resource leaks
```

**Scenario 2**: Task execution end-to-end
```python
async def test_earnings_task_full_execution():
    # Schedule earnings task
    # Verify it executes at correct time
    # Verify processors called
    # Verify results stored
```

**Scenario 3**: Event handling
```python
async def test_market_open_event_triggers_tasks():
    # Trigger market_open event
    # Verify dependent tasks scheduled
```

---

## Risk Mitigation

| Risk | Mitigation | Effort |
|------|-----------|--------|
| Breaking changes to API | Phased extraction maintains backward compatibility | Low |
| Circular dependencies | Strict dependency rules enforced (Phase 1 utilities have ZERO deps) | Low |
| Incomplete logic transfer | Detailed method extraction list per phase | Medium |
| Test coverage gaps | Comprehensive unit + integration tests per phase | High |
| Database migration issues | TaskStore uses same format, no schema changes | Low |
| Performance regression | Profiling before/after Phase 1 and Phase 6 | Medium |

---

## Validation Checklist (Per Phase)

### General Validation
- [ ] No new imports of the monolithic file
- [ ] Circular dependency check: `pip install pydeps && pydeps src/core/background_scheduler --show-deps`
- [ ] Type checking passes: `mypy src/core/background_scheduler`
- [ ] Linting passes: `ruff check src/core/background_scheduler`
- [ ] All tests pass: `pytest src/core/background_scheduler/tests/`
- [ ] Original file imports still work (backward compatibility)

### Integration Validation
- [ ] Application starts without errors
- [ ] WebSocket connections work
- [ ] Background tasks execute on schedule
- [ ] Events trigger correctly
- [ ] Configuration reloading works
- [ ] No memory leaks or resource exhaustion

---

## Implementation Strategy

### Key Principles

1. **Backward Compatibility**: Old imports continue working throughout refactoring
2. **Phased Approach**: Complete each phase before moving to next
3. **Continuous Testing**: Unit tests before integration
4. **Zero Downtime**: Refactoring doesn't affect running application
5. **Documentation**: Comprehensive docstrings for each new module

### Git Workflow

```bash
# Create feature branch
git checkout -b refactor/background-scheduler-modularization

# Per phase commits
git add src/core/background_scheduler/models.py
git commit -m "Phase 1.1: Extract TaskType, TaskPriority, BackgroundTask models"

# After each phase
git add -A
git commit -m "Phase 1: Extract utility classes (TaskStore, PerplexityClient, APIKeyRotator)"

# Final integration
git add -A
git commit -m "Complete: Background Scheduler modularization (6 phases, 2348 → 1200 lines total)"
```

---

## Success Criteria

✅ **Maintainability**: No file > 400 lines
✅ **Single Responsibility**: Each module handles one domain
✅ **Testability**: 80%+ code coverage
✅ **No Breaking Changes**: All existing imports work
✅ **Performance**: Same or better than original
✅ **Documentation**: Every public class/method documented
✅ **Code Quality**: Passes mypy, ruff, pylint

---

## Timeline Estimate

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| 1: Utilities | 4-6 hrs | Day 1 | Day 1 |
| 2: TaskScheduler | 2-3 hrs | Day 2 | Day 2 |
| 3: Processors | 4-6 hrs | Day 2 | Day 3 |
| 4: Monitors | 3-4 hrs | Day 3 | Day 3 |
| 5: Config/Events | 2-3 hrs | Day 4 | Day 4 |
| 6: Facade | 1-2 hrs | Day 4 | Day 4 |
| 7: Integration | 1-2 hrs | Day 5 | Day 5 |
| Testing | 11 hrs | Throughout | Throughout |
| **Total** | **16-24 hrs** | | |

---

## Next Steps

1. ✅ Review this plan with team
2. ⏳ Proceed to Phase 1 implementation
3. ⏳ Run tests and verify each phase
4. ⏳ Create pull request with all changes
5. ⏳ Code review and merge

---

**Document Version**: 1.0
**Date**: 2025-10-18
**Status**: Plan Complete - Ready for Implementation
**Owner**: Claude Code
