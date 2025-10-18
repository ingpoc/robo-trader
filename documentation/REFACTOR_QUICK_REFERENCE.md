# Background Scheduler Refactoring - Quick Reference

## File Structure After Refactoring

```
src/core/background_scheduler/
├── __init__.py                          # Public API (20 lines)
├── models.py                            # Task models (50 lines)
├── background_scheduler.py              # Facade (150 lines) ← Previously 2348 lines!
├── stores/
│   ├── __init__.py
│   └── task_store.py                    # File I/O (70 lines)
├── clients/
│   ├── __init__.py
│   ├── perplexity_client.py             # Unified API (150 lines)
│   └── api_key_rotator.py               # Key rotation (50 lines)
├── processors/
│   ├── __init__.py
│   ├── earnings_processor.py            # Earnings logic (400 lines)
│   ├── news_processor.py                # News logic (300 lines)
│   └── fundamental_analyzer.py          # Fundamentals (60 lines)
├── monitors/
│   ├── __init__.py
│   ├── market_monitor.py                # Market hours (80 lines)
│   ├── risk_monitor.py                  # Stop loss (150 lines)
│   └── health_monitor.py                # Health checks (30 lines)
├── config/
│   ├── __init__.py
│   └── task_config_manager.py           # Config mgmt (140 lines)
├── events/
│   ├── __init__.py
│   └── event_handler.py                 # Event routing (50 lines)
├── core/
│   ├── __init__.py
│   └── task_scheduler.py                # Task lifecycle (250 lines)
└── tests/
    ├── test_models.py
    ├── test_background_scheduler.py
    ├── stores/
    │   └── test_task_store.py
    ├── clients/
    │   ├── test_perplexity_client.py
    │   └── test_api_key_rotator.py
    ├── processors/
    │   ├── test_earnings_processor.py
    │   ├── test_news_processor.py
    │   └── test_fundamental_analyzer.py
    ├── monitors/
    │   ├── test_market_monitor.py
    │   ├── test_risk_monitor.py
    │   └── test_health_monitor.py
    ├── config/
    │   └── test_task_config_manager.py
    ├── events/
    │   └── test_event_handler.py
    └── core/
        └── test_task_scheduler.py
```

---

## Methods → New Locations

| Method | Original Lines | New File | New Lines | Status |
|--------|----------------|----------|-----------|--------|
| `__init__` | 105-400 | Facade | 30-50 | Phase 6 |
| `start()` | 132-155 | Facade | Coordinates | Phase 6 |
| `stop()` | 157-168 | Facade | Coordinates | Phase 6 |
| `schedule_task()` | 170-195 | `task_scheduler.py` | ~50 | Phase 2 |
| `cancel_task()` | 197-212 | `task_scheduler.py` | ~30 | Phase 2 |
| `trigger_event()` | 214-229 | `event_handler.py` | ~40 | Phase 5 |
| `reload_config()` | 231-384 | `task_config_manager.py` | ~100 | Phase 5 |
| `get_scheduler_status()` | 386-400 | Facade | ~40 | Phase 6 |
| `_count_tasks_by_type()` | 402-409 | `task_scheduler.py` | ~15 | Phase 2 |
| `_count_tasks_by_priority()` | 411-418 | `task_scheduler.py` | ~15 | Phase 2 |
| `_scheduling_loop()` | 420-428 | `task_scheduler.py` | ~30 | Phase 2 |
| `_market_monitoring_loop()` | 430-438 | `market_monitor.py` | ~25 | Phase 4 |
| `_execute_due_tasks()` | 440-500+ | `task_scheduler.py` | ~100 | Phase 2 |
| `_execute_task_logic()` | ~500-900 | Task dispatch (Facade) | ~200 | Phase 2-6 |
| `_load_tasks()` | ~900-950 | `task_store.py` | ~50 | Phase 1 |
| `_save_task()` | ~950-1000 | `task_store.py` | ~30 | Phase 1 |
| Earnings methods (8 methods) | ~1400-1950 | `earnings_processor.py` | ~400 | Phase 3 |
| News methods (6 methods) | ~1600-1800 | `news_processor.py` | ~300 | Phase 3 |
| Sentiment/parsing methods (4 methods) | ~1750-1900 | `news_processor.py` or `earnings_processor.py` | ~150 | Phase 3 |
| Health check methods | ~2100-2150 | `health_monitor.py` | ~30 | Phase 4 |
| Stop loss methods (3 methods) | ~2150-2200 | `risk_monitor.py` | ~150 | Phase 4 |
| Market check methods (3 methods) | ~2200-2250 | `market_monitor.py` | ~80 | Phase 4 |
| Recommendation methods | ~2250-2300 | Facade + orchestrator delegation | ~50 | Phase 6 |
| Portfolio/screening methods | ~2300-2348 | Facade + orchestrator delegation | ~50 | Phase 6 |

