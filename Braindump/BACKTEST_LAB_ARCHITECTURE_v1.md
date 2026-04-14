# Institutional-Grade Backtesting Pipeline — Architecture Plan v1

> Authored: 2026-04-09 | Status: Approved for implementation (Phase 1-5)

## Context

Build an institutional-grade backtesting pipeline that runs B2B zone backtests from the sigma-quant web app, displays beautiful interactive results (not Jupyter/Streamlit), allows parameter tweaking and retesting, and eventually lets AI agents automate the whole process.

**Key architectural decision:** Python is the ONLY backtesting engine (already built in sigma-crypto). MT5/IBKR are for live execution only. MultiCharts is not used.

## Decisions (Confirmed by Syafiq)
- **Deploy**: Build locally first (localhost:8080), deploy to Cloud Run later
- **First asset**: Both BTCUSDT + XAUUSD simultaneously (build data_loader abstraction for both)
- **Page location**: New `/backtest-lab` route (keep existing `/backtest` dashboard untouched)
- **Scope**: Phase 1-5 (Core pipeline + Monte Carlo + WFV) this round. Phase 6-7 deferred.

---

## What Already Exists (DO NOT REBUILD)

| Component | Location | What It Does |
|-----------|----------|-------------|
| VectorizedBacktester | `sigma-crypto/simulation/engine/vectorized_backtester.py` | Full MTF event-driven backtester (MN1 → M30) |
| TradeManager | `sigma-crypto/core/execution/trade_manager.py` | Position management: SL/TP/BE/trailing stops |
| StrategyOrchestrator | `sigma-crypto/core/strategy/orchestrator.py` | MTF narrative flow, latch-based gating (Gate A/B/Discovery Bridge) |
| RiskCalculator | `sigma-crypto/core/risk/sizing.py` | Fixed-risk %, break-even, trailing stops |
| Reporting | `sigma-crypto/simulation/engine/reporting.py` | QuantStats tearsheets, Plotly trade overlay |
| Supabase Push | `sigma-crypto/scripts/supabase_push.py` | Trade serialization, batch insert, deduplication |
| Dashboard | `sigma-quant/src/components/dashboard/` | HeroStats, EquityCurve, MonthlyHeatmap, TradeTable, VectorAnalysis, etc. |
| FastAPI App | `sigma-research/pipelines/server.py` | `/health`, `/search` endpoints, CORS configured |
| Data Pipelines | `sigma-research/data/pipelines/` | yfinance, FRED, Binance (ccxt) — all working |
| sigma_core | `sigma_core/b2b/` | B2B engine, swing points, zone manager, confluence, zone status |

---

## Architecture — Data Flow

```
sigma-quant (Next.js)              sigma-research (FastAPI)           sigma-crypto (Python Engine)
                                                                     
[Backtest Lab Page]                                                  
  |                                                                  
  POST /api/backtest/run ---------> POST /backtest/run               
  (Next.js API route proxy)           |                              
                                      |-- Creates job in Supabase   
                                      |-- Background task:           
                                      |     import VectorizedBacktester
                                      |     load_data()              
                                      |     run_detection_pipeline() 
                                      |     run_simulation()         
                                      |     push results to Supabase 
                                      |                              
  SSE /api/backtest/stream <------- GET /backtest/stream/{job_id}    
  (progress updates)                                                 
                                                                     
  Supabase Realtime <------------- INSERT into backtest_runs, trades 
  (auto-refresh dashboard)                                           
```

**Key decision: Direct Python import, not HTTP microservice.** sigma-research imports sigma-crypto's VectorizedBacktester directly via sys.path / pip install -e. No HTTP overhead, no serialization, same process.

---

## Phase 1: Python Plumbing (Wire sigma-crypto into sigma-research)

### Files to create/modify:
- `sigma-research/backtest/__init__.py` — new package
- `sigma-research/backtest/runner.py` — wraps VectorizedBacktester with:
  - Progress callback support (emits phase + percentage)
  - Config override injection (DetectionConfig, BacktestConfig, RiskConfig)
  - Data source abstraction (local parquet, ccxt fetch, yfinance)
  - Returns structured result (equity curve, trade list, metrics)
- `sigma-research/backtest/serializer.py` — converts ClosedTrade objects to Supabase dicts
  - Reuse logic from `sigma-crypto/scripts/supabase_push.py`
  - Map ClosedTrade fields to existing `trades` table schema
