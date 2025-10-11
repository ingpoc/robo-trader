-- TimescaleDB initialization for Robo Trader
-- Creates hypertables for efficient time-series market data storage

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create market data hypertable for OHLCV data
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open_price DOUBLE PRECISION,
    high_price DOUBLE PRECISION,
    low_price DOUBLE PRECISION,
    close_price DOUBLE PRECISION,
    volume BIGINT,
    source TEXT DEFAULT 'unknown',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable partitioned by time
SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data (time DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data (symbol);

-- Create technical indicators table
CREATE TABLE IF NOT EXISTS technical_indicators (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    value DOUBLE PRECISION,
    period INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('technical_indicators', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_technical_indicators_symbol_time ON technical_indicators (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_name ON technical_indicators (indicator_name);

-- Create tick data table for high-frequency data
CREATE TABLE IF NOT EXISTS tick_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume INTEGER NOT NULL,
    trade_type TEXT, -- 'buy', 'sell', 'unknown'
    exchange TEXT DEFAULT 'NSE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable with smaller chunks for high-frequency data
SELECT create_hypertable('tick_data', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tick_data_symbol_time ON tick_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_tick_data_time ON tick_data (time DESC);

-- Create market statistics table
CREATE TABLE IF NOT EXISTS market_stats (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    vwap DOUBLE PRECISION,  -- Volume Weighted Average Price
    turnover DOUBLE PRECISION,
    volatility DOUBLE PRECISION,
    adv_20 DOUBLE PRECISION,  -- Average Daily Volume (20-day)
    market_cap DOUBLE PRECISION,
    pe_ratio DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('market_stats', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_market_stats_symbol_time ON market_stats (symbol, time DESC);

-- Create continuous aggregates for common queries
-- 1-minute OHLCV bars
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    FIRST(open_price, time) AS open_price,
    MAX(high_price) AS high_price,
    MIN(low_price) AS low_price,
    LAST(close_price, time) AS close_price,
    SUM(volume) AS volume
FROM market_data
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('market_data_1m',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

-- 5-minute OHLCV bars
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    symbol,
    FIRST(open_price, time) AS open_price,
    MAX(high_price) AS high_price,
    MIN(low_price) AS low_price,
    LAST(close_price, time) AS close_price,
    SUM(volume) AS volume
FROM market_data
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy
SELECT add_continuous_aggregate_policy('market_data_5m',
    start_offset => INTERVAL '6 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

-- Create retention policies (keep data for different periods)
-- Keep tick data for 30 days
SELECT add_retention_policy('tick_data', INTERVAL '30 days', if_not_exists => TRUE);

-- Keep raw market data for 1 year
SELECT add_retention_policy('market_data', INTERVAL '1 year', if_not_exists => TRUE);

-- Keep technical indicators for 6 months
SELECT add_retention_policy('technical_indicators', INTERVAL '6 months', if_not_exists => TRUE);

-- Keep market stats for 2 years
SELECT add_retention_policy('market_stats', INTERVAL '2 years', if_not_exists => TRUE);

-- Create compression policies for older data
-- Compress tick data older than 7 days
ALTER TABLE tick_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('tick_data', INTERVAL '7 days', if_not_exists => TRUE);

-- Compress market data older than 30 days
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('market_data', INTERVAL '30 days', if_not_exists => TRUE);

-- Grant permissions (adjust for your application user)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO robo_trader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_internal TO robo_trader;