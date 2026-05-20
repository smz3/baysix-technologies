# Session Handover — May 18, 2026 (Evening — B2B Edge Resolved + Lab Built)

## Headline

**The B2B H1 retest signal on XAUUSD has real, statistically significant edge:** +0.309 R per trade over 1,084 trades, z = +7.19 vs break-even, robust across all parameter combinations. Pre-cost Sharpe ≈ 2.16.

This session built the full XAUUSD research lab from scratch, ran the naive edge measurement, identified three methodology flaws, ran the corrected measurement, archived all SAMTC artifacts to prevent attribution contamination, and laid out a 4-session roadmap to convert this into a pod-shop QR research memo for Balyasny / Millennium.

The finding memo is the long-lived artifact: `workspace/baysix-engine/sigma-are/strategies/b2b-gold/2026-05-18_phase_b_naive_edge_findings.md`. Read that for the verdict. Read this handover for session context and forward priorities.

---

## What Was Accomplished This Session

### Phase A — Detector parity (visual audit)
- Built `scripts/run_xauusd_h1_audit.py` — CLI runner that ingests Dukascopy 10-yr H1 CSV, runs `swing_points → breakouts → b2b_engine → zone_status → confluence`, and emits 3 Plotly audit HTML files.
- Built `notebooks/00_data_audit_xauusd_h1.ipynb` — interactive version for zooming into any date range.
- **Result:** 7,072 zones detected over 10 years (BUY 3,638 / SELL 3,434), stable ~700/year across all regimes.

### Pivot — Stopped writing my own port, used existing detectors
- Initially built `strategies/b2b-gold/h1_test/` with my own Python port. After audit found that `sigma-are/core/detectors/` already had a full B2B port (same logic, more complete chain including zone_status + confluence + manager).
- Deleted `h1_test/`, kept `B2B_STRATEGY_MASTER.md`. Used existing detectors going forward.

### Folder cleanup (commit 568064a)
- Promoted `notebooks/` and `reports/` to top level (were buried in `research/`).
- Consolidated `alpha_engine/core/` into `core/alpha_metrics/` (ic_engine, capacity, regimes, cost_registry, report — kept the IC/capacity stubs).
- Archived stale folders to `_archive/`: `alpha_engine/adapters/`, `dashboard/`, empty strategy placeholders (stat-arb, vol-regime, xsection-momentum), stray research files.
- `core/` keeps its name (28 files import from it; renaming would break SKILL.md doctrine and force updating all imports for no gain).

### Phase B — Naive edge measurement (notebook 01)
- Built `notebooks/01_b2b_ic_measurement.ipynb` (commit bf6736f).
- For every L1-touched zone: TP=L1+2R, SL=L2, forward returns at 1h/4h/24h, stratified by direction / freshness / D1 alignment.
- **Result:** +1.047 R per trade, 68.2% TP hit rate, 6,831 trades. Looked like hedge-fund-grade edge.

### Identified three methodology flaws (the critical step)
1. **Asymmetric stop:** TP fired on wick touch (`highs[k] >= tp_price`), SL only on close beyond (`closes[k] < sl_price`). Structurally biased toward TPs.
2. **Same-bar entry:** 96% of zones had L1 "touched" on the SAME bar that confirmed the zone (the P4 breakout bar). We were measuring breakout continuation, not B2B retest theory.
3. **Sample clustering:** 7,072 zones over 10 years cluster at common price levels. One XAUUSD move would hit TP on multiple stacked zones.