- `sigma-research/backtest/data_loader.py` — unified data loading:
  - `load_from_parquet(symbol, timeframes)` — existing BTCUSDT parquet data
  - `fetch_from_ccxt(symbol, timeframes, start, end)` — live Binance fetch (crypto)
  - `fetch_from_yfinance(symbol, timeframes, start, end)` — XAUUSD, equities, FX
  - `resample_to_mtf(base_df, target_tfs)` — generate higher TFs from base data
  - Returns: `Dict[str, pd.DataFrame]` (same format VectorizedBacktester expects)
  - **BTCUSDT**: parquet files already exist in `sigma-crypto/data/raw/`
  - **XAUUSD**: fetch via yfinance (GC=F or XAUUSD=X), resample from base TF
- Modify `sigma-research/requirements.txt` — add sigma_core dependency path

### Connection mechanism:
```python
# sigma-research/backtest/runner.py
import sys
sys.path.insert(0, "../sigma-crypto")
sys.path.insert(0, "../sigma_core")

from simulation.engine.vectorized_backtester import VectorizedBacktester, BacktestConfig
from sigma_core.b2b.models.structures import DetectionConfig
```

### Verification:
- From sigma-research dir: `python -c "from backtest.runner import run_backtest; print('OK')"`
- Run a single backtest via Python, verify trades appear in Supabase

---

## Phase 2: FastAPI Endpoints

### Files to create/modify:
- `sigma-research/backtest/router.py` — FastAPI router with endpoints:

```
POST /backtest/run
  Body: { symbol, timeframes, start_date, end_date, initial_balance,
          swing_window, swing_lookback, max_zone_age_bars,
          base_risk_pct, max_open_positions, data_source }
  Returns: { job_id, status: "queued", environment_tag, stream_url }

GET /backtest/stream/{job_id}
  SSE stream: { phase, pct, detail } -> { complete, metrics }

GET /backtest/jobs
  Returns: list of all backtest_runs from Supabase

GET /backtest/{job_id}
  Returns: full result (equity_curve, trades, metrics)
```

- Modify `sigma-research/pipelines/server.py` — mount backtest router
- `sigma-research/backtest/benchmarks.py` — fetch SPY + asset buy-hold + risk-free via yfinance
  - Returns daily return series aligned to backtest date range
  - Stored in backtest_runs.benchmarks JSONB

### Supabase schema additions:
```sql
CREATE TABLE backtest_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  environment_tag TEXT UNIQUE NOT NULL,
  job_type        TEXT DEFAULT 'single',
  status          TEXT DEFAULT 'queued',
  config          JSONB NOT NULL,
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
  equity_curve    JSONB,
  benchmarks      JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  completed_at    TIMESTAMPTZ,
  elapsed_seconds NUMERIC,
  triggered_by    TEXT DEFAULT 'manual',
  error_message   TEXT
);
```

Trades go into existing `trades` table with `environment` = `environment_tag`.

### Verification:
- `curl -X POST localhost:8080/backtest/run -d '{"symbol":"BTCUSDT",...}'`
- `curl localhost:8080/backtest/stream/{job_id}` — watch progress
- Check Supabase: backtest_runs row + trades rows appear

---

## Phase 3: sigma-quant Backtest Lab Page (Configure + Results)

### Files to create:
- `src/app/backtest-lab/page.tsx` — server component, fetches backtest_runs
- `src/components/backtest-lab/BacktestLabClient.tsx` — client orchestrator with tabs
- `src/components/backtest-lab/ConfigPanel.tsx` — form: symbol, dates, detection params (sliders), risk params
- `src/components/backtest-lab/RunButton.tsx` — triggers POST, opens SSE stream
- `src/components/backtest-lab/ProgressPanel.tsx` — SSE consumer, progress bar + log
- `src/components/backtest-lab/RunSelector.tsx` — dropdown of all backtest_runs
- `src/hooks/useBacktestProgress.ts` — EventSource hook for SSE

### New dependencies:
```bash
npm install react-plotly.js plotly.js-dist-min  # ONLY for 3D sensitivity surface
```

### New API routes:
- `src/app/api/backtest/run/route.ts` — proxy POST to sigma-research
- `src/app/api/backtest/stream/[jobId]/route.ts` — proxy SSE from sigma-research

### Modify:
- `src/components/layout/Sidebar.tsx` — add "Backtest Lab" nav item

