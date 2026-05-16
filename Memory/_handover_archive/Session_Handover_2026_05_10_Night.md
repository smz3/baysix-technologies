# Session Handover — May 10, 2026 (Night — Strategic pivot to QR + Research Framework built)

## What Was Accomplished This Session

### 1. Career Trajectory Reframed: QD → Quant Researcher (Deployable)
First-principles analysis confirmed the correct career path is **Quant Researcher (deployable)**, not AI Quant Developer.
- QD path leads to Senior QD ceiling — does not lead to running a fund
- QR path: Junior QR → Senior QR → PM → Family Office (the actual goal)
- "Deployable" QR = owns the full loop (signal discovery → backtest → LEAN validation → live deployment)
- Work-life balance: QR works in research cycles, not daily screen-watching like QT

**Key insight:** 7yr live trading experience is a QR differentiator — most academic QRs have never placed a real trade.

**Geographic target:** Singapore (Quantedge, Dymon Asia, GIC/Temasek) — Malaysia ceiling too low (~RM20k/month).

### 2. Strategic Direction Plan Finalized (3 Decisions)
**Decision 1 — Market Focus: ETF**
- Universe: 11 SPDR sector ETFs first, then factor ETFs (MTUM, QUAL, USMV), then crypto ETFs (IBIT)
- First strategy: cross-sectional momentum ranked monthly (12-1 momentum), FRED macro regime gate
- Skip ASEAN ETFs — too thin for systematic work
- FRED integration already live in sigma-research → direct bridge to ETF macro filter

**Decision 2 — Language Priority**
| Language | Action | Timeline |
|----------|--------|----------|
| Python | Deepen: polars, numba, asyncio, pydantic | Now → 6 months |
| kdb+/q | One real project (1yr SPY 1-min, VWAP) | Months 6–12 |
| Rust | Nautilus Python API only — don't write it | Month 18+ |
| C++ | Skip entirely | Indefinitely |

**Decision 3 — LEAN + Nautilus Architecture**
- LEAN: signal research → IS/OOS validation (permanent role)
- Nautilus Trader: paper trading → live execution (add only after LEAN OOS confirmed)
- Gate: LEAN IS Sharpe ≥ 1.0 AND OOS degradation < 30% before touching Nautilus

### 3. Baysix 8-Gate Research Framework Built
Created the institutional QR signal validation pipeline. All future signals follow this process — no gates skipped.

**Files created:**
- `Research/RESEARCH_FRAMEWORK.md` — 8-gate pipeline with pass/fail criteria, agent responsibilities, signal registry
- `Research/_MEMO_TEMPLATE.md` — reusable 1-2 page research memo template
- `Research/SAMTC/memo_test13a.md` — first completed QR portfolio piece (real tearsheet numbers)

**8-Gate pipeline:**
```
GATE 0  Hypothesis        GATE 4  OOS Validation
GATE 1  Data Audit        GATE 5  Stress Testing
GATE 2  Signal Construct  GATE 6  Research Memo ← portfolio piece
GATE 3  IS Validation     GATE 7  Paper Trading
                          GATE 8  Live Deployment
```

### 4. SAMTC Test 13A Research Memo Completed
First real QR portfolio piece written at `Research/SAMTC/memo_test13a.md`.

**Actual tearsheet numbers (extracted from HTML):**
| Metric | IS (2020-2022) | OOS (2024-2025) | Degradation |
|--------|---------------|-----------------|-------------|
| Sharpe | 1.60 | **1.16** | ▼ 27.5% (passes <30% gate, marginal) |
| Sortino | 2.78 | **2.39** | ▼ 14% |
| Calmar | 0.60 | **1.36** | ▲ improved |
| CAGR | 60.35% | **114.75%** | ▲ improved |
| Max DD | 99.95% | **84.55%** | Compounded curve — not position-sized |
| Payoff | 1.53 | **1.65** | ▲ improved |
| Skew | — | **3.43** | Positive fat right tail |
| Prob. Sharpe | 99.97% | **99.68%** | Signal is statistically real |

**Gate 4 verdict: PASSED** (marginal on Sharpe degradation — 27.5% vs 30% threshold)  
**Memo verdict: CONDITIONAL DEPLOY** — Gate 5 (Monte Carlo) and LEAN cross-validation must complete first.

