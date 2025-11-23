# Status Coordinator - src/core/coordinators/status/

System status aggregation (scheduler, infrastructure, AI, agents, portfolio). Broadcast on changes only.

## Hierarchy
```
StatusCoordinator (orchestrator)
├── StatusAggregationCoordinator (aggregation/)
├── StatusBroadcastCoordinator (broadcast/)
├── SystemStatusCoordinator
│   ├── SchedulerStatusCoordinator
│   └── InfrastructureStatusCoordinator
├── AIStatusCoordinator, AgentStatusCoordinator
└── PortfolioStatusCoordinator
```

## Status Structure
```python
{
    "status": "healthy" | "degraded" | "unhealthy",
    "components": {"name": {"status": "...", "details": {...}, "last_updated": "ISO"}},
    "timestamp": "ISO"
}
```

## Pattern
```python
scheduler = await scheduler_coordinator.get_status()
infra = await infra_coordinator.get_status()
await broadcast_coordinator.broadcast_on_change(status)
```

## Rules
| DO | DON'T |
|----|-------|
| Delegate aggregation | Business logic in orchestrator |
| Broadcast on changes only | Broadcast every call |
| Structured status dict | Unstructured data |
| Use BroadcastCoordinator | Direct service access |
| Track last state | Exceed 200/150 lines |
| Change detection | Return raw data |

## Dependencies
BroadcastCoordinator, BackgroundScheduler, DatabaseStateManager, SessionCoordinator, domain services

