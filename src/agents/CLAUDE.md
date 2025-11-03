# Agents Directory Guidelines

> **Scope**: Applies to `src/agents/` directory. Read `src/CLAUDE.md` and `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `agents/` directory contains specialized trading agent implementations for the multi-agent framework. Each agent represents a domain-specific trading expert that collaborates with other agents to make trading decisions.

## Architecture Pattern

### Multi-Agent System

Agents in this directory are **specialized trading experts** that work together:
- **Technical Analyst** - Chart analysis, pattern recognition
- **Fundamental Screener** - Financial statement analysis, valuation
- **Risk Manager** - Portfolio risk assessment, position sizing
- **Portfolio Analyzer** - Portfolio optimization, sector analysis
- **Market Monitor** - Market data collection, news analysis
- **Strategy Agent** - Strategy design, backtesting, optimization
- **Execution Agent** - Trade execution management
- **Recommendation Agent** - Trading recommendation generation

### Agent Structure

Each agent should follow this pattern:

```python
from src.core.event_bus import EventHandler, Event, EventType
from src.core.coordinators.agent.agent_profile import AgentProfile, AgentRole

class TechnicalAnalyst(EventHandler):
    """Technical analysis agent for chart patterns and indicators."""
    
    def __init__(self, config, dependencies):
        """Initialize agent with dependencies."""
        self.role = AgentRole.TECHNICAL_ANALYST
        # Initialize dependencies
    
    async def analyze(self, symbol: str, data: Dict) -> Dict[str, Any]:
        """Perform technical analysis."""
        # Agent-specific logic
        pass
```

## Rules

### ✅ DO

- ✅ Inherit from `EventHandler` for event handling
- ✅ Use `AgentProfile` and `AgentRole` for agent identity
- ✅ Emit agent lifecycle events
- ✅ Communicate via `EventBus` (never direct calls)
- ✅ Register with `AgentCoordinator`
- ✅ Keep single responsibility (one domain per agent)
- ✅ Max 350 lines per agent file
- ✅ Use async operations throughout

### ❌ DON'T

- ❌ Make direct service-to-service calls
- ❌ Implement multiple responsibilities in one agent
- ❌ Block on I/O operations
- ❌ Exceed file size limits
- ❌ Use direct API calls (use services)

## Agent Communication

Agents communicate via the EventBus:

```python
# Agent publishes analysis result
await self.event_bus.publish(Event(
    type=EventType.AI_ANALYSIS_COMPLETE,
    source=self.agent_id,
    data={"symbol": symbol, "analysis": result}
))

# Agent subscribes to relevant events
self.event_bus.subscribe(EventType.MARKET_DATA_UPDATED, self)
```

## Agent Registration

Agents must be registered with `AgentCoordinator`:

```python
profile = AgentProfile(
    agent_id="technical_analyst",
    role=AgentRole.TECHNICAL_ANALYST,
    capabilities=["chart_analysis", "pattern_recognition"],
    specialization_areas=["trend_analysis", "momentum_signals"]
)

await agent_coordinator.register_agent(profile)
```

## Dependencies

Agents typically depend on:
- `EventBus` - For communication
- `AgentCoordinator` - For registration
- Domain-specific services - For data access
- `DatabaseStateManager` - For state persistence (optional)

## Best Practices

1. **Single Responsibility**: Each agent focuses on one domain
2. **Event-Driven**: Use events for all communication
3. **Stateless Design**: Agents should be stateless when possible
4. **Error Handling**: Emit error events, don't raise exceptions
5. **Resource Cleanup**: Implement proper cleanup in `close()` method

