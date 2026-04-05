# Baysix Technologies — Master Build Plan
**Version:** 4.0
**Date:** 2026-04-04
**Author:** Chief of Staff (Antigravity)
**Status:** ACTIVE — supersedes all prior versions and discussion files

> **What changed from v3:** Quant-centric product philosophy locked. ~100 quantitative capabilities from `BAYSIX_QUANT_CAPABILITY_FRAMEWORK.md` integrated into build phases. Supabase schema expanded with quant analytics tables. Frontend pages reframed around statistical rigour. Hypothesis Board added as first-class feature. Daily Brief upgraded to Quantitative Morning Report format.

---

## 0. Do Not Start Building Until You Have Read Sections 0–6

**Who:** Syafiq M. Zin — solo founder, AI Quantitative Developer, Kuala Lumpur
**What:** Baysix Technologies — production-grade quantitative research system and agentic trading platform
**Why:** (1) Live trading operation across three asset classes. (2) Professional showcase for AI Quant Developer roles — differentiated by genuine statistical rigour, not pretty UI.

---

## 1. Brand & Naming Convention (FINAL)

| Name | What It Is |
|---|---|
| **Baysix** | The software product. The platform. What the world sees. |
| **Sigma** | The proprietary trading strategy engine inside Baysix. B2B zones + SAMTC. |
| **sigma_core** | The compiled `.pyd` binary. The sealed mathematical heart of the Sigma engine. |

**Tagline:** *"Baysix — Powered by the Sigma Strategy Engine"*

**Rules:**
- All user-facing text uses "Baysix"
- "Sigma" appears as the named strategy within Baysix (e.g. "Sigma Engine", "Sigma Zones")
- `sigma_core` is internal only — never in LLM context, never public
- Repos: `baysix` (frontend), `baysix-backend` (FastAPI + LangGraph), `sigma-brain` (HQ, private)
- `sigma-quant` stays live during parallel build (Option C), archived after Baysix Tier 0 launches

---

## 2. Product Philosophy — Quant Centric (LOCKED)

Baysix is not a trading dashboard with AI. It is a **quantitative research platform where AI is the analytical layer, Sigma is the edge, and everything is statistically grounded.**

Every number carries its uncertainty. Every claim has a source and a sample size. Every model has a permutation test result. Every hypothesis lives on a board with a p-value and a status.

**The one-line standard:** If a quant PM at a top fund reviewed any output from this system, they would see a peer and not a hobbyist.

### Design Language (Non-Negotiable)
- Monospace fonts for all numbers — precision signals professionalism
- Color is semantic only: green = statistically significant positive, red = drawdown/failed gate, amber = inconclusive
- Dense information layout — quants are comfortable with data density; wasted whitespace signals lack of depth
- Confidence intervals always visible alongside point estimates
- Bloomberg Terminal aesthetic — dark, sharp, institutional

---

## 3. Hardware & Infrastructure Constraints

| Component | Spec | Implication |
|---|---|---|
| CPU | Intel i7-7700 @ 3.6GHz, 4c/8t | No heavy parallel compute |
| RAM | 40GB | Supports large in-memory datasets |
| GPU | NVIDIA RTX 3060 Ti — 8GB VRAM | Gemma 3 9B Q4 fits (~6-7GB). Cannot run inference + GPU training simultaneously. |
| OS | Windows 10 Home | Ollama native (not Docker). MT5 native. |
| Budget | $0 cloud spend | Supabase free, Groq free, Gemini free, OCI Always Free |
| Storage | Standard SSD | Model artifacts on OCI ARM (200GB free) |

**GPU rule:** Ollama inference and LSTM/LoRA training cannot run simultaneously. ML GPU training is scheduled for windows when Ollama is idle. Enforced by the scheduler.

---

## 4. Current State of Each Project

| Project | Status | Action |
|---|---|---|
| sigma-quant | Live at syafiqmzin-sigma-quant.pages.dev | Run in parallel. Archive after Baysix Tier 0 launches. |
| sigma-brain | Pushed to GitHub (private). HQ. | Stays as-is. Memory, PRD, agents. |
| sigma_core | ✅ COMPLETE — compiled `.pyd` | Sealed. Never exposed. |
| sigma-research | LangGraph skeleton (stubs only) | Superseded by `baysix-backend`. Stop development. |
| sigma-mt5 | MQL5 EA in live deployment | Continues. Polls Supabase for signals. |
| baysix (frontend) | Does not exist yet | New Next.js 15 repo. Build at Phase 8. |
| baysix-backend | Does not exist yet | New Python repo. Build at Phase 0. |

---

## 5. Full System Architecture

### 5.1 The Three Departments

