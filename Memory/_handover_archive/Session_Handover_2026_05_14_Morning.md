# Session Handover — May 14, 2026 (Morning — Cost Registry Build + Architecture Deep-Dives)

## What Was Accomplished This Session

### 1. Cost Registry Built — `core/cost_registry.py` (NEW FILE)

Created `workspace/sigma-crypto/alpha_engine/core/cost_registry.py` — the single source of truth for all cost model parameters across the engine.

**What's in it:**
- `CostProfile` dataclass (frozen=True) — 12 fields covering every cost component
- `InvestorProfile` dataclass (frozen=True) — captures tax treatment + commission tier by entity
- `COST_REGISTRY` — 8 asset class profiles: `us_etf`, `europe_etf`, `asia_etf`, `my_equity`, `us_equity`, `futures`, `spot_fx`, `cfd_gold`
- `INVESTOR_PROFILES` — 2 profiles: `individual_my` (IBKR, 30% WHT), `institutional_my` (Kenanga/Affin Hwang, 8 bps negotiated)
- 3 computation functions: `almgren_impact_bps()`, `total_cost_bps()`, `net_ic_after_costs()`

**Key design decision:** Every adapter (`adapters/*/costs.py`) imports from this registry. No hardcoded cost numbers anywhere else.

**3 bugs caught by review agents before merge:**

| Bug | Severity | Fix Applied |
|-----|----------|-------------|
| Stamp duty applied one-way only | Medium | `2.0 ×` for round-trip (buy + sell both incur duty) |
| IS applied to half-spread, not round-trip | Medium | `2.0 ×` for entry + exit IS |
| Net IC formula: `bps / 10_000` instead of `bps / (σ_annual × 10_000)` | **Critical** | Fixed to Grinold-Kahn vol-normalised form — costs appeared 6× smaller, weak signals falsely passed gate |

**The corrected net IC formula (line ~410 of cost_registry.py):**
```python
vol_annual = daily_vol * (252 ** 0.5)
net = round(gross_ic - (costs['total'] / (vol_annual * 10_000)), 6)
```

---

### 2. ADR-005 Updated

`Research/architecture/ADR-005-cost-model.md` updated with:
- New **Registry Architecture** section documenting the 8-profile / 2-investor-profile structure
- Table of all 8 asset classes with WHT and short-restriction flags
- 3 new cost components now explicitly documented: dividend WHT, broker commission, FX conversion
- **Upgrade 4** added: per-ticker parameter overrides (trigger: universe > 50 names)
- Interview defence updated to include dividend WHT language and the full 8-asset-class framing

---

### 3. Architecture Deep-Dives (Educational — No Code Changes)

Several conceptual questions resolved during session:

**Languages for the engine:**
- Python (pandas) is correct for the research/backtesting lab — confirmed and locked
- Polars swap trigger: when universe scales beyond ~200 names OR intraday data added (not just ETF count)
- OCaml: Wrong tool — no quant finance library ecosystem, used at Jane Street for execution not research
- Rust: Wrong for research layer — correct for future execution engine at fund launch stage
- Execution engine for IBKR paper trading: Python + `ib_insync` is sufficient (daily/weekly ETF rebalancing, no sub-second latency required)

**Multi-agent architecture for engine build:**
- Sessions 1-2 (now): single quant-developer + code-reviewer pipeline
- Sessions 3-5 (signals 2-5): parallel quant-developer agents in git worktrees (interfaces must be locked first)
- Prerequisite for parallelism: function signatures + column names spec written before spawning

**Tax clarification for Malaysian investor trading US ETFs:**
- Liquidating position (capital gains): 0% US tax, 0% Malaysian CGT
- Dividends: 30% US WHT — deducted automatically by IBKR
- This 30% WHT is now in the cost registry for `us_etf`, `asia_etf`, `us_equity`
- Ireland-domiciled ETFs (CSPX, IWDA): 0% WHT at distribution level — structural advantage for income strategies
- `europe_etf` profile reflects this correctly

**Execution bridge (IBKR paper trading) — what it needs:**
- Signal consumer (engine-lab output) → position sizing → order generator → `ib_insync` → IBKR paper
- Build AFTER Session 5 (first validated tearsheet exists)
- ADR-005 Upgrade 2 trigger: 6 months live fill data → swap Almgren estimates for empirical IS model

---

## What Is NOT Done / Still Open

