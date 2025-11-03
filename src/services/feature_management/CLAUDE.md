# Feature Management Service Guidelines

> **Scope**: Applies to `src/services/feature_management/` directory. Read `src/services/CLAUDE.md` for parent context.

## Purpose

The `feature_management/` directory contains the **feature management system** that handles feature flags, dependencies, lifecycle management, and integration with other services.

## Architecture Pattern

### Service Layer Pattern

The feature management system uses a **service layer architecture** with domain-separated modules:

- **`service.py`**: Main feature management service (orchestrator)
  - Feature CRUD operations
  - Dependency resolution
  - State management
  - Integration orchestration

- **Supporting Modules**:
  - `database.py` - Feature database operations
  - `models.py` - Feature data models
  - `dependency_resolver.py` - Dependency resolution logic
  - `lifecycle_manager.py` - Feature lifecycle management
  - `scheduler_integration.py` - Background scheduler integration
  - `agent_integration.py` - Agent management integration
  - `service_integration.py` - Service registry integration
  - `resource_cleanup.py` - Resource cleanup management
  - `error_recovery.py` - Error recovery management
  - `event_broadcasting.py` - Event broadcasting service

## File Structure

```
feature_management/
├── __init__.py
├── service.py                    # Main service (orchestrator)
├── database.py                   # Database operations
├── models.py                     # Data models
├── dependency_resolver.py        # Dependency resolution
├── lifecycle_manager.py          # Lifecycle management
├── scheduler_integration.py      # Scheduler integration
├── agent_integration.py          # Agent integration
├── service_integration.py        # Service integration
├── resource_cleanup.py           # Resource cleanup
├── error_recovery.py             # Error recovery
└── event_broadcasting.py         # Event broadcasting
```

## Rules

### ✅ DO

- ✅ **Keep service < 350 lines** - Refactor if exceeds limit
- ✅ **Use dependency injection** - Inject dependencies via constructor
- ✅ **Emit events** - Use `EventBus` for cross-cutting concerns
- ✅ **Handle errors gracefully** - Wrap in `TradingError` with proper categories
- ✅ **Use database locking** - Use locked state methods for database operations
- ✅ **Validate dependencies** - Check dependencies before feature operations
- ✅ **Track feature state** - Maintain feature state consistency

### ❌ DON'T

- ❌ **Access database directly** - Use database module
- ❌ **Exceed line limits** - Refactor if service exceeds 350 lines
- ❌ **Mix concerns** - Keep supporting modules focused
- ❌ **Skip validation** - Always validate feature configs and dependencies

## Dependencies

- `EventBus` - For event-driven communication
- `Config` - For configuration
- `DatabaseStateManager` - For state management (via locked methods)
- `BackgroundScheduler` - For scheduler integration
- `AgentCoordinator` - For agent integration
- `ServiceRegistry` - For service integration

## Testing

- Test feature CRUD operations
- Test dependency resolution
- Test lifecycle management
- Test integration with other services
- Test error recovery
- Test resource cleanup

## Maintenance

- **When service grows**: Split into focused services or extract supporting modules
- **When patterns change**: Update this CLAUDE.md and parent `src/services/CLAUDE.md`
- **When new features needed**: Add to appropriate module or create new focused module

