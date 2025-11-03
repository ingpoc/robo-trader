# Status Aggregation Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/status/aggregation/` directory. Read `src/core/coordinators/status/CLAUDE.md` for parent context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `status/aggregation/` directory contains focused coordinators responsible for **aggregating system components** from various status coordinators. These coordinators collect and combine status information from multiple sources.

## Architecture Pattern

### Focused Coordinator Pattern

This directory contains focused coordinators extracted from `StatusCoordinator` for single responsibility:

- **`StatusAggregationCoordinator`**: Handles system component aggregation
  - Aggregates status from focused status coordinators
  - Transforms status formats for consistency
  - Handles queue status delegation
  - Combines components into unified structure

## File Structure

```
status/aggregation/
├── __init__.py                        # Package exports
└── status_aggregation_coordinator.py  # Aggregation coordinator (max 150 lines)
```

## Rules

### ✅ DO

- ✅ **Inherit from `BaseCoordinator`** - All coordinators must inherit from base
- ✅ **Keep focused** - Each coordinator should have single responsibility
- ✅ **Max 150 lines** - Keep files small and maintainable
- ✅ **Aggregate in parallel** - Use `asyncio.gather()` for performance
- ✅ **Handle errors gracefully** - Don't fail if one component fails
- ✅ **Transform consistently** - Use consistent status format
- ✅ **Delegate appropriately** - Delegate to queue coordinator for queue status

### ❌ DON'T

- ❌ **Mix concerns** - Don't add broadcasting logic here
- ❌ **Access services directly** - Use dependency injection
- ❌ **Block on aggregation** - Use async patterns for parallel aggregation
- ❌ **Exceed line limits** - Refactor if exceeds 150 lines

## Implementation Pattern

```python
from ....base_coordinator import BaseCoordinator

class StatusAggregationCoordinator(BaseCoordinator):
    """
    Coordinates status aggregation from focused coordinators.
    
    Responsibilities:
    - Aggregate system components
    - Get queue status
    - Transform status formats
    """
    
    def __init__(self, config, system_status_coordinator, ai_status_coordinator, portfolio_status_coordinator):
        super().__init__(config)
        self.system_status_coordinator = system_status_coordinator
        self.ai_status_coordinator = ai_status_coordinator
        self.portfolio_status_coordinator = portfolio_status_coordinator
        self.container = None
    
    async def aggregate_system_components(
        self,
        scheduler_status: Dict[str, Any],
        claude_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate system components from focused coordinators."""
        # Use asyncio.gather() for parallel aggregation
        scheduler, database, websocket, resources, claude_agent, queue = await asyncio.gather(
            self.system_status_coordinator.get_scheduler_status(),
            self.system_status_coordinator.get_database_status(),
            # ... more components
            return_exceptions=True
        )
        
        return {
            "scheduler": scheduler if not isinstance(scheduler, Exception) else {"status": "error"},
            # ... more components
        }
```

## Dependencies

- `BaseCoordinator` - Base class (from `....base_coordinator`)
- `SystemStatusCoordinator` - For system component status
- `AIStatusCoordinator` - For AI component status
- `PortfolioStatusCoordinator` - For portfolio component status
- `DependencyContainer` - For accessing queue coordinator (optional)

## Testing

- Test aggregation collects all components correctly
- Test parallel aggregation improves performance
- Test error handling when components fail
- Test status format transformation

## Maintenance

- **When patterns change**: Update `src/core/coordinators/status/CLAUDE.md` and this file
- **When coordinator grows**: Split further or move logic to shared utilities
- **When new components needed**: Add to aggregation logic

