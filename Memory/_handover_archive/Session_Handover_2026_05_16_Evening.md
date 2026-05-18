# Session Handover — May 16, 2026 (Evening — Architecture brainstorm: ARE, execution bridge, strategy registry locked)

## What Was Accomplished This Session

### 1. Full Infrastructure Brainstorm — Professional QR Architecture

Deep brainstorming session covering the full Baysix infrastructure stack. Key clarity achieved on:

- **ARE is the brain** — sigma-are owns all alpha research, signal measurement, strategy registry
- **Three-room model locked**: sigma-are (Does it work?) → sigma-lean (Simulate it) → sigma-mt5 (Trade it live)
- **Pro workflow established**: IC measurement (seconds) replaces Strategy Tester (hours) as the primary signal validation tool. Strategy Tester now reserved only for execution plumbing test.

---

### 2. Execution Architecture Decision — Python Bridge + ONNX

Researched and locked the execution architecture for three broker targets:

**DWX Connect** (not ZeroMQ — archived Feb 2022) is the official Darwinex Python-MT5 bridge:
- File-based communication (no ZeroMQ dependency)
- Official Darwinex library: https://github.com/darwinex/dwxconnect
- Python writes signal to MQL5/Files/ → MT5 EA reads file → executes

**MQL5 ONNX support confirmed** (MT5 build 3370+):
- Train models in Python (PyTorch, sklearn) → export `.onnx` → `OnnxRun()` in MQL5
- Microsecond inference, fully self-contained EA — preferred for FTMO (grey area on external bridges)

**Execution method per broker:**
| Broker | Method | Rationale |
|--------|--------|-----------|
| Darwinex Zero | DWX Connect | Officially supported, they built the library |
| JustMarkets | DWX Connect | No restrictions, flexible |
| FTMO | ONNX in MQL5 | Self-contained, no grey area on external signals |
| IKBR | Python ib_insync API | No MT5 — pure Python execution for equities |
| Moomoo/Webull | Python API | APAC retail, future state |

**Asset class priorities locked:**
1. XAUUSD (B2B gold) — income engine via Darwinex
2. US Sector ETFs → S&P 500 (cross-sectional momentum) — QR credentialing
3. Macro factors (FRED) — regime conditioners, not standalone signals
4. Stat arb pairs — reuses equities data, built after momentum
5. APAC equities — last, for Kenanga/Affin Hwang framing only

---

### 3. B2B Strategy Clarification — Multi-TF Confluence is the Edge

Critical correction made during session: Multi-TF confluence in B2B is NOT timeframe snooping. Each timeframe has a fixed, non-interchangeable role:

```
Narrative (MN1, W1, D1)      → institutional direction + outer zone
Control   (H4, H1, M30, M15) → refined zone inside Narrative
Sniper    (M5, M1)           → precision entry inside Control
```

Entry fires ONLY when all three layers align. The IC question for B2B:
- Signal: `zone_score` (composite of narrative alignment + control quality + touch count + sniper confirmation)
- Measurement: time-series IC (rolling Spearman, single instrument XAUUSD)
- Decay curve: determines optimal hold period (NOT which TF to use — those are fixed by design)

Full B2B documentation read and context ingested from:
- `sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md`
- `sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md`
- `sigma-mt5/Documentation/B2B_CLUSTER_FIX_PLAN.md`
- `sigma-mt5/Documentation/B2B_LOGIC_REVIEW.md`

---

### 4. Broker Context Folders Created

`baysix-engine/brokers/` created as top-level cross-cutting folder (not inside sigma-mt5 — corrected after user feedback):

```
baysix-engine/brokers/
├── README.md
├── darwinex-zero/CONTEXT.md     ← PRIMARY: DWX Connect, rules, build order
├── retail-prop-firm/CONTEXT.md  ← FTMO: ONNX preferred, future state
├── high-leverage-broker/CONTEXT.md ← JustMarkets: re-strategizing
├── ibkr/CONTEXT.md              ← equities, Python API, future
└── moomoo-webull/CONTEXT.md     ← APAC retail, lowest priority
```

