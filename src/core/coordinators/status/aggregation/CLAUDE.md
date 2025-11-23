# Status Aggregation Coordinator - status/aggregation/

Focused coordinator. Aggregates system components from status coordinators.

## Responsibilities
Aggregate status from focused coordinators, transform formats, handle queue delegation, combine into unified structure.

## Pattern
```python
scheduler, database, websocket = await asyncio.gather(
    self.system_coord.get_scheduler_status(),
    self.system_coord.get_database_status(),
    return_exceptions=True
)
return {
    "scheduler": scheduler if not isinstance(scheduler, Exception) else {"status": "error"}
}
```

## Rules
| DO | DON'T |
|----|-------|
| Inherit BaseCoordinator | Mix concerns (no broadcast) |
| asyncio.gather() | Direct service access |
| Handle errors gracefully | Block on aggregation |
| Consistent format | Exceed 150 lines |
| Delegate queue ops | Return raw data |

## Dependencies
BaseCoordinator, SystemStatusCoordinator, AIStatusCoordinator, PortfolioStatusCoordinator, Container (optional)

