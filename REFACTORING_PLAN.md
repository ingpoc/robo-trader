# Robo-Trader Modularization Refactoring Plan

**Created**: 2025-11-04
**Branch**: orb-stack-containerized
**Goal**: Reduce all files to ≤350 lines following CLAUDE.md standards

---

## Executive Summary

**Current State**: 25 files exceed 350-line limit (worst: 1,428 lines)
**Target State**: All files ≤350 lines, max 10 methods per class
**Timeline**: 3-week phased approach
**Risk Level**: Medium (requires careful import management)

---

## Phase 1: Critical Files (Week 1)

### 1.1 configuration_state.py (1,428 lines → 4 files)

**Current Structure**: Single ConfigurationState class with ~50 methods

**Refactoring Strategy**:
```
src/core/database_state/
├── configuration_state.py (300 lines) - Main facade
├── config_storage/
│   ├── __init__.py
│   ├── background_tasks_store.py (250 lines)
│   ├── ai_agents_store.py (250 lines)
│   ├── global_settings_store.py (200 lines)
│   └── prompts_store.py (200 lines)
└── config_backup.py (200 lines) - Backup operations
```

**Method Distribution**:
- `configuration_state.py`: __init__, initialize, get_*, core API (15 methods)
- `background_tasks_store.py`: Task config CRUD (10 methods)
- `ai_agents_store.py`: Agent config CRUD (10 methods)
- `global_settings_store.py`: Settings CRUD (8 methods)
- `prompts_store.py`: Prompt management (8 methods)
- `config_backup.py`: Backup/restore logic (6 methods)

**Backward Compatibility**:
```python
# configuration_state.py becomes facade
from .config_storage.background_tasks_store import BackgroundTasksStore
from .config_storage.ai_agents_store import AIAgentsStore
# ... etc

class ConfigurationState:
    def __init__(self, db_connection):
        self.tasks = BackgroundTasksStore(db_connection)
        self.agents = AIAgentsStore(db_connection)
        # Proxy methods for backward compatibility
```

---

### 1.2 feature_management/service.py (1,228 lines → 4 files)

**Current Structure**: FeatureManagementService with 47 methods

**Refactoring Strategy**:
```
src/services/feature_management/
├── service.py (300 lines) - Main service facade
├── core/
│   ├── __init__.py
│   ├── feature_crud.py (280 lines) - Create/Read/Update/Delete
│   ├── feature_activation.py (250 lines) - Enable/disable logic
│   └── feature_validation.py (200 lines) - Validation logic
├── dependency_resolver.py (existing - OK at 320 lines)
├── lifecycle_manager.py (847 lines - REFACTOR IN PHASE 2)
└── ... (other existing files)
```

**Method Distribution**:
- `service.py`: __init__, initialize, handle_event, integrations (12 methods)
- `feature_crud.py`: create_feature, get_*, update_feature, delete_feature (10 methods)
- `feature_activation.py`: enable_feature, disable_feature, bulk_update (8 methods)
- `feature_validation.py`: validate_*, check_dependencies (6 methods)

**Key Changes**:
- Extract CRUD operations to feature_crud.py
- Extract enable/disable to feature_activation.py
- Extract validation to feature_validation.py
- Keep event handling and integration in main service

---

### 1.3 portfolio_intelligence_analyzer.py (1,052 lines → 3 files)

**Current Structure**: PortfolioIntelligenceAnalyzer with analysis logic

**Refactoring Strategy**:
```
src/services/portfolio_intelligence/
├── __init__.py
├── analyzer.py (300 lines) - Main facade
├── data_fetcher.py (280 lines) - Data fetching logic
├── claude_analyzer.py (280 lines) - Claude AI analysis
└── recommendation_builder.py (250 lines) - Build recommendations
```

**Method Distribution**:
- `analyzer.py`: Main entry point, coordination (4 methods)
- `data_fetcher.py`: Fetch portfolio, earnings, news, fundamentals (6 methods)
- `claude_analyzer.py`: Claude session, prompt building, analysis (5 methods)
- `recommendation_builder.py`: Parse analysis, build recommendations (5 methods)

**Backward Compatibility**:
```python
# Move file: portfolio_intelligence_analyzer.py → portfolio_intelligence/__init__.py
# Export main class for backward compatibility
from .analyzer import PortfolioIntelligenceAnalyzer
__all__ = ['PortfolioIntelligenceAnalyzer']
```