---

## Import Changes for Users

### Before (Current)
```python
from src.core.background_scheduler import BackgroundScheduler, TaskType, TaskPriority

scheduler = BackgroundScheduler(config, state_manager)
```

### After (New - Backward Compatible!)
```python
# OLD imports still work!
from src.core.background_scheduler import BackgroundScheduler, TaskType, TaskPriority

# OR use new structure (but not necessary)
from src.core.background_scheduler.background_scheduler import BackgroundScheduler
from src.core.background_scheduler.models import TaskType, TaskPriority

# Both work identically
scheduler = BackgroundScheduler(config, state_manager)
```

---

## Dependency Graph (High Level)

```
┌─────────────────────────────────────────────────────────┐
│ BackgroundScheduler (Facade)                            │
├─────────────────────────────────────────────────────────┤
│  ↓                ↓              ↓           ↓           │
│ TaskScheduler  TaskConfigMgr  EventHandler Orchestrator │
│  ↓              ↓               ↓            ↓           │
│ TaskStore    (Monitors)     Processors    (CLI/API)     │
│              (Processors)                                │
└─────────────────────────────────────────────────────────┘

Processors:
├── EarningsProcessor → PerplexityClient
├── NewsProcessor → PerplexityClient
└── FundamentalAnalyzer → FundamentalService

Monitors:
├── MarketMonitor (no deps)
├── RiskMonitor → Orchestrator
└── HealthMonitor (no deps)

Clients:
├── PerplexityClient → APIKeyRotator
└── APIKeyRotator (no deps)
```

**Key Principle**: Low-level modules (clients, stores) have NO dependencies on high-level modules (facade, orchestrator)

---

## Phase Execution Guide

### Phase 1: Utilities ⏱ 4-6 hours
1. Create `src/core/background_scheduler/` directory
2. Create `models.py` - COPY lines 26-90
3. Create `stores/task_store.py` - EXTRACT file I/O methods
4. Create `clients/perplexity_client.py` - CONSOLIDATE API calls
5. Create `clients/api_key_rotator.py` - EXTRACT key rotation
6. Create `__init__.py` - PUBLIC API
7. **Test**: Unit tests for each module
8. **Verify**: Original imports still work

### Phase 2: Task Scheduler ⏱ 2-3 hours
1. Create `core/task_scheduler.py` - Task lifecycle & queuing
2. **Move methods**:
   - `schedule_task()`
   - `cancel_task()`
   - `_scheduling_loop()`
   - `_execute_due_tasks()`
   - `_count_tasks_by_type()`
   - `_count_tasks_by_priority()`
3. Update original file to import from new module
4. **Test**: Unit + integration tests
5. **Verify**: Scheduler behavior unchanged

### Phase 3: Domain Processors ⏱ 4-6 hours
1. Create `processors/earnings_processor.py` - Earnings domain
2. Create `processors/news_processor.py` - News domain
3. Create `processors/fundamental_analyzer.py` - Fundamentals
4. **Move methods** (see table above)
5. **Update original** to use processors
6. **Test**: Earnings, news, fundamentals independently
7. **Verify**: No duplicate API calls

### Phase 4: Monitor Services ⏱ 3-4 hours
1. Create `monitors/market_monitor.py` - Market hours
2. Create `monitors/risk_monitor.py` - Stop loss detection
3. Create `monitors/health_monitor.py` - Health checks
4. **Move methods** (see table above)
5. **Update original** to use monitors
6. **Test**: Each monitor independently
7. **Verify**: Monitoring behavior unchanged