```
┌──────────────────────────────────────────────────────────────────┐
│  FLOOR 3 — LEARNING LAB                                          │
│  Zone outcomes → Feature vectors → XGBoost → Better sizing      │
│  LSTM classifies regime → feeds zone scorer as a feature         │
│  Monte Carlo + WFO validate every model before deployment        │
│  Hypothesis Board tracks every research question with p-values   │
├──────────────────────────────────────────────────────────────────┤
│  FLOOR 2 — RESEARCH DESK                                         │
│  8 AI agents running on schedule + events                        │
│  Macro regime (probability distribution, not just label)         │
│  Bull/Bear debate → CIO synthesis → Quantitative Morning Report  │
├──────────────────────────────────────────────────────────────────┤
│  FLOOR 1 — TRADING DESK                                          │
│  Sigma zones detected → ML-scored → Risk-sized → Executed       │
│  MT5 (Forex/Gold) + Hyperliquid (Crypto) + IBKR (Equities)     │
│  LangGraph writes signals. Brokers read signals. Never direct.  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Infrastructure Diagram

```
YOUR LOCAL MACHINE (Windows)
├── MT5 EA (MQL5)       — polls Supabase trading_signals, executes Forex/XAUUSD
├── IBKR TWS            — equities execution (or Client Portal API on OCI)
├── Ollama (native)     — Gemma 3 9B Q4, GPU inference, no Docker
└── sigma_core.pyd      — sealed, called by MT5 EA and local scripts only

OCI ARM (Always Free — Ubuntu 22.04, always-on)
└── docker-compose.yml:
    ├── fastapi              (port 8000, internal only — never public)
    ├── qdrant               (port 6333, internal only — vector search)
    ├── hyperliquid-adapter  (crypto perps execution, polls Supabase)
    └── ibkr-adapter         (equities, if using Client Portal API)

SUPABASE (Cloud — free tier, universal bus)
├── trading_signals          (broker adapters poll this)
├── zone_outcomes            (THE data flywheel)
├── backtest_runs            (IS/OOS/WFO results per strategy version)
├── risk_metrics_daily       (daily snapshot: Sharpe, VaR, drawdown)
├── monte_carlo_results      (simulation outputs per backtest)
├── hypothesis_tests         (Hypothesis Board records)
├── regime_performance       (regime × instrument × session cross-table)
├── model_versions           (XGBoost + LSTM artifacts, permutation p-values)
├── model_explanations       (SHAP values per zone prediction)
├── agent_logs               (every agent input/output)
├── research_cycles          (cycle history, trigger type, status)
├── sector_state             (current regime probability distribution)
├── checkpoints              (LangGraph PostgresSaver)
├── daily_brief              (Quantitative Morning Report — publicly readable)
└── public_regime_state      (VIEW — anon-readable, computed, no sensitive data)

CLOUDFLARE PAGES (Free CDN)
└── Baysix Next.js 15 frontend
```

### 5.3 LLM Routing (Final)

| Agent | Model | Hosting | Why |
|---|---|---|---|
| Data Agent | No LLM | — | Pure data fetching |
| Macro Researcher | Gemma 3 9B Q4 | Ollama (local) | Structured JSON, private, free |
| Micro Researcher | Gemma 3 9B Q4 | Ollama (local) | Zone probability estimation |
| Sentiment Agent | Gemma 3 2B Q4 | Ollama (local) | Simple classification |
| Risk Manager | Gemma 3 9B Q4 | Ollama (local) | Rule-based + narrative |
| P&L Attribution | Gemma 3 9B Q4 | Ollama (local) | Structured daily report |
| Equity Researcher | Gemini Flash | Cloud | Long PDF context (10-K, transcripts) |
| Peer Reviewer | Groq Llama 3.3 70B | Cloud | Statistical claim validation + logic gate |
| CIO Synthesizer | Groq Llama 3.3 70B | Cloud | Highest-stakes synthesis, low frequency |

**Local-first:** ~80% of calls go to local Gemma 3. Cloud only for highest-stakes reasoning.
**Model tag:** Use `gemma3:9b` until Gemma 4 is confirmed on Ollama (`ollama search gemma`).

### 5.4 Multi-Broker Architecture

```
LangGraph (OCI) → writes signal → Supabase trading_signals
                                         │
              ┌──────────────────────────┼──────────────────────┐
              ▼                          ▼                       ▼
        MT5 EA polls              Hyperliquid adapter      IBKR adapter
        (local machine)           polls (OCI ARM)          polls (local/OCI)
        Forex / XAUUSD            Crypto perpetuals         Equities
```

**Instrument routing:**
- Forex pairs, XAUUSD → MT5
- BTC-PERP, ETH-PERP, SOL-PERP → Hyperliquid
- SPY, QQQ, NVDA, AAPL → IBKR (paper first)

**Rule:** LangGraph never calls broker APIs. It writes a signal to Supabase. Each adapter independently reads and executes. One broker failure does not affect the others.

### 5.5 Docker Placement

```
LOCAL MACHINE (Windows) → NO Docker
├── Ollama: native (Docker+WSL2 GPU passthrough is slower and fragile)
├── MT5: native Windows app
└── Python training scripts: native (GPU access, no container overhead)