### SAMTC archive (commit 0b54717)
- The whole sigma-are/ codebase originated as the SAMTC port (BTCUSDT crypto interview project for ASCEND). Mixing SAMTC results with XAUUSD work risked attribution contamination (citing Test 13A Sharpe 1.16 as a gold result).
- Moved all SAMTC artifacts to `_archive/samtc/`:
  - 16 BTCUSDT parquet files + okx data (225 MB — gitignored, lives local-only)
  - OOS/in_sample reports (196 MB — gitignored)
  - Entire `research/` folder (papers, signals, thesis, analytics)
  - SAMTC scripts: binance_*, run_phase_4, run_{backtest,is_validation,oos_backtest}, diagnose_*, calculate_metrics, audit_oos_bias, verify_*, quant_*, monte_carlo, supabase_push, generate_*, render_mermaid, data_fetcher
  - `scripts/tools/`: analyze_dd, analyze_test_9, calc_dd, check_direction, smoke_test_refactor, temp_visualizer
  - `simulation/` (vectorized_backtester had SAMTC-hardcoded paths)
  - `config/binance_config.yaml`, `config/exchange_config.yaml`
  - `.agent/skills/SKILL.md` → `_archive/samtc/skills/SAMTC_SKILL.md`
  - Broken tests: `test_detector.py` (import bug), `test_day3.py` (API drift), placeholders `test_detectors.py` + `test_engine.py`
  - `logs/data_fetcher.log`
- **Kept in place** (used by XAUUSD work): `core/` (engine — symbol-agnostic), passing tests, our new notebooks, strategies/b2b-gold/, reports/xauusd_h1_audit/, data/raw/XAUUSD_H1.parquet, config/defaults.yaml.
- Updated `CLAUDE.md` to reflect XAUUSD focus and SAMTC archival.

### Phase B v2 — Honest edge measurement (commit be5404f)
- Built `notebooks/02_b2b_ic_measurement_v2.ipynb` with all three fixes:
  1. Symmetric close-based TP/SL
  2. Retest filter: `fresh_bars >= 2`
  3. Decluster: keep first zone per direction in 12-bar window
- Executed headlessly via `jupyter nbconvert --execute --inplace`, captured outputs.
- **Edge attribution:**
  - Symmetric stop fix: −0.33 R
  - Retest filter: **−0.41 R (biggest)** — 96% of "trades" were same-bar breakouts
  - Decluster: −0.001 R (retest filter already declustered)
- **Final verdict:** +0.309 R per trade, n=1,084, TP rate 43.6%, z = +7.19. Edge is real but ~30% of the naive measurement.
- Robustness sweep: EV stays in +0.28 to +0.36 R across all combinations of `retest_min_bars ∈ {1,2,5,10}` × `decluster_bars ∈ {1,6,12,24,48}`. Not a single-knob artefact.

### Memo + memory updated
- `strategies/b2b-gold/2026-05-18_phase_b_naive_edge_findings.md` — full memo with naive numbers, methodology critique, post-fix verdict, attribution table, parameter sweep, immediate next steps, and pod-shop framing roadmap (4 sessions).
- Memory entry `b2b_h1_phase_b_naive_finding.md` updated from "INFLATED, awaiting re-measurement" to "RESOLVED, edge is real."

---

## Current State of sigma-are/

```
sigma-are/
├── CLAUDE.md                       (rewritten for XAUUSD focus)
├── README.md
├── core/                           THE ENGINE (symbol-agnostic, do not break)
│   ├── detectors/                  swing_points, breakouts, b2b_engine,
│   │                                confluence, zone_status, zone_manager
│   ├── alpha_metrics/              ic_engine, capacity, regimes, cost_registry, report
│   ├── models/structures.py
│   ├── visualization/plotly_visualizer.py   ChartVisualizer (3 audit charts)
│   └── ... (strategy/, filters/, risk/, execution/, system/, features/ — most empty stubs)
├── notebooks/                      ← XAUUSD research notebooks
│   ├── 00_data_audit_xauusd_h1.ipynb       Visual audit (passed)
│   ├── 01_b2b_ic_measurement.ipynb         Naive measurement (HISTORICAL — do not cite)
│   └── 02_b2b_ic_measurement_v2.ipynb      Post-fix measurement (TRUSTWORTHY)
├── scripts/
│   ├── run_xauusd_h1_audit.py
│   └── tools/_build_notebook_{00,01,02}.py
├── strategies/b2b-gold/
│   ├── B2B_STRATEGY_MASTER.md      Master B2B doctrine
│   ├── 2026-05-18_phase_b_naive_edge_findings.md  ← THE FINDING MEMO
│   ├── README.md, hypothesis.md, decisions.md, config.yaml, XAUUSD_OPTIONS_FRAMEWORK.md
├── tests/                          3 passing (confluence, timeframe_mgr, zone_mgr)
├── data/raw/XAUUSD_H1.parquet      10-yr Dukascopy H1
├── reports/xauusd_h1_audit/        Plotly audit HTMLs from Phase A
├── config/defaults.yaml            generic detection params
└── _archive/samtc/                 ALL SAMTC artifacts (BTCUSDT crypto port)
    └── (data, reports, research, scripts, simulation, configs, skills, broken tests)
```

