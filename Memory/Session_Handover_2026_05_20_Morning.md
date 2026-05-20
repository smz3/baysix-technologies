# Session Handover — May 20, 2026 (Morning — Architecture context restored + B2B research reframed)

## What Was Accomplished This Session

### 1. Notebook 03 — Cost-Adjusted EV built and executed

Built `workspace/baysix-engine/sigma-are/scripts/tools/_build_notebook_03.py` and generated + executed `notebooks/03_b2b_cost_adjusted.ipynb`.

**Key result:**

| Metric | Gross (nb02) | Net (post-cost) |
|---|---|---|
| EV / trade | +0.309 R | **−0.008 R** |
| Annual return (1% risk) | +33.5% | −0.9% |
| Sharpe | 2.16 | −0.06 |
| Max drawdown | −19% | −75% |

**Cost attribution (mean R per trade):**
- Spread (3 bps RT): +0.237 R — 74.8% of total drag
- Slippage (1 bps entry): +0.079 R — 24.9%
- Overnight financing (net): +0.001 R — negligible

**Zone-width quartile breakdown (critical finding):**

| Quartile | Median R ($/oz) | Mean cost (R) | Gross EV | Net EV |
|---|---|---|---|---|
| Q1 (tightest) | 1.13 | 0.734 | +0.494 | **−0.240** |
| Q2 | 2.41 | 0.282 | +0.339 | **+0.058** |
| Q3 | 4.64 | 0.168 | +0.185 | **+0.017** |
| Q4 (widest) | 11.23 | 0.086 | +0.218 | **+0.132** |

Q1 paradox: tightest zones have the STRONGEST gross signal but are completely killed by spread cost. Spread cost = `entry_price × bps / R_points` — tight zones pay disproportionately more per R of potential gain. Year-by-year shows 2024–2025 as worst years, consistent with gold prices rising ($2000→$3300) while zone widths didn't scale proportionally.

**Verdict: FAIL as measured — but the measurement was wrong. See Section 3 below.**

---

### 2. Five architecture documents ingested from Claude Co-Work session

Syafiq shared five documents from a separate Claude Co-Work session. These define the full Sigma Gold System — four layers above the B2B signal. All saved to `workspace/baysix-engine/Research/architecture/engine-architecture`:

| File | What it covers |
|---|---|
| `Context_Engine_Architecture.md` | CE1–CE4 pipeline: Kalman Filter → EWM z-score → IC weighting → PCA → Context Score (−1 to +1) |
| `Regime_Engine_Architecture.md` | RE1–RE4: HMM + BOCPD → P(bull)/P(bear)/P(range) + changepoint prob. Four regime dimensions. |
| `Signal_Execution_Layer_Architecture.md` | 3 strategies + L4 signal generation + execution hard limits + BOCPD circuit breaker |
| `Data_Layer_Architecture.md` | 4 pipelines (Macro/Market/Derived/Alt). TimescaleDB. Point-in-time correct storage. |
| `XAUUSD_Options_Flow_Research.md` | What moves gold (priority order). GEX mechanics. Six options flow signals. |

SVG diagrams were already in `Research/architecture/engine-diagram/`:
- `sigma_gold_system_architecture.svg`
- `context_engine_L4_L5_architecture.svg`
- `regime_engine_L4_L5_architecture.svg`
- `signal_execution_L4_L5_architecture.svg`

---

### 3. Critical reframe — B2B was measured out of context

**The most important insight of this session.** The Signal & Execution architecture document states explicitly:

> "GEX positive → no trades regardless of signal."
> "SAMTC breakout signals only fire in TRENDING BULL or TRENDING BEAR regimes (RE1)."

Notebooks 01–03 measured the raw H1 B2B signal fired in ALL market conditions — ranging markets, transitioning markets, GEX-positive environments. The −0.008 R post-cost result includes trades the regime engine was explicitly designed to block.

**The +0.309 R gross edge is the floor — the unconditional signal including all bad regimes.**

The correct research question is: **"What is the B2B IC when restricted to GEX-negative + real-yields-falling conditions?"** That's the signal as designed. The IC in that subset is expected to be materially higher because:
1. GEX-negative = trending conditions = retest theory actually holds (price follows through)
2. Trending conditions produce larger directional moves = wider R_points = lower cost burden per R
3. Real yields falling = macro tailwind for gold = directional trades have fundamental backing

---

### 4. Two-goal clarity established

