# Status Broadcast Coordinator - status/broadcast/

Focused coordinator. Status broadcasting and change detection.

## Responsibilities
Track broadcast state changes, compute state hashes, broadcast health updates, track metrics.

## Pattern
```python
def has_state_changed(self, components: Dict) -> bool:
    current_hash = self.compute_state_hash(components)
    return current_hash != self._last_broadcast_state.get("hash")

await self.broadcast_coordinator.broadcast_to_ui(status)
self.track_broadcast_metrics(success, duration)
```

## Rules
| DO | DON'T |
|----|-------|
| Inherit BaseCoordinator | Mix concerns (no aggregation) |
| Single responsibility | Access services directly |
| Hash comparison | Broadcast every call |
| Track metrics | Exceed 150 lines |
| Error handling | Direct injection |

## Dependencies
BaseCoordinator, BroadcastCoordinator, Config

