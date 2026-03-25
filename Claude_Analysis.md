# Robo Trader - Architecture Analysis

> Analysis date: 2026-03-20
> Sources: Direct codebase exploration + DeepWiki (https://deepwiki.com/ingpoc/robo-trader)

---

## Architecture Overview

Robo Trader is a **coordinator-based monolith** with an AI-first autonomous swing trading design built around three pillars:

1. **RoboTraderOrchestrator** — Central facade coordinating all domain coordinators via Claude Agent SDK
2. **State Management** — Focused Stores pattern (16 async state managers) backed by SQLite with asyncio locking
3. **Background Scheduler** — 3 parallel queues for autonomous task execution with resource management

```
Frontend (React/Vite - Port 3000)
         ↕ REST/WebSocket
Backend (FastAPI - Port 8000)
  ├── Orchestrator (thin facade)
  ├── 62 Coordinators (domain-driven, event-driven, 150 lines max each)
  ├── EventBus (50+ event types, pub/sub)
  ├── DI Container (5 modular registries)
  ├── 16 Async State Managers (SQLite-backed, asyncio.Lock per state)
  └── Services (analytics, execution, risk, learning)
         ↕
External: Claude Agent SDK | Zerodha Kite | Perplexity | Upstox
```

---

## Key Design Patterns

| Pattern | Detail |
|---------|--------|
| **Coordinator Pattern** | 62 files, 150 lines max each, single responsibility per domain |
| **Event-Driven** | No direct service calls; all communication via EventBus (50+ EventTypes) |
| **DI Container** | 5 modular registries (`di_registry_core`, `_services`, `_paper_trading`, `_sdk`, `_coordinators`) |
| **Locked State** | `asyncio.Lock()` per state class to prevent SQLite concurrency issues |
| **Queue System** | 3 parallel queues (PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS), max 20 tasks, max 3 stocks/AI task |
| **Focused Stores** | PortfolioStore, IntentLedger, PlanningStore, AnalyticsCache — modular over monolithic |

---

## Main Components & Roles

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **RoboTraderOrchestrator** | `src/core/orchestrator.py` | Thin facade coordinating all coordinators |
| **Coordinators (62 files)** | `src/core/coordinators/` | Event-driven domain orchestration |
| **EventBus** | `src/core/event_bus.py` | Pub/sub routing with 50+ typed events |
| **DependencyContainer** | `src/core/di.py` | Singleton service resolution |
| **Services (20+ files)** | `src/services/` | Domain logic: analytics, execution, risk, learning |
| **State Managers (16)** | `src/core/database_state/` | Async SQLite state with locking |
| **FastAPI Routes** | `src/web/routes/` | REST endpoints + WebSocket handling |
| **Models** | `src/models/` | Pydantic DTOs: queue, trading, market data |
| **Frontend** | `ui/src/` | React/TypeScript operator console |
| **Safety Framework** | `src/services/` | AutonomousTradingSafeguards, RiskService, SafetyLayer |

---

## Strengths

### 1. Safety-First Design
- Paper trading mandatory before any live execution
- `SafetyLayer` validates all trades before execution
- `AutonomousTradingSafeguards` with daily loss limits and consecutive loss circuit breakers
- `ApprovalState` for manual approval workflows on critical operations
- Environment-based permissions (dry-run / paper / live)

### 2. Observability & AI Transparency
- `ClaudeDecisionLogger` logs all AI reasoning and trade recommendations
- `IntentLedger` provides full audit trail of decisions
- Dedicated AI Transparency UI tab
- System health dashboard with real-time queue and backend status

### 3. Event-Driven, Loosely Coupled
- No direct service-to-service calls; everything via EventBus
- Easy to add new behavior without ripple effects
- Events are typed (50+ `EventType` enum values) and can be persisted for audit/replay

### 4. Scalable Queue Architecture
- 3 parallel queues prevent resource contention
- AI tasks capped at 3 symbols/task to prevent token exhaustion
- Queue capacity of 20 prevents runaway task creation

### 5. Broker Flexibility
- `QuoteStreamAdapter` abstraction enables operation without a full Zerodha subscription
- Market data layer is decoupled from execution layer

### 6. Modular DI & Clean Separation
- 5 DI registries loaded in dependency order
- Lazy initialization, testable, single instance per service
- No hardcoded service names — canonical names documented in `di_registry_*.py`

### 7. Rich Documentation
- 8 layer-specific `CLAUDE.md` files (root, src/, core/, services/, web/, ui/, coordinators/)
- Common issues & fixes, canonical constants, anti-patterns all documented
- Serves as both developer guide and operating manual

---

## Weaknesses

### 1. Steep Learning Curve / Complexity
- Coordinator pattern + EventBus + DI + asyncio locking = many concepts to master simultaneously
- 62 coordinator files can be hard to navigate
- Multiple CLAUDE.md warnings reflect how easy it is to misuse patterns

### 2. SQLite Concurrency Bottleneck
- Single-writer SQLite with `asyncio.Lock()` per state class
- Under high concurrency, this could become a performance bottleneck
- "database is locked" errors are a recurring issue documented across the codebase

### 3. Silent Mock / Fallback Paths
- Some integrations (Zerodha auth, live trading, Upstox) still use mocks or fallbacks
- Risk of AI Transparency showing trades while Paper Trading tab shows no positions (data source mismatch)
- Hard to detect without explicit end-to-end testing

### 4. Heavy Claude SDK Dependency
- No fallback behavior if Claude Agent SDK times out or becomes unavailable
- Orchestrator startup polls for auth status without retry/escalation logic
- System effectively stalls if SDK is unreachable

### 5. Token Batching Constraints
- 3-symbols-per-AI-task limit may restrict sophisticated multi-stock correlation analysis
- Queue capacity of 20 can be a ceiling during high-volume market events

### 6. asyncio Misuse Risk
- `get_event_loop()` vs `get_running_loop()` is a subtle but critical distinction
- Easy to introduce bugs when writing new coordinators or services
- Requires linter enforcement; manual discipline alone is insufficient

### 7. Frontend-Backend Data Consistency
- Paper Trading and AI Transparency tabs read from different data sources
- Can show conflicting information without a single state authority
- Requires strict use of `state_manager` as the canonical read path

### 8. Operational Maturity
- Relatively new system; production edge cases likely not fully discovered
- No alerting or escalation beyond health check endpoints
- Limited troubleshooting runbooks beyond the health check script

---

## Maturity Assessment

| Area | Status | Notes |
|------|--------|-------|
| Paper Trading Execution | ✅ Production-ready | Dedicated state, routes, UI, safeguards |
| Event Bus & Coordination | ✅ Strong | 50+ typed events, proper cleanup |
| Risk Management | ✅ Strong | RiskService, SafetyLayer, circuit breakers |
| AI Transparency | ✅ Strong | Decision logging, reasoning traces, dedicated UI |
| Broker Flexibility | ✅ Strong | QuoteStreamAdapter abstraction |
| Live Trading Integration | ⚠️ Partial | Mocks/fallbacks remain, Zerodha auth incomplete |
| Test Coverage | ⚠️ Partial | Integration tests exist, coordinator gaps |
| Operational Alerting | ⚠️ Partial | Health endpoints only, no escalation |
| Production Edge Cases | ⚠️ Unknown | System is relatively new |

---

## Critical Operational Rules

1. **Queue AI tasks** — `QueueName.AI_ANALYSIS` with max 3 stocks (prevents token exhaustion)
2. **Use locked state** — `config_state.store_*()` not direct DB (prevents locking errors)
3. **No direct service calls** — emit events via EventBus (maintains loose coupling)
4. **Async throughout** — `asyncio.get_running_loop()`, never `get_event_loop()`
5. **Coordinator max 150 lines** — exceed this = refactor into subdomain
6. **Unsubscribe in cleanup** — every coordinator must unsubscribe to prevent memory leaks
7. **Health check before work** — run `./.claude/scripts/health_check.sh`
8. **Paper trading first** — live trading explicitly out of scope

---

## Summary

Robo Trader is a well-architected, AI-first trading platform with strong foundations in safety, observability, and event-driven design. The coordinator pattern combined with the EventBus provides clean separation of concerns. However, the system carries real risks around **complexity adherence** (patterns must be followed strictly), **SQLite scalability**, and **incomplete live trading integration**. The CLAUDE.md documentation is effectively the system's operating manual — deviating from it is the primary source of bugs. Paper trading and observability are production-ready; live trading and some broker integrations remain aspirational.
