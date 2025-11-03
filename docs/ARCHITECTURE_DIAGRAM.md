# Robo-Trader Architecture Diagram

Generated: 2025-11-02

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROBOTRADER APPLICATION                            │
│                      (Coordinator-Based Monolithic Architecture)              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER (React/TS)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Dashboard   │  │  AI Trans-   │  │ System Health│  │ Paper Trading│  │
│  │   Feature    │  │  parency     │  │   Feature    │  │   Feature    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┼──────────────────┼──────────────────┘          │
│                            │                  │                             │
│                    ┌───────▼──────────────────▼────────┐                    │
│                    │      WebSocket Client             │                    │
│                    │   (Real-time Updates)              │                    │
│                    └───────┬───────────────────────────┘                    │
│                            │                                                 │
└────────────────────────────┼─────────────────────────────────────────────────┘
                             │ HTTP/WebSocket
                             │
┌────────────────────────────▼─────────────────────────────────────────────────┐
│                        WEB API LAYER (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application (app.py)                    │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │   Routes    │  │  Middleware │  │ Error Handler│              │   │
│  │  │  Handlers   │  │ (Rate Limit)│  │  (TradingError│              │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘              │   │
│  │         │                 │                 │                      │   │
│  │         └─────────────────┼─────────────────┘                      │   │
│  │                           │                                        │   │
│  │                    ┌──────▼──────────┐                            │   │
│  │                    │  API Endpoints  │                            │   │
│  │                    │  - /api/health  │                            │   │
│  │                    │  - /api/claude/*│                            │   │
│  │                    │  - /api/portfolio│                           │   │
│  │                    │  - /api/backups │                            │   │
│  │                    └──────┬──────────┘                            │   │
│  └────────────────────────────┼────────────────────────────────────────┘   │
│                               │                                              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│                         ORCHESTRATOR LAYER                                     │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │              RoboTraderOrchestrator (Thin Facade)                   │     │
│  │                                                                     │     │
│  │  Responsibilities:                                                  │     │
│  │  - Coordinate coordinator lifecycle                                 │     │
│  │  - Delegate to focused coordinators                                │     │
│  │  - NO business logic                                               │     │
│  │                                                                     │     │
│  │  ┌──────────────────────────────────────────────────────────┐    │     │
│  │  │                  Dependency Container                     │    │     │
│  │  │              (Centralized DI Management)                  │    │     │
│  │  │                                                            │    │     │
│  │  │  - Singleton: ClaudeSDKClientManager                     │    │     │
│  │  │  - Singleton: DatabaseConnection                          │    │     │
│  │  │  - Factory: Coordinators (stateful)                       │    │     │
│  │  │  - Factory: Services (stateful)                            │    │     │
│  │  └──────────────────────────────────────────────────────────┘    │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
┌───────────────▼───┐  ┌────────▼────────┐  ┌──▼──────────────────────┐
│   COORDINATOR     │  │    EVENT BUS    │  │   SEQUENTIAL QUEUE      │
│      LAYER        │  │                 │  │      MANAGER            │
│                   │  │  (Event-Driven  │  │                          │
│                   │  │ Communication)  │  │  ┌────────────────────┐ │
│  ┌─────────────┐  │  │                 │  │  │ PORTFOLIO_SYNC    │ │
│  │SessionCoord │  │  │  EventType enum │  │  │ - Portfolio ops   │ │
│  │ClaudeCoord  │  │  │  - SYSTEM_ERROR │  │  │ - Trading         │ │
│  │QueryCoord   │  │  │  - TRADE_*      │  │  └────────────────────┘ │
│  │TaskCoord    │  │  │  - PORTFOLIO_*  │  │                          │
│  │StatusCoord  │  │  │  - AI_*         │  │  ┌────────────────────┐ │
│  │PortfolioCoord│ │  │                 │  │  │ DATA_FETCHER      │ │
│  │QueueCoord   │  │  │  Services       │  │  │ - Market data      │ │
│  │BroadcastCoord│ │  │  subscribe to   │  │  │ - Analysis        │ │
│  │              │  │  │  events they   │  │  └────────────────────┘ │
│  │ All inherit  │  │  │  handle        │  │                          │
│  │ from         │  │  │                 │  │  ┌────────────────────┐ │
│  │BaseCoordinator│ │  └─────────────────┘  │  │ AI_ANALYSIS       │ │
│  └─────────────┘  │                         │  │ - Claude analysis │ │
│                   │                         │  │ - MUST use queue   │ │
│  Rules:           │                         │  │   (prevents turn  │ │
│  - Max 150 lines  │                         │  │   limit exhaust) │ │
│  - Single resp.   │                         │  └────────────────────┘ │
│  - Delegate to    │                         │                          │
│    services       │                         │  Executes sequentially   │
│  - Emit events    │                         │  (FIFO, one-at-a-time)  │
└───────────────────┘                         └──────────────────────────┘
        │
        │ Delegates to
        │
┌───────▼──────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │PortfolioIntelligence│ │Recommendation   │  │PaperTrading      │          │
│  │Analyzer          │  │Engine            │  │ExecutionService   │          │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬──────────┘          │
│           │                     │                     │                      │
│  ┌────────▼─────────┐  ┌───────▼────────┐  ┌────────▼──────────┐          │
│  │PortfolioService  │  │RiskService     │  │ExecutionService   │          │
│  │                  │  │                 │  │                   │          │
│  │ - Portfolio ops  │  │ - Risk calc    │  │ - Order execution │          │
│  │ - Holdings mgmt  │  │ - Position size │  │ - Trade management│          │
│  └────────┬─────────┘  └────────┬────────┘  └────────┬──────────┘          │
│           │                     │                     │                      │
│           └─────────────────────┼─────────────────────┘                      │
│                                 │                                           │
│  ┌──────────────────────────────▼──────────────────────────┐               │
│  │              LearningEngine / StrategyEvolution          │               │
│  │              AIPlanner / MultiAgentFramework             │               │
│  │                                                          │               │
│  │  All use:                                                │               │
│  │  - ClaudeSDKClientManager (singleton)                    │               │
│  │  - query_with_timeout() helpers                         │               │
│  │  - receive_response_with_timeout() helpers               │               │
│  └──────────────────────────────┬──────────────────────────┘               │
│                                 │                                           │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                    ┌──────────────┼──────────────┐
                    │              │              │
┌───────────────────▼──────┐ ┌───▼──────────┐ ┌─▼──────────────────────┐
│  CLAUDE SDK CLIENT        │ │  DATABASE    │ │   BACKGROUND           │
│      MANAGER              │ │   STATE      │ │   SCHEDULER            │
│                           │ │   MANAGER    │ │                        │
│  ┌─────────────────────┐ │ │              │ │  ┌──────────────────┐ │
│  │ Singleton Pattern   │ │ │  ┌────────┐ │ │  │ Task Processing  │ │
│  │                     │ │ │  │Config  │ │ │  │                  │ │
│  │ get_instance()      │ │ │  │State   │ │ │  │ - Queue tasks    │ │
│  │   └─► get_client() │ │ │  └───┬────┘ │ │  │ - Execute tasks  │ │
│  │                     │ │ │      │      │ │  │ - Retry logic    │ │
│  │ Client Types:       │ │ │  ┌───▼────┐ │ │  │                  │ │
│  │ - trading           │ │ │  │Portfolio│ │ │  │  ┌────────────┐  │ │
│  │ - query             │ │ │  │State    │ │ │  │  │Backup      │  │ │
│  │ - conversation      │ │ │  └───┬────┘ │ │  │  │Scheduler   │  │ │
│  │                     │ │ │      │      │ │  │  └────────────┘  │ │
│  │ Features:           │ │ │  ┌───▼────┐ │ │  └──────────────────┘ │
│  │ - Client reuse      │ │ │  │Analysis │ │ │                      │
│  │ - Health monitoring │ │ │  │State    │ │ │                      │
│  │ - Auto-recovery     │ │ │  └───┬────┘ │ │                      │
│  │                     │ │ │      │      │ │                      │
│  │ All clients use:    │ │ │  ┌───▼────┐ │ │                      │
│  │ - query_with_timeout│ │ │  │News/Earn│ │ │                      │
│  │ - receive_response_ │ │ │  │State    │ │ │                      │
│  │   _with_timeout     │ │ │  └────────┘ │ │                      │
│  └─────────────────────┘ │ │             │ │                      │
│                           │ │  ALL STATE │ │                      │
│                           │ │  MANAGERS  │ │                      │
│                           │ │  USE:      │ │                      │
│                           │ │  - asyncio │ │                      │
│                           │ │    .Lock() │ │                      │
│                           │ │  - async   │ │                      │
│                           │ │    with    │ │                      │
│                           │ │    self._  │ │                      │
│                           │ │    lock:   │ │                      │
│                           │ │            │ │                      │
│                           │ │  Prevents: │ │                      │
│                           │ │  "database │ │                      │
│                           │ │  is locked"│ │                      │
│                           │ │  errors    │ │                      │
│                           │ └────────────┘ │                      │
└───────────────────────────┴────────────────┴──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE LAYER (SQLite)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              DatabaseConnection (Base)                               │   │
│  │                                                                     │   │
│  │  - Async SQLite connection                                         │   │
│  │  - Connection pooling                                              │   │
│  │  - Automatic table creation                                        │   │
│  │  - Backup management (startup/shutdown/periodic)                   │   │
│  │  - Atomic writes (temp file → os.replace())                        │   │
│  │                                                                     │   │
│  │  Tables:                                                            │   │
│  │  - background_tasks_config                                         │   │
│  │  - ai_agents_config                                                │   │
│  │  - global_settings_config                                          │   │
│  │  - ai_prompts_config                                               │   │
│  │  - configuration_backups                                           │   │
│  │  - analysis_history                                                │   │
│  │  - recommendations                                                 │   │
│  │  - portfolio data                                                  │   │
│  │  - news/earnings data                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Architecture Patterns Detail

### 1. Coordinator-Based Monolithic Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (Thin Facade)                     │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │SessionCoord│  │QueryCoord │  │TaskCoord   │            │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
│        │                │               │                    │
│        └────────────────┼───────────────┘                    │
│                         │                                     │
│                  ┌───────▼────────┐                          │
│                  │  Services      │                          │
│                  │  (Business     │                          │
│                  │   Logic)      │                          │
│                  └───────┬────────┘                          │
│                          │                                    │
│                  ┌───────▼────────┐                          │
│                  │  State         │                          │
│                  │  Managers      │                          │
│                  │  (Database)    │                          │
│                  └────────────────┘                          │
└───────────────────────────────────────────────────────────────┘

Rules:
- Orchestrator: Max 300 lines, delegates only
- Coordinators: Max 150 lines, single responsibility
- Services: Business logic implementation
- State: Database operations with locking
```

### 2. Event-Driven Communication

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Coordinator │────────►│  Event Bus   │────────►│  Service     │
│    A         │  emit   │              │ publish │    B         │
└──────────────┘         └──────┬───────┘         └──────────────┘
                                 │
                                 │ subscribe
                                 │
                    ┌────────────▼────────────┐
                    │   EventType enum        │
                    │                         │
                    │ - SYSTEM_ERROR          │
                    │ - TRADE_PLACED          │
                    │ - PORTFOLIO_UPDATED    │
                    │ - AI_ANALYSIS_COMPLETE │
                    │                         │
                    │ Services handle events  │
                    │ they subscribe to       │
                    └─────────────────────────┘

Benefits:
- Loose coupling
- No direct service-to-service calls
- Cross-cutting concerns via events
```

### 3. Sequential Queue Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         SequentialQueueManager                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PORTFOLIO_SYNC Queue                                │  │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐              │  │
│  │  │ T1 │→│ T2 │→│ T3 │→│ T4 │→│ T5 │→ ...         │  │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘              │  │
│  │  Executes: ONE at a time (FIFO)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DATA_FETCHER Queue                                  │  │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐              │  │
│  │  │ T1 │→│ T2 │→│ T3 │→│ T4 │→│ T5 │→ ...         │  │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘              │  │
│  │  Executes: ONE at a time (FIFO)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AI_ANALYSIS Queue (CRITICAL)                       │  │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐              │  │
│  │  │ T1 │→│ T2 │→│ T3 │→│ T4 │→│ T5 │→ ...         │  │
│  │  └────┘ └────┘ └────┘ └────┘ └────┘              │  │
│  │  Executes: ONE at a time (FIFO)                   │  │
│  │                                                     │  │
│  │  Each task analyzes 2-3 stocks                    │  │
│  │  Prevents turn limit exhaustion                   │  │
│  │  (81 stocks = ~40 tasks × 2-3 stocks each)       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Task Types:                                                 │
│  - RECOMMENDATION_GENERATION                                 │
│  - DATA_FETCH                                               │
│  - PORTFOLIO_SYNC                                           │
└──────────────────────────────────────────────────────────────┘
```

### 4. Claude SDK Client Management

```
┌─────────────────────────────────────────────────────────────┐
│         ClaudeSDKClientManager (Singleton)                   │
│                                                              │
│  Instance Management:                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  _instance: Optional[ClaudeSDKClientManager]        │   │
│  │  _lock: asyncio.Lock()                              │   │
│  │                                                      │   │
│  │  get_instance() ──┐                                 │   │
│  │                    │                                 │   │
│  │                    ▼                                 │   │
│  │              get_client(type, options)               │   │
│  │                                                      │   │
│  │  Client Types:                                      │   │
│  │  - trading (with MCP tools)                        │   │
│  │  - query (general queries)                         │   │
│  │  - conversation (conversational)                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Features:                                                   │
│  - Client reuse (singleton pattern)                        │
│  - Health monitoring                                        │
│  - Auto-recovery                                            │
│  - Performance metrics                                      │
│                                                              │
│  Usage Pattern:                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  client_manager = await ClaudeSDKClientManager       │   │
│  │      .get_instance()                                 │   │
│  │  client = await client_manager.get_client(           │   │
│  │      "trading", options                               │   │
│  │  )                                                    │   │
│  │                                                      │   │
│  │  # ALWAYS use timeout helpers                        │   │
│  │  response = await query_with_timeout(                │   │
│  │      client, prompt, timeout=60.0                    │   │
│  │  )                                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 5. Database State Management with Locking

```
┌─────────────────────────────────────────────────────────────┐
│         DatabaseStateManager (Facade)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ConfigurationState                                 │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │  self._lock = asyncio.Lock()                 │  │   │
│  │  │                                              │  │   │
│  │  │  async def get_config(...):                  │  │   │
│  │  │      async with self._lock:  ◄──── CRITICAL  │  │   │
│  │  │          cursor = await self.db.connection    │  │   │
│  │  │              .execute(...)                    │  │   │
│  │  │          # ... process results                │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PortfolioStateManager                               │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │  self._lock = asyncio.Lock()                 │  │   │
│  │  │  (Each state class has its own lock)        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AnalysisStateManager                               │   │
│  │  NewsEarningsStateManager                           │   │
│  │  IntentStateManager                                 │   │
│  │  ApprovalStateManager                               │   │
│  │                                                      │   │
│  │  ALL use same pattern:                              │   │
│  │  - async with self._lock:                           │   │
│  │  - All database operations inside lock              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Why This Matters:                                          │
│  - Prevents "database is locked" errors                     │
│  - SQLite allows only one writer at a time                  │
│  - Concurrent async operations need synchronization         │
│  - Each state class needs its own lock                      │
└──────────────────────────────────────────────────────────────┘
```

### 6. Request Flow Example: Portfolio Analysis

```
User Request
    │
    ▼
┌─────────────────┐
│  FastAPI Route  │  /api/claude/transparency/analyze
│  POST /analyze  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ QueryCoordinator │  process_query()
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│ SequentialQueueManager           │
│                                  │
│ create_task(                     │
│   queue=AI_ANALYSIS,             │
│   type=RECOMMENDATION_GENERATION,│
│   payload={...}                   │
│ )                                │
└────────┬──────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ AI_ANALYSIS Queue               │
│ (Sequential execution)           │
│                                  │
│ Task 1: Analyze 2-3 stocks ────┐│
│ Task 2: Analyze 2-3 stocks     ││
│ Task 3: Analyze 2-3 stocks     ││
│ ...                             ││
│                                 ││
│ Executes ONE at a time         ││
└────────────────────────────────┼┘
         │                       │
         ▼                       │
┌─────────────────────────────────┘
│ Task Handler                    │
│ (PortfolioIntelligenceAnalyzer) │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ ClaudeSDKClientManager          │
│ get_client("trading", options)  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ query_with_timeout()            │
│ (SDK Helper)                    │
│                                  │
│ - Wraps client.query()          │
│ - Wraps client.receive_response()│
│ - Handles timeouts              │
│ - Converts to TradingError      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Claude Agent SDK                │
│ (via Claude Code CLI)           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ ConfigurationState              │
│ store_analysis_history()        │
│                                  │
│ async with self._lock:          │
│   await db.connection.execute() │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Event Bus                       │
│ emit AI_ANALYSIS_COMPLETE       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ BroadcastCoordinator             │
│ (WebSocket broadcast)            │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Frontend                        │
│ (Real-time update)              │
└─────────────────────────────────┘
```

## Key Architectural Principles

### 1. Separation of Concerns
- **Orchestrator**: Lifecycle management only
- **Coordinators**: Service orchestration
- **Services**: Business logic
- **State**: Data persistence

### 2. Dependency Injection
- Centralized container (`di.py`)
- Singleton for expensive resources
- Factory for stateful instances
- No global state

### 3. Event-Driven Communication
- Services communicate via events
- No direct service-to-service calls
- Loose coupling
- Easy to test

### 4. Queue-Based Processing
- Sequential execution for critical operations
- Prevents resource exhaustion
- Fair resource allocation
- Graceful error handling

### 5. Timeout Protection
- All Claude SDK calls use timeout helpers
- Consistent error handling
- Prevents hanging operations

### 6. Database Locking
- All database operations locked
- Prevents "database is locked" errors
- Thread-safe concurrent access

## File Structure Mapping

```
robo-trader/
├── src/
│   ├── main.py                    # Entry point
│   ├── orchestrator.py            # Thin facade
│   ├── core/
│   │   ├── di.py                  # Dependency injection
│   │   ├── event_bus.py           # Event infrastructure
│   │   ├── claude_sdk_client_manager.py  # Client singleton
│   │   ├── sdk_helpers.py         # Timeout helpers
│   │   ├── coordinators/          # Service orchestration
│   │   │   ├── base_coordinator.py
│   │   │   ├── session_coordinator.py
│   │   │   ├── query_coordinator.py
│   │   │   ├── claude_agent_coordinator.py
│   │   │   └── ...
│   │   ├── database_state/        # State management
│   │   │   ├── base.py
│   │   │   ├── configuration_state.py
│   │   │   ├── portfolio_state.py
│   │   │   └── ...
│   │   └── background_scheduler/ # Queue management
│   │       └── queue_manager.py
│   ├── services/                  # Business logic
│   │   ├── portfolio_intelligence_analyzer.py
│   │   ├── recommendation_service.py
│   │   ├── paper_trading_execution_service.py
│   │   └── ...
│   └── web/                       # API layer
│       ├── app.py                # FastAPI application
│       └── routes/                # API endpoints
├── ui/                            # Frontend (React/TS)
│   └── src/
│       ├── features/              # Feature modules
│       └── stores/                # State management
└── docs/                          # Documentation
```

## Architecture Compliance Checklist

✅ **Orchestrator Pattern**
- Thin facade (max 300 lines)
- Delegates to coordinators only
- No business logic

✅ **Coordinator Pattern**
- Max 150 lines per coordinator
- Single responsibility
- Inherit from BaseCoordinator
- Delegate to services

✅ **Service Pattern**
- Business logic implementation
- Use client manager for Claude SDK
- Use timeout helpers

✅ **State Pattern**
- All database operations locked
- Async operations only
- Atomic writes

✅ **Client Management**
- Singleton pattern
- Client reuse
- Timeout protection

✅ **Event Communication**
- Typed events
- EventHandler pattern
- No direct service calls

✅ **Queue Processing**
- Sequential execution
- Task-based processing
- Error handling

## Conclusion

This architecture provides:
- **Modularity**: Clear separation of concerns
- **Testability**: Dependency injection and event-driven
- **Scalability**: Queue-based processing
- **Reliability**: Database locking and timeout protection
- **Maintainability**: Focused coordinators and services

All components follow established patterns and are compliant with the documented architecture guidelines.