### Reuse from existing dashboard:
- HeroStats + StatCell, EquityCurve, MonthlyHeatmap, ResultDistribution, TradeTable
- VectorAnalysis, TouchDepthPie, ProtocolAudit
- All Supabase query functions in `src/lib/supabase/queries/`
- `calculateMetrics()` and `calculateEquityCurve()` from `src/lib/metrics.ts`

### Layout:
```
TAB: Configure                      TAB: Results
+----------+----------------+      +------------------------------+
| Config   | Progress       |      | Run Selector dropdown        |
| Panel    | Panel          |      |------------------------------|
|          |                |      | HeroStats (reused)           |
| Symbol   | ####.. 65%     |      | EquityCurve + Benchmark      |
| Dates    | "Simulation    |      |  overlay (SPY + buy-hold)    |
| Params   |  bar 4500/8760"|      | Drawdown (Underwater) chart  |
| [RUN]    |                |      | Rolling Sharpe (12mo window) |
|          |                |      | MonthlyHeatmap (reused)      |
|          |                |      | MAE/MFE Scatter              |
|          |                |      | R-Multiple Distribution      |
|          |                |      | TradeTable (reused)          |
|          |                |      | B2B Analytics (reused)       |
+----------+----------------+      +------------------------------+

TAB: Validation
+----------------------------------------------------------+
| SubTab: Walk-Forward                                      |
|   WFV Timeline (IS/OOS window bars)                      |
|   Stitched OOS Equity Curve                              |
|   Window Table (IS vs OOS Sharpe per window)             |
|----------------------------------------------------------|
| SubTab: Monte Carlo                                       |
|   Equity Fan Chart (50 paths + 5th/50th/95th bands)      |
|   Sharpe Distribution Histogram                          |
|   Confidence Table (5th/50th/95th pct metrics)           |
|----------------------------------------------------------|
| SubTab: Sensitivity                                       |
|   3D Surface Plot (param1 x param2 x Sharpe) [Plotly.js] |
|   + 2D Heatmap below for quick reference                 |
|   Cliff Detector (highlights >50% metric drop)           |
+----------------------------------------------------------+
```

### Visualization Spec

**Results Tab (2D charts):**

| Component | Library | Data Source | Status |
|-----------|---------|-------------|--------|
| `BenchmarkEquityCurve` | Lightweight Charts or Recharts | equity_curve + SPY + asset buy-hold | NEW |
| `UnderwaterChart` | Recharts AreaChart | equity_curve drawdown series | NEW |
| `RollingSharpe` | Recharts LineChart | 252-bar rolling window over returns | NEW |
| `MAEMFEScatter` | Recharts ScatterChart | trades.mae_points vs trades.mfe_points | NEW |
| `RMultipleDistribution` | Recharts BarChart (histogram) | trades.r_multiple binned | NEW |
| `HeroStats` | existing | metrics | Reuse |
| `MonthlyHeatmap` | existing | trades grouped by month | Reuse |
| `TradeTable` | existing | trades | Reuse |

**Validation Tab:**

| Component | Library | Data Source | Status |
|-----------|---------|-------------|--------|
| `EquityFanChart` | Recharts LineChart | 50 MC sample paths | NEW |
| `SharpeDistribution` | Recharts BarChart | MC Sharpe quantiles | NEW |
| `WFVTimeline` | Custom SVG/Recharts | wfv_windows IS/OOS ranges | NEW |
| `StitchedEquityCurve` | Recharts AreaChart | stitched OOS equity | NEW |
| `SensitivitySurface3D` | **Plotly.js** (react-plotly.js) | sensitivity matrix | NEW (only 3D) |
| `SensitivityHeatmap2D` | Recharts or custom SVG | same data, flat view | NEW |

**Benchmark data:** SPY (universal), asset buy-hold (BTCUSDT/XAUUSD), risk-free (^TNX/FRED DGS10).

### Verification:
- Open localhost:3000/backtest-lab
- Configure BTCUSDT D1 2020-2022
- Click Run -> see progress -> see results
- `npm run build` passes

---

## Phase 4: Monte Carlo Engine

### Files to create:
- `sigma-research/backtest/monte_carlo.py` — numpy trade shuffler:
  - 1000 iterations, shuffle trade order
  - Variable slippage per iteration
  - 5% execution drop (random trades skipped)
  - Returns: Sharpe distribution, equity fan (50 sample paths), ruin probability