---

## The Numbers (one-glance)

| Metric | Naive (notebook 01) | Fixed (notebook 02) |
|---|---|---|
| Trades | 6,831 | **1,084** |
| EV per trade | +1.045 R | **+0.309 R** |
| TP hit rate | 68.2% | **43.6%** (break-even 33.3%) |
| z vs break-even | n/a | **+7.19** |
| Trades/year | ~683 | ~108 |
| Annual return @ 1% risk | n/a | **~33.5% gross** |
| Annual vol @ 1% risk | n/a | ~15.5% |
| Pre-cost Sharpe | n/a | **~2.16** |
| Post-cost Sharpe (est) | n/a | **1.0 – 1.4** (TBD next session) |

**Do not cite the naive +1.047 R. Use +0.309 R only.**

---

## Git State (this session — 5 commits)

```
be5404f feat: Phase B v2 — honest edge measurement after methodology fixes
0b54717 chore: archive SAMTC (BTCUSDT crypto interview project) under _archive/samtc/
bf6736f feat: notebook 01 — B2B IC measurement (Phase B edge measurement)
568064a chore: sigma-are folder cleanup (archive stale, promote notebooks+reports)
f287be0 feat: XAUUSD H1 audit pipeline + notebook 00
```

All commits are independently revertible. Each represents a coherent logical unit.

---

## What Is NOT Done / Open Items

1. **Cost-adjusted EV** — the biggest unknown. Naive Sharpe ≈ 2.16 sounds great but JustMarkets spread (~3 bps) + overnight financing (~3.5%/yr) + slippage will eat into +0.31 R. After-cost EV could be +0.10 R (still tradable) or near zero (kill signal). This is the next session's job.
2. **D1 reindex bug** in notebook 02 — `d1.reindex(df["time"], method="ffill")` returns empty `d1_aligned` column. Stratifier silent until fixed. Likely a small bug, may add a meaningful conditioner.
3. **MQL5 simple-mode EA** — designed in May 16 handover, never written. Now justified by Phase B v2 result, but should wait until post-cost EV is confirmed.
4. **Lingering IDE-locked folder:** `research/reports/xauusd_h1_audit/` (canonical copy is at `reports/xauusd_h1_audit/`). When VSCode closes the file, `rm -rf research` from sigma-are/ root to clean up.

---

## The 4-Session Roadmap (Forward Priority)

The signal isn't the bottleneck — the framing is. Pre-cost Sharpe of 2.16 from a single signal on a single instrument is already pod-shop territory. The next 4 sessions convert this finding into a pod-shop QR research memo for Balyasny / Millennium.

