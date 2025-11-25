# Agent Coordinator - src/core/coordinators/agent/

Multi-agent sessions (morning/evening). Orchestrator + focused coordinators.

## Structure
- `ClaudeAgentCoordinator` (orchestrator, max 200)
- `AgentSessionCoordinator` (session/, max 150)
- `MorningSessionCoordinator` (session/, max 150)
- `EveningSessionCoordinator` (session/, max 150)

## Agent Roles
| Role | Purpose |
|------|---------|
| TECHNICAL_ANALYST | Chart analysis, patterns |
| FUNDAMENTAL_SCREENER | Financials, valuation |
| RISK_MANAGER | Risk, position sizing |
| PORTFOLIO_ANALYST | Optimization, sectors |
| MARKET_MONITOR | Market data, news |
| STRATEGY_AGENT | Strategy, backtesting |

## Pattern
```python
client_manager = await ClaudeSDKClientManager.get_instance()
client = await client_manager.get_client("trading", options)
profile = AgentProfile(agent_id="tech_analyst", role=AgentRole.TECHNICAL_ANALYST)
await agent_coordinator.register_agent(profile)
```

## Rules
| DO | DON'T |
|----|-------|
| Use ClaudeSDKClientManager | Create clients directly |
| Validate prompts (8k tokens) | Exceed prompt limits |
| Emit lifecycle events | Block on I/O |
| Use AgentProfile | Exceed 200/150 lines |
| Graceful errors | Raise exceptions |

## Events
agent_registered, agent_session_started, agent_session_ended, agent_decision_made

## Dependencies
ClaudeSDKClientManager, EventBus, ClaudeStrategyStore, ToolExecutor, ResponseValidator