### sigma-quant components:
- `src/components/backtest-lab/validation/EquityFanChart.tsx`
- `src/components/backtest-lab/validation/SharpeDistribution.tsx`
- `src/components/backtest-lab/validation/ConfidenceTable.tsx`

### Supabase:
```sql
CREATE TABLE backtest_monte_carlo (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id          UUID REFERENCES backtest_runs(id),
  iterations      INTEGER,
  sharpe_distribution JSONB,
  equity_fan      JSONB,
  cagr_5th_pct    NUMERIC,
  mdd_5th_pct     NUMERIC,
  ruin_probability NUMERIC,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Phase 5: Walk-Forward Validation

### Files to create:
- `sigma-research/backtest/wfv_orchestrator.py`:
  - Rolling IS/OOS windows with configurable sizes
  - Grid search over DetectionConfig params per IS window
  - Each window loads fresh data with 2yr warmup for MN1 zone detection
  - Stitches OOS equity curves -> true unbiased performance
  - SSE progress per window

### B2B-specific WFV nuances:
- Zone detection requires 2+ years of historical data before any window for MN1 context
- Zone state is NOT carried across windows (prevents information leakage)
- DetectionConfig optimization targets: swing_window [2-6], min_age_bars [3-20], max_zone_age_bars [1000-10000]
- RiskConfig targets: max_open_positions [3-15], base_risk_pct [0.005-0.02]
- Objective function: Calmar ratio (better than Sharpe for structural strategies with large winning tails)

### sigma-quant components:
- `src/components/backtest-lab/validation/WFVTimeline.tsx`
- `src/components/backtest-lab/validation/StitchedEquityCurve.tsx`
- `src/components/backtest-lab/validation/WindowTable.tsx`

### Supabase:
```sql
CREATE TABLE backtest_wfv_windows (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id          UUID REFERENCES backtest_runs(id),
  window_index    INTEGER,
  is_start_date   TEXT,
  is_end_date     TEXT,
  oos_start_date  TEXT,
  oos_end_date    TEXT,
  best_params     JSONB,
  is_sharpe       NUMERIC,
  oos_sharpe      NUMERIC,
  oos_trades      INTEGER,
  oos_equity_curve JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Phase 6: Parameter Sensitivity Surface (Deferred)

- `sigma-research/backtest/sensitivity.py` — 2D grid sweep
- `SensitivitySurface3D` component (Plotly.js) + `SensitivityHeatmap2D` (Recharts)
- Supabase `backtest_sensitivity` table

---

## Phase 7: AI Agent Pipeline (Deferred)

- `sigma-research/agents/backtest_agent.py` — LangGraph StateGraph
- ConfigGenerator -> BacktestRunner -> GovernanceGate -> Publisher -> Reporter
- Governance thresholds: Sharpe > 0.8, DD < 25%, trades > 30, PF > 1.3
- Supabase `backtest_agent_runs` table

---

## Platform Strategy (Settled)

| Platform | Role | When |
|----------|------|------|
| **Python (sigma-crypto)** | ALL backtesting | Now (already built) |
| **MT5** | Paper/live execution (XAUUSD) | After validation |
| **IBKR** | Paper/live execution (multi-asset) | Future |
| **MultiCharts** | NOT USED | N/A |

---

## Key Files Reference

### Reuse (don't rebuild):
- `sigma-crypto/simulation/engine/vectorized_backtester.py` — core engine
- `sigma-crypto/core/execution/trade_manager.py` — position management
- `sigma-crypto/core/strategy/orchestrator.py` — MTF gating
- `sigma-crypto/core/risk/sizing.py` — position sizing
- `sigma-crypto/simulation/engine/reporting.py` — QuantStats + Plotly
- `sigma-crypto/scripts/supabase_push.py` — Supabase serialization
- `sigma-research/pipelines/server.py` — FastAPI app to extend
- `sigma-quant/src/components/dashboard/DashboardClient.tsx` — dashboard layout
- `sigma-quant/src/lib/metrics.ts` — metric calculations
- `sigma-quant/src/lib/supabase/queries/` — Supabase query patterns

### New files (~20 Python + ~20 TypeScript):
- `sigma-research/backtest/{runner,router,data_loader,serializer,benchmarks,monte_carlo,wfv_orchestrator}.py`
- `sigma-quant/src/app/backtest-lab/page.tsx` + `~15 new components`