---

## Phase 2: High-Priority Files (Week 2)

### 2.1 recommendation_service.py (916 lines → 3 files)

**Refactoring Strategy**:
```
src/services/recommendation/
├── __init__.py
├── service.py (300 lines) - Main service
├── builder.py (280 lines) - Build recommendations
└── validator.py (250 lines) - Validate recommendations
```

### 2.2 lifecycle_manager.py (847 lines → 3 files)

**Refactoring Strategy**:
```
src/services/feature_management/lifecycle/
├── __init__.py
├── manager.py (300 lines) - Main manager
├── activation_handler.py (280 lines) - Activation logic
└── deactivation_handler.py (280 lines) - Deactivation logic
```

### 2.3 learning_engine.py (833 lines → 3 files)

**Refactoring Strategy**:
```
src/core/learning/
├── __init__.py
├── engine.py (300 lines) - Main engine
├── pattern_learner.py (280 lines) - Pattern learning
└── performance_tracker.py (250 lines) - Performance tracking
```

### 2.4 web/app.py (822 lines → 3 files)

**Refactoring Strategy**:
```
src/web/
├── app.py (300 lines) - FastAPI app setup
├── startup.py (280 lines) - Startup logic
└── websocket_manager.py (250 lines) - WebSocket management
```

---

## Phase 3: Moderate-Priority Files (Week 3)

### 3.1 ai_planner.py (787 lines → 3 files)
### 3.2 claude_agent_api.py (783 lines → 2 files)
### 3.3 error_recovery.py (756 lines → 2 files)
### 3.4 service_integration.py (735 lines → 2 files)
### 3.5 feature_management_api.py (716 lines → 2 files)

**Strategy**: Split each into 2-3 focused modules

---

## Implementation Checklist

### Pre-Refactoring
- [x] Analyze file structures
- [x] Create refactoring plan
- [x] Create feature branch
- [ ] Run existing tests to establish baseline

### During Refactoring (Per File)
- [ ] Create new module structure
- [ ] Extract methods to new files
- [ ] Update imports in new files
- [ ] Create facade in original file for backward compatibility
- [ ] Update all internal imports
- [ ] Test module in isolation
- [ ] Verify backward compatibility

### Post-Refactoring
- [ ] Run full test suite
- [ ] Update CLAUDE.md if needed
- [ ] Update documentation
- [ ] Create PR with detailed changes

---

## Testing Strategy

1. **Unit Tests**: Each new module should maintain existing tests
2. **Integration Tests**: Verify facades work with old imports
3. **Import Tests**: Verify all imports resolve correctly
4. **Regression Tests**: Ensure no functionality breaks

---

## Risk Mitigation

1. **Backward Compatibility**: All original imports must work
2. **Incremental Changes**: Commit after each file refactoring
3. **Rollback Plan**: Each commit is independently reversible
4. **Import Validation**: Script to check all imports after each change

---

## Success Criteria

- ✅ All files ≤350 lines
- ✅ All classes ≤10 methods
- ✅ All tests pass
- ✅ No breaking changes to public APIs
- ✅ Documentation updated
- ✅ Zero import errors

---

## Refactoring Script Templates

### Template: Create Module Structure
```bash
# Example: configuration_state refactoring
mkdir -p src/core/database_state/config_storage
touch src/core/database_state/config_storage/__init__.py
touch src/core/database_state/config_storage/background_tasks_store.py
# ... etc
```

### Template: Backward Compatibility Test
```python
# Test that old imports still work
from src.core.database_state.configuration_state import ConfigurationState
# Should work without errors
```

---

## Dependencies & Order

**Critical Path**:
1. configuration_state.py (no dependencies)
2. feature_management/service.py (depends on config)
3. portfolio_intelligence_analyzer.py (depends on config)
4. All others (can be done in parallel)

**Import Impact Analysis**:
- configuration_state: Used by ~20 files → High risk
- feature_management: Used by ~10 files → Medium risk
- portfolio_intelligence: Used by ~5 files → Low risk

---

## Notes

- Keep all original files as facades initially
- Remove facades only after full migration
- Use `__all__` to control public exports
- Document all breaking changes (should be none)
