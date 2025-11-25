# Message Coordinator - src/core/coordinators/message/

Inter-agent communication, message routing. Orchestrator + focused coordinators.

## Pattern
- `MessageCoordinator` (orchestrator, max 200)
- `MessageRoutingCoordinator` (routing, max 150)
- `MessageHandlingCoordinator` (handlers, max 150)

## Message Types
| Type | Purpose |
|------|---------|
| ANALYSIS_RESPONSE | Agent analysis results |
| DECISION_PROPOSAL | Agent decision proposals |
| VOTE | Votes on decisions |
| ERROR_REPORT | Agent errors |
| STATUS_UPDATE | Status updates |
| TASK_ASSIGNMENT | Task assignments |

## Implementation
```python
await message_coordinator.send_message(message)
response = await message_coordinator.send_request_response(request, timeout=30.0)
await message_coordinator.register_handler(MessageType.ANALYSIS_RESPONSE, handler)
```

## Rules
| DO | DON'T |
|----|-------|
| Use AgentMessage model | Block on I/O |
| Use MessageType enum | Sync processing |
| Register handlers | Forget cleanup |
| Emit message events | Exceed 200/150 lines |
| Queue messages | Direct access |
| Timeout on req-resp | Unhandled messages |

## Events
message_sent, analysis_response_received, decision_proposal_received, vote_received, agent_error_reported, agent_status_update

## Dependencies
EventBus, DatabaseStateManager (optional), TaskCoordinator

