-- ============================================================================
-- ROBO TRADER DATABASE INITIALIZATION SCRIPT
-- ============================================================================
-- This script initializes the database schema for all microservices
-- Executed automatically when PostgreSQL container starts

-- ============================================================================
-- PORTFOLIO SERVICE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    quantity INT NOT NULL DEFAULT 0,
    avg_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    current_value DECIMAL(12, 2) NOT NULL DEFAULT 0,
    pnl DECIMAL(12, 2) NOT NULL DEFAULT 0,
    pnl_percentage DECIMAL(5, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_value DECIMAL(15, 2) NOT NULL,
    cash_balance DECIMAL(15, 2) NOT NULL,
    invested_amount DECIMAL(15, 2) NOT NULL,
    pnl DECIMAL(15, 2) NOT NULL,
    pnl_percentage DECIMAL(5, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
    transaction_date TIMESTAMP DEFAULT NOW(),
    order_id VARCHAR(50)
);

-- ============================================================================
-- RISK MANAGEMENT SERVICE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS risk_limits (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    max_position_size INT NOT NULL,
    max_loss_percentage DECIMAL(5, 2) NOT NULL,
    stop_loss_percentage DECIMAL(5, 2) NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stop_loss_triggers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    stop_loss_price DECIMAL(10, 2) NOT NULL,
    current_price DECIMAL(10, 2),
    quantity INT NOT NULL,
    triggered_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'TRIGGERED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    exposure_percentage DECIMAL(5, 2) NOT NULL,
    approved BOOLEAN DEFAULT FALSE,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EXECUTION SERVICE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PLACED', 'FILLED', 'PARTIALLY_FILLED', 'REJECTED', 'CANCELLED')),
    order_type VARCHAR(10) NOT NULL CHECK (order_type IN ('BUY', 'SELL')),
    broker_order_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS executions (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL REFERENCES orders(order_id),
    symbol VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    filled_quantity INT DEFAULT 0,
    filled_price DECIMAL(10, 2),
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_history (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2),
    status VARCHAR(20) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ANALYTICS SERVICE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS screening_results (
    id SERIAL PRIMARY KEY,
    screening_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    score DECIMAL(5, 2),
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fundamental_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    pe_ratio DECIMAL(8, 2),
    market_cap BIGINT,
    revenue BIGINT,
    net_profit BIGINT,
    debt_to_equity DECIMAL(5, 2),
    roe DECIMAL(5, 2),
    analysis_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS earnings (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    quarter VARCHAR(10),
    year INT,
    announcement_date DATE,
    results_date DATE,
    eps DECIMAL(8, 2),
    revenue BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS news_feed (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    headline TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    sentiment VARCHAR(20) CHECK (sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')),
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- RECOMMENDATION SERVICE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD')),
    reason TEXT,
    target_price DECIMAL(10, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approval_queue (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(50) NOT NULL REFERENCES recommendations(recommendation_id),
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,
    submitted_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    approved_by VARCHAR(100)
);

-- ============================================================================
-- TASK SCHEDULER SERVICE SCHEMA
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    execute_at TIMESTAMP NOT NULL,
    interval_seconds INT,
    is_active BOOLEAN DEFAULT TRUE,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_executed TIMESTAMP,
    next_execution TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_executions (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL REFERENCES scheduled_tasks(task_id),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT')),
    error_message TEXT,
    duration_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_history (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    executed_at TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    duration_ms INT,
    result_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ALERT AND NOTIFICATION SERVICE SCHEMA (Phase 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL UNIQUE,
    rule_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20),
    condition_type VARCHAR(50) NOT NULL,
    threshold DECIMAL(10, 2),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS active_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL UNIQUE,
    rule_id VARCHAR(50) NOT NULL REFERENCES alert_rules(rule_id),
    symbol VARCHAR(20),
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL,
    rule_id VARCHAR(50),
    message TEXT,
    severity VARCHAR(20),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- LEARNING SERVICE SCHEMA (Phase 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS performance_history (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(50),
    period_date DATE NOT NULL,
    total_return DECIMAL(8, 2),
    annualized_return DECIMAL(8, 2),
    max_drawdown DECIMAL(8, 2),
    sharpe_ratio DECIMAL(5, 2),
    trades_count INT,
    win_rate DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_data (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(50),
    feature_set VARCHAR(100),
    label VARCHAR(50),
    training_date DATE,
    accuracy DECIMAL(5, 2),
    precision DECIMAL(5, 2),
    recall DECIMAL(5, 2),
    f1_score DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);
CREATE INDEX IF NOT EXISTS idx_holdings_updated_at ON holdings(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_snapshots_date ON portfolio_snapshots(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_executions_order_id ON executions(order_id);

CREATE INDEX IF NOT EXISTS idx_screening_symbol ON screening_results(symbol);
CREATE INDEX IF NOT EXISTS idx_screening_date ON screening_results(screening_date DESC);

CREATE INDEX IF NOT EXISTS idx_fundamental_symbol ON fundamental_analysis(symbol);

CREATE INDEX IF NOT EXISTS idx_earnings_symbol ON earnings(symbol);
CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings(announcement_date DESC);

CREATE INDEX IF NOT EXISTS idx_news_symbol ON news_feed(symbol);
CREATE INDEX IF NOT EXISTS idx_news_date ON news_feed(published_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendations_status ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recommendations_symbol ON recommendations(symbol);

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON scheduled_tasks(is_active, execute_at);

CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_status ON task_executions(status);

CREATE INDEX IF NOT EXISTS idx_alerts_severity ON active_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON active_alerts(acknowledged);

-- ============================================================================
-- FUNDAMENTAL ANALYSIS SCHEMA EXTENSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS fundamental_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    analysis_date DATE NOT NULL,
    revenue_growth_yoy DECIMAL(8, 2),
    revenue_growth_qoq DECIMAL(8, 2),
    earnings_growth_yoy DECIMAL(8, 2),
    earnings_growth_qoq DECIMAL(8, 2),
    gross_margin DECIMAL(5, 2),
    operating_margin DECIMAL(5, 2),
    net_margin DECIMAL(5, 2),
    roe DECIMAL(8, 2),
    roa DECIMAL(8, 2),
    debt_to_equity DECIMAL(8, 2),
    current_ratio DECIMAL(8, 2),
    cash_to_debt DECIMAL(8, 2),
    pe_ratio DECIMAL(8, 2),
    peg_ratio DECIMAL(8, 2),
    pb_ratio DECIMAL(8, 2),
    ps_ratio DECIMAL(8, 2),
    fundamental_score INTEGER,
    investment_recommendation VARCHAR(50),
    recommendation_confidence INTEGER,
    fair_value_estimate DECIMAL(12, 2),
    growth_sustainable BOOLEAN,
    competitive_advantage TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, analysis_date)
);

CREATE TABLE IF NOT EXISTS fundamental_details (
    id SERIAL PRIMARY KEY,
    fundamental_metrics_id INTEGER NOT NULL REFERENCES fundamental_metrics(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    analysis_date DATE NOT NULL,
    revenue_trend TEXT,
    earnings_trend TEXT,
    margin_trend TEXT,
    debt_assessment TEXT,
    liquidity_assessment TEXT,
    valuation_assessment TEXT,
    growth_catalysts TEXT,
    industry_tailwinds TEXT,
    industry_headwinds TEXT,
    key_risks TEXT,
    execution_risks TEXT,
    market_risks TEXT,
    regulatory_risks TEXT,
    key_strengths TEXT,
    key_concerns TEXT,
    investment_thesis TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE earnings ADD COLUMN IF NOT EXISTS revenue_growth_yoy DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS revenue_growth_qoq DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS earnings_growth_yoy DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS earnings_growth_qoq DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS gross_margin DECIMAL(5, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS operating_margin DECIMAL(5, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS net_margin DECIMAL(5, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS roe DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS roa DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS debt_to_equity DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS pe_ratio DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS peg_ratio DECIMAL(8, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS valuation_assessment TEXT;
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS fair_value_estimate DECIMAL(12, 2);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS fundamental_score INTEGER;
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS investment_recommendation VARCHAR(50);
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS recommendation_confidence INTEGER;
ALTER TABLE earnings ADD COLUMN IF NOT EXISTS investment_thesis TEXT;

ALTER TABLE news_feed ADD COLUMN IF NOT EXISTS article_type VARCHAR(50);
ALTER TABLE news_feed ADD COLUMN IF NOT EXISTS news_category VARCHAR(50);
ALTER TABLE news_feed ADD COLUMN IF NOT EXISTS impact_score DECIMAL(3, 2);
ALTER TABLE news_feed ADD COLUMN IF NOT EXISTS relevance_score DECIMAL(3, 2);
ALTER TABLE news_feed ADD COLUMN IF NOT EXISTS sentiment_analysis VARCHAR(20);
ALTER TABLE news_feed ADD COLUMN IF NOT EXISTS key_points TEXT;

CREATE INDEX IF NOT EXISTS idx_fundamental_metrics_symbol ON fundamental_metrics(symbol);
CREATE INDEX IF NOT EXISTS idx_fundamental_metrics_date ON fundamental_metrics(analysis_date DESC);
CREATE INDEX IF NOT EXISTS idx_fundamental_metrics_score ON fundamental_metrics(fundamental_score DESC);
CREATE INDEX IF NOT EXISTS idx_fundamental_metrics_symbol_date ON fundamental_metrics(symbol, analysis_date DESC);

CREATE INDEX IF NOT EXISTS idx_fundamental_details_metrics ON fundamental_details(fundamental_metrics_id);
CREATE INDEX IF NOT EXISTS idx_fundamental_details_symbol ON fundamental_details(symbol);

CREATE INDEX IF NOT EXISTS idx_earnings_growth_yoy ON earnings(revenue_growth_yoy);
CREATE INDEX IF NOT EXISTS idx_earnings_score ON earnings(fundamental_score);

CREATE INDEX IF NOT EXISTS idx_news_type ON news_feed(article_type);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_feed(sentiment_analysis);

-- ============================================================================
-- INITIALIZATION COMPLETE
-- ============================================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO robo_trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO robo_trader;
