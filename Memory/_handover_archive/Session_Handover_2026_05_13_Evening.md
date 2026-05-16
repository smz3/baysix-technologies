# Session Handover — May 13, 2026 (Evening — Alpha Research Engine Design + Full Brainstorm)

## What Was Accomplished This Session

### 1. Full Engine Design Brainstorm — Locked and Documented

Ran a complete brainstorming session on the Alpha Research Engine. All major decisions locked:

**Strategy suite (5 signals, in build order):**
| # | Signal | Horizon | Mechanism |
|---|--------|---------|-----------|
| 1 | Cross-sectional momentum | Medium (10–60d IC) | Institutional herding |
| 2 | VWAP mean reversion | Short (1–5d IC) | VWAP anchoring — Almgren & Chriss |
| 3 | Vol Risk Premium / IV rank | Medium (weekly) | IV > RV premium, cross-sectional IVR |
| 4 | Statistical arbitrage | Short-medium | Cointegration mean reversion |
| 5 | Low volatility factor | Medium (monthly) | Benchmark-constrained overpay for high vol |

**Key architectural decisions:**
- **Single engine, dual universe** — one parameter swap: `asset_class='equities_us'` vs `asset_class='equities_asean'`
  - US: 11 SPDR sector ETFs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLB, XLU, XLRE, XLC)
  - ASEAN: EWM, EWJ, EWS, EWY, FXI, EWA
- **Multi-horizon** — IC decay at [1, 5, 10, 20, 60] days covers both short and medium horizon signals
- **HMM regime detection** — 3 probabilistic states (calm-trending / volatile / crisis), not VIX threshold
- **Build approach: Approach C** — momentum end-to-end first (Sessions 1–5 = first full tearsheet), then each subsequent signal plugs in (1 session each)
- **Signal combination** — IC-weighted Phase 1, upgrade to HRP when all 5 signals live (see ADR-003)
- **SME pillars locked** — Implied Volatility (IV rank, VRP, option chain) + Hidden Markov Models

**The 6 engine layers (every component belongs to one):**
```
Layer 1 — Data Integrity
Layer 2 — Signal Construction
Layer 3 — Statistical Validation  (Spearman IC, ICIR, NW t-stat, BH, subsample stability)
Layer 4 — Economic Validation     (spread + Almgren + borrow + stamp duty)
Layer 5 — Risk Attribution        (FF5 US / MSCI ASEAN / Custom 4F crypto)
Layer 6 — Robustness & Monitoring (HMM 3-state conditioning)
```

**Malaysia buyside added as secondary target** — Type B (Kenanga, Affin Hwang) + Type C (systematic/prop shops KL). NOT government-linked (EPF, Khazanah, PNB).

---

### 2. Full Design Spec Written + 5 ADRs Created

**Design spec:** `Research/architecture/engine-design-v1.md`

**ADRs** (Architecture Decision Records) — the governance safety net. Each documents: what was decided, why, every alternative considered, and exact trigger conditions for upgrading:

| File | Component | Current → Trigger |
|------|-----------|------------------|
| `Research/architecture/ADR-001-factor-model.md` | Factor model | FF5 static OLS → rolling betas when IC unstable across subsamples |
| `Research/architecture/ADR-002-regime-detection.md` | Regime detection | HMM 3-state → RF classifier when live signal data >2yr |
| `Research/architecture/ADR-003-signal-combination.md` | Signal combination | IC-weighted → HRP when all 5 signals live |
| `Research/architecture/ADR-004-ic-method.md` | IC method | Spearman/NW/BH → Deflated Sharpe when >20 signals tested |
| `Research/architecture/ADR-005-cost-model.md` | Cost model | Almgren + stamp duty → empirical IS when live execution data available |

**ADR governance rule:** Any agent modifying an engine component MUST read the relevant ADR first, check trigger conditions, and only deviate by writing a new ADR with Syafiq approval. This is in `CLAUDE.md`-equivalent scope — apply it to all future builds.

---

### 3. RESEARCH_FRAMEWORK.md Updated to v3.0

`Research/RESEARCH_FRAMEWORK.md` — targeted updates:
- Added Malaysia buyside as secondary target
- Gate 3 now requires subsample IC stability, bootstrap CI, rolling IC plot (new requirements)
- Regime section replaced with HMM 3-state model (was simple VIX threshold)
- Build sequence updated to Approach C 10-session plan with dual universe
- Signal registry updated to 5 strategies + SAMTC reframe + HMM conditioner
- New Part 6: ADR Governance with trigger table + links to ADR files
- Part 7: Agent Responsibilities (renumbered)

---

### 4. _MEMO_TEMPLATE.md Fully Rewritten

`Research/_MEMO_TEMPLATE.md` — complete restructure to Tier C tearsheet format:
- **Leads with IC analysis** (Sections 3–7) before LEAN equity curve results (Section 8)
- New sections: IC analysis (with subsample stability), cost model, factor decomp, regime breakdown, capacity estimate
- Section 11 "Tier C Verdict" has a pre-filled **interview sentence template** — fill in numbers, ready to say in any Balyasny/Millennium interview
- Gate table extended to all 13 pipeline stages

---

### 5. All Memory Saved

