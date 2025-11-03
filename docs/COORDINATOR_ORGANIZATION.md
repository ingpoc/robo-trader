# Coordinator Folder Organization

## Overview

The `src/core/coordinators/` directory is organized into domain-specific subdirectories to improve maintainability and clarity. Each subdirectory contains coordinators and related files for a specific domain.

## Directory Structure

```
src/core/coordinators/
├── __init__.py                    # Package exports (maintains backward compatibility)
├── base_coordinator.py            # Base class for all coordinators
│
├── core/                          # Core system coordinators
│   ├── __init__.py
│   ├── session_coordinator.py     # Claude SDK session lifecycle
│   ├── query_coordinator.py       # Query/request processing
│   ├── lifecycle_coordinator.py   # Emergency operations
│   └── portfolio_coordinator.py   # Portfolio operations
│
├── status/                        # Status aggregation coordinators
│   ├── __init__.py
│   ├── status_coordinator.py      # Main status orchestrator
│   ├── system_status_coordinator.py
│   ├── scheduler_status_coordinator.py
│   ├── infrastructure_status_coordinator.py
│   ├── ai_status_coordinator.py
│   ├── agent_status_coordinator.py
│   └── portfolio_status_coordinator.py
│
├── queue/                         # Queue management coordinators
│   ├── __init__.py
│   ├── queue_coordinator.py       # Main queue orchestrator
│   ├── queue_execution_coordinator.py
│   ├── queue_monitoring_coordinator.py
│   ├── queue_event_coordinator.py
│   └── queue_lifecycle_coordinator.py
│
├── task/                          # Task management coordinators
│   ├── __init__.py
│   ├── task_coordinator.py        # Main task orchestrator
│   ├── task_creation_coordinator.py
│   ├── task_execution_coordinator.py
│   ├── task_maintenance_coordinator.py
│   └── collaboration_task.py       # Model: CollaborationTask
│
├── message/                       # Message routing coordinators
│   ├── __init__.py
│   ├── message_coordinator.py      # Main message orchestrator
│   ├── message_routing_coordinator.py
│   ├── message_handling_coordinator.py
│   └── agent_message.py           # Model: AgentMessage, MessageType
│
├── broadcast/                     # Broadcast coordinators
│   ├── __init__.py
│   ├── broadcast_coordinator.py   # Main broadcast orchestrator
│   ├── broadcast_execution_coordinator.py
│   └── broadcast_health_coordinator.py
│
└── agent/                         # Agent coordination coordinators
    ├── __init__.py
    ├── agent_coordinator.py       # Multi-agent coordination
    ├── claude_agent_coordinator.py # Claude agent session management
    ├── agent_session_coordinator.py
    ├── agent_tool_coordinator.py
    ├── agent_prompt_builder.py
    └── agent_profile.py           # Model: AgentProfile, AgentRole
```

## Organization Principles

### 1. Domain Separation
Each subdirectory represents a specific domain:
- **core/**: Fundamental system coordinators (session, query, lifecycle, portfolio)
- **status/**: All status-related coordinators
- **queue/**: Queue management and execution
- **task/**: Task lifecycle and execution
- **message/**: Inter-agent communication
- **broadcast/**: UI broadcasting and health monitoring
- **agent/**: Agent coordination and management

### 2. Orchestrator Pattern
Each domain has:
- A main orchestrator coordinator (e.g., `status_coordinator.py`)
- Focused sub-coordinators (e.g., `scheduler_status_coordinator.py`)
- The orchestrator delegates to focused coordinators

### 3. Model Files Co-location
Model files (data classes, enums) are placed in the same directory as their coordinators:
- `collaboration_task.py` in `task/`
- `agent_message.py` in `message/`
- `agent_profile.py` in `agent/`

### 4. Import Structure
All imports maintain backward compatibility through `__init__.py` files:
```python
# Old import (still works):
from src.core.coordinators import StatusCoordinator

# New import (recommended):
from src.core.coordinators.status import StatusCoordinator
```

## File Size Limits

Following architectural guidelines:
- **Orchestrator coordinators**: Max 200 lines (delegates to focused coordinators)
- **Focused coordinators**: Max 150 lines (single responsibility)
- **Model files**: No limit (data structures)

## Benefits

1. **Clarity**: Easy to find coordinators by domain
2. **Maintainability**: Related code is grouped together
3. **Scalability**: Easy to add new coordinators to appropriate domains
4. **Discoverability**: Clear folder structure guides developers
5. **Separation of Concerns**: Each folder has a specific, well-defined purpose

## Migration Notes

- All existing imports continue to work (backward compatible)
- New code should use domain-specific imports when possible
- `base_coordinator.py` remains at the root level (used by all coordinators)

