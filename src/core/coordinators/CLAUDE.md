# Coordinators Directory Guidelines

> **Scope**: Applies to `src/core/coordinators/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-09 | **Status**: Active | **Tier**: Reference

## Purpose

The `coordinators/` directory contains all coordinator classes that orchestrate system operations using the **coordinator-based monolithic architecture**. Coordinators are organized into domain-specific subdirectories for clear separation of concerns.

## Architecture Pattern

### Coordinator-Based Monolithic Architecture

Coordinators orchestrate operations by delegating to focused sub-coordinators and services. This pattern provides:
- **Better performance** than microservices (no network overhead)
- **Clear separation of concerns** (domain-specific folders)
- **Maintainability** (focused, single-responsibility coordinators)

### Directory Structure

```
coordinators/
├── base_coordinator.py          # Base class for all coordinators
├── core/                        # Core system coordinators
│   ├── session_coordinator.py   # Claude SDK session lifecycle
│   ├── query_coordinator.py    # Query/request processing
│   ├── lifecycle_coordinator.py # Emergency operations
│   └── portfolio_coordinator.py # Portfolio operations
├── status/                      # Status aggregation coordinators
│   ├── status_coordinator.py    # Main orchestrator
│   ├── broadcast/               # Broadcasting coordinators
│   └── aggregation/             # Aggregation coordinators
├── queue/                       # Queue management coordinators
├── task/                        # Task management coordinators
├── message/                     # Message routing coordinators
├── broadcast/                   # Broadcast coordinators
└── agent/                       # Agent coordination coordinators
    └── session/                 # Session management coordinators