6 memory files written/updated in `C:\Users\User\.claude\projects\c--Users-User-Desktop-sigma-brain\memory\`:

| File | Action | Content |
|------|--------|---------|
| `user_sme_focus.md` | NEW | IV + HMM as SME pillars, combined thesis sentence |
| `feedback_adr_governance.md` | NEW | ADR rule — applies to ALL future builds |
| `project_engine_design.md` | NEW | Design locked, file locations, build state |
| `user_career_goals.md` | Updated | Malaysia B+C firms added as secondary target |
| `project_job_applications.md` | Updated | Kenanga/Affin Hwang/KL systematic shops added |
| `qr_roadmap.md` | Updated | 5 strategies, dual universe, Approach C, ADR governance |

---

### 6. File Consolidation

- Moved spec from `docs/superpowers/specs/` → `Research/architecture/engine-design-v1.md`
- Deleted `docs/` folder entirely — not appropriate for this project structure
- All research design artifacts now live under `Research/` — single unified folder

---

## What Is NOT Done / Still Open

- **Alpha engine implementation** — ALL files are stubs (`raise NotImplementedError`). Zero code written. Design only.
- **Session 1 not started** — `data.py` and `signals.py` are next to implement
- **`Research/hypothesis_log.md`** — file referenced in RESEARCH_FRAMEWORK.md but not yet created
- **SAMTC IC reframe** — SAMTC Gate 4 passed but IC/ICIR metrics not computed yet. Needs crypto adapter (Session 7)
- **LEAN H1 IS backtest** — status unknown. Docker container `e192f80bd287`. Check with `docker ps | grep lean`
- **Resume rewrite** — deferred. Do AFTER portfolio artifacts exist
- **LinkedIn update** — deferred. Do AFTER portfolio

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| MT5 XAUUSD live trading | Assumed running | Just Markets live account |
| LEAN H1 IS backtest | Unknown | Check Docker on next session — `docker ps | grep lean` |
| Alpha Research Engine | Not started | All stubs — Session 1 is next |

---

## Priority for Next Session

1. **Start Session 1 — `adapters/equities/data.py`**
   - Load 11 SPDR ETFs + ASEAN ETFs via yfinance
   - Load FRED macro (VIX = `^VIX`, yield curve = `DGS10` minus `DGS2`)
   - `compute_returns()` from adjusted close prices
   - Test: load → verify no NaN gaps beyond 3 days, check date alignment
   - File: `workspace/sigma-crypto/alpha_engine/adapters/equities/data.py`

2. **Session 1 continued — `adapters/equities/signals.py`**
   - Implement `momentum(returns, lookback, skip=1)` for 12-1, 6-1, 3-1 lookbacks
   - Lag by 1 period — signal at `t` predicts return at `t+1`
   - Cross-sectional z-score normalisation
   - Test: compute signal, verify no look-ahead bias, check z-score distribution
   - File: `workspace/sigma-crypto/alpha_engine/adapters/equities/signals.py`

3. **Create `Research/hypothesis_log.md`** — log H001 (momentum) with full hypothesis template before touching code

4. **Check LEAN Docker** — `docker ps | grep lean` — confirm H1 IS backtest state

---

## Key Decisions Made This Session

- **Approach C locked** — one signal (momentum) end-to-end first, then replicate. Non-negotiable.
- **HMM over VIX threshold** — probabilistic regime output is the core reason. P(crisis)=0.7 > binary flag.
- **ADR governance** — every major component decision gets an ADR with trigger conditions. Safety net against future agent drift.
- **Malaysia B+C as secondary target** — private AMs + systematic shops, NOT government-linked. Different language than Tier C pod shops.
- **SME pillars** — IV rank + HMM is the differentiated thesis. Most QRs use VIX > 20. We use HMM on IV surface inputs.
- **Full cost model mandatory** — no partial implementation. Stamp duty (Bursa 0.1%) must be included for Malaysia signals.
- **Dual universe, single engine** — not two separate engines. One parameter swap. Portfolio showcase: "same IC methodology, same tearsheet, portable by design."
- **Spec moved** — `docs/superpowers/specs/` deleted. All design artifacts under `Research/architecture/`.

---

## Blockers

- None for Session 1 — data.py can be started immediately
- yfinance availability: verify `pip install yfinance pandas-datareader statsmodels hmmlearn` in sigma-crypto environment before Session 1

---

## Reference: Full File Map

```
Research/
├── RESEARCH_FRAMEWORK.md             ← v3.0 (updated this session)
├── _MEMO_TEMPLATE.md                 ← Tier C format (rewritten this session)
├── architecture/
│   ├── engine-design-v1.md           ← master design spec
│   ├── ADR-001-factor-model.md
│   ├── ADR-002-regime-detection.md
│   ├── ADR-003-signal-combination.md
│   ├── ADR-004-ic-method.md
│   └── ADR-005-cost-model.md
└── SAMTC/
    └── memo_test13a.md

workspace/sigma-crypto/alpha_engine/
├── __init__.py
├── core/
│   ├── ic_engine.py    ← STUB — Session 2
│   ├── regimes.py      ← STUB — Session 4
│   ├── capacity.py     ← STUB — Session 4
│   └── report.py       ← STUB — Session 5
└── adapters/equities/
    ├── data.py         ← STUB — Session 1 NEXT
    ├── signals.py      ← STUB — Session 1 NEXT
    ├── factors.py      ← STUB — Session 3
    └── costs.py        ← STUB — Session 3
```
