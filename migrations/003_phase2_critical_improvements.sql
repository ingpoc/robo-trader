-- ============================================================================
-- PHASE 2: CRITICAL IMPROVEMENTS
-- ============================================================================
-- Migration for critical architectural improvements
-- Adds missing constraints, indexes, and database-driven configuration

-- ============================================================================
-- ADDITIONAL CONSTRAINTS AND INDEXES
-- ============================================================================

-- Add NOT NULL constraints where appropriate
ALTER TABLE scheduler_queues ALTER COLUMN queue_name SET NOT NULL;
ALTER TABLE scheduler_queues ALTER COLUMN queue_type SET NOT NULL;
ALTER TABLE scheduler_queues ALTER COLUMN priority SET NOT NULL;
ALTER TABLE scheduler_queues ALTER COLUMN is_active SET NOT NULL;

ALTER TABLE queue_tasks ALTER COLUMN task_id SET NOT NULL;
ALTER TABLE queue_tasks ALTER COLUMN queue_name SET NOT NULL;
ALTER TABLE queue_tasks ALTER COLUMN task_type SET NOT NULL;
ALTER TABLE queue_tasks ALTER COLUMN priority SET NOT NULL;
ALTER TABLE queue_tasks ALTER COLUMN status SET NOT NULL;
ALTER TABLE queue_tasks ALTER COLUMN payload SET NOT NULL;

ALTER TABLE event_triggers ALTER COLUMN trigger_id SET NOT NULL;
ALTER TABLE event_triggers ALTER COLUMN event_type SET NOT NULL;
ALTER TABLE event_triggers ALTER COLUMN trigger_condition SET NOT NULL;
ALTER TABLE event_triggers ALTER COLUMN is_active SET NOT NULL;

-- Add unique constraints
ALTER TABLE scheduler_queues ADD CONSTRAINT IF NOT EXISTS uk_scheduler_queues_name UNIQUE (queue_name);
ALTER TABLE queue_tasks ADD CONSTRAINT IF NOT EXISTS uk_queue_tasks_task_id UNIQUE (task_id);
ALTER TABLE event_triggers ADD CONSTRAINT IF NOT EXISTS uk_event_triggers_trigger_id UNIQUE (trigger_id);

-- Add foreign key constraints with proper naming
ALTER TABLE queue_tasks ADD CONSTRAINT IF NOT EXISTS fk_queue_tasks_queue_name
    FOREIGN KEY (queue_name) REFERENCES scheduler_queues(queue_name) ON DELETE CASCADE;

ALTER TABLE event_triggers ADD CONSTRAINT IF NOT EXISTS fk_event_triggers_source_queue
    FOREIGN KEY (source_queue) REFERENCES scheduler_queues(queue_name) ON DELETE SET NULL;

ALTER TABLE event_triggers ADD CONSTRAINT IF NOT EXISTS fk_event_triggers_target_queue
    FOREIGN KEY (target_queue) REFERENCES scheduler_queues(queue_name) ON DELETE SET NULL;

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_queue_tasks_queue_status_priority
    ON queue_tasks(queue_name, status, priority DESC);

CREATE INDEX IF NOT EXISTS idx_queue_tasks_status_scheduled
    ON queue_tasks(status, scheduled_at ASC);

CREATE INDEX IF NOT EXISTS idx_queue_tasks_status_created
    ON queue_tasks(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_triggers_active_type
    ON event_triggers(is_active, event_type);

CREATE INDEX IF NOT EXISTS idx_event_triggers_source_active
    ON event_triggers(source_queue, is_active);

-- Partial indexes for active records only
CREATE INDEX IF NOT EXISTS idx_scheduler_queues_active_only
    ON scheduler_queues(queue_name, priority DESC)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_queue_tasks_pending_only
    ON queue_tasks(queue_name, priority DESC, scheduled_at ASC)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_queue_tasks_running_only
    ON queue_tasks(queue_name, started_at ASC)
    WHERE status = 'RUNNING';

CREATE INDEX IF NOT EXISTS idx_event_triggers_active_only
    ON event_triggers(trigger_id, priority DESC)
    WHERE is_active = TRUE;

-- ============================================================================
-- QUEUE METRICS AND MONITORING TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS queue_metrics (
    id SERIAL PRIMARY KEY,
    queue_name VARCHAR(50) NOT NULL REFERENCES scheduler_queues(queue_name),
    metric_date DATE NOT NULL DEFAULT CURRENT_DATE,
    tasks_processed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    average_execution_time DECIMAL(10,3),
    total_execution_time INTEGER DEFAULT 0,
    min_execution_time INTEGER,
    max_execution_time INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(queue_name, metric_date)
);

CREATE TABLE IF NOT EXISTS queue_health_checks (
    id SERIAL PRIMARY KEY,
    queue_name VARCHAR(50) NOT NULL REFERENCES scheduler_queues(queue_name),
    check_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) NOT NULL CHECK (status IN ('HEALTHY', 'WARNING', 'CRITICAL', 'UNKNOWN')),
    response_time_ms INTEGER,
    error_message TEXT,
    last_successful_check TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0
);

