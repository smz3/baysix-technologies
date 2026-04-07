-- Supabase Schema — Baysix AI Trading Platform
-- Apply via: Supabase Dashboard > SQL Editor, or MCP apply_migration tool

-- Zone outcome tracking: every deployed B2B zone and its result
CREATE TABLE IF NOT EXISTS zone_outcomes (
    id          BIGSERIAL PRIMARY KEY,
    zone_id     TEXT NOT NULL,
    instrument  TEXT NOT NULL,
    direction   TEXT NOT NULL CHECK (direction IN ('long', 'short')),
    entry_price DECIMAL(18, 8) NOT NULL,
    regime      TEXT NOT NULL,
    tp1_hit     BOOLEAN DEFAULT FALSE,
    tp2_hit     BOOLEAN DEFAULT FALSE,
    tp3_hit     BOOLEAN DEFAULT FALSE,
    invalidated BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- CIO trading context: single-row table polled by MT5 EA every 15 min
CREATE TABLE IF NOT EXISTS trading_context (
    id         INTEGER PRIMARY KEY DEFAULT 1,
    payload    JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent run logs: feeds sigma-quant Swarm Terminal
CREATE TABLE IF NOT EXISTS agent_logs (
    id              BIGSERIAL PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL,
    output_snippet  TEXT,
    run_duration_ms INTEGER DEFAULT 0,
    regime          TEXT DEFAULT 'UNKNOWN',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Daily P&L per instrument
CREATE TABLE IF NOT EXISTS pnl_records (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    instrument  TEXT NOT NULL,
    pnl_usd     DECIMAL(12, 2) NOT NULL,
    num_trades  INTEGER DEFAULT 0,
    regime      TEXT DEFAULT 'UNKNOWN',
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, instrument)
);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at  ON agent_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_name  ON agent_logs (agent_name);
CREATE INDEX IF NOT EXISTS idx_zone_outcomes_instrument ON zone_outcomes (instrument, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pnl_records_date       ON pnl_records (date DESC);