OCI ARM (Linux) → YES Docker
└── docker-compose.yml — 4 services, all with restart: always
    ├── fastapi
    ├── qdrant
    ├── hyperliquid-adapter
    └── ibkr-adapter
```

### 5.6 ML Training Architecture

| Model | Purpose | Trains On | Inference On | Trigger |
|---|---|---|---|---|
| **XGBoost Zone Scorer** | Score zone quality in current regime | OCI ARM (CPU sufficient) | OCI ARM | Auto Sunday 2am + manual |
| **LSTM Regime Classifier** | Classify macro regime from time-series | Local (RTX 3060 Ti) | OCI ARM (artifact loaded) | Manual via Command page |
| **Gemma 3 LoRA Fine-Tune** | Domain reasoning on Sigma zones | Local (Unsloth + QLoRA) | Local Ollama | Phase 9+ only |

**All artifacts write to Supabase Storage on completion. Baysix reads from Supabase. You see all results in the UI regardless of where training ran.**

### 5.7 Research Cycle — Three-Trigger Model

```
Trigger       When                             What Runs
─────────     ───────────────────────────────  ─────────────────────────────────────
Scheduled     Market open (9am ET)             Full macro + micro cycle
              Every 4h during market hours     Watchlist refresh + regime check
              Market close                     P&L attribution + daily metrics snapshot
              Sunday 2am                       XGBoost retraining + WFO validation

Event-Driven  VIX > 25                         Risk-Off emergency protocol
              NFP / CPI / FOMC release         Macro event deep-dive
              Earnings surprise ≥ 5%           Equity researcher triggered
              New Sigma zone detected          Zone Inspector + XGBoost scoring
              Kill switch breached             Risk Manager emergency cycle
              Monte Carlo ruin p > 1%          Automatic sizing reduction

On-Demand     User triggers via Baysix UI      Any agent, any scope
```

---

## 6. The Data Flywheel (The Most Critical Component)

Build this before any agent. Before any UI. It runs silently from day one.

```
1.  sigma_core detects B2B zone
2.  Zone Inspector records feature vector → zone_outcomes (status: 'open'):
    {zone_id, instrument, timeframe, direction, zone_age, touch_count,
     atr_ratio, session, macro_regime_at_entry, regime_probability_at_entry,
     sentiment_score, ml_confidence_at_entry, cascade_score, entry_price}
3.  XGBoost scores zone → confidence + SHAP values → trading_signals
4.  Risk Manager: Kelly fraction × regime_confidence → final size
5.  Broker adapter executes
6.  Zone resolves → outcome written (status: 'closed'):
    {outcome, r_multiple, exit_price, duration_bars, slippage, mae, mfe}
7.  Sunday 2am: XGBoost retrains on all outcomes
8.  Permutation test p < 0.05 required to mark deployed = true
9.  Monte Carlo runs on new model: probability_of_ruin must be < 1%
10. OOS efficiency ratio checked: OOS Sharpe / IS Sharpe must be > 0.4
11. New artifact → Supabase Storage → FastAPI loads → models improve
```

**Every trade makes the system smarter. This loop never stops.**

---

## 7. Full Database Schema

Apply ALL tables in a single migration at Phase 0. Design the whole schema now — retrofitting is expensive.

```sql
-- ═══════════════════════════════════════
-- CORE FLYWHEEL
-- ═══════════════════════════════════════

CREATE TABLE zone_outcomes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id text NOT NULL,
    instrument text NOT NULL,
    timeframe text NOT NULL,
    direction text NOT NULL,             -- 'long' | 'short'
    zone_age integer,
    touch_count integer,
    atr_ratio numeric,
    cascade_score numeric,
    session text,                        -- 'london' | 'ny' | 'asia' | 'overlap'
    macro_regime_at_entry text,
    regime_probability_at_entry numeric, -- e.g. 0.61 (confidence in regime label)
    sentiment_score numeric,
    ml_confidence_at_entry numeric,
    entry_price numeric,
    exit_price numeric,
    outcome text,                        -- 'T1_hit' | 'T2_hit' | 'stopped' | 'invalidated'
    r_multiple numeric,
    mae numeric,                         -- max adverse excursion in R
    mfe numeric,                         -- max favorable excursion in R
    duration_bars integer,
    slippage numeric,
    broker text,                         -- 'mt5' | 'hyperliquid' | 'ibkr'
    logic_trace text,                    -- why was this zone scored X?
    opened_at timestamptz,
    closed_at timestamptz
);

-- ═══════════════════════════════════════
-- SIGNAL BUS
-- ═══════════════════════════════════════