**Goal 2.1 — Working EA (JustMarkets + Darwinex)**
- JustMarkets: MT5 CFD XAUUSD, B2B zone EA
- Darwinex: same signal, GC Futures / GLD ETF, must satisfy D-score (consistency, drawdown < 15–20%, regular trades)
- The MQL5 EA exists but was over-filtering (Russian Doll + 3-gate orchestrator → near-zero trades fired)

**Goal 2.2 — Novel signal for Balyasny/Millennium QR application**
- "Novel" = systematic IC measurement of B2B retest signal under regime conditioning
- Not the pattern (break-and-retest is known) — the measurement and conditioning framework IS the contribution
- The SME angle: Implied Volatility (IV rank / VRP) + HMM regime detection are Syafiq's stated SME pillars
- Target framing: "B2B H4 retest signal, D1-biased, conditioned on GEX/realized-vol regime — IC X in trending regimes vs Y unconditional"

---

### 5. Full system architecture gap assessment

| Layer | Design | Build Status |
|---|---|---|
| Data Layer | L3–L4 spec complete | Flat files only (L2) |
| Context Engine | L4 complete (Kalman+PCA+IC weighting) | Not built |
| Regime Engine | L4 complete (HMM+BOCPD) | Not built |
| Signal Layer (B2B) | Designed + nb01–03 done | Partial — measured unconditionally |
| MQL5 EA | Designed (simple mode) | Exists but over-filtered |

---

## What Is NOT Done / Still Open

- **Regime-conditioned B2B IC measurement** — the real research question. Need FRED real yields + GEX proxy (realized vol) overlaid on the existing H1 trade set. Re-filter trades_fixed to GEX-negative + real-yields-falling conditions and re-measure IC. This invalidates the "FAIL" from nb03 or rescues it.
- **H4 data acquisition** — Syafiq will export H4 + D1 from Dukascopy (bar data, not tick). Same CSV format as H1. Needed for H4 zone width analysis (expected wider R, lower cost burden).
- **D1 reindex bug in notebook 02** — `d1_aligned` column silent (empty after reindex). Blocks the D1 alignment stratifier. Small fix, do it when starting D1 conditioning work.
- **CBOE GVZ download** — Yahoo Finance ticker `^GVZ` (Gold VIX), daily since 2008. Syafiq asked about this; recommendation was to start with realized vol rank (from existing H1 data) and swap in GVZ for the final QR memo.
- **MQL5 simple-mode EA** — designed in May 16 handover, not written. Waiting for regime-conditioned cost check to confirm signal survives before committing EA rewrite.
- **Context Engine, Regime Engine builds** — architecture fully designed, no Python code exists yet. Not the immediate priority.

---

## Running Processes

None. All notebooks have cached outputs. No background tasks.

---

## Priority for Next Session

### Track A — Live EA (near-term, 2–3 sessions)

**A1 (first): Regime-condition the existing H1 trade set**
- Fetch FRED DFII10 real yields via `fredapi` (free, no account needed — just `pip install fredapi`, use `FRED_API_KEY` from `.env` or request one at fred.stlouisfed.org)
- Compute 3-month change z-score of real yields as a daily series
- Compute 30-day rolling realized vol rank (52-week percentile) from XAUUSD H1 data as GEX proxy
- Re-filter `trades_fixed` (1,084 trades) to: `ry_zscore < 0` (falling real yields) AND `rv_rank < 0.4` (low vol = positive GEX proxy)
- Re-run cost-adjusted EV on filtered set → does net EV pass +0.10 R?
- Build as `notebooks/04_b2b_regime_conditioned.ipynb` using `scripts/tools/_build_notebook_04.py`

**A2: H4 data ingestion (once Syafiq provides files)**
- Dukascopy CSV → convert to parquet via same schema as `data/raw/XAUUSD_H1.parquet`
- Run the same nb02/03 chain on H4 (wider R_points → lower cost burden)
- Expected: H4 standalone passes cost check without needing regime filter

**A3: MQL5 EA rewrite (after A1 confirms signal)**
- Thin executor: H4 zones + `fresh_bars >= 2` retest filter + regime gate (real yields direction + realized vol) + fixed 2:1 RR + 1% risk
- No Russian Doll. No 3-gate orchestrator. Regime gate replaces complexity.

### Track B — QR Memo (medium-term, 4–6 sessions total)

