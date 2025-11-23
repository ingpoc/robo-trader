# Feature Management - src/services/feature_management/

## Modules
| Module | Purpose | Scope |
|--------|---------|-------|
| service.py | Feature CRUD & orchestration | <350 lines |
| database.py | Database operations | Feature persistence |
| models.py | Data models | Feature schema |
| dependency_resolver.py | Dependency resolution | Feature deps |
| lifecycle_manager.py | Lifecycle management | State transitions |
| scheduler_integration.py | Scheduler integration | Task scheduling |
| agent_integration.py | Agent management | Agent registry |
| resource_cleanup.py | Resource cleanup | Memory management |

## Rules
| Rule | Requirement |
|------|-------------|
| Lines | <350 per file, refactor if over |
| Database | Use locked state methods ONLY |
| Events | Emit via EventBus for comms |
| Validation | Check deps before feature ops |
| State | Maintain feature consistency |
| Errors | Wrap in TradingError with context |

## Pattern
```python
class FeatureManagementService(EventHandler):
    async def enable_feature(self, feature_id):
        await self._validate_deps(feature_id)
        await config_state.store_feature(feature_id, enabled=True)
        self.event_bus.emit(FeatureEnabled(feature_id))

    async def cleanup(self):
        self.event_bus.unsubscribe(EventType.ALL, self)
```

