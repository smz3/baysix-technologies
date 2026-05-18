# Session Handover — May 15, 2026 (Evening — ARE architecture locked + workspace restructured)

## What Was Accomplished This Session

### 1. New Mission Trajectory Ingested — Darwinex Zero + B2B Architecture Rebuild

Two documents were provided (attached as .md at session start):
- `Darwinex_Zero_Handoff.md` — Darwinex Zero calibration rules, SILVER/GOLD progression, performance fee model, confirmed support answers (√Time is dynamic, homogeneity assessed from executed profile only, green light to deploy)
- `Claude_Code_Handoff_B2B_Architecture.md` — Phase 0 (Python B2B rebuild), Phase 1 (entry sequence, zone score, VaR engine), Phase 2 (regime filter). Three-stage workflow: Python → LEAN → MT5 Strategy Tester.

**Key confirmation from Darwinex support (2026-05-15):**
- √Time assessed dynamically over position lifespan — M5 entry → H4/D1 target (4–24 hr holds) = meaningful exposure score per trade
- Homogeneity assessed from executed profile only — multi-TF confluence fully compatible
- Green light to build and deploy

---

### 2. ARE Architecture Decision — Single Unified Engine, Option A

Brainstorming session resolved the core architectural question: **one Alpha Research Engine (ARE) with parameterized adapters**, not two separate engines.

**Root cause identified by quant-researcher stress-test:** The ARE had 3 implicit assumptions baked in everywhere:
1. Cross-sectional (N assets)
2. Daily frequency
3. Multi-instrument `[dates × assets]` data matrix

B2B/XAUUSD violates all three simultaneously.

**7 Critical issues found (all silent — produce wrong numbers without error):**

| # | Layer | Issue |
|---|-------|-------|
| C1 | IC Engine | Cross-sectional z-score undefined for single instrument |
| C2 | IC Engine | Spearman correlation returns trivial 1.0 in time-series mode |
| C3 | Factor Model | No valid factor model for XAUUSD — FF5 wrong, need DXY/real yield/VIX/oil |
| C4 | Cost Model | Almgren requires ADV; OTC CFD has no ADV — default 0.001 is fabricated |
| C5 | Regime | SPY/VIX inputs wrong for gold — risk-off is gold's BEST regime, labels inverted |
| C6 | Data Pipeline | `load_data()` returns 2D matrix — can't represent 5 simultaneous TFs |
| C7 | IC Engine | "1-period lag" ambiguous across H1/daily frequencies |

**5 targeted fixes (no redesign needed — just parameterisation):**
1. Add `signal_mode='cross_sectional'|'time_series'` to `ic_engine.py` (fixes C1, C2, C7)
2. Create `adapters/gold/` with macro factor model (DXY, real yield, VIX, oil) + XAUUSD regime inputs (fixes C3, C5)
3. Fix OTC CFD cost model — add `impact_model='almgren'|'spread_based'|'fixed_bps'` selector, keep Almgren for exchange-traded instruments (fixes C4)
4. Loosen `base.py` to allow multi-TF dict return from `load_data()` (fixes C6)
5. Add `trading_days_per_year` param to cost model (XAUUSD=261, crypto=365, equities=252) (fixes M7)

**Almgren correction:** "Remove Almgren" was bad advice from earlier analysis. Keep it. Add model selector. CFD gold uses `spread_based`, equities/futures use `almgren`. Nothing gets deleted.

**New build order (Session 0 before Session 1):**
```
Step 0  — Patch ic_engine.py: add signal_mode flag
Step 0  — Patch base.py: allow multi-TF return type
Step 0  — Patch cost_registry.py: add impact_model selector, trading_days_per_year param
Step 1  — Build adapters/equities/ (momentum, as planned)
Step 2  — Build adapters/gold/ (B2B signal wrapper + macro factor model)
```

---

### 3. Workspace Restructured — baysix-engine/

**Old structure:**
```
workspace/
├── sigma-crypto/
├── sigma-lean/
├── sigma-mt5/
├── kronos/
├── freqtrade-kronos/
└── ...
Research/   (at sigma-brain root)
```

