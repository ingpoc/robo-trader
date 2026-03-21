# Comprehensive Implementation Plan: Industrial-Grade Robo-Trader

This plan aligns the robo-trader repo with recommendations from both Codex and Claude's own analysis (Claude_Analysis.md), fixing identified weaknesses and shifting the architecture toward production-grade reliability.

**Core Shifts:**
1. **LLM as Feature Extractor** (biggest): Transform LLM from "should I buy?" decision-maker to structured feature extractor with deterministic scoring
2. **Reconciliation Infrastructure**: Internal state vs external truth verification
3. **Walk-Forward Evaluation**: Backtesting, shadow-live, divergence tracking
4. **Bug Fixes**: asyncio crashes, hardcoded IDs, silent fallbacks, oversized coordinators, wrong config defaults

---

## PHASE 1: Critical Asyncio Bug Fixes ✅ COMPLETED

**Priority**: P0 — runtime crash risks.

### 1a. Fix `logging_config.py` lines 146-147 ✅

File: `src/core/logging_config.py`

The code called `asyncio.get_event_loop()` at module-level import time. This crashes in Python 3.12+ when no loop is running.

**Fix**: Extracted handler to deferred function `install_asyncio_exception_handler()` called from `src/web/app.py` after the event loop is running, using `asyncio.get_running_loop()`.

### 1b. Fix `safety_layer.py` CircuitBreaker (lines 102, 115) ✅

File: `src/core/safety_layer.py`

`CircuitBreaker.record_failure()` and `can_execute()` called `asyncio.get_event_loop().time()` in non-async methods.

**Fix**: Replaced with `time.monotonic()` — `loop.time()` just delegates to monotonic clock anyway.

### 1c. Fix `kite_connect_service.py` line 992 ✅

**Fix**: `asyncio.get_event_loop()` → `asyncio.get_running_loop()`.

### 1d. Fix `zerodha_oauth_service.py` line 269 ✅

**Fix**: `asyncio.get_event_loop()` → `asyncio.get_running_loop()`.

### 1e. Regression tests ✅

Created `tests/test_asyncio_safety.py` — grep-based test scanning `src/` for any remaining `get_event_loop()` calls.

---

## PHASE 2: Research Ledger — LLM as Feature Extractor ✅ COMPLETED

**This is the biggest architectural shift.** The old system asked Claude "should I buy?" and got back a subjective answer. The new system asks Claude specific factual questions and stores structured features in a research ledger.

### 2a. Feature Schema ✅

Created: `src/models/research_ledger.py`

Pydantic models: `ManagementFeatures`, `FinancialFeatures`, `CatalystFeatures`, `MarketFeatures`, `ResearchLedgerEntry`.

Key features extracted (the "factual questions"):
- `guidance_raised`: Did management raise/lower/maintain guidance? (categorical)
- `dilution_detected`: Was there equity dilution in last quarter? (boolean)
- `promoter_pledge_pct`: Promoter pledge as % of holdings (numeric)
- `promoter_holding_change`: Change in promoter holding QoQ (numeric)
- `institutional_flow`: FII/DII net buy/sell last month (numeric)
- `earnings_surprise_pct`: Actual vs consensus EPS deviation (numeric)
- `debt_equity_trend`: Improving/stable/deteriorating (categorical)
- `revenue_growth_3yr_cagr`: 3-year revenue CAGR (numeric)
- `sector_momentum`: Sector relative strength vs Nifty (numeric)
- `corporate_action`: Any upcoming bonus/split/buyback (categorical)

Each feature is Optional with description. `count_extracted_features()` returns (extracted, total) for confidence calculation.

### 2b. Research Ledger Store ✅

Created: `src/stores/research_ledger_store.py`

SQLite-backed store following `paper_trading_store.py` pattern with `asyncio.Lock()`. Methods: `store_entry()`, `get_latest()`, `get_history()`, `get_all_latest()`, `get_buy_candidates()`.

### 2c. Feature Extractor ✅

Created: `src/services/recommendation_engine/feature_extractor.py`

4 separate extraction prompts (management, financial, catalyst, market), each asking specific factual questions returning structured JSON. Uses `ClaudeSDKClientManager` and `query_with_timeout` per project rules.

**Key architectural change**: Instead of one big prompt asking for a recommendation, we make N small targeted queries. Each returns a typed value. This makes the system auditable and deterministic downstream.

### 2d. Deterministic Scorer ✅