```

## Organization Principles

### 1. Domain Separation
Each subdirectory represents a specific domain:
- **core/**: Fundamental system coordinators
- **status/**: Status aggregation and reporting
- **queue/**: Queue management and execution
- **task/**: Task lifecycle and execution
- **message/**: Inter-agent communication
- **broadcast/**: UI broadcasting and health monitoring
- **agent/**: Agent coordination and management

### 2. Focused Subfolders
When coordinators are split into focused components, they go into focused subfolders:
- `status/broadcast/` → Broadcasting coordinators
- `status/aggregation/` → Aggregation coordinators
- `agent/session/` → Session management coordinators

### 3. Orchestrator Pattern
Each domain has:
- A main orchestrator coordinator (e.g., `status_coordinator.py`)
- Focused sub-coordinators (e.g., `status/broadcast/status_broadcast_coordinator.py`)
- The orchestrator delegates to focused coordinators

## Rules

### ✅ DO

- ✅ **Inherit from `BaseCoordinator`** - All coordinators must inherit from `BaseCoordinator`
- ✅ **Organize by domain** - Place coordinators in domain-specific subdirectories
- ✅ **Use focused subfolders** - Split focused coordinators into focused subfolders
- ✅ **Keep orchestrators < 150 lines** - Main orchestrator coordinators should be thin
- ✅ **Keep focused coordinators < 150 lines** - Each focused coordinator should be small
- ✅ **Use dependency injection** - Inject dependencies via constructor
- ✅ **Emit events** - Use `EventBus` for cross-cutting concerns
- ✅ **Follow naming convention** - `{Domain}Coordinator` for orchestrators, `{Domain}{Focus}Coordinator` for focused coordinators
- ✅ **Document in CLAUDE.md** - Each subdirectory must have its own CLAUDE.md

### ❌ DON'T

- ❌ **Place coordinators in root** - Always use domain subdirectories
- ❌ **Mix domains** - Don't put status coordinators in queue folder
- ❌ **Create god coordinators** - Split large coordinators into focused ones
- ❌ **Access services directly** - Use dependency injection
- ❌ **Exceed line limits** - Refactor if coordinator exceeds 150 lines
- ❌ **Create orphaned files** - All coordinators must have a clear purpose and location

## BaseCoordinator Implementation Pattern

**Rule**: All coordinators MUST inherit from `BaseCoordinator` and follow the established lifecycle pattern.

### Implementation Template
```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventHandler, Event, EventType
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class MyCoordinator(BaseCoordinator, EventHandler):
    """Example coordinator following the established pattern."""

    def __init__(self, container: 'DependencyContainer', event_bus: 'EventBus'):
        super().__init__(container, event_bus)
        self.container = container
        self.event_bus = event_bus
        self._initialized = False
        self.service = None  # Will be injected in initialize()

    async def initialize(self) -> None:
        """Initialize coordinator dependencies and subscriptions."""
        if self._initialized:
            return

        self._log_info("Initializing MyCoordinator")

        # Get dependencies from container
        self.service = await self.container.get("my_service")

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.MY_EVENT, self)

        self._initialized = True
        self._log_info("MyCoordinator initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup resources and event subscriptions."""
        if not self._initialized:
            return

        self._log_info("Cleaning up MyCoordinator")

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.MY_EVENT, self)

        self._initialized = False
        self._log_info("MyCoordinator cleanup complete")

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events based on type."""
        try:
            if event.type == EventType.MY_EVENT:
                await self._handle_my_event(event)
        except Exception as e:
            self._log_error(f"Failed to handle {event.type.value}: {e}")

    async def _handle_my_event(self, event: Event) -> None:
        """Handle specific event type."""
        # Event handling logic here
        data = event.get("data", {})
        self._log_info(f"Processing my_event: {data}")

        # Use injected service
        result = await self.service.process(data)

        # Emit completion event if needed
        await self.event_bus.publish(Event(
            id=str(uuid.uuid4()),
            type=EventType.MY_EVENT_COMPLETED,
            source="MyCoordinator",
            timestamp=datetime.utcnow(),
            data={"result": result}
        ))
```

### Key Requirements
- ✅ **Inherit from BaseCoordinator**: Provides logging and lifecycle management
- ✅ **Implement EventHandler**: For event-driven communication
- ✅ **Initialize() method**: Get dependencies and subscribe to events
- ✅ **Cleanup() method**: Unsubscribe from events and cleanup resources
- ✅ **Logging**: Use `_log_info()`, `_log_warning()`, `_log_error()` for structured logging
- ✅ **Event Handling**: Handle specific events in dedicated private methods
- ✅ **Dependency Injection**: Use `container.get()` for all dependencies
- ✅ **Error Handling**: Wrap event handling in try/catch with proper logging

### Common Pitfalls to Avoid
- ❌ **Direct Service Calls**: Never call other coordinators directly, use events
- ❌ **Missing Cleanup**: Always implement cleanup() to prevent memory leaks
- ❌ **Blocking Operations**: All coordinator methods must be async
- ❌ **Global State**: Don't use global variables, use container-injected dependencies
- ❌ **Large Files**: Keep coordinators under 150 lines, split if needed

## File Organization

### New Coordinator Creation

1. **Identify domain** - Determine which domain subdirectory it belongs to
2. **Check if focused subfolder needed** - If coordinator is focused (not orchestrator), create subfolder
3. **Create coordinator** - Place in appropriate domain folder or focused subfolder
4. **Update CLAUDE.md** - Document coordinator in directory's CLAUDE.md
5. **Register in DI** - Add to `di_registry_coordinators.py`
6. **Update __init__.py** - Add to `src/core/coordinators/__init__.py`

### Refactoring Pattern

When a coordinator exceeds 150 lines:

1. **Identify responsibilities** - What distinct responsibilities does it have?
2. **Create focused subfolder** - Create subfolder under domain directory (e.g., `status/broadcast/`)
3. **Extract focused coordinators** - Split into focused coordinators in subfolder
4. **Refactor orchestrator** - Make main coordinator a thin orchestrator
5. **Update imports** - Fix all imports to new locations
6. **Update CLAUDE.md** - Document new structure in both parent and subfolder CLAUDE.md files

## Example: Status Coordinator Refactoring

**Before**: `status_coordinator.py` (261 lines)

**After**:
```
status/
├── status_coordinator.py (143 lines ✅ - orchestrator)
├── broadcast/
│   └── status_broadcast_coordinator.py (126 lines ✅)
└── aggregation/
    └── status_aggregation_coordinator.py (108 lines ✅)
```

## Dependencies

Coordinators typically depend on:
- `BaseCoordinator` - Base class
- `EventBus` - Event-driven communication
- `Config` - Configuration
- Domain-specific services (injected via DI)
- Other coordinators (injected via DI)

## Testing

- Test orchestrator delegates correctly to focused coordinators
- Test each focused coordinator independently
- Test event emission and handling
- Test error handling and recovery

## Maintenance

- **When adding new coordinator**: Follow domain organization, create focused subfolder if needed
- **When coordinator grows**: Split into focused coordinators in focused subfolder
- **When patterns change**: Update relevant CLAUDE.md files
- **When folder structure changes**: Update this CLAUDE.md and all affected subfolder CLAUDE.md files

