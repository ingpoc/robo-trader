-- Phase 1 Database Migration: Paper Trading, Claude Agent, Scheduler Tasks
-- This migration creates the foundation for autonomous trading with Claude Agent SDK

-- Paper Trading Accounts (multi-account support)
CREATE TABLE IF NOT EXISTS paper_trading_accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    initial_balance REAL NOT NULL DEFAULT 100000.0,
    current_balance REAL NOT NULL DEFAULT 100000.0,
    buying_power REAL NOT NULL DEFAULT 100000.0,
    strategy_type TEXT NOT NULL DEFAULT 'swing' CHECK(strategy_type IN ('swing', 'options', 'hybrid')),
    risk_level TEXT NOT NULL DEFAULT 'moderate' CHECK(risk_level IN ('conservative', 'moderate', 'aggressive')),
    max_position_size REAL NOT NULL DEFAULT 5.0,
    max_portfolio_risk REAL NOT NULL DEFAULT 10.0,
    is_active BOOLEAN DEFAULT 1,
    month_start_date TEXT NOT NULL DEFAULT date('now'),
    monthly_pnl REAL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Paper Trades (execution log with full audit trail)
CREATE TABLE IF NOT EXISTS paper_trades (
    trade_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    trade_type TEXT NOT NULL CHECK(trade_type IN ('buy', 'sell')),
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    entry_timestamp TEXT NOT NULL,
    exit_timestamp TEXT,
    strategy_rationale TEXT NOT NULL,
    claude_session_id TEXT NOT NULL,
    realized_pnl REAL,
    unrealized_pnl REAL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed', 'stopped_out')),
    stop_loss REAL,
    target_price REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES paper_trading_accounts(account_id)
);

-- Claude Strategy Logs (decision audit trail and learning)
CREATE TABLE IF NOT EXISTS claude_strategy_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    session_type TEXT NOT NULL CHECK(session_type IN ('morning_prep', 'evening_review', 'intraday_analysis')),
    account_type TEXT NOT NULL DEFAULT 'swing' CHECK(account_type IN ('swing', 'options')),
    prompt_template TEXT NOT NULL,
    context_data TEXT NOT NULL, -- JSON: structured context passed to Claude
    claude_response TEXT NOT NULL, -- JSON: full Claude response with reasoning
    tools_used TEXT, -- JSON array: list of tools called
    decision_made TEXT, -- JSON: parsed decisions and actions
    execution_result TEXT, -- JSON: results of executed tools
    what_worked TEXT, -- JSON array: strategies that succeeded
    what_failed TEXT, -- JSON array: strategies that failed
    learnings TEXT, -- JSON: extracted learnings for next session
    token_usage_input INTEGER DEFAULT 0,
    token_usage_output INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    duration_ms INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Scheduler Tasks (sequential queue system)
CREATE TABLE IF NOT EXISTS scheduler_tasks (
    task_id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL CHECK(queue_name IN ('portfolio_sync', 'data_fetcher', 'ai_analysis')),
    task_type TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    payload TEXT NOT NULL, -- JSON: task-specific data
    dependencies TEXT, -- JSON array: task_ids that must complete first
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'retrying')),
    retry_count INTEGER DEFAULT 0 CHECK(retry_count BETWEEN 0 AND 10),
    max_retries INTEGER DEFAULT 3,
    scheduled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Stock Metadata (enriched stock context)
CREATE TABLE IF NOT EXISTS stock_metadata (
    symbol TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT,
    market_cap REAL,
    avg_volume REAL,
    price_52w_high REAL,
    price_52w_low REAL,
    beta REAL,
    pe_ratio REAL,
    fundamental_score REAL,
    technical_score REAL,
    last_news_check TEXT, -- ISO date
    last_earnings_check TEXT, -- ISO date
    last_fundamentals_check TEXT, -- ISO date
    next_earnings_date TEXT,
    earnings_fetch_status TEXT DEFAULT 'pending' CHECK(earnings_fetch_status IN ('pending', 'fetched', 'scheduled')),
    needs_news_update BOOLEAN DEFAULT 1,
    needs_earnings_update BOOLEAN DEFAULT 1,
    needs_fundamentals_update BOOLEAN DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Perplexity Queries (external enrichment cache)
CREATE TABLE IF NOT EXISTS perplexity_queries (
    query_id TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_type TEXT NOT NULL CHECK(query_type IN ('earnings', 'news', 'sector_analysis', 'macro_event', 'fundamentals')),
    response_data TEXT NOT NULL, -- JSON: structured response
    tokens_used INTEGER DEFAULT 0,
    is_cached BOOLEAN DEFAULT 0,
    cache_expires_at TEXT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Claude Token Usage (cost tracking and budget management)
CREATE TABLE IF NOT EXISTS claude_token_usage (
    usage_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES claude_strategy_logs(session_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_paper_trades_account ON paper_trades(account_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status);
CREATE INDEX IF NOT EXISTS idx_paper_trades_timestamp ON paper_trades(entry_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_scheduler_tasks_queue ON scheduler_tasks(queue_name, status);
CREATE INDEX IF NOT EXISTS idx_scheduler_tasks_scheduled ON scheduler_tasks(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_scheduler_tasks_dependencies ON scheduler_tasks(dependencies);
CREATE INDEX IF NOT EXISTS idx_claude_logs_session ON claude_strategy_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_claude_logs_type ON claude_strategy_logs(session_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_perplexity_cache ON perplexity_queries(query_text, cache_expires_at);
CREATE INDEX IF NOT EXISTS idx_stock_metadata_updates ON stock_metadata(last_news_check, last_earnings_check);
CREATE INDEX IF NOT EXISTS idx_token_usage_session ON claude_token_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON claude_token_usage(timestamp DESC);

-- Trigger: Update modified timestamp
CREATE TRIGGER IF NOT EXISTS update_paper_trading_accounts_timestamp
AFTER UPDATE ON paper_trading_accounts
FOR EACH ROW
BEGIN
  UPDATE paper_trading_accounts SET updated_at = CURRENT_TIMESTAMP WHERE account_id = NEW.account_id;
END;

CREATE TRIGGER IF NOT EXISTS update_paper_trades_timestamp
AFTER UPDATE ON paper_trades
FOR EACH ROW
BEGIN
  UPDATE paper_trades SET updated_at = CURRENT_TIMESTAMP WHERE trade_id = NEW.trade_id;
END;

CREATE TRIGGER IF NOT EXISTS update_stock_metadata_timestamp
AFTER UPDATE ON stock_metadata
FOR EACH ROW
BEGIN
  UPDATE stock_metadata SET updated_at = CURRENT_TIMESTAMP WHERE symbol = NEW.symbol;
END;