---

### 5. Strategy Registry Built Inside sigma-are

`sigma-are/strategies/` created as the strategy registry (correct location — user confirmed sigma-are owns all alpha research):

```
sigma-are/strategies/
├── README.md                    ← inventory + status legend
├── b2b-gold/
│   ├── README.md                ← status RESEARCHING Phase 0, IC targets, code links
│   ├── hypothesis.md            ← economic mechanism, falsification criteria, factor model
│   ├── config.yaml              ← ALL parameters (single source of truth)
│   └── decisions.md            ← 7 decisions logged (DEC-001 to DEC-007)
├── xsection-momentum/
│   └── README.md                ← HYPOTHESIS, ETF → S&P 500
├── stat-arb/
│   └── README.md                ← HYPOTHESIS, shares equities data pipeline
└── vol-regime/
    └── README.md                ← CONDITIONER not strategy, HMM planned
```

**config.yaml is the single source of truth for all parameters.** Sub-systems must read from here, never hardcode.

---

### 6. Data Infrastructure Direction Established (Not Yet Built)

Key decisions on data layer:
- **DuckDB** — confirmed as the data store. Handles 11 ETFs today, S&P 500 / Russell 1000 eventually. SQL queryable, parquet-native, zero-server, free.
- **Universe will always expand** — user confirmed this explicitly. DuckDB from day one, not flat parquet files.
- **Data layer not yet built** — needs to be designed and built before Session 1 signal code

Data layer plan:
| Layer | Format | Contents |
|-------|--------|---------|
| Equity prices (OHLCV) | DuckDB | All tickers, all dates, point-in-time |
| Macro factors | Parquet | FRED series (VIX, DXY, real yields, oil) |
| XAUUSD bars | Parquet by TF | H1, H4, D1 |
| Signal outputs | DuckDB | IC tables, factor exposures (queryable history) |

---

## What Is NOT Done / Still Open

