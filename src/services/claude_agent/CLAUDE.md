# Claude Agent Services - src/services/claude_agent/

**Context**: Services supporting Agent SDK bot's Claude interactions.
Claude Code debugs issues and verifies correct SDK usage.
Claude Code does NOT implement or modify agent decision-making logic.

## Services
| Module | Purpose | Max Size |
|--------|---------|----------|
| tool_executor.py | MCP tool execution | 350 lines |
| response_validator.py | Response parsing & validation | 350 lines |
| analysis_logger.py | Transparency logging | 350 lines |
| research_tracker.py | Research activity tracking | 350 lines |
| execution_monitor.py | Trade execution monitoring | 350 lines |

## SDK Pattern (MANDATORY)
```python
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

# Lazy client initialization
client_mgr = await ClaudeSDKClientManager.get_instance()
self.client = await client_mgr.get_client("trading", options)

# Always use timeout helpers
await query_with_timeout(self.client, prompt, timeout=60.0)
async for resp in receive_response_with_timeout(self.client, timeout=120.0):
    # Process response
```

## Rules
| Rule | Requirement |
|------|-------------|
| SDK only | NO direct Anthropic imports |
| Client mgr | Always use ClaudeSDKClientManager |
| Timeout | MUST use query_with_timeout + receive_response_with_timeout |
| Lines | <350 per file, refactor if over |
| Events | Emit via EventBus for comms |
| Errors | Wrap in TradingError with context |