**New structure:**
```
workspace/
├── baysix-engine/
│   ├── sigma-are/      ← was sigma-crypto (GitHub remote: smz3/sigma-crypto — unchanged)
│   ├── sigma-lean/
│   ├── sigma-mt5/
│   └── Research/       ← moved from sigma-brain root
├── _archive/
│   ├── kronos/
│   └── freqtrade-kronos/
├── sigma-quant/        ← untouched (deployed)
├── sigma-research/     ← untouched (serves sigma-quant)
└── sigma-linkedin/     ← untouched
```

**Git status of moves:**
- `sigma-are` (.git intact, remote: `smz3/sigma-crypto`) — just a local folder rename
- `sigma-mt5` (.git intact, remote: `smz3/sigma-mt5`) — just a local folder move
- `sigma-lean` (no own git, lives in sigma-brain git) — filesystem move only
- `Research/` (was untracked at root) — moved to `workspace/baysix-engine/Research/`, `.gitignore` updated with `!workspace/baysix-engine/Research/**` exception so sigma-brain still tracks it
- `kronos` (remote: `shiyu-coder/Kronos` — NOT Syafiq's repo) — archived, do not push
- `freqtrade-kronos` (no own git) — archived

**LEAN paths:** `lean.json` uses `"data-folder": "./data"` (relative). Moving sigma-lean into baysix-engine/ did NOT break LEAN — always run `lean` commands from within the `sigma-lean/` directory.

**sigma_core duplication (unresolved — deferred to Phase 0):**
There are 3 copies of the B2B detection code:
- `sigma-are/core/detectors/` — Python research copy
- `sigma-lean/sigma_core/b2b/` — LEAN top-level copy
- `sigma-lean/B2BZoneStrategy/sigma_core/` — LEAN strategy bundle copy (LEAN requires it here)

Phase 0 rebuild will replace all three with one source of truth in `sigma-are/core/`, with sigma-lean importing via symlink or LEAN library path config.

**Files updated:**
- `.gitignore` — added Research/ whitelist exception
- `CLAUDE.md` — updated workspace layout, all Research/ path references
- `AI_REFERENCE.md` — updated project map table, absolute paths, worktree protocol example

**Commit:** `d6c36c1` — "chore: restructure workspace into baysix-engine/ and archive legacy projects"

---

## What Is NOT Done / Still Open

- **ARE Session 0 patches** — `ic_engine.py`, `base.py`, `cost_registry.py` need the 5 targeted fixes before any Session 1 code is written
- **Session 1 not started** — `adapters/equities/data.py` and `signals.py` still stubs (`raise NotImplementedError`)
- **`Research/hypothesis_log.md`** — must be written BEFORE Session 1 code (log H001 cross-sectional momentum hypothesis)
- **`adapters/gold/`** — does not exist yet; B2B adapter is planned but not built
- **Phase 0 B2B rebuild** — cluster bug not yet fixed, OOS still broken (98% DD)
- **sigma_core duplication** — 3 copies of B2B detection code; resolved during Phase 0 rebuild
- **ARE documentation** — ADRs (ADR-001 through ADR-005) were identified as needing updates to reflect Option A multi-mode architecture, but not yet updated this session
- **LEAN H1 IS backtest** — status unknown. Check: `docker ps | grep lean`
- **Darwinex Zero account** — not yet opened; awaiting Phase 0 + Phase 1 completion

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| MT5 XAUUSD live trading | Assumed running | Just Markets live account |
| LEAN H1 IS backtest | Unknown | Check `docker ps \| grep lean` |
| Alpha Research Engine | Not started | Session 0 patches needed first |

---

## Priority for Next Session

1. **ARE Session 0 — Patch `ic_engine.py`**
   - File: `workspace/baysix-engine/sigma-are/alpha_engine/core/ic_engine.py`
   - Add `signal_mode: Literal['cross_sectional', 'time_series'] = 'cross_sectional'` parameter
   - In `time_series` mode: rolling Spearman IC over time axis (not cross-sectional rank)
   - In `time_series` mode: rolling IC decay in H1 bars `[1, 4, 8, 24, 48]`, not calendar days `[1, 5, 10, 20, 60]`
   - NW lags = `avg_holding_period_days * 2` (not hardcoded 5)

2. **ARE Session 0 — Patch `base.py` and `cost_registry.py`**
   - `base.py`: Allow `load_data()` to return `dict[str, pd.DataFrame]` (multi-TF) OR standard tuple; add `signal_mode` to adapter interface
   - `cost_registry.py`: Add `impact_model: Literal['almgren', 'spread_based', 'fixed_bps']` to `CostProfile`; add `trading_days_per_year: int` field; keep Almgren intact, add spread-based path
   - `cfd_gold` profile: set `impact_model='spread_based'`, `trading_days_per_year=261`

3. **Create `Research/hypothesis_log.md`**
   - Log H001: cross-sectional momentum (11 SPDR ETFs, 12-1/6-1/3-1 signals)
   - Template: hypothesis statement, expected IC range, expected decay horizon, why it should work, what would falsify it

4. **Session 1 — `adapters/equities/data.py` and `signals.py`** (as per May 14 handover)

---

## Key Decisions Made

- **Single ARE, Option A**: One engine with 5 parameterisation flags — not two separate engines. The adapter pattern handles all asset-class differences. Complexity is in the parameter design, not the architecture.
- **Almgren stays**: Add `impact_model` selector to `CostProfile`. `almgren` for exchange-traded (equities, futures, ETFs). `spread_based` for OTC CFD (XAUUSD, crypto CFD). Nothing deleted.
- **sigma-crypto renamed to sigma-are**: Local folder name change only. GitHub remote still `smz3/sigma-crypto` — functional, rename on GitHub optionally later.
- **baysix-engine/ as unified container**: sigma-are + sigma-lean + sigma-mt5 + Research/ all under one roof. Research pipeline = research (sigma-are) → validation (sigma-lean) → production (sigma-mt5).
- **kronos/freqtrade-kronos archived**: freqtrade is superseded by sigma-lean. kronos is a third-party repo (shiyu-coder). Both archived to `workspace/_archive/`.
- **Darwinex trajectory confirmed**: B2B gold adapter in ARE is the bridge between live trading (Darwinex income) and QR research (Balyasny/Millennium credentialing). Same IC engine, same Tier C output.

---

## Blockers

- **Session 0 must precede Session 1**: Writing `adapters/equities/signals.py` before patching `ic_engine.py` means building on broken cross-sectional-only foundations. Session 0 patches are a hard prerequisite.
- **Phase 0 B2B**: Must fix cluster bug and validate OOS (Sharpe > 1.0, DD < 15%) before building `adapters/gold/`. The gold adapter wraps the detection engine — if the engine is broken, the adapter measures noise.

---

## Reference: Key File Paths (Updated)

```
workspace/baysix-engine/
├── sigma-are/                              ← GitHub: smz3/sigma-crypto
│   └── alpha_engine/
│       ├── core/
│       │   ├── ic_engine.py               ← Session 0: add signal_mode flag
│       │   ├── cost_registry.py           ← Session 0: add impact_model + trading_days_per_year
│       │   ├── regimes.py                 ← needs feature_set param (XAUUSD inputs differ)
│       │   └── report.py                  ← needs strategy_type param
│       └── adapters/
│           ├── base.py                    ← Session 0: loosen load_data() return type
│           ├── equities/                  ← Session 1 NEXT (data.py, signals.py stubs)
│           └── gold/                      ← Phase 1 (does not exist yet)
├── sigma-lean/
│   └── B2BZoneStrategy/main.py            ← LEAN strategy (sigma_core import)
├── sigma-mt5/
│   └── Documentation/                     ← B2B strategy decisions, cluster fix plan
└── Research/
    ├── RESEARCH_FRAMEWORK.md              ← 8-gate pipeline
    ├── hypothesis_log.md                  ← CREATE THIS (H001 first)
    ├── architecture/
    │   ├── ADR-001 through ADR-005        ← need updates for Option A multi-mode
    │   └── engine-design-v1.md
    └── SAMTC/
        └── memo_test13a.md                ← Gate 4 PASSED
```
