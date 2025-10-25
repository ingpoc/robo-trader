-- ============================================================================
-- PHASE 3: SCHEDULER DATABASE MIGRATION
-- ============================================================================
-- Migration to move scheduler data from file-based to database storage
-- Implements the required database-driven scheduler architecture

-- ============================================================================
-- SCHEDULER TASKS TABLE (replaces scheduler_tasks.json)
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduler_background_tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    task_type VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    execute_at TIMESTAMP NOT NULL,
    interval_seconds INTEGER,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    last_executed TIMESTAMP,
    next_execution TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- STOCK SCHEDULER STATE TABLE (replaces stock_scheduler_state.json)
-- ============================================================================

CREATE TABLE IF NOT EXISTS stock_scheduler_state (
    symbol VARCHAR(20) PRIMARY KEY,
    last_news_check DATE,
    last_earnings_check DATE,
    last_fundamentals_check DATE,
    last_portfolio_update TIMESTAMP,
    needs_fundamentals_recheck BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- STRATEGY LOGS TABLE (replaces strategy_logs/*.json)
-- ============================================================================

CREATE TABLE IF NOT EXISTS strategy_logs (
    id SERIAL PRIMARY KEY,
    strategy_type VARCHAR(50) NOT NULL, -- 'swing_trading' or 'options_trading'
    date DATE NOT NULL,
    what_worked JSONB DEFAULT '[]',
    what_didnt_work JSONB DEFAULT '[]',
    tomorrows_focus JSONB DEFAULT '[]',
    market_observations JSONB DEFAULT '[]',
    trades_executed INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    pnl_realized DECIMAL(15,2) DEFAULT 0.0,
    token_usage JSONB DEFAULT '{"used": 0, "limit": 10000}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(strategy_type, date)
);

-- ============================================================================
-- PERPLEXITY QUERIES TABLE (for query versioning)
-- ============================================================================

CREATE TABLE IF NOT EXISTS perplexity_queries (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    query_type VARCHAR(50) NOT NULL, -- 'news', 'earnings', 'fundamentals'
    query_text TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    date DATE DEFAULT CURRENT_DATE,
    created_by VARCHAR(50) DEFAULT 'system',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, query_type, version)
);

-- ============================================================================
-- PENDING APPROVALS TABLE (for Claude recommendations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pending_approvals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    recommendation VARCHAR(20) NOT NULL CHECK (recommendation IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    fair_value DECIMAL(15,2),
    reasoning TEXT,
    analysis_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours'),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED'))
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Background tasks indexes
CREATE INDEX IF NOT EXISTS idx_scheduler_tasks_active_execute
    ON scheduler_background_tasks(is_active, execute_at ASC)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_scheduler_tasks_type_priority
    ON scheduler_background_tasks(task_type, priority DESC);

-- Stock state indexes
CREATE INDEX IF NOT EXISTS idx_stock_state_news_check
    ON stock_scheduler_state(last_news_check DESC);

CREATE INDEX IF NOT EXISTS idx_stock_state_earnings_check
    ON stock_scheduler_state(last_earnings_check DESC);

CREATE INDEX IF NOT EXISTS idx_stock_state_fundamentals_check
    ON stock_scheduler_state(last_fundamentals_check DESC);

-- Strategy logs indexes
CREATE INDEX IF NOT EXISTS idx_strategy_logs_type_date
    ON strategy_logs(strategy_type, date DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_logs_date
    ON strategy_logs(date DESC);

-- Perplexity queries indexes
CREATE INDEX IF NOT EXISTS idx_perplexity_queries_symbol_type
    ON perplexity_queries(symbol, query_type, version DESC);

CREATE INDEX IF NOT EXISTS idx_perplexity_queries_active
    ON perplexity_queries(is_active, created_at DESC)
    WHERE is_active = TRUE;

-- Pending approvals indexes
CREATE INDEX IF NOT EXISTS idx_pending_approvals_status_expires
    ON pending_approvals(status, expires_at ASC);

CREATE INDEX IF NOT EXISTS idx_pending_approvals_symbol
    ON pending_approvals(symbol, created_at DESC);

-- ============================================================================
-- DEFAULT DATA INSERTION
-- ============================================================================

-- Insert default perplexity queries
INSERT INTO perplexity_queries (symbol, query_type, query_text, version, created_by)
VALUES
    ('DEFAULT', 'news', 'Fetch latest news on [SYMBOL] in the last 24 hours', 1, 'system'),
    ('DEFAULT', 'earnings', 'Fetch latest earnings data, fundamentals, and ratios for [SYMBOL]', 1, 'system'),
    ('DEFAULT', 'fundamentals', 'Fetch current fundamentals, valuation metrics, and growth rates for [SYMBOL]', 1, 'system')
ON CONFLICT (symbol, query_type, version) DO NOTHING;

-- ============================================================================
-- CLEANUP TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_scheduler_tasks_updated_at
    BEFORE UPDATE ON scheduler_background_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_state_updated_at
    BEFORE UPDATE ON stock_scheduler_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategy_logs_updated_at
    BEFORE UPDATE ON strategy_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO robo_trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO robo_trader;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================