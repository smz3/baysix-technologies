# Session Handover — May 11, 2026 (Strategy Pivot + Alpha Engine Plan)

## What Was Accomplished This Session

### 1. Target Firms Locked — Tier C Direct Approach
Syafiq confirmed: **Balyasny Asset Management + Millennium Management** are the primary targets. Direct Tier C approach — NOT starting with Tier B (Quantedge, Dymon, GIC).

Career goal chain (explicit, locked):
```
Get QR Job (Balyasny / Millennium)
  → Build institutional experience + auditable P&L track record
    → Launch own systematic fund
      → Grow to Family Office
        → Grow to massive Private Family Office
```

### 2. Firm Landscape Mapped Systematically
Full Singapore quant landscape analysed across 5 market types:
- Options Market Making (Optiver, IMC, Jane Street) — wrong interview profile for current skills
- HFT — not relevant
- Systematic HF / Tier B (Quantedge, Dymon) — deprioritised, not the primary target
- **Multi-Manager Pod Shops / Tier C (Balyasny, Millennium)** — primary target ✅
- Crypto Prop (DRW, GSR) — secondary / backup

Balyasny is more accessible than Millennium at junior QR level. Apply to both simultaneously.

### 3. Critical Language Shift: Tier B → Tier C
Pod shops evaluate alpha attribution, not equity curves:

| Old (Tier B) | New (Tier C — required) |
|-------------|------------------------|
| Sharpe 1.16 | IC: 0.05, ICIR: 1.2 |
| OOS degradation 27.5% | IC stable IS→OOS, t-stat 2.3 |
| Max DD 15% | Residual alpha 60 bps after FF5 decomp |
| Calmar 1.36 | Capacity ~$45M before alpha decays |

### 4. Alpha Research Engine Designed
Full 8-component plan documented at `Braindump/alpha_research_engine_plan.md`.

Components:
1. Data Layer (yfinance + FRED loader)
2. Signal Generator (momentum, z-score, vol regime)
3. IC Engine — IC, ICIR, IC decay curve (the core)
4. Transaction Cost Model (linear + market impact, net IC)
5. Factor Decomposition (Fama-French 5-factor, residual alpha bps/yr)
6. Regime Breakdown (IC by bull/bear, high/low vol, risk-on/off)
7. Capacity Estimator (AUM at which alpha decays to zero)
8. Research Report Generator (Tier C tearsheet → markdown)

File location: `workspace/sigma-crypto/alpha_engine/`

### 5. All Direction Files Updated
Updated to reflect Tier C targeting and IC/ICIR language:
- `CLAUDE.md` — target firms, build order, framing rules
- `AI_INSTRUCTIONS.md` — QR identity, Tier C language
- `AI_REFERENCE.md` — research philosophy, alpha metrics required
- `Research/RESEARCH_FRAMEWORK.md` — Tier C memo format, QR language table, signal registry
- `memory/user_career_goals.md` — career chain, firm targets
- `memory/project_job_applications.md` — Balyasny/Millennium as primaries
- `memory/qr_roadmap.md` — Alpha Research Engine build order, Tier C interview prep

---

## What Is NOT Done / Still Open

- **Alpha Research Engine** — designed, not built. Start with Component 1 (data.py) next session.
- **SAMTC Gate 5 (Monte Carlo)** — still pending. Not urgent until engine is built.
- **LEAN H1 IS backtest** — unknown state. Docker container `e192f80bd287`. Check with `docker ps | grep lean`.
- **Resume rewrite** — deferred by Syafiq. Still says wrong framing. Do AFTER portfolio is built.
- **LinkedIn update** — deferred. Do AFTER portfolio.

---

## Priority for Next Session

1. **Build Component 1: `data.py`** — yfinance loader for 11 SPDR ETFs + FRED macro data
2. **Build Component 2: `signals.py`** — momentum signal (12-1, 6-1, 3-1), properly lagged
3. **Test**: load data → compute signal → confirm no look-ahead bias
4. Then Component 3: `ic_engine.py` — IC, ICIR, IC decay

Read `Braindump/alpha_research_engine_plan.md` for full component specs before starting.

---

## Key Decisions Made This Session

- **Tier C direct**: Balyasny + Millennium without going through Tier B first
- **Pod shop language**: IC/ICIR/factor decomp replaces Sharpe/Calmar/MaxDD as primary output
- **LEAN stays**: Still used for IS/OOS validation. Alpha engine is for alpha attribution — different purpose.
- **5 projects framework (Julian Kam)**: Good for beginners/prop shops. Our projects go deeper with IC analysis.
- **Build order**: Alpha Research Engine first, then plug 3 strategies through it.

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| MT5 XAUUSD live trading | Assumed running | Just Markets live account |
| LEAN H1 IS backtest | Unknown | Check Docker on next session |
| Alpha Research Engine | Not started | Build starts next session |
