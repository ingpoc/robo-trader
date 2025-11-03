# Background Scheduler Monitors Directory Guidelines

> **Scope**: Applies to `src/core/background_scheduler/monitors/` directory. Read `src/core/background_scheduler/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `monitors/` directory contains health monitoring components for the background scheduler. Monitors check system health, market conditions, risk levels, and other critical system metrics.

## Architecture Pattern

### Health Monitoring Pattern

Monitors continuously check system health and emit alerts when thresholds are exceeded. Each monitor focuses on a specific health domain.

### Directory Structure

```
monitors/
├── health_monitor.py        # General system health
├── market_monitor.py         # Market condition monitoring
├── risk_monitor.py           # Risk level monitoring
└── monthly_reset_monitor.py  # Monthly reset monitoring
```

## Rules

### ✅ DO

- ✅ Monitor specific health domains
- ✅ Check health at regular intervals
- ✅ Emit alerts when thresholds exceeded
- ✅ Use async operations for health checks
- ✅ Log health status for debugging
- ✅ Handle health check errors gracefully
- ✅ Set configurable thresholds

### ❌ DON'T

- ❌ Mix multiple monitoring domains
- ❌ Use blocking operations
- ❌ Skip error handling
- ❌ Hardcode thresholds
- ❌ Skip logging health status
- ❌ Create monitoring dependencies

## Monitor Pattern

```python
from src.core.background_scheduler.monitors.health_monitor import HealthMonitor

# Initialize monitor
monitor = HealthMonitor()
monitor.set_claude_status_callback(get_claude_status)
monitor.set_state_manager(state_manager)

# Check system health
health_status = await monitor.check_system_health()

# Health status contains:
# - overall_status: "healthy" | "degraded" | "unhealthy"
# - components: Dict with component health
# - timestamp: Health check timestamp
```

## Health Check Structure

```python
health_status = {
    "timestamp": "2024-01-01T12:00:00Z",
    "overall_status": "healthy",
    "components": {
        "claude_api": {
            "status": "healthy",
            "latency_ms": 150,
            "last_check": "2024-01-01T12:00:00Z"
        },
        "database": {
            "status": "healthy",
            "connection_count": 5,
            "last_check": "2024-01-01T12:00:00Z"
        }
    }
}
```

## Market Monitor Pattern

```python
from src.core.background_scheduler.monitors.market_monitor import MarketMonitor

# Initialize market monitor
market_monitor = MarketMonitor()

# Check market conditions
market_status = await market_monitor.check_market_conditions()

# Market status contains:
# - market_open: bool
# - volatility_level: "low" | "medium" | "high"
# - trading_hours: Dict with hours info
```

## Risk Monitor Pattern

```python
from src.core.background_scheduler.monitors.risk_monitor import RiskMonitor

# Initialize risk monitor
risk_monitor = RiskMonitor()

# Check risk levels
risk_status = await risk_monitor.check_risk_levels()

# Risk status contains:
# - overall_risk: "low" | "medium" | "high"
# - portfolio_risk: Dict with portfolio metrics
# - alerts: List of risk alerts
```

## Alert Emission

Monitors emit alerts when thresholds are exceeded:

```python
from src.core.event_bus import Event, EventType

# Emit health alert
await event_bus.publish(Event(
    type=EventType.HEALTH_ALERT,
    source="health_monitor",
    data={
        "component": "claude_api",
        "severity": "critical",
        "message": "API latency exceeded threshold"
    }
))
```

## Periodic Monitoring

Monitors run periodically:

```python
async def periodic_health_check():
    """Run periodic health checks."""
    while True:
        health_status = await monitor.check_system_health()
        
        # Emit if unhealthy
        if health_status['overall_status'] != "healthy":
            await emit_alert(health_status)
        
        # Wait before next check
        await asyncio.sleep(60)  # Check every minute
```

## Dependencies

Monitor components depend on:
- `EventBus` - For alert emission
- `StateManager` - For database health checks
- `ClaudeSDKClient` - For Claude API health checks
- External APIs - For market data health checks

## Testing

Test monitor health checks:

```python
import pytest
from src.core.background_scheduler.monitors.health_monitor import HealthMonitor

async def test_health_monitor():
    """Test health monitor."""
    monitor = HealthMonitor()
    
    health_status = await monitor.check_system_health()
    
    assert health_status['overall_status'] in ['healthy', 'degraded', 'unhealthy']
    assert 'components' in health_status
    assert 'timestamp' in health_status
```

## Maintenance

When adding new monitors:

1. Focus on specific health domain
2. Implement async health checks
3. Emit alerts for threshold violations
4. Log health status
5. Update this CLAUDE.md file

