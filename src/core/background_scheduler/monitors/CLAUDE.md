# Background Scheduler Monitors - src/core/background_scheduler/monitors/

Health monitoring components. Monitor system health, market conditions, risk levels. Emit alerts on threshold violations.

## Pattern
```python
monitor = HealthMonitor()
monitor.set_claude_status_callback(get_claude_status)
health_status = await monitor.check_system_health()
# Returns: {"timestamp": "...", "overall_status": "healthy/degraded/unhealthy", "components": {...}}

# Emit alert
await event_bus.publish(Event(
    type=EventType.HEALTH_ALERT,
    source="health_monitor",
    data={"component": "claude_api", "severity": "critical"}
))
```

## Monitors
| Monitor | Checks |
|---------|--------|
| HealthMonitor | System health (API, DB, resources) |
| MarketMonitor | Market conditions (hours, volatility) |
| RiskMonitor | Risk levels (portfolio, position risk) |

## Rules
| DO | DON'T |
|----|-------|
| Monitor specific domains | Mix monitoring domains |
| Check at regular intervals | Use blocking operations |
| Emit alerts on violations | Hardcode thresholds |
| Use async operations | Skip error handling |
| Log health status | Create dependencies |
| Configure thresholds | |

## Dependencies
EventBus, StateManager, ClaudeSDKClient, External APIs