- **Session 1 not started** — `data.py` and `signals.py` are still stubs (`raise NotImplementedError`)
- **`adapters/equities/costs.py`** — still stub. Needs to import from `cost_registry.py` and implement functions using the registry (Session 3)
- **`Research/hypothesis_log.md`** — referenced in RESEARCH_FRAMEWORK.md but not yet created. Must be written BEFORE Session 1 code
- **LEAN H1 IS backtest** — status unknown. Check with `docker ps | grep lean`
- **Resume rewrite** — deferred until portfolio artifacts exist (post Session 5)
- **LinkedIn update** — deferred until portfolio exists

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| MT5 XAUUSD live trading | Assumed running | Just Markets live account |
| LEAN H1 IS backtest | Unknown | Check `docker ps | grep lean` on next session |
| Alpha Research Engine | Not started | All stubs — Session 1 is next |

---

## Priority for Next Session

1. **Create `Research/hypothesis_log.md`** — log H001 (cross-sectional momentum) before any code. Template: hypothesis statement, expected IC range, expected decay horizon, why it should work, what would falsify it.

2. **Start Session 1 — `adapters/equities/data.py`**
   - File: `workspace/sigma-crypto/alpha_engine/adapters/equities/data.py`
   - Load 11 SPDR ETFs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLB, XLU, XLRE, XLC) + ASEAN ETFs (EWM, EWJ, EWS, EWY, FXI, EWA) via yfinance
   - Load FRED macro: VIX (`^VIX`), yield curve (`DGS10` minus `DGS2`)
   - `compute_returns()` from adjusted close prices
   - Verify: no NaN gaps beyond 3 days, date alignment correct, forward-fill capped
   - Check `pip install yfinance pandas-datareader statsmodels hmmlearn` in sigma-crypto env first

3. **Session 1 continued — `adapters/equities/signals.py`**
   - File: `workspace/sigma-crypto/alpha_engine/adapters/equities/signals.py`
   - `momentum(returns, lookback, skip=1)` for 12-1, 6-1, 3-1 lookbacks
   - Lag by 1 period — signal at `t` predicts return at `t+1`. No exceptions.
   - Cross-sectional z-score normalisation
   - Test: no look-ahead bias, z-score distribution ~N(0,1)

4. **Check LEAN Docker** — `docker ps | grep lean`

---

## Key Decisions Made

- **Cost registry pattern locked**: Single `core/cost_registry.py` file. All adapters import from it. No per-adapter cost hardcoding.
- **Net IC formula is Grinold-Kahn vol-normalised**: `net_ic = gross_ic - (cost_bps / (σ_annual × 10_000))`. Simplified form `bps / 10_000` rejected — makes costs 6× too small in IC space.
- **Stamp duty is round-trip**: 0.1% Bursa stamp duty applies on buy AND sell. Round-trip = 0.2%. Registry applies `2×` multiplier.
- **Dividend WHT is a real engine cost**: 30% on US ETF dividends for Malaysian individual investors. Now captured in `dividend_withholding_rate` field and activated via `investor.applies_dividend_wht`.
- **Two investor profiles locked**: `individual_my` (IBKR, 30% WHT) and `institutional_my` (Kenanga/Affin Hwang, 8 bps commission, no WHT).
- **Python stays as engine language**: Confirmed. Polars upgrade is triggered by data volume (not ETF count). Rust/C++ deferred to execution engine at fund launch stage.
- **IBKR paper trading bridge is Python**: `ib_insync` wrapper. Build after Session 5. No Rust/C++ needed for daily/weekly ETF signal execution.

---

## Blockers

- **Session 1 prerequisite**: Verify Python environment in sigma-crypto has required packages before writing code: `yfinance`, `statsmodels`, `hmmlearn`, `pandas-datareader`. Run `pip list | grep -E "yfinance|statsmodels|hmmlearn"` first.
- None for the cost registry — it's complete and reviewed.

---

## Reference: Key File Paths

```
workspace/sigma-crypto/alpha_engine/
├── core/
│   └── cost_registry.py        ← NEW this session — 8 profiles, 2 investor types, 3 functions
├── adapters/equities/
│   ├── data.py                 ← STUB — Session 1 NEXT
│   ├── signals.py              ← STUB — Session 1 NEXT
│   ├── factors.py              ← STUB — Session 3
│   └── costs.py                ← STUB — Session 3 (import from cost_registry)

Research/
├── RESEARCH_FRAMEWORK.md       ← v3.0
├── _MEMO_TEMPLATE.md           ← Tier C format
├── architecture/
│   ├── engine-design-v1.md     ← master design spec
│   ├── ADR-001-factor-model.md
│   ├── ADR-002-regime-detection.md
│   ├── ADR-003-signal-combination.md
│   ├── ADR-004-ic-method.md
│   └── ADR-005-cost-model.md   ← UPDATED this session — registry architecture documented
└── SAMTC/
    └── memo_test13a.md
```