**Important note on Max DD:** The 84.55% and 99.95% DDs are on a compounded equity curve with no position sizing. Under Baysix risk framework (1-2% Kelly), account-level Max DD is estimated <10%. Memo explains this clearly.

### 5. All Agent Files Updated to QR Standard
Updated `CLAUDE.md`, `GEMINI.md`, `AI_REFERENCE.md`, `AI_INSTRUCTIONS.md` — all now carry:
- QR identity (not AI Quant Dev)
- Research framework reference (read `Research/RESEARCH_FRAMEWORK.md` before any strategy task)
- QR language standards (framing rules)
- `Research/` directory documented in workspace layout

Updated memory files:
- `user_career_goals.md` — QR → PM → Family Office trajectory
- `user_career_transition.md` — "AI Quant Dev" retired, QR locked
- `project_job_applications.md` — Singapore QR targets, old apps marked stale
- `qr_roadmap.md` — new file, full skill gap analysis and interview prep questions

---

## What Is NOT Done / Still Open

- **LEAN H1 IS backtest** — was running in Docker (`e192f80bd287`) at session start. Unknown if still running or completed. Check immediately.
- **Gate 5 (Stress Testing)** — Monte Carlo (3 methods) not yet run. Required before SAMTC paper trading.
- **Deflated Sharpe Ratio** — not yet implemented in sigma-crypto. Required for Gate 3 completion.
- **ETF cross-sectional momentum strategy** — planned, not started. First new QR piece.
- **sigma-research Cloud Run deployment** — still blocked (Vector DB offline). Secondary priority.
- **Resume rewrite** — still says "AI Quant Dev" framing. Needs QR language + alpha evidence front and centre.
- **LinkedIn headline** — likely still says old framing. Needs update via sigma-linkedin.

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| LEAN H1 IS backtest (BTC/USDT) | Unknown — was running at session start | Docker: `e192f80bd287`. Check with `docker ps \| grep lean` |
| MT5 XAUUSD live trading | Assumed running | Just Markets live account |

---

## Priority for Next Session

1. **Check LEAN backtest result** — `docker ps | grep lean` → if done, `ls -lt workspace/sigma-lean/B2BZoneStrategy/backtests/ | head -3`, then run `/check-lean-health` to parse results
2. **If IS Sharpe ≥ 1.0**: run OOS backtest (2023-2025) — change dates in `workspace/sigma-lean/B2BZoneStrategy/main.py` lines SetStartDate/SetEndDate
3. **After OOS confirmed**: implement Deflated Sharpe Ratio in `workspace/sigma-crypto/` evaluation module (Bailey & de Prado 2014)
4. **Run Monte Carlo** (Gate 5) for SAMTC to complete the stress testing section of `Research/SAMTC/memo_test13a.md`
5. **Start ETF momentum strategy** — yfinance data, 11 SPDR sectors, FRED macro gate — first new QR portfolio piece

---

## Key Decisions Made

- **QR over QD**: First-principles analysis confirmed QR is the only path that leads to running a fund. QD is a support role with a ceiling.
- **ETF as primary market**: Universal benchmark, clean data, richest strategy library, best interview credibility.
- **Python → kdb+/q sequence**: Don't learn C++. kdb+/q is the tier 1 differentiator for ASEAN.
- **LEAN before Nautilus**: Nautilus only after LEAN OOS confirmed. Two systems debugging simultaneously is a trap.
- **Research memos are mandatory**: Every signal that passes Gate 4 gets a memo. No exceptions. The thesis (`samtc_sr.pdf`) is methodology — the memo is evidence.
- **Sharpe degradation threshold: 27.5%** — SAMTC is marginal. This is honest and must be stated in interviews.

---

## Blockers

- **Gate 5 (Monte Carlo)**: Blocked on Deflated Sharpe implementation first. Build DSR, then run Monte Carlo.
- **Nautilus paper trading**: Blocked on LEAN OOS result — cannot proceed without it.
- **ETF strategy**: No blocker — can start anytime with `yfinance`. First action is data acquisition and FRED macro filter design.
