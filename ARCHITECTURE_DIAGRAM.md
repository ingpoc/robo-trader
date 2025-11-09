# Robo Trader Architecture Diagram

**Generated from codebase analysis** | **Last Updated**: 2025-01-XX

## Table of Contents
1. [System Overview](#system-overview)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Data Flow](#data-flow)
5. [Communication Patterns](#communication-patterns)
6. [Queue System](#queue-system)
7. [Event Bus System](#event-bus-system)
8. [Dependency Injection](#dependency-injection)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (React/TypeScript Frontend)                   │
│                      Port: 3000 (Vite Dev)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP REST API
                             │ WebSocket (Real-time)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    FASTAPI BACKEND SERVER                       │
│                      Port: 8000 (Uvicorn)                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Dependency Injection Container              │  │
│  │  (Singleton Services, Coordinators, Orchestrator)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Event Bus System                       │  │
│  │  (Event-driven communication, persistence, replay)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Sequential Queue Manager                     │  │
│  │  (3 Parallel Queues: PORTFOLIO_SYNC, DATA_FETCHER,       │  │
│  │   AI_ANALYSIS - Tasks execute sequentially per queue)     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│   SQLite DB    │  │  Claude SDK     │  │  Market Data    │
│  (State,       │  │  (AI Analysis)  │  │  (External APIs) │
│   Events,      │  │                 │  │                 │
│   Tasks)       │  │                 │  │                 │
└────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Backend Architecture

### Coordinator-Based Monolithic Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RoboTraderOrchestrator                       │
│                    (Thin Facade Pattern)                        │
│                                                                  │
│  Delegates to focused coordinators (max 150 lines each)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│   Core         │  │   Status         │  │   Agent          │
│ Coordinators   │  │ Coordinators     │  │ Coordinators    │
├────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • Session      │  │ • System        │  │ • Agent         │
│ • Query        │  │ • AI            │  │ • Message       │
│ • Task         │  │ • Portfolio     │  │ • Communication │
│ • Lifecycle    │  │ • Scheduler     │  │ • Registration  │
│ • Portfolio    │  │ • Infrastructure│  │ • Tool          │
└────────────────┘  └─────────────────┘  └─────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Services      │
                    ├─────────────────┤
                    │ • Portfolio     │
                    │ • Risk          │
                    │ • Execution     │
                    │ • Analytics     │
                    │ • Market Data   │
                    │ • Learning      │
                    │ • Paper Trading │
                    └─────────────────┘
```

### Detailed Coordinator Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    Coordinator Hierarchy                        │
└─────────────────────────────────────────────────────────────────┘

BaseCoordinator (Abstract)
├── Core Coordinators
│   ├── SessionCoordinator
│   │   └── Manages Claude SDK session lifecycle
│   ├── QueryCoordinator
│   │   └── Processes user queries and AI interactions
│   ├── TaskCoordinator
│   │   └── Manages analytics and background tasks
│   ├── LifecycleCoordinator
│   │   └── Emergency stop/resume operations
│   └── PortfolioCoordinator
│       └── Portfolio operations and analysis
│
├── Status Coordinators (Aggregation Pattern)
│   ├── StatusCoordinator (Main)
│   ├── SystemStatusCoordinator
│   ├── AIStatusCoordinator
│   ├── PortfolioStatusCoordinator
│   ├── SchedulerStatusCoordinator
│   ├── InfrastructureStatusCoordinator
│   └── AgentStatusCoordinator
│
├── Agent Coordinators
│   ├── AgentCoordinator
│   ├── ClaudeAgentCoordinator
│   ├── AgentCommunicationCoordinator
│   ├── AgentRegistrationCoordinator
│   └── AgentToolCoordinator
│
├── Broadcast Coordinators
│   ├── BroadcastCoordinator
│   ├── BroadcastExecutionCoordinator
│   └── BroadcastHealthCoordinator
│
└── Queue Coordinators
    ├── QueueCoordinator
    ├── QueueExecutionCoordinator
    ├── QueueLifecycleCoordinator
    ├── QueueMonitoringCoordinator
    └── QueueEventCoordinator
```

---

## Frontend Architecture

### Feature-Based React Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Application (Vite)                       │
│                      Port: 3000/5173                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│   Features     │  │   Shared        │  │   State          │
│   (Modular)    │  │   Components    │  │   Management     │
├────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • Dashboard    │  │ • UI Primitives │  │ • Zustand       │
│ • AI           │  │ • Dashboard     │  │   Stores        │
│   Transparency │  │ • Sidebar        │  │ • WebSocket     │
│ • System       │  │ • Layout         │  │   Client        │
│   Health       │  │                 │  │ • API Hooks     │
│ • Paper        │  │                 │  │                 │
│   Trading      │  │                 │  │                 │
│ • News/        │  │                 │  │                 │
│   Earnings     │  │                 │  │                 │
│ • Agents       │  │                 │  │                 │
│ • Configuration│  │                 │  │                 │
└────────────────┘  └─────────────────┘  └─────────────────┘
```

### Frontend Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Data Flow                            │
└─────────────────────────────────────────────────────────────────┘

User Interaction
      │
      ▼
React Component
      │
      ▼
Custom Hook (useDashboardData, useWebSocket, etc.)
      │
      ├─────────────────┬─────────────────┐
      │                 │                 │
      ▼                 ▼                 ▼
  REST API         WebSocket         Zustand Store
  (HTTP)           (Real-time)      (Local State)
      │                 │                 │
      └─────────────────┼─────────────────┘
                        │
                        ▼
              Backend API Endpoints
                        │
                        ▼
              Orchestrator/Coordinators
```

---

## Data Flow

### Request Flow (HTTP API)

```
┌──────────┐
│  Client  │
│ (Browser) │
└─────┬────┘
      │ HTTP Request
      ▼
┌─────────────────────────────────────┐
│     FastAPI Route Handler           │
│  (src/web/routes/*.py)              │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Dependency Injection Container     │
│  (Get Orchestrator/Service)         │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│     RoboTraderOrchestrator          │
│     (Thin Facade)                   │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│     Focused Coordinator             │
│     (Session, Query, Task, etc.)    │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│     Domain Service                  │
│     (Portfolio, Risk, Execution)     │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│     Database State Manager          │
│     (SQLite with async operations)  │
└─────────────────────────────────────┘
```

### Real-time Flow (WebSocket)

```
┌──────────┐
│  Client  │
│ (Browser)│
└─────┬────┘
      │ WebSocket Connection
      ▼
┌─────────────────────────────────────┐
│  WebSocket Endpoint (/ws)           │
│  ConnectionManager                   │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  BroadcastCoordinator                │
│  (Sets broadcast callback)          │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  StatusCoordinator                   │
│  (Aggregates system status)         │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Event Bus                           │
│  (Publishes status events)           │
└─────┬───────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  WebSocket Broadcast                 │
│  (Real-time updates to all clients) │
└─────────────────────────────────────┘
```

---

## Communication Patterns

### Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Bus Communication                      │
└─────────────────────────────────────────────────────────────────┘

Service A                    Event Bus                    Service B
    │                            │                            │
    │─── publish(event) ────────>│                            │
    │                            │                            │
    │                            │─── notify ────────────────>│
    │                            │   subscribers             │
    │                            │                            │
    │                            │<── handle_event() ─────────│
    │                            │                            │
    │                            │  (Event persisted to DB)    │
    │                            │                            │
```

### Event Types

```
EventType Enum:
├── Market Events
│   ├── MARKET_PRICE_UPDATE
│   ├── MARKET_VOLUME_SPIKE
│   ├── MARKET_NEWS
│   └── MARKET_EARNINGS
│
├── Portfolio Events
│   ├── PORTFOLIO_POSITION_CHANGE
│   ├── PORTFOLIO_PNL_UPDATE
│   └── PORTFOLIO_CASH_CHANGE
│
├── Risk Events
│   ├── RISK_BREACH
│   ├── RISK_STOP_LOSS_TRIGGER
│   └── RISK_EXPOSURE_CHANGE
│
├── Execution Events
│   ├── EXECUTION_ORDER_PLACED
│   ├── EXECUTION_ORDER_FILLED
│   ├── EXECUTION_ORDER_REJECTED
│   └── EXECUTION_ORDER_CANCELLED
│
├── AI Events
│   ├── AI_RECOMMENDATION
│   ├── AI_ANALYSIS_COMPLETE
│   └── AI_LEARNING_UPDATE
│
├── Task Scheduler Events
│   ├── TASK_CREATED
│   ├── TASK_COMPLETED
│   ├── TASK_FAILED
│   └── TASK_STARTED
│
└── System Events
    ├── SYSTEM_HEALTH_CHECK
    ├── SYSTEM_ERROR
    └── SYSTEM_STATUS
```

---

## Queue System

### Sequential Queue Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│           Sequential Queue Manager Architecture                 │
└─────────────────────────────────────────────────────────────────┘

                    SequentialQueueManager
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│ PORTFOLIO_SYNC │  │  DATA_FETCHER    │  │  AI_ANALYSIS     │
│   Queue        │  │   Queue          │  │   Queue          │
├────────────────┤  ├─────────────────┤  ├─────────────────┤
│ Executes in    │  │ Executes in     │  │ Executes in     │
│ PARALLEL with  │  │ PARALLEL with   │  │ PARALLEL with   │
│ other queues   │  │ other queues    │  │ other queues    │
│                │  │                 │  │                 │
│ Tasks execute  │  │ Tasks execute   │  │ Tasks execute   │
│ SEQUENTIALLY   │  │ SEQUENTIALLY    │  │ SEQUENTIALLY    │
│ (one-at-a-time)│  │ (one-at-a-time) │  │ (one-at-a-time) │
│                │  │                 │  │                 │
│ ThreadSafe     │  │ ThreadSafe      │  │ ThreadSafe      │
│ QueueExecutor   │  │ QueueExecutor   │  │ QueueExecutor   │
│ (Worker Thread) │  │ (Worker Thread) │  │ (Worker Thread) │
└────────────────┘  └─────────────────┘  └─────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Task Service   │
                    │  (Task CRUD)    │
                    └─────────────────┘
```

### Queue Execution Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                    Queue Execution Flow                         │
└─────────────────────────────────────────────────────────────────┘

BackgroundScheduler (Event-driven)
    │
    │ (Subscribes to events)
    ▼
Event Handlers
    │
    │ (Creates tasks on events)
    ▼
SchedulerTaskService
    │
    │ (Creates task in queue)
    ▼
SequentialQueueManager
    │
    │ (Starts executor threads)
    ▼
ThreadSafeQueueExecutor (per queue)
    │
    │ (Executes tasks sequentially)
    ▼
Task Handler (Registered per TaskType)
    │
    │ (Executes business logic)
    ▼
Domain Service / Coordinator
    │
    │ (Completes task)
    ▼
Task Status Updated (via callback)
```

### Why Sequential Per Queue?

**Problem**: Analyzing 81 stocks in one Claude session hits turn limits (~15 turns before optimization completes).

**Solution**: Queue system batches requests automatically:
- Each task analyzes 2-3 stocks in its own session
- Tasks execute sequentially (one-at-a-time) per queue
- Each session has plenty of turns available for optimization

**Result**: 81 stocks = ~40 tasks × 2-3 stocks each = 40 queue tasks executed sequentially with full Claude session turns.

---

## Event Bus System

### Event Bus Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Bus Components                        │
└─────────────────────────────────────────────────────────────────┘

EventBus
├── Event Publishing
│   ├── publish(event) → Persist to DB
│   └── Notify subscribers
│
├── Event Subscription
│   ├── subscribe(event_type, handler)
│   └── unsubscribe(event_type, handler)
│
├── Event Persistence
│   ├── SQLite database (event_bus.db)
│   ├── Events table (id, type, timestamp, data, status)
│   └── Dead letter queue (failed events)
│
├── Event Replay
│   ├── get_pending_events()
│   └── replay_events(from_timestamp, to_timestamp)
│
└── Error Handling
    ├── Retry logic (max 3 retries)
    └── Dead letter queue for failed events
```

### Event Handler Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Handler Pattern                      │
└─────────────────────────────────────────────────────────────────┘

EventHandler (Base Class)
    │
    ├── handle_event(event) → Must implement
    │
    └── Subclasses:
        ├── BackgroundScheduler EventHandlers
        │   ├── handle_portfolio_updated()
        │   ├── handle_stock_added()
        │   └── handle_stock_removed()
        │
        └── Service Event Handlers
            ├── PortfolioService handlers
            ├── RiskService handlers
            └── ExecutionService handlers
```

---

## Dependency Injection

### DI Container Structure

```
┌─────────────────────────────────────────────────────────────────┐
│              Dependency Injection Container                     │
└─────────────────────────────────────────────────────────────────┘

DependencyContainer
├── Core Services Registry (di_registry_core.py)
│   ├── DatabaseStateManager
│   ├── EventBus
│   ├── ResourceManager
│   ├── SafetyLayer
│   └── BackgroundScheduler
│
├── Domain Services Registry (di_registry_services.py)
│   ├── PortfolioService
│   ├── RiskService
│   ├── ExecutionService
│   ├── AnalyticsService
│   ├── MarketDataService
│   └── LearningService
│
├── Paper Trading Registry (di_registry_paper_trading.py)
│   ├── PaperTradingAccountManager
│   ├── PaperTradingTradeExecutor
│   └── PaperTradingPriceMonitor
│
├── SDK Services Registry (di_registry_sdk.py)
│   ├── ClaudeSDKClientManager (Singleton)
│   ├── ClaudeSDKAuth
│   └── SDK Helpers
│
├── MCP Services Registry (di_registry_mcp.py)
│   ├── ClaudeAgentMCPServer
│   └── MCP Integration Services
│
└── Coordinators Registry (di_registry_coordinators.py)
    ├── SessionCoordinator
    ├── QueryCoordinator
    ├── TaskCoordinator
    ├── StatusCoordinator
    ├── LifecycleCoordinator
    ├── BroadcastCoordinator
    ├── QueueCoordinator
    ├── PortfolioCoordinator
    └── RoboTraderOrchestrator (Last - depends on all)
```

### DI Initialization Order

```
1. Core Services (Database, EventBus, etc.)
2. Domain Services (Portfolio, Risk, Execution, etc.)
3. Paper Trading Services (depends on MarketDataService)
4. SDK Services (Claude SDK client manager)
5. MCP Services (depends on SDK services)
6. Coordinators (depends on all services)
7. Orchestrator (depends on all coordinators)
```

---

## Database Architecture

### Database State Management

```
┌─────────────────────────────────────────────────────────────────┐
│              Database State Manager (Facade)                    │
└─────────────────────────────────────────────────────────────────┘

DatabaseStateManager
├── PortfolioStateManager
│   └── Manages portfolio holdings, cash, P&L
│
├── IntentStateManager
│   └── Manages trading intents and signals
│
├── ApprovalStateManager
│   └── Manages trade approval queue
│
├── NewsEarningsStateManager
│   └── Manages news and earnings data
│
├── AnalysisStateManager
│   └── Manages analysis history and recommendations
│
├── PortfolioAnalysisState
│   └── Manages portfolio analysis workflows
│
└── PaperTradingState
    └── Manages paper trading accounts and positions
```

### Database Files

```
state/
├── robo_trader.db          # Main application state
├── event_bus.db            # Event persistence
├── portfolio.db            # Portfolio data
├── risk.db                 # Risk metrics
├── market_data.db          # Market data cache
├── feature_management.db  # Feature flags
└── backups/                # Automatic backups
    └── robo_trader_{label}_{timestamp}.db
```

---

## Background Scheduler

### Scheduler Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Background Scheduler (Event-driven)                │
└─────────────────────────────────────────────────────────────────┘

BackgroundScheduler
├── Event Handlers
│   ├── handle_portfolio_updated()
│   ├── handle_stock_added()
│   └── handle_stock_removed()
│
├── Triggers (Scheduled)
│   ├── run_morning_routine() (Market open)
│   ├── run_evening_routine() (Market close)
│   └── Monthly reset monitoring
│
├── Stores
│   ├── TaskStore (Task persistence)
│   ├── StockStateStore (Stock state tracking)
│   └── StrategyLogStore (Strategy execution logs)
│
└── Monitors
    └── MonthlyResetMonitor (Monthly reset detection)
```

### Scheduler Task Flow

```
Market Event / Scheduled Time
    │
    ▼
BackgroundScheduler
    │
    ├── Event Handler OR Trigger
    │
    ▼
SchedulerTaskService.create_task()
    │
    │ (Queue: PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS)
    │ (TaskType: RECOMMENDATION_GENERATION, PORTFOLIO_SCAN, etc.)
    │
    ▼
SequentialQueueManager
    │
    │ (Executes task in appropriate queue)
    │
    ▼
Task Handler (Registered per TaskType)
    │
    │ (Executes business logic)
    │
    ▼
Domain Service / Coordinator
    │
    │ (Completes task)
    │
    ▼
Task Status: COMPLETED / FAILED
```

---

## Key Architectural Patterns

### 1. Coordinator Pattern
- **Purpose**: Thin, focused coordinators (max 150 lines each)
- **Benefit**: Single responsibility, testable, maintainable
- **Example**: SessionCoordinator, QueryCoordinator, TaskCoordinator

### 2. Facade Pattern
- **Purpose**: RoboTraderOrchestrator as thin facade
- **Benefit**: Simple interface, delegates to coordinators
- **Example**: `orchestrator.run_portfolio_scan()` → PortfolioCoordinator

### 3. Dependency Injection
- **Purpose**: Eliminate global state, improve testability
- **Benefit**: Loose coupling, easier testing, better maintainability
- **Implementation**: DependencyContainer with modular registries

### 4. Event-Driven Architecture
- **Purpose**: Decouple services, enable reactive scheduling
- **Benefit**: Loose coupling, scalability, event replay capability
- **Implementation**: EventBus with typed events and handlers

### 5. Queue-Based Task Execution
- **Purpose**: Prevent resource exhaustion, ensure sequential execution
- **Benefit**: Prevents Claude turn limit exhaustion, fair resource allocation
- **Implementation**: SequentialQueueManager with ThreadSafeQueueExecutor

### 6. Singleton Pattern
- **Purpose**: Expensive resources (ClaudeSDKClientManager)
- **Benefit**: Resource efficiency, shared state management
- **Implementation**: Singleton instances in DI container

### 7. Repository Pattern
- **Purpose**: Abstract database access
- **Benefit**: Testable, swappable data sources
- **Implementation**: QueueStateRepository, TaskStore, StockStateStore

---

## Technology Stack

### Backend
- **Language**: Python 3.x
- **Framework**: FastAPI (async web framework)
- **Database**: SQLite (async via aiosqlite)
- **AI SDK**: Claude Agent SDK (not direct Anthropic API)
- **Task Queue**: Custom SequentialQueueManager
- **Event System**: Custom EventBus with SQLite persistence
- **Logging**: Loguru

### Frontend
- **Language**: TypeScript
- **Framework**: React 18+
- **Build Tool**: Vite
- **State Management**: Zustand
- **UI Components**: Radix UI + TailwindCSS
- **Real-time**: WebSocket (native browser API)
- **HTTP Client**: Fetch API

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Process Management**: Uvicorn (backend), Vite (frontend)
- **Development**: Hot reload for both frontend and backend

---

## Critical Constraints & Rules

### 1. Queue Execution
- **3 queues execute in PARALLEL**: PORTFOLIO_SYNC, DATA_FETCHER, AI_ANALYSIS
- **Tasks WITHIN each queue execute SEQUENTIALLY**: One-at-a-time per queue
- **Why**: Prevents Claude turn limit exhaustion, database contention

### 2. Claude SDK Usage
- **CRITICAL**: All AI functionality uses Claude Agent SDK only
- **NO direct Anthropic API calls**
- **Authentication**: Claude Code CLI only (no API keys)

### 3. Database Access
- **Rule**: Never access database directly via `db.connection.execute()`
- **Use**: Locked state methods from ConfigurationState
- **Why**: Prevents database contention during long-running processes

### 4. Background Process Limits
- **Maximum 2 persistent processes**: Backend (port 8000) + Frontend (port 3000)
- **Why**: Prevents port conflicts, memory leaks, hard-to-debug state issues

### 5. Modularization Limits
- **Max 350 lines per file**
- **Max 10 methods per class**
- **Single responsibility per file**

---

## Data Flow Examples

### Example 1: Portfolio Scan Request

```
User clicks "Run Portfolio Scan"
    │
    ▼
Frontend: POST /api/portfolio/scan
    │
    ▼
Backend: portfolio_router.py → run_portfolio_scan()
    │
    ▼
Orchestrator.run_portfolio_scan()
    │
    ▼
PortfolioCoordinator.run_portfolio_scan()
    │
    ▼
PortfolioIntelligenceAnalyzer.analyze_portfolio_intelligence()
    │
    ├── Creates task in AI_ANALYSIS queue
    │
    ▼
SequentialQueueManager (AI_ANALYSIS queue)
    │
    ▼
Task Handler: RECOMMENDATION_GENERATION
    │
    ▼
Claude SDK Analysis (2-3 stocks per task)
    │
    ▼
Analysis results stored in database
    │
    ▼
Event: AI_ANALYSIS_COMPLETE published
    │
    ▼
WebSocket broadcast to frontend
    │
    ▼
Frontend updates UI with results
```

### Example 2: Real-time Status Update

```
StatusCoordinator.get_system_status()
    │
    ├── Aggregates from multiple coordinators
    │   ├── SystemStatusCoordinator
    │   ├── AIStatusCoordinator
    │   ├── PortfolioStatusCoordinator
    │   └── SchedulerStatusCoordinator
    │
    ▼
BroadcastCoordinator.broadcast_to_ui()
    │
    ▼
ConnectionManager.broadcast()
    │
    ▼
WebSocket: Send to all connected clients
    │
    ▼
Frontend: WebSocketClient receives message
    │
    ▼
Zustand store updates
    │
    ▼
React components re-render with new data
```

---

## Summary

The Robo Trader system uses a **coordinator-based monolithic architecture** with:

1. **Thin Facade**: RoboTraderOrchestrator delegates to focused coordinators
2. **Event-Driven**: Services communicate via typed events through EventBus
3. **Queue-Based**: Sequential task execution prevents resource exhaustion
4. **Dependency Injection**: Centralized DI eliminates global state
5. **Feature-Based Frontend**: Modular React features with shared components
6. **Real-time Updates**: WebSocket for live status and data updates

This architecture provides:
- ✅ Better performance than microservices (no network overhead)
- ✅ Maintainability through modular coordinators
- ✅ Scalability through queue-based task execution
- ✅ Testability through dependency injection
- ✅ Real-time capabilities through WebSocket

