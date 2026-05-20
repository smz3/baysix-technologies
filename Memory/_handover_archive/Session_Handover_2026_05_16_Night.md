# Session Handover — May 16, 2026 (Night — Framework locked, B2B docs consolidated)

## What Was Accomplished This Session

### 1. Vectorized vs Event-Based Backtesting — Resolved

Deep discussion on the architecture concern: B2B and macro strategies are event-driven,
not vectorized. Resolution locked:

**3-Room Model (now in RESEARCH_FRAMEWORK.md):**

| Room | Engine | Mode | Purpose |
|------|--------|------|---------|
| sigma-are | Python IC engine | Vectorized (dense) OR event-time (sparse) | Signal quality gate |
| sigma-lean | LEAN CLI | Event-based — MANDATORY, not optional | Strategy simulation |
| sigma-mt5 | MT5 Strategy Tester | Event-based, tick-level | Production plumbing test |

Key insight: "IC replaces Strategy Tester" framing from prior session was imprecise.
IC measures signal predictive power. LEAN simulates execution. They serve different
purposes and both are required. Room 2 (LEAN) is non-negotiable for B2B.

---

### 2. Event-Time IC Mode — Locked as DEC-008

B2B is sparse (~3 fires/week). Computing IC across all 8,760 H1 bars/year dilutes
signal with noise bars. Solution: **event-time IC** — measure IC only at zone activation
moments.

Architecture (3 phases):
- **Phase 1** — sequential event detection loop (state-aware, multi-TF): identifies zone
  activation timestamps. Loop IS intentional — multi-TF state cannot be vectorized.
- **Phase 2** — forward return computed for each event timestamp (vectorized over events)
- **Phase 3** — Spearman IC over event subset (vectorized)

This is now DEC-008 in `sigma-are/strategies/b2b-gold/decisions.md`.

ic_engine.py now requires **3 signal modes** (updated from 2):
- `cross_sectional` — ETFs, equities (Spearman across instruments per date)
- `time_series` — single instrument, dense signal (rolling Spearman over time)
- `event_time` — sparse, event-driven (Spearman over activation events only) ← NEW

---

### 3. Gemini's Framework Advice — Assessed

Gemini correctly identified the conceptual problem (vectorized ≠ execution simulator).
Two specific libraries it recommended — StrategyTester5 and PyEventBT — could not be
verified as real maintained libraries. Not added to stack. LEAN remains the event-based
simulator. No new framework dependencies introduced.

---

### 4. DEC-005 (Cluster Fix) — Withdrawn

The 98% OOS drawdown was caused by **wrong-direction trades** (price pulling back while
EA kept shorting). The cluster pairing logic was not the root cause — it was a
misdiagnosis. DEC-005 marked WITHDRAWN in decisions.md. No cluster fix needed.

---

### 5. Framework Documents Updated

Files changed:
- `Research/RESEARCH_FRAMEWORK.md` — added 3-room model section; IC engine spec now
  has all 3 modes with input shapes; B2B signal registry updated XAUUSD/macro factor
  model; fixed stale sigma-crypto path to baysix-engine/sigma-are
- `sigma-are/strategies/b2b-gold/decisions.md` — DEC-005 WITHDRAWN, DEC-008 added
- `sigma-mt5/CLAUDE.md` — Active Issue section removed, cluster fix references cleared

---

### 6. Full sigma-mt5 Module Documentation Read

All 30 module docs read and understood. Full system picture:

**Detection pipeline (per new bar):**
SwingPointDetector [FROZEN] → RawBreakoutDetector → B2BDetector (5-pointer zones) →
B2BConfluence (Russian Doll nesting) → B2BZoneStatus (T0/T1/T2/T3 tracking) →
MetricCalculator (fractal depth 0-4)

**Execution (per tick):**
TradeSignalGenerator → ContextMapper (session boundaries, path check) →
StrategyOrchestrator OR IntradayOrchestrator (3-gate authorization) →
RiskManager → OrderManager (Sniper Protocol: 1-trade-per-zone) →
B2BTradeTracker (stamps zone) → QuantLogger (CSV export)

