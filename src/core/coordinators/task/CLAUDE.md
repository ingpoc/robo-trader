# Task Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/task/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Overview

Task coordinators manage collaborative task lifecycle in the multi-agent framework. The architecture follows an orchestrator pattern where `TaskCoordinator` delegates to focused task coordinators.

## Architecture Pattern

### Orchestrator + Focused Coordinators

- **`TaskCoordinator`**: Main orchestrator (max 200 lines)
  - Delegates to focused task coordinators
  - Provides unified task management API
  - Manages task lifecycle

- **Focused Coordinators** (max 150 lines each):
  - `TaskCreationCoordinator` - Task creation and agent assignment
  - `TaskExecutionCoordinator` - Task execution and status management
  - `TaskMaintenanceCoordinator` - Deadline checking and cleanup

- **Model Files**:
  - `collaboration_task.py` - `CollaborationTask`, `CollaborationMode`, `AgentRole`

## Rules

### ✅ DO

- ✅ Inherit from `BaseCoordinator`
- ✅ Use `CollaborationTask` model for task representation
- ✅ Emit task lifecycle events (`task_created`, `task_status_changed`)
- ✅ Handle agent assignment logic
- ✅ Implement deadline checking
- ✅ Clean up old completed tasks
- ✅ Keep orchestrators under 200 lines
- ✅ Keep focused coordinators under 150 lines

### ❌ DON'T

- ❌ Implement business logic directly in orchestrator
- ❌ Access agents directly (use injected dependencies)
- ❌ Block on task operations
- ❌ Exceed line limits

## Implementation Pattern

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.coordinators.task.task_creation_coordinator import TaskCreationCoordinator
from src.core.coordinators.task.task_execution_coordinator import TaskExecutionCoordinator
from src.core.coordinators.task.collaboration_task import CollaborationTask, AgentRole

class TaskCoordinator(BaseCoordinator):
    """Orchestrates task operations."""
    
    def __init__(self, config: Any, state_manager: DatabaseStateManager, event_bus: EventBus):
        super().__init__(config, "task_coordinator")
        self.creation_coordinator = TaskCreationCoordinator(config, event_bus)
        self.execution_coordinator = TaskExecutionCoordinator(config, event_bus)
        # ... other focused coordinators
    
    async def create_task(
        self,
        description: str,
        required_roles: List[AgentRole],
        **kwargs
    ) -> Optional[CollaborationTask]:
        """Create a new collaborative task."""
        task = await self.creation_coordinator.create_task(description, required_roles, **kwargs)
        if task:
            self.execution_coordinator.register_task(task)
        return task
```

## Task Lifecycle

1. **Creation**: `TaskCreationCoordinator.create_task()` - Creates task, emits `task_created` event
2. **Assignment**: `TaskCreationCoordinator.assign_agents_to_task()` - Assigns agents to task
3. **Execution**: `TaskExecutionCoordinator.start_task()` - Starts task, emits status update
4. **Status Updates**: `TaskExecutionCoordinator.update_task_status()` - Updates status, emits `task_status_changed` event
5. **Maintenance**: `TaskMaintenanceCoordinator.check_task_deadlines()` - Checks deadlines
6. **Cleanup**: `TaskMaintenanceCoordinator.cleanup_old_tasks()` - Removes old tasks

## Collaboration Modes

- `SEQUENTIAL` - Agents work one after another
- `PARALLEL` - Agents work simultaneously
- `CONSENSUS` - Agents vote on decisions

## Event Types

- `task_created` - Task created
- `task_status_changed` - Task status updated
- `agent_message` - Message to agent about task

## Dependencies

Task coordinators typically depend on:
- `EventBus` - For event emission
- `DatabaseStateManager` - For task persistence (optional)
- `AgentCoordinator` - For agent availability