| # | Session | Output | Why |
|---|---|---|---|
| 1 | **Cost-adjusted EV** | `notebooks/03_b2b_cost_adjusted.ipynb` + JustMarkets cost model | Tells us whether signal survives reality. Hard prerequisite. |
| 2 | **IC / ICIR framing** | `notebooks/04_b2b_ic_framing.ipynb` + IC tables + decay curve | The language Balyasny QRs use. "IC 0.04, ICIR 1.3 across 2,400 daily cross-sections" gets interviews. |
| 3 | **Factor decomposition** | `notebooks/05_b2b_factor_decomp.ipynb` + residual alpha vs momentum/VIX/DXY/vol regime | Show alpha is NOT a momentum proxy. Quote "60 bps/yr residual alpha after 4-factor decomposition, t-stat 2.7." |
| 4 | **Walk-forward OOS** | `notebooks/06_b2b_walkforward.ipynb` + IS(2016-2020) vs OOS(2021-2026) | Robustness without parameter refit. |

After these 4 sessions you have a complete pod-shop research memo. That's what gets submitted with the Balyasny / Millennium application. **The quality of the analysis is what hires you, not the size of the Sharpe.**

True hedge-fund-grade (Sharpe 2+ post-cost) requires cross-asset (USDJPY / EURUSD / ES / CL), multi-TF aggregation, capacity stress testing, continuous walk-forward — that's 3-6 months of work, done in-pod or while building toward own fund. Not the immediate priority.

---

## Running Processes

None. All notebooks have cached outputs.

---

## How to Start Next Session

1. Read `strategies/b2b-gold/2026-05-18_phase_b_naive_edge_findings.md` (the finding memo) — first thing.
2. Pull up `notebooks/02_b2b_ic_measurement_v2.ipynb` for the current state. Outputs are cached.
3. **Session 1 priority:** Build notebook 03 (`scripts/tools/_build_notebook_03.py`) for cost-adjusted EV. Cost model:
   - Spread: 3 bps per round trip (JustMarkets XAUUSD)
   - Slippage: 1 bps per trade (conservative for H1)
   - Overnight financing: 3.5% annualised, accrued on positions held past 22:00 UTC
   - Recompute EV per trade subtracting these from the +0.309 R baseline
4. If post-cost EV > +0.10 R, proceed to Session 2. If not, the H1 retest is unviable and we pivot to a different signal hypothesis.

---

## Key Decisions Made

- **Use existing `core/detectors/` instead of re-porting from MQL5.** The Python port already exists, tested, and the cleanup we did made it cleanly accessible.
- **Archive SAMTC, do not delete.** SAMTC was the interview project that built this codebase. The detectors are useful; the SAMTC-specific outputs would pollute XAUUSD attribution. Hard separation in `_archive/samtc/` preserves history without contamination.
- **Notebook 01 stays in place as historical "naive baseline" reference.** Do not delete. The methodology contrast (naive vs fixed) is itself part of the research story.
- **Goal split:** Pod-shop interview material (4 sessions) is the priority. True hedge-fund-grade alpha (3-6 months) is the longer arc, done in-pod.
- **Sharpe ~2.16 pre-cost is the cleanest current number.** Cite it with the "pre-cost" caveat. Real post-cost number arrives next session.

---

## Blockers

None material. The IDE-locked `research/reports/xauusd_h1_audit/` is a cleanup leftover, not a blocker.

---

## Files Referenced (canonical paths)

- Finding memo: `workspace/baysix-engine/sigma-are/strategies/b2b-gold/2026-05-18_phase_b_naive_edge_findings.md`
- Notebooks: `workspace/baysix-engine/sigma-are/notebooks/{00,01,02}_*.ipynb`
- Notebook builders: `workspace/baysix-engine/sigma-are/scripts/tools/_build_notebook_*.py`
- Audit runner: `workspace/baysix-engine/sigma-are/scripts/run_xauusd_h1_audit.py`
- Detector engine: `workspace/baysix-engine/sigma-are/core/detectors/`
- Data: `workspace/baysix-engine/sigma-are/data/raw/XAUUSD_H1.parquet`
- SAMTC archive: `workspace/baysix-engine/sigma-are/_archive/samtc/`
- Memory: `C:\Users\User\.claude\projects\c--Users-User-Desktop-sigma-brain\memory\b2b_h1_phase_b_naive_finding.md`