**3 Execution Gates (Russian Doll mode):**
Gate 1 DIRECTION: FlowState origin→outpost→magnet chain valid
Gate 2 LOCATION: ContextMapper — no opposing zone blocking path
Gate 3 STRUCTURE: entry zone nested in HTF parent

**God Data fields already tracked per zone:**
fractal_depth, is_nested, is_multi_parent, is_pioneer, touch_count, zone_age_bars,
entry_level_used (T1/50%/T3), MAE, MFE, rr_planned, pnl, exit_reason

---

### 7. B2B Documentation Consolidated

**4 stale files deleted:**
- B2B_CLUSTER_FIX_PLAN.md
- B2B_DETECTION_SYSTEM.md
- B2B_LOGIC_REVIEW.md
- B2B_STRATEGY_DECISIONS.md

**Reason:** Multiple misalignments found between strategy docs and module docs:
- Logic review had stale "more extreme" pairing rule (removed Dec 18 2025)
- Dedup "Better L1" was inverted vs pairing logic within the same file
- Cluster bug references throughout (now known to be misdiagnosis)
- Implementation checklists were stale (many items marked pending were already built)

**New master document created:**
`sigma-are/strategies/b2b-gold/B2B_STRATEGY_MASTER.md`
— 13 sections, grounded entirely in module docs, single source of truth for B2B strategy.
Covers: TF hierarchy, 5-pointer mechanics, zone lifecycle, Russian Doll confluence,
God Data, both execution engines, risk sizing, trade management, source file map.

**Module docs cleaned:**
- `sigma-mt5/Documentation/modules/Detection/B2BDetector.md` — cluster bug note replaced
  with correct L1 selection rule (Higher for BUY, Lower for SELL)
- `sigma-mt5/Documentation/modules/INDEX.md` — cluster bug removed from status and
  Known Issues table

---

## What Is NOT Done / Still Open

- **B2B strategy improvement brainstorm** — was ABOUT TO START when session ended.
  This is the #1 priority for next session. See "Priority for Next Session" below.
- **ARE Session 0 patches** — ic_engine.py now needs 3 modes (cross_sectional,
  time_series, event_time). Previously only 2 were specced.
