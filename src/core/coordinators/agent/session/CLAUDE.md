# Agent Session Coordinator - agent/session/

Morning prep and evening review sessions. Focused coordinators (max 150 each).

## Structure
- `AgentSessionCoordinator` (orchestrator)
- `MorningSessionCoordinator` (morning prep)
- `EveningSessionCoordinator` (evening review)

## Session Types
Morning Prep: SessionType.MORNING_PREP | Evening Review: SessionType.EVENING_REVIEW

## Pattern
```python
# MANDATORY: Use timeout helpers
await query_with_timeout(self.client, prompt, timeout=90.0)
async for response in receive_response_with_timeout(self.client, timeout=180.0):
    # Process response
    pass
await self.validator.validate_session_result(result)
await self.strategy_store.save_session(result)
```

## Rules
| DO | DON'T |
|----|-------|
| Inherit BaseCoordinator | Mix session types |
| Timeout helpers (MANDATORY) | Direct service access |
| Validate results | Skip timeout protection |
| Store via ClaudeStrategyStore | Exceed 150 lines |
| Emit lifecycle events | Raise on errors (TradingError) |
| Single responsibility | Block on I/O |

## Dependencies
BaseCoordinator, ClaudeSDKClient, ToolExecutor, ResponseValidator, ClaudeStrategyStore, EventBus, AgentPromptBuilder

