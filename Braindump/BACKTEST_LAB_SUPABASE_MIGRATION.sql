-- ============================================================
-- BACKTEST LAB — Supabase Schema Migration
-- Run in Supabase SQL Editor: https://supabase.com/dashboard
-- Project: sigma-quant
-- Created: 2026-04-10
-- ============================================================

-- ============================================================
-- TABLE: backtest_runs
-- Purpose: Store metadata and results for each backtest execution
-- ============================================================
CREATE TABLE IF NOT EXISTS backtest_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  environment_tag TEXT UNIQUE NOT NULL,        -- e.g. "LAB_20240410_abc123"
  job_type        TEXT DEFAULT 'single',        -- "single" | "wfv" | "monte_carlo"
  status          TEXT DEFAULT 'queued',        -- "queued" | "running" | "complete" | "failed"
  config          JSONB NOT NULL DEFAULT '{}',
  symbol          TEXT,
  start_date      TEXT,
  end_date        TEXT,
  initial_balance NUMERIC,
  final_equity    NUMERIC,
  total_trades    INTEGER,
  sharpe_ratio    NUMERIC,
  sortino_ratio   NUMERIC,
  calmar_ratio    NUMERIC,
  max_drawdown_pct NUMERIC,
  win_rate        NUMERIC,
  profit_factor   NUMERIC,
  expectancy      NUMERIC,
  cagr            NUMERIC,
  equity_curve    JSONB DEFAULT '[]',
  benchmarks      JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  completed_at    TIMESTAMPTZ,
  elapsed_seconds NUMERIC,
  triggered_by    TEXT DEFAULT 'manual',
  error_message   TEXT
);

-- ============================================================
-- TABLE: backtest_monte_carlo
-- Purpose: Store Monte Carlo simulation results linked to runs
-- ============================================================
CREATE TABLE IF NOT EXISTS backtest_monte_carlo (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id               UUID REFERENCES backtest_runs(id) ON DELETE CASCADE,
  iterations           INTEGER NOT NULL DEFAULT 1000,
  sharpe_distribution  JSONB DEFAULT '[]',
  equity_fan           JSONB DEFAULT '[]',
  cagr_5th_pct         NUMERIC,
  cagr_50th_pct        NUMERIC,
  cagr_95th_pct        NUMERIC,
  mdd_5th_pct          NUMERIC,
  mdd_50th_pct         NUMERIC,
  mdd_95th_pct         NUMERIC,
  ruin_probability     NUMERIC,
  created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: backtest_wfv_windows
-- Purpose: Store Walk-Forward Validation window results
-- ============================================================
CREATE TABLE IF NOT EXISTS backtest_wfv_windows (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id           UUID REFERENCES backtest_runs(id) ON DELETE CASCADE,
  window_index     INTEGER NOT NULL,
  is_start_date    TEXT,
  is_end_date      TEXT,
  oos_start_date   TEXT,
  oos_end_date     TEXT,
  best_params      JSONB DEFAULT '{}',
  is_sharpe        NUMERIC,
  oos_sharpe       NUMERIC,
  oos_calmar       NUMERIC,
  oos_trades       INTEGER,
  oos_win_rate     NUMERIC,
  oos_equity_curve JSONB DEFAULT '[]',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- backtest_runs indexes
CREATE INDEX IF NOT EXISTS idx_backtest_runs_status ON backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol ON backtest_runs(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);

-- backtest_monte_carlo indexes
CREATE INDEX IF NOT EXISTS idx_mc_run_id ON backtest_monte_carlo(run_id);

-- backtest_wfv_windows indexes
CREATE INDEX IF NOT EXISTS idx_wfv_run_id ON backtest_wfv_windows(run_id);
CREATE INDEX IF NOT EXISTS idx_wfv_window_index ON backtest_wfv_windows(run_id, window_index);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE backtest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_monte_carlo ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_wfv_windows ENABLE ROW LEVEL SECURITY;

-- Permissive policies: anon can read, service role can write
CREATE POLICY "Allow anon read" ON backtest_runs FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon read" ON backtest_monte_carlo FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon read" ON backtest_wfv_windows FOR SELECT TO anon USING (true);