- **DEC-005 (cluster fix) — OPEN**: Which option to implement? A (temporal proximity, recommended), B (all pairs + dedup), or C (hybrid). Syafiq must decide before Phase 0 code is written. See `sigma-are/strategies/b2b-gold/decisions.md`.
- **ARE Session 0 patches** — `ic_engine.py`, `base.py`, `cost_registry.py` still need the 5 targeted fixes. Not started.
- **DuckDB data layer** — not designed or built. Prerequisite for Session 1 signal code.
- **Research/hypothesis_log.md** — H001 (cross-sectional momentum) not logged yet.
- **adapters/gold/** — does not exist. Planned for Phase 1 after cluster fix.
- **adapters/equities/** — stub files with `raise NotImplementedError`. Not implemented.
- **LEAN H1 IS backtest** — status unknown. Check: `docker ps | grep lean`
- **Darwinex Zero account** — not opened. Awaiting Phase 0 completion.
- **DWX Connect bridge** — not built. Planned for Phase 2 after Phase 0 + Phase 1.
- **ADRs (ADR-001 to ADR-005)** — need updates to reflect Option A multi-mode architecture.
- **Visual backtesting (Plotly)** — discussed but not designed. Plotly chart spec for B2B needs multi-TF zone overlay design.

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| MT5 XAUUSD live trading | NOT RUNNING | Re-strategizing — no live MT5 as of 2026-05-16 |
| LEAN H1 IS backtest | Unknown | Check `docker ps \| grep lean` |
| Alpha Research Engine | Not started | Session 0 patches needed first |

---

## Priority for Next Session

1. **Decide DEC-005 — Cluster fix option (A, B, or C)**
   - File: `sigma-are/strategies/b2b-gold/decisions.md`
   - Recommended: Option A (temporal proximity)
   - This is a hard gate — nothing in Phase 0 can be coded until this is decided

2. **Design DuckDB data layer**
   - What tables? What schema? How is point-in-time enforced?
   - What data sources? (yfinance + FRED for equities, MT5 exported CSVs for XAUUSD)
   - This should be specced before any adapter code is written

3. **ARE Session 0 — Patch `ic_engine.py`**
   - File: `sigma-are/alpha_engine/core/ic_engine.py`
   - Add `signal_mode: Literal['cross_sectional', 'time_series']`
   - time_series mode: rolling Spearman IC over time axis
   - IC decay horizons in H1 bars: `[1, 4, 8, 24, 48]`
   - NW lags = `avg_holding_period_days * 2`

4. **ARE Session 0 — Patch `base.py` and `cost_registry.py`**
   - `base.py`: Allow `load_data()` to return `dict[str, pd.DataFrame]` for multi-TF
   - `cost_registry.py`: Add `impact_model` selector + `trading_days_per_year` field

5. **Write `Research/hypothesis_log.md`** — Log H001 before Session 1 code

---

## Key Decisions Made

- **DWX Connect (not ZeroMQ)**: File-based Python-MT5 bridge. ZeroMQ archived. DWX Connect is official Darwinex successor.
- **ONNX for FTMO**: Train in Python, export `.onnx`, run natively via `OnnxRun()` in MQL5 EA. No external process dependency.
- **strategies/ inside sigma-are**: Strategy registry lives in the Alpha Research Engine. Cross-cutting deployment context (brokers/) lives at baysix-engine level.
- **DuckDB from day one**: Universe will always expand (user confirmed). Parquet files insufficient for S&P 500 scale.
- **Multi-TF confluence is the edge**: B2B is NOT timeframe snooping. Each TF has a fixed role. IC measures the composite zone_score, not individual timeframe signals.
- **MT5 not currently live**: Re-strategizing. No live account running as of 2026-05-16.
- **Pro workflow established**: IC (seconds) → factor decomp → walk-forward → LEAN → Plotly spot-check → MT5 execution test (15 min). Replaces hours of Strategy Tester.

---

## Blockers

- **DEC-005 (cluster fix option)**: Must be decided by Syafiq before any Phase 0 B2B code. Options A/B/C in `sigma-are/strategies/b2b-gold/decisions.md`.
- **Session 0 patches block Session 1**: `ic_engine.py` is fully stubbed. No IC can be measured until patches are applied.
- **Data layer blocks adapters**: Cannot write `adapters/equities/data.py` until DuckDB schema is designed and data is loaded.

---

## Reference: Updated Workspace Structure

```
baysix-engine/
├── sigma-are/
│   ├── alpha_engine/
│   │   ├── core/
│   │   │   ├── ic_engine.py         ← Session 0: add signal_mode flag (STUBBED)
│   │   │   ├── cost_registry.py     ← Session 0: add impact_model + trading_days_per_year (BUILT)
│   │   │   └── regimes.py           ← needs feature_set param
│   │   └── adapters/
│   │       ├── base.py              ← Session 0: loosen load_data() return type (BUILT)
│   │       ├── equities/            ← Session 1 (stubs only)
│   │       └── gold/                ← Phase 1 (does not exist)
│   └── strategies/                  ← NEW THIS SESSION
│       ├── README.md
│       ├── b2b-gold/                ← hypothesis, config, decisions
│       ├── xsection-momentum/
│       ├── stat-arb/
│       └── vol-regime/
├── sigma-lean/
├── sigma-mt5/
│   └── Documentation/               ← B2B cluster fix plan (decision pending)
├── brokers/                         ← NEW THIS SESSION (moved from sigma-mt5)
│   ├── darwinex-zero/
│   ├── retail-prop-firm/
│   ├── high-leverage-broker/
│   ├── ibkr/
│   └── moomoo-webull/
└── Research/
    ├── RESEARCH_FRAMEWORK.md
    └── SAMTC/memo_test13a.md        ← Gate 4 PASSED
```
