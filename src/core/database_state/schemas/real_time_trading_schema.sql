-- Real-Time Trading Database Schema
-- Enhances existing paper trading with real-time capabilities

-- Real-time market data storage
CREATE TABLE IF NOT EXISTS real_time_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    last_price REAL NOT NULL,
    change_price REAL,
    change_percent REAL,
    volume INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'kite',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

-- Enhanced order tracking
CREATE TABLE IF NOT EXISTS order_book (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT DEFAULT 'NSE',
    order_type TEXT NOT NULL CHECK (order_type IN ('BUY', 'SELL')),
    product_type TEXT NOT NULL CHECK (product_type IN ('CNC', 'INTRADAY', 'CO', 'OCO')),
    quantity INTEGER NOT NULL,
    price REAL,
    trigger_price REAL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED')),
    validity TEXT DEFAULT 'DAY' CHECK (validity IN ('DAY', 'IOC')),
    variety TEXT DEFAULT 'regular' CHECK (variety IN ('regular', 'amo', 'bo', 'co')),
    disclosed_quantity INTEGER DEFAULT 0,
    filled_quantity INTEGER DEFAULT 0,
    pending_quantity INTEGER DEFAULT 0,
    cancelled_quantity INTEGER DEFAULT 0,
    average_price REAL DEFAULT 0,
    placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    exchange_order_id TEXT,
    exchange_timestamp DATETIME,
    exchange_update_timestamp DATETIME,
    parent_order_id TEXT,
    order_guid TEXT,
    FOREIGN KEY (account_id) REFERENCES paper_trading_account(account_id)
);

-- Real-time position tracking with enhanced P&L
CREATE TABLE IF NOT EXISTS real_time_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT DEFAULT 'NSE',
    product_type TEXT NOT NULL CHECK (product_type IN ('CNC', 'INTRADAY', 'CO', 'OCO')),
    quantity INTEGER NOT NULL,
    buy_quantity INTEGER DEFAULT 0,
    sell_quantity INTEGER DEFAULT 0,
    buy_average_price REAL DEFAULT 0,
    sell_average_price REAL DEFAULT 0,
    last_price REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    realized_pnl REAL DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    pnl_percent REAL DEFAULT 0,
    day_change_price REAL DEFAULT 0,
    day_change_percent REAL DEFAULT 0,
    value REAL DEFAULT 0,
    investment REAL DEFAULT 0,
    margin_used REAL DEFAULT 0,
    span_margin REAL DEFAULT 0,
    exposure_margin REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, symbol, product_type),
    FOREIGN KEY (account_id) REFERENCES paper_trading_account(account_id)
);

-- Kite Connect session management
CREATE TABLE IF NOT EXISTS kite_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    public_token TEXT,
    access_token TEXT,
    refresh_token TEXT,
    enctoken TEXT,
    user_type TEXT,
    email TEXT,
    user_name TEXT,
    user_shortname TEXT,
    avatar_url TEXT,
    broker TEXT DEFAULT 'ZERODHA',
    products TEXT,
    exchanges TEXT,
    active BOOLEAN DEFAULT 1,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES paper_trading_account(account_id)
);

-- Market data subscription management
CREATE TABLE IF NOT EXISTS market_data_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('quote', 'ltp', 'depth', 'ticks')),
    exchange TEXT DEFAULT 'NSE',
    instrument_token TEXT,
    subscription_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_update DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, symbol, data_type, exchange),
    FOREIGN KEY (account_id) REFERENCES paper_trading_account(account_id)
);

-- Trade execution logs for audit trail
CREATE TABLE IF NOT EXISTS trade_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    order_id TEXT,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('PLACE_ORDER', 'MODIFY_ORDER', 'CANCEL_ORDER', 'ORDER_UPDATE', 'POSITION_UPDATE')),
    request_data TEXT,
    response_data TEXT,
    status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'ERROR', 'TIMEOUT')),
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES paper_trading_account(account_id)
);

-- Performance metrics for real-time monitoring
CREATE TABLE IF NOT EXISTS real_time_performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    metric_date DATE NOT NULL,
    total_value REAL DEFAULT 0,
    cash_balance REAL DEFAULT 0,
    invested_amount REAL DEFAULT 0,
    day_pnl REAL DEFAULT 0,
    day_pnl_percent REAL DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    total_pnl_percent REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, metric_date),
    FOREIGN KEY (account_id) REFERENCES paper_trading_account(account_id)
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_real_time_quotes_symbol_timestamp ON real_time_quotes(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_real_time_quotes_created_at ON real_time_quotes(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_book_account_id ON order_book(account_id);
CREATE INDEX IF NOT EXISTS idx_order_book_symbol ON order_book(symbol);
CREATE INDEX IF NOT EXISTS idx_order_book_status ON order_book(status);
CREATE INDEX IF NOT EXISTS idx_order_book_placed_at ON order_book(placed_at DESC);

CREATE INDEX IF NOT EXISTS idx_real_time_positions_account_id ON real_time_positions(account_id);
CREATE INDEX IF NOT EXISTS idx_real_time_positions_symbol ON real_time_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_real_time_positions_updated_at ON real_time_positions(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_kite_sessions_account_id ON kite_sessions(account_id);
CREATE INDEX IF NOT EXISTS idx_kite_sessions_active ON kite_sessions(active);
CREATE INDEX IF NOT EXISTS idx_kite_sessions_expires_at ON kite_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_market_data_subscriptions_account_id ON market_data_subscriptions(account_id);
CREATE INDEX IF NOT EXISTS idx_market_data_subscriptions_symbol ON market_data_subscriptions(symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_subscriptions_active ON market_data_subscriptions(subscription_active);

CREATE INDEX IF NOT EXISTS idx_trade_execution_logs_account_id ON trade_execution_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_execution_logs_order_id ON trade_execution_logs(order_id);
CREATE INDEX IF NOT EXISTS idx_trade_execution_logs_created_at ON trade_execution_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_real_time_performance_metrics_account_id ON real_time_performance_metrics(account_id);
CREATE INDEX IF NOT EXISTS idx_real_time_performance_metrics_date ON real_time_performance_metrics(metric_date DESC);

-- Triggers for automatic timestamp updates
CREATE TRIGGER IF NOT EXISTS update_real_time_quotes_timestamp
    AFTER UPDATE ON real_time_quotes
    BEGIN
        UPDATE real_time_quotes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_order_book_timestamp
    AFTER UPDATE ON order_book
    BEGIN
        UPDATE order_book SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_real_time_positions_timestamp
    AFTER UPDATE ON real_time_positions
    BEGIN
        UPDATE real_time_positions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_kite_sessions_timestamp
    AFTER UPDATE ON kite_sessions
    BEGIN
        UPDATE kite_sessions SET updated_at = CURRENT_TIMESTAMP, last_used_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_market_data_subscriptions_timestamp
    AFTER UPDATE ON market_data_subscriptions
    BEGIN
        UPDATE market_data_subscriptions SET last_update = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_real_time_performance_metrics_timestamp
    AFTER UPDATE ON real_time_performance_metrics
    BEGIN
        UPDATE real_time_performance_metrics SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;