# Broadcast Coordinator - src/core/coordinators/broadcast/

Real-time UI updates via WebSocket. Orchestrator + focused coordinators.

## Pattern
- `BroadcastCoordinator` (orchestrator, max 200)
- `BroadcastExecutionCoordinator` (execution, max 150)
- `BroadcastHealthCoordinator` (health, max 150)

## Circuit Breaker
Opens: 5 consecutive failures | Closes: 3 consecutive successes | Recovery: 60-second timeout

## Implementation
```python
result = await broadcast_coordinator.broadcast_to_ui(message)
if result:
    health_coordinator.record_broadcast_success(...)
else:
    health_coordinator.record_broadcast_failure(...)
```

## Message Types
| Type | Purpose |
|------|---------|
| claude_status_update | Claude SDK status |
| system_health_update | System health |
| queue_status_update | Queue status |
| custom_types | Domain-specific |

## Rules
| DO | DON'T |
|----|-------|
| Inherit BaseCoordinator | Block on broadcast |
| Circuit breaker pattern | Ignore failures |
| Track metrics | Exceed 200/150 lines |
| Change detection | Direct WS access |
| Use BroadcastHealthMonitor | Broadcast every call |

## Dependencies
BroadcastHealthMonitor (optional), WebSocket connection manager