- **DuckDB data layer** — not designed or built. Prerequisite for Session 1 signal code.
- **hypothesis_log.md** — H001 (cross-sectional momentum) still not logged.
- **adapters/gold/** — does not exist. Planned for Phase 1 after B2B research is framed.
- **LEAN H1 IS backtest** — status unknown. Check: `docker ps | grep lean`
- **Darwinex Zero account** — not opened. Awaiting Phase 0 completion.
- **DWX Connect bridge** — not built. Phase 2 after Phase 0 + Phase 1.
- **Cascade invalidation** — decided but not yet implemented in MQL5 EA.

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| MT5 XAUUSD live trading | NOT RUNNING | Re-strategizing — no live MT5 |
| LEAN H1 IS backtest | Unknown | Check `docker ps \| grep lean` |
| Alpha Research Engine | Not started | Session 0 patches needed first |

---

## Priority for Next Session

### 1. B2B Strategy Improvement Brainstorm (START HERE)

We were mid-conversation when session ended. The B2B module docs are now fully read
and consolidated. The question to answer:

> How do we improve B2B from a Quant Research perspective — signal quality, zone
> scoring, execution — so it can be measured with IC and framed for Balyasny/Millennium?

Starting points to explore:
- **Signal side**: What composite `zone_score` captures the edge? fractal_depth, touch
  count, pioneer flag, path clearance, session position — which combinations have IC?
- **Execution side**: Are Gate 1/2/3 optimal? Should reward/risk ratio be part of entry
  filter? Is T1/T2/T3 entry level material to IC?
- **God Data**: MAE/MFE/exit_reason data is already being captured — what does it reveal
  about which zone characteristics predict trade outcomes?
- **Macro conditioning**: Can FRED regime (DXY, real yields, VIX) condition zone_score IC?

### 2. ARE Session 0 — Patch ic_engine.py (3 modes)

File: `sigma-are/alpha_engine/core/ic_engine.py`
- Add `signal_mode: Literal['cross_sectional', 'time_series', 'event_time']`
- `event_time` mode: Phase 1 sequential loop → activation timestamps → Phase 2+3 vectorized
- IC decay horizons for event_time in H1 bars: `[1, 4, 8, 24, 48]`
- NW lags = `avg_holding_period_days * 2`

### 3. ARE Session 0 — Patch base.py

File: `sigma-are/alpha_engine/adapters/base.py`
- Allow `load_data()` to return `dict[str, pd.DataFrame]` for multi-TF (gold adapter needs this)

### 4. Design DuckDB Data Layer

- What tables and schema?
- How is point-in-time enforced?
- Sources: yfinance + FRED for equities, MT5 exported CSVs for XAUUSD bars

---

## Key Decisions Made This Session

| Decision | What it says | File |
|----------|-------------|------|
| DEC-005 WITHDRAWN | Cluster pairing was not the root cause of 98% OOS drawdown. Wrong-direction trades were. No cluster fix needed. | decisions.md |
| DEC-008 | B2B gold IC mode = event_time. Phase 1 is sequential loop (intentional). IC computed over event subset only. | decisions.md |
| 3-Room Model | ARE = signal quality gate. LEAN = event-based simulator (mandatory). MT5 = production plumbing test. | RESEARCH_FRAMEWORK.md |
| IC modes (3) | cross_sectional / time_series / event_time. event_time is for sparse strategies like B2B. | RESEARCH_FRAMEWORK.md |
| B2B_STRATEGY_MASTER.md | Single source of truth for B2B strategy. 4 stale docs deleted. Lives in sigma-are/strategies/b2b-gold/. | — |

---

## Blockers

- **Session 0 patches block Session 1**: ic_engine.py is stubbed. No IC can be measured
  until 3-mode patch is applied.
- **Data layer blocks adapters**: Cannot write adapters/equities/data.py until DuckDB
  schema is designed.
- **B2B brainstorm is the current focus**: Do this before writing any B2B adapter code —
  must know what we're measuring before building the measurement tool.

---

## Reference: Updated Workspace Structure

```
baysix-engine/
├── sigma-are/
│   ├── alpha_engine/
│   │   ├── core/
│   │   │   ├── ic_engine.py         ← Session 0: add 3 signal modes (STUBBED)
│   │   │   ├── cost_registry.py     ← Session 0: impact_model + trading_days_per_year (BUILT)
│   │   │   └── regimes.py           ← needs feature_set param
│   │   └── adapters/
│   │       ├── base.py              ← Session 0: loosen load_data() return type (BUILT)
│   │       ├── equities/            ← Session 1 (stubs only)
│   │       └── gold/                ← Phase 1 (does not exist yet)
│   └── strategies/
│       ├── README.md
│       ├── b2b-gold/
│       │   ├── B2B_STRATEGY_MASTER.md  ← NEW THIS SESSION (unified B2B doc)
│       │   ├── hypothesis.md
│       │   ├── config.yaml
│       │   └── decisions.md            ← DEC-005 WITHDRAWN, DEC-008 added
│       ├── xsection-momentum/
│       ├── stat-arb/
│       └── vol-regime/
├── sigma-lean/
├── sigma-mt5/
│   ├── CLAUDE.md                    ← cluster bug section removed
│   └── Documentation/
│       └── modules/                 ← 30 module docs (authoritative source)
│           ├── INDEX.md             ← cluster bug removed
│           └── Detection/
│               └── B2BDetector.md  ← cluster bug note replaced with L1 selection rule
├── brokers/
│   ├── darwinex-zero/
│   ├── retail-prop-firm/
│   ├── high-leverage-broker/
│   ├── ibkr/
│   └── moomoo-webull/
└── Research/
    ├── RESEARCH_FRAMEWORK.md        ← 3-room model + 3 IC modes added
    └── SAMTC/memo_test13a.md        ← Gate 4 PASSED
```
