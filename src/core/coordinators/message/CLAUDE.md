# Message Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/message/` directory. Read `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Overview

Message coordinators handle inter-agent communication and message routing in the multi-agent framework. The architecture follows an orchestrator pattern where `MessageCoordinator` delegates to focused message coordinators.

## Architecture Pattern

### Orchestrator + Focused Coordinators

- **`MessageCoordinator`**: Main orchestrator (max 200 lines)
  - Delegates to focused message coordinators
  - Provides unified message management API
  - Tracks message statistics

- **Focused Coordinators** (max 150 lines each):
  - `MessageRoutingCoordinator` - Message queuing, routing, and request-response pattern
  - `MessageHandlingCoordinator` - Message type handlers and default handlers

- **Model Files**:
  - `agent_message.py` - `AgentMessage`, `MessageType` enum

## Message Types

- `ANALYSIS_RESPONSE` - Analysis results from agents
- `DECISION_PROPOSAL` - Decision proposals from agents
- `VOTE` - Votes on decisions
- `ERROR_REPORT` - Error reports from agents
- `STATUS_UPDATE` - Status updates from agents
- `TASK_ASSIGNMENT` - Task assignment messages

## Rules

### ✅ DO

- ✅ Inherit from `BaseCoordinator`
- ✅ Use `AgentMessage` model for messages
- ✅ Use `MessageType` enum for message types
- ✅ Implement message queuing and async processing
- ✅ Register handlers for message types
- ✅ Emit message events for monitoring
- ✅ Handle request-response pattern with timeouts
- ✅ Keep orchestrators under 200 lines
- ✅ Keep focused coordinators under 150 lines

### ❌ DON'T

- ❌ Block on message operations
- ❌ Process messages synchronously
- ❌ Forget to cleanup message handlers
- ❌ Exceed line limits

## Implementation Pattern

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.coordinators.message.message_routing_coordinator import MessageRoutingCoordinator
from src.core.coordinators.message.message_handling_coordinator import MessageHandlingCoordinator
from src.core.coordinators.message.agent_message import AgentMessage, MessageType

class MessageCoordinator(BaseCoordinator):
    """Orchestrates message operations."""
    
    def __init__(self, config: Any, state_manager: DatabaseStateManager, event_bus: EventBus):
        super().__init__(config, "message_coordinator")
        self.routing_coordinator = MessageRoutingCoordinator(config, event_bus)
        self.handling_coordinator = MessageHandlingCoordinator(config, event_bus)
    
    async def send_message(self, message: AgentMessage) -> None:
        """Send a message for routing."""
        # Update statistics
        self.message_counts[message.message_type.value] += 1
        await self.routing_coordinator.send_message(message)
```

## Message Processing Flow

1. **Send**: `MessageCoordinator.send_message()` - Adds to queue, updates statistics
2. **Routing**: `MessageRoutingCoordinator._route_message()` - Routes to handlers or pending responses
3. **Handling**: `MessageHandlingCoordinator._handle_*()` - Processes message, emits events

## Request-Response Pattern

```python
# Send request and wait for response
response = await message_coordinator.send_request_response(
    request=AgentMessage(...),
    timeout=30.0
)
```

## Handler Registration

```python
# Register custom handler
await message_coordinator.register_handler(
    MessageType.ANALYSIS_RESPONSE,
    async def handle_response(message: AgentMessage):
        # Process message
        pass
)
```

## Default Handlers

- `ANALYSIS_RESPONSE` → `_handle_analysis_response()`
- `DECISION_PROPOSAL` → `_handle_decision_proposal()`
- `VOTE` → `_handle_vote()`
- `ERROR_REPORT` → `_handle_error_report()`
- `STATUS_UPDATE` → `_handle_status_update()`

## Event Types

- `message_sent` - Message sent for routing
- `analysis_response_received` - Analysis response received
- `decision_proposal_received` - Decision proposal received
- `vote_received` - Vote received
- `agent_error_reported` - Agent error reported
- `agent_status_update` - Agent status updated

## Dependencies

Message coordinators typically depend on:
- `EventBus` - For event emission
- `DatabaseStateManager` - For message persistence (optional)
- `TaskCoordinator` - For task result storage

