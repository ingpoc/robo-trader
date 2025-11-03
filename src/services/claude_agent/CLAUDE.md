# Claude Agent Services Guidelines

> **Scope**: Applies to `src/services/claude_agent/` directory. Read `src/services/CLAUDE.md` for parent context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `claude_agent/` directory contains **Claude Agent SDK integration services** that provide transparency, logging, monitoring, and tool execution for Claude-powered trading operations.

## Architecture Pattern

### Service Layer Pattern

The Claude agent services use a **service layer architecture** with focused services:

- **Core Services**:
  - `tool_executor.py` - MCP tool execution
  - `response_validator.py` - Response validation and parsing
  - `analysis_logger.py` - Analysis logging for transparency
  - `research_tracker.py` - Research activity tracking
  - `execution_monitor.py` - Trade execution monitoring
  - `daily_strategy_evaluator.py` - Daily strategy evaluation
  - `activity_summarizer.py` - Activity summarization

- **Supporting Modules**:
  - `mcp_server.py` - MCP server setup
  - `prompt_templates.py` - Prompt templates
  - `prompt_optimization_tools.py` - Prompt optimization tools
  - `context_builder.py` - Context building
  - `trade_decision_logger.py` - Trade decision logging
  - `sdk_auth.py` - SDK authentication

## File Structure

```
claude_agent/
├── __init__.py
├── tool_executor.py           # Tool execution (max 350 lines)
├── response_validator.py       # Response validation (max 350 lines)
├── analysis_logger.py          # Analysis logging (max 350 lines)
├── research_tracker.py          # Research tracking (max 350 lines)
├── execution_monitor.py        # Execution monitoring (max 350 lines)
├── daily_strategy_evaluator.py # Strategy evaluation (max 350 lines)
├── activity_summarizer.py       # Activity summarization (max 350 lines)
└── ... (supporting modules)
```

## Rules

### ✅ DO

- ✅ **Use Claude SDK only** - NO direct Anthropic API calls
- ✅ **Use `ClaudeSDKClientManager`** - Always use client manager
- ✅ **Use timeout helpers** - Always use `query_with_timeout`, `receive_response_with_timeout`
- ✅ **Keep services < 350 lines** - Refactor if exceeds limit
- ✅ **Use dependency injection** - Inject dependencies via constructor
- ✅ **Emit events** - Use `EventBus` for cross-cutting concerns
- ✅ **Handle errors gracefully** - Wrap in `TradingError` with proper categories
- ✅ **Log to transparency** - Use `analysis_logger.py` for analysis logging

### ❌ DON'T

- ❌ **Direct API calls** - NEVER use Anthropic API directly
- ❌ **Direct client creation** - Always use `ClaudeSDKClientManager`
- ❌ **Skip timeout protection** - Always use timeout helpers
- ❌ **Exceed line limits** - Refactor if service exceeds 350 lines
- ❌ **Mix concerns** - Keep services focused

## SDK Integration Pattern

```python
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

class ClaudeAgentService:
    """Service for Claude agent operations."""
    
    async def _ensure_client(self):
        """Lazy initialization using client manager."""
        if not self.client:
            client_manager = await ClaudeSDKClientManager.get_instance()
            options = ClaudeAgentOptions(...)
            self.client = await client_manager.get_client("trading", options)
    
    async def perform_operation(self, prompt: str) -> Dict[str, Any]:
        """Perform operation with timeout protection."""
        await self._ensure_client()
        
        # Use timeout helpers (MANDATORY)
        await query_with_timeout(self.client, prompt, timeout=60.0)
        
        async for response in receive_response_with_timeout(self.client, timeout=120.0):
            # Process response
            pass
```

## Dependencies

- `ClaudeSDKClientManager` - For client management
- `EventBus` - For event-driven communication
- `Config` - For configuration
- `AnalysisLogger` - For analysis logging (if needed)
- Domain-specific stores - For data persistence

## Testing

- Test SDK integration works correctly
- Test timeout protection works
- Test error handling and recovery
- Test event emission
- Test analysis logging

## Maintenance

- **When service grows**: Split into focused services or extract supporting modules
- **When patterns change**: Update this CLAUDE.md and parent `src/services/CLAUDE.md`
- **When SDK changes**: Update all services using SDK to match new patterns