### Phase 5: Config & Events ⏱ 2-3 hours
1. Create `config/task_config_manager.py` - Config reload
2. Create `events/event_handler.py` - Event routing
3. **Move methods**:
   - `reload_config()` → task_config_manager
   - `trigger_event()` → event_handler
4. **Break down if-elif chains** → config mapping
5. **Test**: Config reload, event routing
6. **Verify**: No breaking changes

### Phase 6: Facade & Integration ⏱ 1-2 hours
1. Refactor `background_scheduler.py` → Facade pattern
2. **Keep only**:
   - `__init__()` - dependency injection
   - `start()` - coordinates all components
   - `stop()` - graceful shutdown
   - Delegation methods (delegating to components)
3. **Create `__init__.py`** - public API exports
4. **Integration tests** - end-to-end scenarios
5. **Verify**: All existing code still works

---

## Testing Checklist

### Per Phase
- [ ] Unit tests for new modules (80%+ coverage)
- [ ] Mocking external dependencies (Perplexity, FundamentalService)
- [ ] No circular imports
- [ ] Type hints correct (`mypy` passes)
- [ ] Original imports still work
- [ ] No performance regression

### Final Integration
- [ ] Full application starts without errors
- [ ] WebSocket connections work
- [ ] Background tasks execute on schedule
- [ ] Events trigger correctly
- [ ] Configuration reloading works
- [ ] No resource leaks
- [ ] Full test suite passes: `pytest`
- [ ] Type checking passes: `mypy src/`
- [ ] Linting passes: `ruff check src/`

---

## Git Commit Strategy

```bash
# Per-phase commits
git add src/core/background_scheduler/models.py
git commit -m "Phase 1.1: Extract Task model definitions"

git add src/core/background_scheduler/stores/
git commit -m "Phase 1.2: Extract TaskStore (persistence layer)"

git add src/core/background_scheduler/clients/
git commit -m "Phase 1.3: Extract PerplexityClient and APIKeyRotator"

# After phase validation
git commit -m "Phase 1: Extract utility classes (models, stores, clients)

- Consolidated 8 duplicated Perplexity API calls into single client
- Extracted TaskStore for file persistence (atomic writes with aiofiles)
- Created APIKeyRotator for key management
- All utilities are independent with zero cross-dependencies
- Tests: 15 new unit tests, 95% coverage"

# Continue for phases 2-6...

# Final summary
git commit -m "Complete: Background Scheduler modularization

- Reduced monolithic file from 2348 → 150 lines (94% reduction)
- Split into 10 focused modules per SOLID principles
- Consolidated duplicate code (8 → 1 API client)
- Achieved 80%+ test coverage
- Zero breaking changes to public API
- 90% improvement in maintainability

Modules:
- models: Task definitions
- task_store: Persistence
- perplexity_client: Unified API
- api_key_rotator: Key rotation
- task_scheduler: Task lifecycle
- earnings_processor: Earnings domain
- news_processor: News domain
- fundamental_analyzer: Fundamentals
- market_monitor: Market hours
- risk_monitor: Stop loss
- health_monitor: Health checks
- task_config_manager: Config reload
- event_handler: Event routing
- background_scheduler: Facade coordination"
```

---

## Common Questions

**Q: When should I start?**
A: After approval of this plan. See `BACKGROUND_SCHEDULER_REFACTOR_PLAN.md` for detailed specs.

**Q: Will existing code break?**
A: No. Phases maintain 100% backward compatibility. Old imports continue working.

**Q: How long for Phase 1?**
A: 4-6 hours including tests. Lowest risk, highest value (consolidates duplicate code).

**Q: Can I skip phases?**
A: No. Each phase builds on previous. Do them in order.

**Q: What if I find bugs?**
A: Document them. Fix after current phase completes. Add regression test.

**Q: How do I handle circular imports?**
A: Strict dependency rules: utilities have ZERO deps, then core, then processors, then facade.

---

## Success Indicators

- ✅ Phase completes with all tests passing
- ✅ No new circular dependencies
- ✅ No performance regression
- ✅ Type checking passes (`mypy`)
- ✅ Linting passes (`ruff check`)
- ✅ Original imports still work
- ✅ Application starts without errors
- ✅ Background tasks execute normally

---

**Status**: Ready for Implementation
**Next**: Begin Phase 1 when approved
