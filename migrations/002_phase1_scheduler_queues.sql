-- ============================================================================
-- PHASE 1: SCHEDULER QUEUES INFRASTRUCTURE
-- ============================================================================
-- Migration for Phase 1 scheduler queue system
-- Adds new tables and columns for advanced queue management

-- ============================================================================
-- SCHEDULER QUEUES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduler_queues (
    id SERIAL PRIMARY KEY,
    queue_name VARCHAR(50) NOT NULL UNIQUE,
    queue_type VARCHAR(20) NOT NULL CHECK (queue_type IN ('PORTFOLIO_SYNC', 'DATA_FETCHER', 'AI_ANALYSIS')),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    is_active BOOLEAN DEFAULT TRUE,
    max_concurrent_tasks INTEGER DEFAULT 1,
    timeout_seconds INTEGER DEFAULT 300,
    retry_policy JSONB DEFAULT '{"max_retries": 3, "backoff_multiplier": 2.0}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- QUEUE TASKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS queue_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    queue_name VARCHAR(50) NOT NULL REFERENCES scheduler_queues(queue_name),
    task_type VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    payload JSONB NOT NULL DEFAULT '{}',
    dependencies JSONB DEFAULT '[]',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING')),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    scheduled_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EVENT TRIGGERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_triggers (
    id SERIAL PRIMARY KEY,
    trigger_id VARCHAR(100) NOT NULL UNIQUE,
    event_type VARCHAR(50) NOT NULL,
    source_queue VARCHAR(50) REFERENCES scheduler_queues(queue_name),
    target_queue VARCHAR(50) REFERENCES scheduler_queues(queue_name),
    trigger_condition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- MODIFY EXISTING TABLES
-- ============================================================================

-- Add last_scheduler_run to portfolio_snapshots table
ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS last_scheduler_run TIMESTAMP;

-- Add tracking columns to holdings table (assuming this represents stocks)
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS last_fundamental_update TIMESTAMP;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS last_news_update TIMESTAMP;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS last_earnings_check TIMESTAMP;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (tracking_status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'));

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Scheduler queues indexes
CREATE INDEX IF NOT EXISTS idx_scheduler_queues_active ON scheduler_queues(is_active, priority DESC);
CREATE INDEX IF NOT EXISTS idx_scheduler_queues_type ON scheduler_queues(queue_type);

-- Queue tasks indexes
CREATE INDEX IF NOT EXISTS idx_queue_tasks_queue_status ON queue_tasks(queue_name, status);
CREATE INDEX IF NOT EXISTS idx_queue_tasks_status_priority ON queue_tasks(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_queue_tasks_scheduled_at ON queue_tasks(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_queue_tasks_created_at ON queue_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_queue_tasks_task_type ON queue_tasks(task_type);

-- Event triggers indexes
CREATE INDEX IF NOT EXISTS idx_event_triggers_active ON event_triggers(is_active);
CREATE INDEX IF NOT EXISTS idx_event_triggers_event_type ON event_triggers(event_type);
CREATE INDEX IF NOT EXISTS idx_event_triggers_source_target ON event_triggers(source_queue, target_queue);

-- Holdings tracking indexes
CREATE INDEX IF NOT EXISTS idx_holdings_tracking_status ON holdings(tracking_status);
CREATE INDEX IF NOT EXISTS idx_holdings_fundamental_update ON holdings(last_fundamental_update);
CREATE INDEX IF NOT EXISTS idx_holdings_news_update ON holdings(last_news_update);
CREATE INDEX IF NOT EXISTS idx_holdings_earnings_check ON holdings(last_earnings_check);

-- ============================================================================
-- INITIAL DATA SEEDING
-- ============================================================================

-- Insert default scheduler queues
INSERT INTO scheduler_queues (queue_name, queue_type, priority, max_concurrent_tasks, timeout_seconds)
VALUES
    ('portfolio_sync', 'PORTFOLIO_SYNC', 10, 1, 300),
    ('data_fetcher', 'DATA_FETCHER', 7, 3, 600),
    ('ai_analysis', 'AI_ANALYSIS', 5, 2, 900)
ON CONFLICT (queue_name) DO NOTHING;

-- Insert default event triggers for cross-queue communication
INSERT INTO event_triggers (trigger_id, event_type, source_queue, target_queue, trigger_condition)
VALUES
    ('portfolio_sync_complete', 'TASK_COMPLETED', 'portfolio_sync', 'data_fetcher', '{"task_types": ["sync_account_balances", "update_positions"]}'),
    ('data_fetcher_complete', 'TASK_COMPLETED', 'data_fetcher', 'ai_analysis', '{"task_types": ["fundamentals_update", "news_monitoring"]}'),
    ('earnings_trigger_ai', 'EARNINGS_ANNOUNCEMENT', 'data_fetcher', 'ai_analysis', '{"symbols": "all"}')
ON CONFLICT (trigger_id) DO NOTHING;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO robo_trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO robo_trader;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================