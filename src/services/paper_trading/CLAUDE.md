# Paper Trading Services - src/services/paper_trading/

## Services
| Module | Purpose | Max Size |
|--------|---------|----------|
| account_manager.py | Account management & state | 350 lines |
| trade_executor.py | Simulated trade execution | 350 lines |
| performance_calculator.py | Performance metrics | 350 lines |
| price_monitor.py | Price tracking & updates | 350 lines |

## Rules
| Rule | Requirement |
|------|-------------|
| Lines | <350 per file, refactor if over |
| Database | Use locked state methods ONLY |
| Events | Emit via EventBus for comms |
| State | Maintain account/trade consistency |
| Validation | Always validate trades & operations |
| Errors | Wrap in TradingError with context |

## Pattern
```python
class PaperTradingService(EventHandler):
    async def handle_event(self, event):
        if event.type == EventType.RELEVANT:
            await self._handle(event)

    async def cleanup(self):
        self.event_bus.unsubscribe(EventType.RELEVANT, self)
```

## Dependencies
- EventBus, Config, DatabaseStateManager, PaperTradingStore, MarketDataService