Created: `src/services/recommendation_engine/deterministic_scorer.py`

Named scoring constants with rationale (e.g., `GUIDANCE_RAISED_SCORE = 15`, `AUDITOR_FLAGS_SCORE = -20`). `BUY_THRESHOLD = 40`, `AVOID_THRESHOLD = 0`, `MIN_CONFIDENCE_FOR_BUY = 0.40`.

**Critically, this scorer has no LLM calls.** Given the same features, it always returns the same score. Confidence = % of features extracted (not LLM opinion).

### 2e-2f. Integration with Stock Discovery ✅

Modified: `src/services/paper_trading/stock_discovery.py`

- Replaced 67-stock hardcoded list with `data/nse_universe.json` (~100 Nifty 500 stocks)
- Replaced placeholder `{"recommendation": "HOLD", "confidence": 0.5}` with FeatureExtractor + DeterministicScorer pipeline
- `_score_stocks()` now reads pre-computed scores from feature extraction

### 2g. Config Defaults for Swing Trading ✅

Modified: `src/config.py`

| Setting | Old (day-trading) | New (swing-trading) |
|---------|-------------------|---------------------|
| `stop_loss_percent` | 2.0 | 8.0 |
| `take_profit_percent` | 5.0 | 15.0 |
| `timeframes` | ["5m", "15m", "1h"] | ["1d", "1w"] |
| `ema_periods` | [9, 21, 50] | [21, 50, 200] |
| `max_holding_period_days` | — | 60 (new) |

---

## PHASE 3: Reconciliation Infrastructure ✅ COMPLETED

### 3a. Reconciliation Service ✅

Created: `src/services/reconciliation_service.py`

Recomputes positions from trade history, compares with stored positions, detects P&L drift. Emits `RECONCILIATION_DRIFT` event.

### 3b. Stale Data Guard ✅

Created: `src/services/stale_data_guard.py`

Pre-execution check: price freshness (<60s), market hours, feed health. Returns `StaleDataCheckResult` with `can_trade`, `reason`, `price_age`, `market_open`. Emits `STALE_DATA_BLOCK` event.

### 3c. Trade Lifecycle Store ✅

Created: `src/stores/trade_lifecycle_store.py`

Tracks: `research_decision → intended_order → submitted_order → fill_or_reject`.

### 3d. Fix Hardcoded Account IDs ✅

Modified: `src/core/database_state/paper_trading_state.py`

Added `DEFAULT_ACCOUNT_ID = 1` constant. Replaced all 8 instances of `WHERE id = 1` with parameterized queries.

### 3e. New Event Types ✅

Added to `src/core/event_bus.py`: `RECONCILIATION_DRIFT`, `STALE_DATA_BLOCK`, `TRADE_LIFECYCLE_UPDATE`.

---

## PHASE 4: Walk-Forward Evaluation Framework ✅ COMPLETED

### 4a. Historical Replay Engine ✅

Created: `src/services/evaluation/replay_engine.py`

Replays historical OHLCV through DeterministicScorer using cached features. Returns `ReplayResult` with: `total_pnl`, `max_drawdown`, `sharpe_ratio`, `win_rate`, `profit_factor`.

### 4b. Shadow-Live Mode ✅

Created: `src/services/evaluation/shadow_live.py`

Records shadow decisions without execution. `check_outcomes()` resolves against current prices. `get_shadow_report()` returns `win_rate`, `avg_pnl`.

### 4c. Divergence Tracker ✅

Created: `src/services/evaluation/divergence_tracker.py`

Compares research signals vs execution outcomes. Tracks `block_reasons`, `execution_rate`.

### 4d. API Routes ✅

Created: `src/web/routes/evaluation.py`

- `GET /api/evaluation/divergence` — divergence report
- `GET /api/evaluation/shadow` — shadow-live report
- `GET /api/evaluation/research-ledger` — research ledger entries

---

## PHASE 5: Coordinator Refactoring (Partial) ✅

### 5a. MorningSessionCoordinator (808 → 150 lines) ✅

Split into 6 files in `src/core/coordinators/paper_trading/`:

| File | Lines | Responsibility |
|------|-------|---------------|
| `morning_session_coordinator.py` | 150 | Thin orchestrator |
| `morning_premarket_coordinator.py` | 95 | Watchlist scan, pre-market data |
| `morning_research_coordinator.py` | 106 | Batch research via Perplexity |
| `morning_trade_idea_coordinator.py` | 107 | Trade ideas via Claude SDK |
| `morning_safeguard_coordinator.py` | 97 | Safeguard checks |
| `morning_execution_coordinator.py` | 141 | Trade execution, account resolution |

