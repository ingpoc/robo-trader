# Agent Coordinator Guidelines

> **Scope**: Applies to `src/core/coordinators/agent/` directory. Read `src/core/CLAUDE.md` for context.

## Overview

Agent coordinators manage Claude AI agent sessions and multi-agent coordination. The architecture follows an orchestrator pattern where `ClaudeAgentCoordinator` delegates to focused agent coordinators.

## Architecture Pattern

### Orchestrator + Focused Coordinators

- **`ClaudeAgentCoordinator`**: Main orchestrator (max 200 lines)
  - Delegates to focused agent coordinators
  - Manages autonomous trading sessions
  - Provides unified agent API

- **Focused Coordinators** (max 150 lines each):
  - `AgentSessionCoordinator` - Orchestrates session operations (session/)
  - `AgentToolCoordinator` - MCP server setup and tool definitions
  - `AgentPromptBuilder` - System, morning, and evening prompts

### Focused Subfolders

- **`session/`**: Session management coordinators
  - `AgentSessionCoordinator` - Main orchestrator (max 150 lines)
  - `MorningSessionCoordinator` - Morning prep sessions (max 150 lines)
  - `EveningSessionCoordinator` - Evening review sessions (max 150 lines)

- **`AgentCoordinator`**: Multi-agent coordination (max 200 lines)
  - Agent registration and profiling
  - Agent availability tracking
  - Basic agent communication routing

- **Model Files**:
  - `agent_profile.py` - `AgentProfile`, `AgentRole` enum

## Agent Roles

- `TECHNICAL_ANALYST` - Chart analysis, pattern recognition
- `FUNDAMENTAL_SCREENER` - Financial statement analysis, valuation
- `RISK_MANAGER` - Portfolio risk assessment, position sizing
- `PORTFOLIO_ANALYST` - Portfolio optimization, sector analysis
- `MARKET_MONITOR` - Market data collection, news analysis
- `STRATEGY_AGENT` - Strategy design, backtesting, optimization

## Rules

### ✅ DO

- ✅ Inherit from `BaseCoordinator`
- ✅ Use `ClaudeSDKClientManager` for client creation
- ✅ Use timeout helpers (`query_with_timeout`, `receive_response_with_timeout`)
- ✅ Validate system prompts with `validate_system_prompt_size()`
- ✅ Emit agent lifecycle events
- ✅ Use `AgentProfile` model for agent representation
- ✅ Keep orchestrators under 200 lines
- ✅ Keep focused coordinators under 150 lines

### ❌ DON'T

- ❌ Create `ClaudeSDKClient` directly (use `ClaudeSDKClientManager`)
- ❌ Call SDK methods without timeout protection
- ❌ Exceed prompt size limits (8000 tokens)
- ❌ Block on agent operations
- ❌ Exceed line limits

## Implementation Pattern

```python
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout

class AgentSessionCoordinator(BaseCoordinator):
    """Manages agent sessions."""
    
    async def run_morning_prep(self) -> None:
        """Run morning preparation session."""
        client_manager = await ClaudeSDKClientManager.get_instance()
        client = await client_manager.get_client("trading", options)
        
        # Use timeout helpers
        await query_with_timeout(client, prompt, timeout=90.0)
        
        async for response in receive_response_with_timeout(client, timeout=120.0):
            # Process response
            pass
```

## Session Types

### Morning Prep Session

- Runs before market open
- Reviews portfolio, market conditions
- Generates trading plan for the day

### Evening Review Session

- Runs after market close
- Reviews trades, performance
- Generates insights and improvements

## Tool Definitions

Use `AgentToolCoordinator` to define MCP tools for Claude agents:

```python
tools = await agent_tool_coordinator.get_tool_definitions()
```

## Prompt Building

Use `AgentPromptBuilder` to build system prompts:

```python
system_prompt = agent_prompt_builder.build_system_prompt()
morning_prompt = agent_prompt_builder.build_morning_prompt()
evening_prompt = agent_prompt_builder.build_evening_prompt()
```

## Agent Registration

```python
profile = AgentProfile(
    agent_id="technical_analyst",
    role=AgentRole.TECHNICAL_ANALYST,
    capabilities=["chart_analysis", "pattern_recognition"],
    specialization_areas=["trend_analysis", "momentum_signals"]
)

await agent_coordinator.register_agent(profile)
```

## Event Types

- `agent_registered` - Agent registered
- `agent_session_started` - Agent session started
- `agent_session_ended` - Agent session ended
- `agent_decision_made` - Agent made trading decision

## Dependencies

Agent coordinators typically depend on:
- `ClaudeSDKClientManager` - For SDK client creation
- `EventBus` - For event emission
- `ClaudeStrategyStore` - For strategy storage
- `ToolExecutor` - For tool execution
- `ResponseValidator` - For response validation

