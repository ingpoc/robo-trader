# Status Broadcast Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/status/broadcast/` directory. Read `src/core/coordinators/status/CLAUDE.md` for parent context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `status/broadcast/` directory contains focused coordinators responsible for **status broadcasting and change detection**. These coordinators handle broadcasting system health updates to the UI and tracking state changes.

## Architecture Pattern

### Focused Coordinator Pattern

This directory contains focused coordinators extracted from `StatusCoordinator` for single responsibility:

- **`StatusBroadcastCoordinator`**: Handles broadcasting and change tracking
  - Tracks broadcast state changes
  - Computes state hashes for change detection
  - Broadcasts system health updates
  - Tracks broadcast metrics

## File Structure

```
status/broadcast/
├── __init__.py                    # Package exports
└── status_broadcast_coordinator.py # Broadcast coordinator (max 150 lines)
```

## Rules

### ✅ DO

- ✅ **Inherit from `BaseCoordinator`** - All coordinators must inherit from base
- ✅ **Keep focused** - Each coordinator should have single responsibility
- ✅ **Max 150 lines** - Keep files small and maintainable
- ✅ **Track state changes** - Use hash comparison to detect changes
- ✅ **Broadcast efficiently** - Only broadcast when state actually changes
- ✅ **Track metrics** - Monitor broadcast success/failure rates
- ✅ **Handle errors gracefully** - Don't fail on broadcast errors

### ❌ DON'T

- ❌ **Mix concerns** - Don't add aggregation logic here
- ❌ **Access services directly** - Use dependency injection
- ❌ **Broadcast on every call** - Only broadcast on state changes
- ❌ **Exceed line limits** - Refactor if exceeds 150 lines

## Implementation Pattern

```python
from ....base_coordinator import BaseCoordinator

class StatusBroadcastCoordinator(BaseCoordinator):
    """
    Coordinates status broadcasting and change detection.
    
    Responsibilities:
    - Track broadcast state changes
    - Handle status broadcasting
    - Compute state hashes for change detection
    """
    
    def __init__(self, config, broadcast_coordinator=None):
        super().__init__(config)
        self._broadcast_coordinator = broadcast_coordinator
        self._last_broadcast_state = {}
        self._broadcast_metrics = {
            "total_broadcasts": 0,
            "successful_broadcasts": 0,
            "failed_broadcasts": 0,
            "state_changes": 0
        }
    
    def has_state_changed(self, components: Dict[str, Any]) -> bool:
        """Check if state has changed since last broadcast."""
        current_hash = self.compute_state_hash(components)
        return current_hash != self._last_broadcast_state.get("hash")
    
    def compute_state_hash(self, components: Dict[str, Any]) -> str:
        """Compute hash of component states for change detection."""
        # Implementation here
        pass
```

## Dependencies

- `BaseCoordinator` - Base class (from `....base_coordinator`)
- `BroadcastCoordinator` - For actual broadcasting (injected)
- `Config` - Configuration

## Testing

- Test state change detection works correctly
- Test broadcasting only happens on state changes
- Test broadcast metrics tracking
- Test error handling on broadcast failures

## Maintenance

- **When patterns change**: Update `src/core/coordinators/status/CLAUDE.md` and this file
- **When coordinator grows**: Split further or move logic to shared utilities
- **When new broadcast types needed**: Add to this coordinator or create new focused coordinator