### 5b. EveningSessionCoordinator (608 → 163 lines) ✅

Split into 4 files:

| File | Lines | Responsibility |
|------|-------|---------------|
| `evening_session_coordinator.py` | 163 | Thin orchestrator |
| `evening_portfolio_review_coordinator.py` | 136 | Prices, metrics, positions |
| `evening_performance_coordinator.py` | 150 | AI insights, watchlist, safeguards |
| `evening_strategy_coordinator.py` | 119 | Strategy analysis, learning |

### 5c. Remaining Oversized Coordinators 🔲 PENDING

| Coordinator | Lines | Status |
|------------|-------|--------|
| `portfolio_analysis_coordinator.py` | 516 | Pending |
| `monthly_analysis_coordinator.py` | 509 | Pending |
| `claude_paper_trading_coordinator.py` | 398 | Pending |
| `stock_discovery_coordinator.py` | 324 | Pending |
| `ai_status_coordinator.py` | 303 | Pending |
| `queue_coordinator.py` | 255 | Pending |
| `broadcast_coordinator.py` | 255 | Pending |

### 5d. Fix Silent Fallbacks ✅

Modified: `src/core/coordinators/status/status_coordinator.py`

Replaced `return {}` on exception with `return {"status": "error", "error": str(e)}`.

---

## PHASE 6: Tests ✅ COMPLETED

| Test File | Coverage |
|-----------|----------|
| `tests/test_asyncio_safety.py` | Grep-based: no `get_event_loop()` in `src/` |
| `tests/test_deterministic_scorer.py` | 10 test cases for scoring rules |
| `tests/test_stale_data_guard.py` | Stale price blocking |
| `tests/test_research_ledger_store.py` | CRUD with in-memory SQLite |
| `tests/test_reconciliation.py` | Drift detection with mocked store |

---

## Summary of Changes

**40 files changed, 3778 insertions, 1439 deletions**

### New Files (22)
- `data/nse_universe.json` — Nifty 500 representative stocks
- `src/models/research_ledger.py` — Structured feature schema
- `src/stores/research_ledger_store.py` — SQLite feature store
- `src/stores/trade_lifecycle_store.py` — Trade lifecycle tracking
- `src/services/recommendation_engine/feature_extractor.py` — LLM feature extraction
- `src/services/recommendation_engine/deterministic_scorer.py` — Rule-based scoring
- `src/services/reconciliation_service.py` — Position reconciliation
- `src/services/stale_data_guard.py` — Pre-execution freshness checks
- `src/services/evaluation/__init__.py` — Evaluation module
- `src/services/evaluation/replay_engine.py` — Historical replay
- `src/services/evaluation/shadow_live.py` — Shadow-live mode
- `src/services/evaluation/divergence_tracker.py` — Signal vs execution tracking
- `src/web/routes/evaluation.py` — Evaluation API routes
- 5 morning sub-coordinators
- 3 evening sub-coordinators
- 5 test files

### Modified Files (18)
- `src/config.py` — Swing trading defaults
- `src/core/logging_config.py` — Deferred asyncio handler
- `src/core/safety_layer.py` — `time.monotonic()` fix
- `src/core/event_bus.py` — 3 new event types
- `src/core/di_registry_paper_trading.py` — New service registrations
- `src/core/database_state/paper_trading_state.py` — `DEFAULT_ACCOUNT_ID`
- `src/core/coordinators/status/status_coordinator.py` — Error reporting
- `src/core/coordinators/paper_trading/morning_session_coordinator.py` — 808→150 lines
- `src/core/coordinators/paper_trading/evening_session_coordinator.py` — 608→163 lines
- `src/services/kite_connect_service.py` — `get_running_loop()` fix
- `src/services/zerodha_oauth_service.py` — `get_running_loop()` fix
- `src/services/paper_trading/stock_discovery.py` — Feature extraction pipeline
- `src/services/recommendation_engine/models.py` — New fields
- `src/web/app.py` — Evaluation routes + asyncio handler

---

## Remaining Work

1. **7 oversized coordinators** still need refactoring (Phase 5c)
2. **Full test suite run** in project venv to verify all tests pass
3. **Health check** to verify backend/frontend startup
4. **UI verification** of Paper Trading and AI Transparency tabs