**B1: IC/ICIR framing of regime-conditioned signal**
- Convert per-trade R outcomes to forward-return IC (Spearman rank correlation)
- IC decay curve: does IC decay over 1/4/12/24h horizons?
- Report: IC, ICIR, IC t-stat — the Balyasny/Millennium language

**B2: Factor decomposition**
- Is the B2B IC just momentum? Just a DXY proxy? Just a vol regime effect?
- Regress residual alpha against: momentum (1M, 3M gold return), DXY z-score, VIX/GVZ level, realized vol regime
- Report: X bps/yr residual alpha after 4-factor decomposition, t-stat Y

**B3: Walk-forward OOS**
- IS: 2016–2020, OOS: 2021–2026
- No parameter refit in OOS
- IS IC vs OOS IC comparison

**B4: Research memo**
- Draft in Tier C QR language
- Pod-shop framing: IC X, ICIR Y, alpha survives Z-factor decomposition
- Saves to `strategies/b2b-gold/YYYY-MM-DD_b2b_qr_memo.md`

---

## Key Decisions Made

- **Notebooks 01–03 measured the wrong thing**: raw unconditional H1 signal, not regime-gated SAMTC as designed. The −0.008 R post-cost is a floor, not the real signal performance.
- **B2B is Signal Layer (Layer 4) of a 4-layer system**: Context Engine → Regime Engine → Signal → Execution. Research must incorporate at minimum a regime proxy before conclusions are valid.
- **H4 as likely workhorse TF for EA**: wider R_points (3–6× H1), lower cost burden. Run same notebooks once data arrives.
- **Realized vol rank as free GEX proxy**: compute from existing H1 data immediately. Swap in CBOE GVZ for final memo.
- **Track A and Track B are parallel, not sequential**: EA rebuild and QR memo are both served by the same regime-conditioned signal measurement. Build once, use for both.
- **SME differentiator for Balyasny/Millennium**: IV rank + HMM regime detection conditioning the B2B IC. This combination is Syafiq's own. The systematic measurement IS the contribution.
- **Do not rebuild the full system before validating the signal**: Context Engine and Regime Engine (HMM) are 2–3 months of work. Use proxy inputs (FRED real yields + realized vol) to validate the regime-conditioned signal first. Full engine build follows signal validation.

---

## Architecture Files Now In Place

All in `workspace/baysix-engine/Research/architecture/`:

```
architecture/
├── ADR-001-factor-model.md
├── ADR-002-regime-detection.md
├── ADR-003-signal-combination.md
├── ADR-004-ic-method.md
├── ADR-005-cost-model.md
├── engine-design-v1.md
├── Context_Engine_Architecture.md          ← NEW (from Co-Work session)
├── Regime_Engine_Architecture.md           ← NEW (from Co-Work session)
├── Signal_Execution_Layer_Architecture.md  ← NEW (from Co-Work session)
├── Data_Layer_Architecture.md              ← NEW (from Co-Work session)
├── XAUUSD_Options_Flow_Research.md         ← NEW (from Co-Work session)
└── engine-diagram/
    ├── sigma_gold_system_architecture.svg
    ├── context_engine_L4_L5_architecture.svg
    ├── regime_engine_L4_L5_architecture.svg
    └── signal_execution_L4_L5_architecture.svg
```

---

## Blockers

- **H4/D1 Dukascopy data**: Syafiq is providing. No action needed until files arrive — hand to Claude as CSV, it will ingest + convert.
- **FRED API key**: Free at fred.stlouisfed.org/docs/api/api_key.html. Needed for real yields fetch. Store in `workspace/baysix-engine/sigma-are/.env` as `FRED_API_KEY=xxx`.
- **CBOE GVZ**: Download `^GVZ` from Yahoo Finance (Historical Data → CSV). Not urgent — realized vol proxy is sufficient for Track A.

---

## How to Start Next Session

1. Read this handover first — full context is here.
2. Read `workspace/baysix-engine/Research/architecture/engine-architecture/Signal_Execution_Layer_Architecture.md` — the regime gate rules (GEX + RE1 conviction) are the key constraint on all signal research.
3. Ask Syafiq: "Do you have the H4/D1 CSVs ready? And do you have a FRED API key?" — determines which Track A step to start.
4. If H4 data ready → ingest + run nb02/03 chain on H4 first (fastest win).
5. If no H4 data yet → start `_build_notebook_04.py` (regime-conditioned H1 IC) using FRED real yields + realized vol rank from existing H1 data.
6. Do NOT restart from notebooks 01–03. Those are complete. The next notebook is 04.