CREATE TABLE trading_signals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument text NOT NULL,
    broker text NOT NULL,
    direction text NOT NULL,
    size numeric NOT NULL,
    stop numeric NOT NULL,
    target_1 numeric NOT NULL,
    target_2 numeric,
    ml_confidence numeric,
    ml_confidence_lower numeric,         -- 95% CI lower bound
    ml_confidence_upper numeric,         -- 95% CI upper bound
    kelly_fraction numeric,
    regime_at_signal text,
    regime_probability numeric,
    sigma_zone_id text,
    status text DEFAULT 'pending',       -- 'pending' | 'filled' | 'rejected' | 'cancelled'
    created_at timestamptz DEFAULT now(),
    filled_at timestamptz,
    fill_price numeric
);

-- ═══════════════════════════════════════
-- BACKTESTING & VALIDATION
-- ═══════════════════════════════════════

CREATE TABLE backtest_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_version text NOT NULL,
    run_type text NOT NULL,              -- 'IS' | 'OOS' | 'WFO_anchored' | 'WFO_rolling'
    instrument text,                     -- null = multi-instrument
    regime_filter text,                  -- null = all regimes
    period_start date NOT NULL,
    period_end date NOT NULL,
    n_trades integer,
    -- Core metrics
    sharpe_ratio numeric,
    sortino_ratio numeric,
    calmar_ratio numeric,
    max_drawdown_pct numeric,
    max_drawdown_duration_days integer,
    recovery_factor numeric,
    profit_factor numeric,
    win_rate numeric,
    avg_r_multiple numeric,
    expectancy numeric,
    -- Risk metrics
    var_95 numeric,
    var_99 numeric,
    cvar_95 numeric,
    cvar_99 numeric,
    ulcer_index numeric,
    -- Validation
    permutation_p_value numeric,
    oos_efficiency_ratio numeric,        -- OOS Sharpe / IS Sharpe
    min_backtest_length_met boolean,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE monte_carlo_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_run_id uuid REFERENCES backtest_runs(id),
    n_simulations integer NOT NULL,      -- typically 10000
    median_sharpe numeric,
    p5_sharpe numeric,                   -- 5th percentile (worst case)
    p95_sharpe numeric,                  -- 95th percentile (best case)
    probability_of_ruin numeric,         -- % sims hitting max drawdown limit
    median_max_drawdown numeric,
    p95_max_drawdown numeric,
    created_at timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════
-- RISK METRICS (DAILY SNAPSHOT)
-- ═══════════════════════════════════════

CREATE TABLE risk_metrics_daily (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date date NOT NULL UNIQUE,
    -- Rolling performance
    rolling_sharpe_30d numeric,
    rolling_sharpe_90d numeric,
    rolling_sharpe_180d numeric,
    rolling_sharpe_z_score numeric,      -- z-score vs historical distribution
    -- Drawdown
    current_drawdown_pct numeric,
    drawdown_limit_pct numeric DEFAULT 8.0,
    drawdown_breached boolean DEFAULT false,
    -- Risk
    historical_var_95 numeric,
    historical_var_99 numeric,
    cvar_95 numeric,
    -- Position
    kelly_fraction numeric,
    active_positions integer,
    total_exposure_r numeric,
    created_at timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════
-- HYPOTHESIS BOARD
-- ═══════════════════════════════════════

CREATE TABLE hypothesis_tests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id text NOT NULL UNIQUE,  -- 'H-001', 'H-002', etc.
    hypothesis text NOT NULL,
    proposed_by text DEFAULT 'user',
    status text DEFAULT 'open',          -- 'open' | 'testing' | 'confirmed' | 'rejected'
    null_hypothesis text,
    test_method text,                    -- 't-test' | 'permutation' | 'chi-square' | etc.
    current_n integer DEFAULT 0,
    required_n integer,                  -- min sample for significance
    current_p_value numeric,
    effect_size numeric,                 -- Cohen's d
    significance_threshold numeric DEFAULT 0.05,
    bonferroni_corrected_threshold numeric, -- if multiple testing correction applied
    conclusion text,
    confirmed_at timestamptz,
    rejected_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════
-- REGIME PERFORMANCE CROSS-TABLE
-- ═══════════════════════════════════════

CREATE TABLE regime_performance (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    regime text NOT NULL,
    instrument text NOT NULL,
    session text,                        -- null = all sessions
    timeframe text,                      -- null = all timeframes
    n_trades integer NOT NULL,
    win_rate numeric,
    win_rate_ci_lower numeric,           -- 95% CI
    win_rate_ci_upper numeric,
    avg_r_multiple numeric,
    sharpe_ratio numeric,
    p_value numeric,                     -- is this edge statistically significant?
    effect_size numeric,
    last_updated timestamptz DEFAULT now(),
    UNIQUE(regime, instrument, session, timeframe)
);

-- ═══════════════════════════════════════
-- ML MODEL REGISTRY
-- ═══════════════════════════════════════

CREATE TABLE model_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_type text NOT NULL,            -- 'xgboost_zone_scorer' | 'lstm_regime'
    version integer NOT NULL,
    trained_at timestamptz NOT NULL,
    training_samples integer,
    is_accuracy numeric,                 -- in-sample accuracy
    oos_accuracy numeric,                -- out-of-sample accuracy (the real metric)
    oos_efficiency_ratio numeric,
    permutation_p_value numeric,
    probability_of_ruin numeric,         -- from Monte Carlo on OOS
    ic numeric,                          -- information coefficient
    icir numeric,                        -- IC / std(IC)
    calibration_score numeric,           -- predicted probability vs actual probability
    deployed boolean DEFAULT false,
    deployment_date timestamptz,
    artifact_path text,
    feature_importances jsonb,
    shap_baseline jsonb                  -- baseline SHAP values for this model version
);