-- ============================================================================
-- EVENT ROUTER CONFIGURATION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_router_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_router_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100),
    event_type VARCHAR(50) NOT NULL,
    trigger_id VARCHAR(100),
    source_queue VARCHAR(50),
    target_queue VARCHAR(50),
    action_taken JSONB,
    processing_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- QUEUE COORDINATOR TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS queue_coordinator_state (
    id SERIAL PRIMARY KEY,
    coordinator_id VARCHAR(50) NOT NULL UNIQUE DEFAULT 'main',
    state VARCHAR(20) NOT NULL DEFAULT 'STOPPED' CHECK (state IN ('STARTED', 'STOPPED', 'ERROR')),
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    execution_mode VARCHAR(20) DEFAULT 'SEQUENTIAL' CHECK (execution_mode IN ('SEQUENTIAL', 'CONCURRENT')),
    max_concurrent_queues INTEGER DEFAULT 2,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS queue_execution_history (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100) NOT NULL UNIQUE,
    execution_mode VARCHAR(20) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_queues INTEGER NOT NULL,
    successful_queues INTEGER DEFAULT 0,
    failed_queues INTEGER DEFAULT 0,
    total_tasks INTEGER DEFAULT 0,
    successful_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    total_execution_time INTEGER, -- milliseconds
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ADDITIONAL INDEXES FOR NEW TABLES
-- ============================================================================

-- Queue metrics indexes
CREATE INDEX IF NOT EXISTS idx_queue_metrics_queue_date ON queue_metrics(queue_name, metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_queue_metrics_date ON queue_metrics(metric_date DESC);

-- Queue health checks indexes
CREATE INDEX IF NOT EXISTS idx_queue_health_queue_time ON queue_health_checks(queue_name, check_time DESC);
CREATE INDEX IF NOT EXISTS idx_queue_health_status ON queue_health_checks(status, check_time DESC);

-- Event router logs indexes
CREATE INDEX IF NOT EXISTS idx_event_router_logs_event_type ON event_router_logs(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_router_logs_trigger ON event_router_logs(trigger_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_router_logs_success ON event_router_logs(success, created_at DESC);

-- Queue execution history indexes
CREATE INDEX IF NOT EXISTS idx_queue_execution_start ON queue_execution_history(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_queue_execution_mode ON queue_execution_history(execution_mode, start_time DESC);

-- ============================================================================
-- DEFAULT CONFIGURATION DATA
-- ============================================================================

-- Insert default event router configuration
INSERT INTO event_router_config (config_key, config_value, description)
VALUES
    ('default_retry_policy', '{"max_retries": 3, "backoff_multiplier": 2.0, "initial_delay": 1.0}', 'Default retry policy for failed operations'),
    ('queue_health_check_interval', '{"seconds": 60}', 'How often to perform queue health checks'),
    ('event_processing_timeout', '{"seconds": 30}', 'Timeout for event processing operations'),
    ('max_concurrent_event_processing', '{"count": 5}', 'Maximum concurrent event processing operations')
ON CONFLICT (config_key) DO NOTHING;

-- Insert initial coordinator state
INSERT INTO queue_coordinator_state (coordinator_id, state, execution_mode, max_concurrent_queues)
VALUES ('main', 'STOPPED', 'SEQUENTIAL', 2)
ON CONFLICT (coordinator_id) DO NOTHING;

-- ============================================================================
-- UPDATE EXISTING DATA
-- ============================================================================

-- Update existing queues with better defaults
UPDATE scheduler_queues
SET
    max_concurrent_tasks = CASE
        WHEN queue_type = 'PORTFOLIO_SYNC' THEN 1
        WHEN queue_type = 'DATA_FETCHER' THEN 3
        WHEN queue_type = 'AI_ANALYSIS' THEN 2
        ELSE max_concurrent_tasks
    END,
    timeout_seconds = CASE
        WHEN queue_type = 'PORTFOLIO_SYNC' THEN 300
        WHEN queue_type = 'DATA_FETCHER' THEN 600
        WHEN queue_type = 'AI_ANALYSIS' THEN 900
        ELSE timeout_seconds
    END,
    updated_at = NOW()
WHERE queue_name IN ('portfolio_sync', 'data_fetcher', 'ai_analysis');

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO robo_trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO robo_trader;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================