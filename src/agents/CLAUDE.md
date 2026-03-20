# Agents - src/agents/

**Context**: Agent SDK bot agents that run autonomously for trading analysis.
Claude Code reviews logs and fixes bugs in agent implementation.
Claude Code does NOT invoke agents directly or implement trading logic.

Specialized trading experts (multi-agent framework). Max 350 lines per agent file.

## Agent Pattern

```python
from src.core.event_bus import EventHandler, Event, EventType
from src.core.coordinators.agent.agent_profile import AgentProfile, AgentRole

class TechnicalAnalyst(EventHandler):
    def __init__(self, config, dependencies):
        self.role = AgentRole.TECHNICAL_ANALYST

    async def analyze(self, symbol: str, data: Dict) -> Dict:
        # Agent-specific logic
        await self.event_bus.publish(Event(
            type=EventType.AI_ANALYSIS_COMPLETE,
            source=self.agent_id,
            data={"symbol": symbol, "analysis": result}
        ))
```

## Agents

| Agent | Purpose |
|-------|---------|
| Technical Analyst | Chart analysis, pattern recognition |
| Fundamental Screener | Financial statements, valuation |
| Risk Manager | Risk assessment, position sizing |
| Portfolio Analyzer | Optimization, sector analysis |
| Market Monitor | Market data, news analysis |
| Strategy Agent | Strategy design, backtesting |
| Execution Agent | Trade execution management |
| Recommendation Agent | Recommendation generation |

## Rules

| DO | DON'T |
|----|-------|
| Inherit EventHandler | Direct service calls |
| Emit lifecycle events | Multiple responsibilities |
| Use EventBus (not direct) | Block on I/O |
| Register with AgentCoordinator | Exceed 350 lines |
| Single responsibility | Direct API calls |
| Async throughout | Stateful design |

## Registration

```python
profile = AgentProfile(
    agent_id="technical_analyst",
    role=AgentRole.TECHNICAL_ANALYST,
    capabilities=["chart_analysis", "pattern_recognition"]
)
await agent_coordinator.register_agent(profile)
```

## Dependencies

- EventBus (communication), AgentCoordinator (registration)
- Domain services (data access), DatabaseStateManager (state)

## Cleanup
Implement `close()` for resource cleanup. Emit error events, don't raise.

