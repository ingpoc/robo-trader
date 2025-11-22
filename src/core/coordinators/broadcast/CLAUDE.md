# Broadcast Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/broadcast/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Overview

Broadcast coordinators manage real-time UI updates via WebSocket. The architecture follows an orchestrator pattern where `BroadcastCoordinator` delegates to focused broadcast coordinators.

## Architecture Pattern

### Orchestrator + Focused Coordinators

- **`BroadcastCoordinator`**: Main orchestrator (max 200 lines)
  - Delegates to focused broadcast coordinators
  - Provides unified broadcast API
  - Manages broadcast lifecycle

- **Focused Coordinators** (max 150 lines each):
  - `BroadcastExecutionCoordinator` - Broadcast execution and health monitor integration
  - `BroadcastHealthCoordinator` - Circuit breaker, health metrics, error handling

## Broadcast Architecture

### Health Monitoring

- Uses `BroadcastHealthMonitor` when available (from `src/core/web/broadcast_health_monitor.py`)
- Falls back to basic broadcasting with circuit breaker pattern
- Tracks broadcast metrics (success rate, average time, failures)

### Circuit Breaker Pattern

- Opens after 5 consecutive failures
- Closes after 3 consecutive successes
- 60-second recovery timeout

## Rules

### ✅ DO

- ✅ Inherit from `BaseCoordinator`
- ✅ Use `BroadcastHealthMonitor` when available
- ✅ Implement circuit breaker pattern
- ✅ Track broadcast metrics
- ✅ Handle broadcast failures gracefully
- ✅ Emit structured broadcast messages
- ✅ Keep orchestrators under 200 lines
- ✅ Keep focused coordinators under 150 lines

### ❌ DON'T

- ❌ Block on broadcast operations
- ❌ Broadcast on every call (use change detection)
- ❌ Ignore broadcast failures
- ❌ Exceed line limits

## Implementation Pattern

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.coordinators.broadcast.broadcast_execution_coordinator import BroadcastExecutionCoordinator
from src.core.coordinators.broadcast.broadcast_health_coordinator import BroadcastHealthCoordinator

class BroadcastCoordinator(BaseCoordinator):
    """Orchestrates broadcast operations."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.health_coordinator = BroadcastHealthCoordinator(config)
        self.execution_coordinator = BroadcastExecutionCoordinator(config, self.health_coordinator)
    
    async def broadcast_to_ui(self, message: Dict[str, Any]) -> bool:
        """Broadcast message to all connected WebSocket clients."""
        result = await self.execution_coordinator.broadcast_to_ui(
            message,
            self.health_coordinator.is_circuit_breaker_open
        )
        # Record metrics
        if result:
            self.health_coordinator.record_broadcast_success(message.get('_broadcast_time', 0.0))
        else:
            self.health_coordinator.record_broadcast_failure(Exception("Broadcast failed"))
        return result
```

## Broadcast Message Types

- `claude_status_update` - Claude SDK status
- `system_health_update` - System health information
- `queue_status_update` - Queue status information
- Custom types - Domain-specific updates

## Broadcast Message Structure

```python
{
    "type": "message_type",
    "data": {...},
    "timestamp": "ISO timestamp"
}
```

## Circuit Breaker States

1. **Closed**: Normal operation, broadcasts allowed
2. **Open**: Failures detected, broadcasts blocked
3. **Half-Open**: Recovery attempt after timeout

## Health Metrics

- `total_broadcasts` - Total broadcast attempts
- `successful_broadcasts` - Successful broadcasts
- `failed_broadcasts` - Failed broadcasts
- `circuit_breaker_trips` - Number of circuit breaker trips
- `average_broadcast_time` - Average broadcast time in seconds
- `success_rate` - Percentage of successful broadcasts

## Dependencies

Broadcast coordinators typically depend on:
- `BroadcastHealthMonitor` - For advanced health monitoring (optional)
- WebSocket connection manager - For actual message sending (injected via callback)

