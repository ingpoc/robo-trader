# Status Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/status/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Overview

Status coordinators aggregate and report system status across multiple domains. The architecture follows an orchestrator pattern where `StatusCoordinator` delegates to focused status coordinators.

## Architecture Pattern

### Orchestrator + Focused Coordinators

- **`StatusCoordinator`**: Main orchestrator (max 200 lines)
  - Delegates to focused status coordinators
  - Handles broadcasting and change detection
  - Provides unified status interface

- **Focused Coordinators** (max 150 lines each):
  - `SystemStatusCoordinator` - Orchestrates scheduler and infrastructure status
  - `SchedulerStatusCoordinator` - Scheduler-specific status
  - `InfrastructureStatusCoordinator` - Database, websocket, system resources
  - `AIStatusCoordinator` - AI and Claude agent status
  - `AgentStatusCoordinator` - Trading agent status
  - `PortfolioStatusCoordinator` - Portfolio status

### Focused Subfolders

- **`broadcast/`**: Broadcasting coordinators
  - `StatusBroadcastCoordinator` - Status broadcasting and change detection
  
- **`aggregation/`**: Aggregation coordinators
  - `StatusAggregationCoordinator` - System component aggregation

### Hierarchy

```
StatusCoordinator (orchestrator)
├── StatusAggregationCoordinator (focused, aggregation/)
│   └── Aggregates from focused coordinators
├── StatusBroadcastCoordinator (focused, broadcast/)
│   └── Handles broadcasting and change detection
├── SystemStatusCoordinator (orchestrator)
│   ├── SchedulerStatusCoordinator (focused)
│   └── InfrastructureStatusCoordinator (focused)
├── AIStatusCoordinator (focused)
├── AgentStatusCoordinator (focused)
└── PortfolioStatusCoordinator (focused)
```

## Rules

### ✅ DO

- ✅ Inherit from `BaseCoordinator`
- ✅ Delegate aggregation to focused coordinators
- ✅ Emit status change events
- ✅ Implement `get_status()` method returning structured dict
- ✅ Use broadcast coordinator for UI updates
- ✅ Track last broadcast state to detect changes
- ✅ Keep orchestrators under 200 lines
- ✅ Keep focused coordinators under 150 lines

### ❌ DON'T

- ❌ Implement business logic directly in orchestrator
- ❌ Access services directly (use injected dependencies)
- ❌ Broadcast on every call (only on changes)
- ❌ Return unstructured status data
- ❌ Exceed line limits

## Implementation Pattern

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.config import Config

class SystemStatusCoordinator(BaseCoordinator):
    """Orchestrates scheduler and infrastructure status."""
    
    def __init__(
        self,
        config: Config,
        scheduler_status_coordinator: SchedulerStatusCoordinator,
        infrastructure_status_coordinator: InfrastructureStatusCoordinator
    ):
        super().__init__(config)
        self.scheduler_status_coordinator = scheduler_status_coordinator
        self.infrastructure_status_coordinator = infrastructure_status_coordinator
    
    async def get_status(self) -> Dict[str, Any]:
        """Get aggregated system status."""
        scheduler_status = await self.scheduler_status_coordinator.get_status()
        infrastructure_status = await self.infrastructure_status_coordinator.get_status()
        
        return {
            "scheduler": scheduler_status,
            "infrastructure": infrastructure_status,
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Status Data Structure

All status methods should return consistent structure:

```python
{
    "status": "healthy" | "degraded" | "unhealthy",
    "components": {
        "component_name": {
            "status": "healthy" | "degraded" | "unhealthy",
            "details": {...},
            "last_updated": "ISO timestamp"
        }
    },
    "timestamp": "ISO timestamp"
}
```

## Broadcasting

- Use `BroadcastCoordinator` for UI updates
- Only broadcast when status changes (compare with last state)
- Include timestamp in all broadcasts
- Handle broadcast failures gracefully

## Dependencies

Status coordinators typically depend on:
- `BroadcastCoordinator` - For UI updates
- `BackgroundScheduler` - For scheduler status
- `DatabaseStateManager` - For infrastructure status
- `SessionCoordinator` - For AI status
- Domain-specific services - For component status

