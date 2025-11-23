# Core Coordinators - src/core/coordinators/core/

Session, query, lifecycle, portfolio. Max 200 lines each.

| Coordinator | Purpose |
|-------------|---------|
| SessionCoordinator | SDK auth, start/stop sessions |
| QueryCoordinator | Process queries, handle responses |
| LifecycleCoordinator | Scheduler start/stop, emergency ops |
| PortfolioCoordinator | Portfolio scan, analysis, trading |

## Pattern
```python
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)
await query_with_timeout(client, query, timeout=30.0)
async for response in receive_response_with_timeout(client, timeout=60.0):
    # Process response
```

## Rules
| DO | DON'T |
|----|-------|
| Use ClaudeSDKClientManager | Create clients directly |
| Use timeout helpers | Call SDK unprotected |
| Handle auth failures gracefully | Raise on auth errors |
| Emit lifecycle events | Block on I/O |
| Delegate to services | Exceed 200 lines |
| Graceful shutdown | Direct service access |

## Events
session_started, session_ended, query_processed, portfolio_updated, lifecycle_changed

## Dependencies
ClaudeSDKClientManager, BroadcastCoordinator, BackgroundScheduler, DatabaseStateManager, EventBus

