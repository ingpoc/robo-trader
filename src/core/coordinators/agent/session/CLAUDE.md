# Agent Session Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/agent/session/` directory. Read `src/core/coordinators/agent/CLAUDE.md` for parent context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Purpose

The `agent/session/` directory contains focused coordinators responsible for **Claude agent session lifecycle management**. These coordinators handle morning prep sessions, evening review sessions, and session state management.

## Architecture Pattern

### Focused Coordinator Pattern

This directory contains focused coordinators extracted from `AgentSessionCoordinator` for single responsibility:

- **`AgentSessionCoordinator`**: Main orchestrator (max 150 lines)
  - Orchestrates session operations from focused coordinators
  - Provides unified session API
  
- **`MorningSessionCoordinator`**: Focused coordinator (max 150 lines)
  - Runs morning preparation sessions
  - Handles morning session state
  - Processes morning tool calls

- **`EveningSessionCoordinator`**: Focused coordinator (max 150 lines)
  - Runs evening review sessions
  - Handles evening session state
  - Processes evening tool calls

## File Structure

```
agent/session/
├── __init__.py                    # Package exports
├── agent_session_coordinator.py  # Main orchestrator (max 150 lines)
├── morning_session_coordinator.py # Morning sessions (max 150 lines)
└── evening_session_coordinator.py # Evening sessions (max 150 lines)
```

## Rules

### ✅ DO

- ✅ **Inherit from `BaseCoordinator`** - All coordinators must inherit from base
- ✅ **Keep focused** - Each coordinator should have single responsibility
- ✅ **Max 150 lines** - Keep files small and maintainable
- ✅ **Use timeout helpers** - Always use `query_with_timeout`, `receive_response_with_timeout`
- ✅ **Validate session results** - Use `ResponseValidator` to validate sessions
- ✅ **Store sessions** - Save sessions via `ClaudeStrategyStore`
- ✅ **Emit events** - Publish session completion events
- ✅ **Handle errors gracefully** - Wrap in `TradingError` with proper categories

### ❌ DON'T

- ❌ **Mix session types** - Don't handle morning and evening in same coordinator
- ❌ **Access services directly** - Use dependency injection
- ❌ **Skip timeout protection** - Always use timeout helpers
- ❌ **Exceed line limits** - Refactor if exceeds 150 lines

## Implementation Pattern

```python
from ....base_coordinator import BaseCoordinator
from ...sdk_helpers import query_with_timeout, receive_response_with_timeout

class MorningSessionCoordinator(BaseCoordinator):
    """
    Coordinates morning preparation sessions.
    
    Responsibilities:
    - Run morning prep sessions
    - Handle morning session state
    - Process morning tool calls
    """
    
    async def run_morning_prep_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """Execute morning preparation session using Claude SDK."""
        if not self.client or not self.tool_executor:
            raise TradingError(...)
        
        # Use timeout helpers (MANDATORY)
        await query_with_timeout(self.client, prompt, timeout=90.0)
        
        async for response in receive_response_with_timeout(self.client, timeout=180.0):
            # Process response
            pass
        
        # Validate and store
        await self.validator.validate_session_result(result)
        await self.strategy_store.save_session(result)
        
        return result
```

## Session Types

- **Morning Prep**: `SessionType.MORNING_PREP` - Preparation sessions for trading day
- **Evening Review**: `SessionType.EVENING_REVIEW` - Review sessions for learning and reflection

## Dependencies

- `BaseCoordinator` - Base class (from `....base_coordinator`)
- `ClaudeSDKClient` - Claude SDK client (injected)
- `ToolExecutor` - For executing tools (injected)
- `ResponseValidator` - For validating session results (injected)
- `ClaudeStrategyStore` - For storing sessions (injected)
- `EventBus` - For emitting events (injected)
- `AgentPromptBuilder` - For building prompts (injected)

## Testing

- Test morning session execution
- Test evening session execution
- Test timeout protection works correctly
- Test session validation and storage
- Test error handling and recovery

## Maintenance

- **When patterns change**: Update `src/core/coordinators/agent/CLAUDE.md` and this file
- **When coordinator grows**: Split further or extract common logic to utilities
- **When new session types needed**: Create new focused coordinator or add to existing one

