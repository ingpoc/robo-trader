-- Migration: Add prompt optimization tables
-- Created: 2025-10-24
-- Purpose: Support Claude's real-time prompt optimization system

-- Store optimized prompts with version control
CREATE TABLE IF NOT EXISTS optimized_prompts (
    id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,  -- 'earnings', 'news', 'fundamentals', 'metrics'
    original_prompt TEXT NOT NULL,
    current_prompt TEXT NOT NULL,  -- Claude's latest optimized version
    quality_score REAL NOT NULL,  -- Claude's satisfaction rating (1-10)
    optimization_version INTEGER DEFAULT 1,  -- How many times optimized
    total_optimizations INTEGER DEFAULT 0,  -- Count of all optimizations
    claude_feedback TEXT,  -- Why current version is better
    session_id TEXT,  -- Session that created this optimization
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_optimized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    avg_quality_rating REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,  -- % of times data met quality threshold
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Track each optimization attempt for full transparency
CREATE TABLE IF NOT EXISTS prompt_optimization_attempts (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,  -- 1, 2, 3 within a session
    prompt_text TEXT NOT NULL,
    data_received TEXT NOT NULL,  -- Perplexity response
    quality_score REAL NOT NULL,
    claude_analysis TEXT,  -- Detailed analysis of what was good/bad
    missing_elements TEXT,  -- JSON array of what Claude needed
    redundant_elements TEXT,  -- JSON array of what was unnecessary
    optimization_time_ms INTEGER,  -- How long the optimization took
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES optimized_prompts(id) ON DELETE CASCADE
);

-- Link prompts to trading sessions for analysis
CREATE TABLE IF NOT EXISTS session_prompt_usage (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    quality_achieved REAL NOT NULL,
    symbols_analyzed TEXT,  -- JSON array of symbols
    trading_decisions_influenced INTEGER DEFAULT 0,  -- How many trades used this data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES optimized_prompts(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_optimized_prompts_type_active ON optimized_prompts(data_type, is_active);
CREATE INDEX IF NOT EXISTS idx_optimization_attempts_prompt ON prompt_optimization_attempts(prompt_id);
CREATE INDEX IF NOT EXISTS idx_session_prompt_usage_session ON session_prompt_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_prompts_last_optimized ON optimized_prompts(last_optimized_at);
CREATE INDEX IF NOT EXISTS idx_optimized_prompts_data_type ON optimized_prompts(data_type);
CREATE INDEX IF NOT EXISTS idx_session_prompt_usage_data_type ON session_prompt_usage(data_type);