-- ═══════════════════════════════════════
-- SHAP EXPLANATIONS (per prediction)
-- ═══════════════════════════════════════

CREATE TABLE model_explanations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_outcome_id uuid REFERENCES zone_outcomes(id),
    model_version_id uuid REFERENCES model_versions(id),
    base_confidence numeric,             -- model's base rate
    final_confidence numeric,
    shap_values jsonb,                   -- {feature_name: shap_contribution}
    top_positive_features jsonb,
    top_negative_features jsonb,
    created_at timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════
-- RESEARCH & AGENTS
-- ═══════════════════════════════════════

CREATE TABLE agent_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id uuid,
    agent_name text NOT NULL,
    model_used text,
    input_summary text,
    output jsonb,                        -- structured JSON — never naked text
    confidence numeric,                  -- agent's self-assessed confidence
    citations jsonb,                     -- [{source, url, date, n, confidence}]
    tokens_used integer,
    latency_ms integer,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE research_cycles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_type text NOT NULL,          -- 'scheduled' | 'event' | 'on_demand'
    trigger_reason text,
    status text DEFAULT 'running',       -- 'running' | 'completed' | 'failed'
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz
);

-- ═══════════════════════════════════════
-- MARKET STATE
-- ═══════════════════════════════════════

CREATE TABLE sector_state (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    macro_regime text NOT NULL,
    regime_probability numeric,          -- point estimate
    regime_prob_risk_on numeric,
    regime_prob_risk_off numeric,
    regime_prob_stagflation numeric,
    regime_prob_deflationary numeric,
    regime_persistence_sessions integer, -- how many sessions in this regime
    active_focus text[],
    sector_rotation text,
    bull_thesis text,
    bear_thesis text,
    cio_verdict text,
    yield_curve_shape text,             -- 'normal' | 'flat' | 'inverted' | 'bear_steepener'
    updated_at timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════
-- PUBLIC VIEWS (anon role access)
-- ═══════════════════════════════════════

CREATE VIEW public_regime_state AS
    SELECT
        macro_regime,
        regime_probability,
        regime_prob_risk_on,
        regime_prob_risk_off,
        regime_prob_stagflation,
        regime_persistence_sessions,
        yield_curve_shape,
        updated_at
    FROM sector_state
    ORDER BY updated_at DESC
    LIMIT 1;

-- ═══════════════════════════════════════
-- QUANTITATIVE MORNING REPORT (public)
-- ═══════════════════════════════════════

CREATE TABLE daily_brief (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_date date NOT NULL UNIQUE,
    -- Regime
    regime text,
    regime_probability numeric,
    regime_p_value numeric,
    regime_n_observations integer,
    yield_curve_shape text,
    regime_persistence_day integer,
    -- Sigma edge (regime-matched, not all-time)
    edge_stats jsonb,                    -- [{instrument, win_rate, win_rate_ci, avg_r, sharpe, n}]
    -- Narrative
    bull_case text,
    bear_case text,
    cio_verdict text,
    -- Hypothesis board summary
    hypotheses_confirmed jsonb,          -- confirmed this week
    hypotheses_testing jsonb,            -- in progress
    hypotheses_rejected jsonb,           -- rejected
    -- Risk posture
    kelly_fraction numeric,
    current_drawdown_pct numeric,
    rolling_sharpe_30d numeric,
    rolling_sharpe_z_score numeric,
    published_at timestamptz DEFAULT now()
);
```

**RLS Policies:**
- `anon`: SELECT on `public_regime_state`, `daily_brief` only
- `authenticated`: SELECT on all read tables
- `admin` (your UID): full access
- Service role (FastAPI): full access via service key, never in frontend

**Keep-alive:**
```sql
SELECT cron.schedule('keep-alive', '0 9 */3 * *', 'SELECT 1');
```

---

## 8. The Baysix Frontend

### Access Tiers

| Tier | Who | Access |
|---|---|---|
| **Public** | Anyone | Home, Research Hub, Daily Brief |
| **Authenticated** | Invited viewers (recruiters, PMs) | + Intelligence, Sigma, Lab, Research Desk, Operations |
| **Admin** | You only | + Command |

### Pages — Quant Centric Design

| Route | Name | Tier | What It Shows |
|---|---|---|---|
| `/` | **Home** | Public | Baysix brand. Live regime probability bar (not just a label). Active hypothesis count. System uptime. CTA to Research Hub and Terminal. |
| `/research` | **Research Hub** | Public | SAMTC paper. Backtest methodology explanation (IS/OOS/WFO). Validated results with confidence intervals. Sigma overview. System architecture. |
| `/daily` | **Quantitative Morning Report** | Public | Full structured report (see Section 9). Published daily by CIO agent. The public showcase. |
| `/intelligence` | **Intelligence Terminal** | Auth | Regime probability distribution chart. Cross-asset factor table (DXY, VIX, 2Y10Y, credit spreads). Bull/Bear debate cards. CIO verdict. Live agent feed. |
| `/sigma` | **Sigma Engine** | Auth | Active zones with ML confidence intervals. Regime-conditional edge table (full cross-table). Zone quality analytics (age, ATR, session, touch count). MAE/MFE charts. SHAP waterfall per zone. |
| `/lab` | **Learning Lab** | Auth | XGBoost model comparison (v1 vs v2 vs v3). Permutation test results. OOS efficiency ratio. Monte Carlo equity curve bands. Calibration curve. IC/ICIR. Feature importances. |
| `/hypotheses` | **Hypothesis Board** | Auth | All hypotheses with p-value, n, status, effect size. Active research. Confirmed edge library. Rejected — shows intellectual honesty. |
| `/operations` | **Operations** | Auth | Agent swarm live status. Research cycle history. Broker adapter heartbeats. System latency. Data quality alerts. |
| `/command` | **Command** | Admin | Agent trigger panel. Kill switch. XGBoost retraining. LSTM training (local machine). Monte Carlo run. Broker adapter status. Raw P&L attribution. |

---

## 9. Quantitative Morning Report Format

Generated daily at market open by CIO agent. Published to `/daily` with no auth required.

```
BAYSIX QUANTITATIVE MORNING REPORT — [DATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MACRO CONTEXT
  SPX: [val] [chg%]    DXY: [val] [chg%]
  VIX: [val]           US10Y: [val]%     2Y10Y: [spread]bp

REGIME CLASSIFICATION                              [confidence]
  Risk-Off:      [pct]%  ████████████░░░░░░░░
  Risk-On:       [pct]%  ████░░░░░░░░░░░░░░░░
  Stagflation:   [pct]%  ███░░░░░░░░░░░░░░░░░
  Yield Curve:   [shape]
  Observations:  [n] cross-asset daily signals
  Significance:  p = [pval] vs null baseline
  Persistence:   Day [n] in current regime

SIGMA EDGE — REGIME-MATCHED STATISTICS (not all-time)
  Instrument    Win Rate  [95% CI]    Avg R   Sharpe   n
  ─────────────────────────────────────────────────────
  XAUUSD        71.3%    [63-79%]    1.43R   3.21     312
  BTC-PERP      64.8%    [58-72%]    1.28R   2.14     187
  SPY            58.2%    [50-66%]    1.12R   1.67      94

HYPOTHESIS BOARD — THIS WEEK
  CONFIRMED: H-043 — BTC edge in Risk-Off regime (p=0.002, n=187)
  TESTING:   H-047 — NFP week edge degradation (p=0.14, n=34 — need ~80)
  REJECTED:  H-039 — London vs NY session edge (p=0.31, n=401)

RISK POSTURE
  Kelly fraction:    [val]x  (capped [val]x conservative)
  Current drawdown:  [pct]%  (limit: [pct]%)
  Rolling 30d Sharpe: [val]  (historical avg: [val])  Z: [val]σ
  Monte Carlo ruin p: [pct]% (threshold: 1%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated by Baysix Research Engine | Powered by Sigma
```

---

## 10. Quant Capability Build Schedule

Full reference: `BAYSIX_QUANT_CAPABILITY_FRAMEWORK.md` — 9 pillars, ~100 capabilities.

### By Phase

**Phase 0 — Foundation**
- Apply full schema (all quant tables designed now)
- Core risk metric functions (Sharpe, Sortino, Calmar, max drawdown) as reusable Python module
- IS/OOS split utility with embargo period enforcement

**Phase 2 — Data Flywheel**
- zone_outcomes records with MAE/MFE fields from day one
- Daily risk_metrics_daily snapshot (drawdown, rolling Sharpe)
- Historical VaR and CVaR computed daily from zone_outcomes returns

**Phase 3 — Research Agents**
- Regime output must include full probability distribution (not just label)
- All agent outputs include confidence field and citations jsonb
- CIO produces Quantitative Morning Report format (daily_brief table)
- Hypothesis Board activated — first hypotheses created manually

**Phase 4 — Equity Researcher**
- IS/OOS framework applied to equity signals
- equity_researcher adds regime-conditional edge stats per equity instrument

**Phase 5 — XGBoost Zone Scorer v1**
- OOS validation (70/30 split, embargo period)
- Permutation test gate (p < 0.05)
- Monte Carlo on OOS: probability_of_ruin < 1% required
- OOS efficiency ratio check: must be > 0.4
- SHAP values computed per prediction → model_explanations table
- Prediction confidence intervals (not just point estimates)
- IC and ICIR computed and stored in model_versions

**Phase 6 — LSTM Regime Classifier**
- Regime output becomes probability distribution, not label
- Calibration curve computed (predicted probability vs actual)
- Regime-conditional performance table (regime_performance) populated

**Phase 7 — P&L Attribution + Quant Analytics**
- Monte Carlo simulation on live outcomes (N=10,000 trades resampled)
- WFO validation applied to Sigma strategy as a whole
- Regime × instrument × session × timeframe cross-table fully populated
- Rolling Sharpe z-score monitored daily
- Live vs backtest drift detection activated
- Hypothesis Board updated with first statistically validated findings
- Multiple hypothesis correction (Bonferroni) applied to hypothesis tests
- MAE/MFE analysis and time-of-day edge analysis computed

**Phase 8 — Frontend (Quant Centric)**
- Bloomberg Terminal aesthetic: dark, monospace numbers, semantic color
- Regime probability bar (not just a label badge)
- Confidence intervals displayed alongside all point estimates
- Hypothesis Board page with full p-value, n, status display
- SHAP waterfall chart per zone in Sigma Engine page
- Monte Carlo equity curve bands in Learning Lab
- IC/ICIR displayed in model comparison panel
- Calibration curve in Learning Lab

**Phase 9 — Advanced Quant (Stretch)**
- Deflated Sharpe Ratio (López de Prado) computation
- HMM regime detection (unsupervised, cross-validates against LSTM)
- Structural break detection (Chow test) on rolling strategy performance
- CSCV + PBO analysis (computationally intensive, run offline)
- Bayesian updating of win rate posterior

---

## 11. Zero-Cost Production Stack

| Layer | Technology | Cost |
|---|---|---|
| Frontend hosting | Cloudflare Pages | $0 |
| Database + Auth + Realtime | Supabase free tier | $0 |
| Vector DB | Qdrant (Docker on OCI) | $0 |
| Python server | OCI ARM Always Free (4 OCPUs, 24GB RAM) | $0 |
| Local LLM | Ollama native + Gemma 3 9B Q4 | $0 |
| Cloud LLM (speed) | Groq free tier (Llama 3.3 70B) | $0 |
| Cloud LLM (context) | Gemini Flash free tier | $0 |
| Economic data | FRED API | $0 |
| Equity data | yfinance | $0 |
| Crypto data | CCXT + Hyperliquid SDK | $0 |
| Document parsing | Docling (pip library) | $0 |
| CI/CD | GitHub Actions | $0 |
| **Total** | | **$0.00/month** |

---

## 12. Repo & Folder Structure

```
baysix-backend/
├── main.py
├── graph/
│   ├── builder.py           # LangGraph StateGraph definition
│   └── state.py             # AgentState schema
├── agents/
│   ├── data_agent.py
│   ├── macro_researcher.py
│   ├── bull_agent.py
│   ├── bear_agent.py
│   ├── micro_researcher.py
│   ├── equity_researcher.py
│   ├── risk_manager.py
│   ├── peer_reviewer.py
│   └── cio_synthesizer.py
├── adapters/
│   ├── mt5_adapter.py
│   ├── hyperliquid.py
│   └── ibkr.py
├── ml/
│   ├── zone_scorer.py       # XGBoost: train, validate, SHAP, IC/ICIR
│   ├── regime_classifier.py # LSTM: train, calibrate, probability output
│   └── validation.py        # WFO, IS/OOS split, Monte Carlo, permutation test
├── quant/
│   ├── metrics.py           # Sharpe, Sortino, Calmar, VaR, CVaR, Ulcer, etc.
│   ├── monte_carlo.py       # Simulation engine (N=10,000 trade resamples)
│   ├── hypothesis.py        # p-value computation, Bonferroni correction, effect size
│   └── attribution.py       # P&L attribution by regime, session, instrument
├── flywheel/
│   └── zone_tracker.py      # Auto-writes zone_outcomes records
├── scheduler/
│   └── triggers.py          # APScheduler three-trigger setup
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 13. Design Principles (Non-Negotiable)

1. **The AI learns to deploy Sigma better. It does not discover strategies.**
2. **No LLM execution.** LLMs write to Supabase. Brokers read from Supabase.
3. **Build the flywheel before the agents.** No data = no ML = no intelligence.
4. **Build the UI last.** Phase 8 only. The UI is a window into a running system.
5. **Sealed core.** `sigma_core` never in LLM context, never public.
6. **PostgresSaver from Phase 0.** Cannot be retrofitted.
7. **RAG for text, SQL for numbers.** Never RAG for zone outcomes, prices, or metrics.
8. **Local-first LLM.** Gemma 3 local for ~80% of calls. Cloud only for CIO and Peer Review.
9. **ML gate is code, not process.** Permutation p < 0.05 enforced in `validation.py`. No manual bypass.
10. **Dual kill switch.** EA hard stop (local) + Supabase `kill_switch` flag (AI side).
11. **Every number has uncertainty.** Point estimates alone are not acceptable outputs anywhere in the system.
12. **Every claim has a citation.** Agent outputs include source, date, n, confidence. No naked statistics.
13. **Hypothesis Board is a first-class feature.** Research questions are tracked formally, not in someone's head.
14. **Monte Carlo before deployment.** Probability of ruin < 1% is a hard deployment gate alongside permutation test.
15. **Quant-centric always.** If a quant PM reviewed any output from this system, they should see a peer.

---

## 14. What NOT to Do

- ❌ Never run Docker on local Windows machine
- ❌ Never use RAG for numerical/structured quant data
- ❌ Never build the frontend before the backend has real data
- ❌ Never deploy a model without permutation test p < 0.05
- ❌ Never deploy a model with Monte Carlo ruin probability > 1%
- ❌ Never output a point estimate without its confidence interval
- ❌ Never make a statistical claim without cited source, date, and n
- ❌ Never run Ollama inference and GPU training simultaneously
- ❌ Never expose FastAPI publicly (always behind OCI firewall or Supabase Edge Functions)
- ❌ Never reference sigma_core in any public documentation or LLM prompt
- ❌ Never push to GitHub without confirming .env is in .gitignore
- ❌ Never use RAGFlow — use Docling
- ❌ Never use Redis/Celery — use APScheduler + Supabase triggers

---

## 15. Immediate Next Actions (Start Here)

**Step 1:** Verify environment
```powershell
ollama --version
ollama list
ollama pull gemma3:9b   # if not already pulled
```

**Step 2:** Get Supabase direct DB URL
- Supabase Dashboard → Settings → Database → Connection String → URI (NOT pooler)
- Save as `SUPABASE_DB_URL=postgresql://...` in `.env`

**Step 3:** Apply Supabase schema
- Run all `CREATE TABLE` statements from Section 7 as one migration
- Apply RLS policies
- Set up keep-alive cron job

**Step 4:** Create `baysix-backend` repo
- Initialize with folder structure from Section 12
- Create `quant/metrics.py` first — this module is used everywhere

**Step 5:** Wire PostgresSaver
```bash
pip show langgraph   # check version first
pip install langgraph-checkpoint-postgres
```

**Step 6:** Build FastAPI skeleton with `/health`, `/trigger`, CORS

**Step 7:** Phase 0 smoke test — trigger LangGraph cycle, confirm checkpoint written to Supabase

---

## 16. Resolved Decisions Log

| Decision | Resolution |
|---|---|
| One app or two | ONE — Baysix. sigma-quant runs in parallel, archived later. |
| Public vs private | Three-tier access: Public / Authenticated / Admin |
| Product philosophy | Quant-centric. Statistical rigour is the product, not the UI. |
| Docker placement | OCI ARM only. No Docker on local Windows. |
| Document parsing | Docling (pip). RAGFlow removed. |
| Event scheduling | APScheduler + Supabase triggers. Redis/Celery removed. |
| Crypto broker | Hyperliquid (not Binance) |
| Equities broker | IBKR — paper account first, Client Portal API |
| XGBoost training location | OCI ARM (CPU sufficient) |
| LSTM training location | Local machine (GPU), inference on OCI |
| UI build order | Phase 8 — after real data exists |
| Branding | Baysix = product. Sigma = strategy engine inside it. |
| Daily Brief format | Quantitative Morning Report — full statistical format |
| Regime output format | Probability distribution (not just a label) |
| Deployment gates | Permutation p < 0.05 AND Monte Carlo ruin < 1% |
| Hypothesis tracking | Formal Hypothesis Board — first-class feature |

---

*Single source of truth. All prior versions and discussion files are superseded.*
*Last updated: 2026-04-04 — Quant-centric layer integrated from BAYSIX_QUANT_CAPABILITY_FRAMEWORK.md*
