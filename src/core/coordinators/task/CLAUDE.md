# Task Coordinator - src/core/coordinators/task/

Multi-agent collaborative task lifecycle. Orchestrator + focused coordinators.

## Pattern
Max 200 lines (orchestrator), max 150 (focused). Use `CollaborationTask` model.

```python
task = await creation_coordinator.create_task(description, required_roles)
await execution_coordinator.register_task(task)
await maintenance_coordinator.check_deadlines()
```

## Coordinators
| Coordinator | Purpose |
|-------------|---------|
| TaskCreationCoordinator | Create, assign agents |
| TaskExecutionCoordinator | Execute, status updates |
| TaskMaintenanceCoordinator | Deadline checking, cleanup |

## Lifecycle
1. Create (emit task_created)
2. Assign agents
3. Execute (emit status_changed)
4. Update status
5. Check deadlines
6. Cleanup old

## Collaboration Modes
SEQUENTIAL - One after another | PARALLEL - Simultaneously | CONSENSUS - Vote on decisions

## Rules
| DO | DON'T |
|----|-------|
| Inherit BaseCoordinator | Business logic in orchestrator |
| Emit lifecycle events | Direct agent access |
| Use CollaborationTask | Block on I/O |
| Handle assignment | Exceed 200/150 lines |
| Check deadlines | Global state |

## Dependencies
EventBus, DatabaseStateManager (optional), AgentCoordinator

