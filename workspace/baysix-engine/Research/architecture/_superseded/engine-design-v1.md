> **⚠️ SUPERSEDED 2026-05-20 — do not build from this document.**
> Replaced by `../ENGINE_BLUEPRINT.md`. The Sigma Gold System (Co-Work `engine-architecture/`)
> is the canonical architecture. v1's statistical rigor and ADR governance were transplanted into
> the blueprint; its generic ETF universe and horizontal build order were rejected. Kept for provenance only.

---

# Baysix Alpha Research Engine — Design Spec v1.0

**Date:** 2026-05-13  
**Owner:** Syafiq M. Zin — Quant Researcher (Deployable)  
**Status:** SUPERSEDED — see ../ENGINE_BLUEPRINT.md  
**Target:** Balyasny Asset Management + Millennium Management (Tier C) + Malaysia buyside (Kenanga, Affin Hwang, systematic shops)

---

## 1. Purpose

Build a vectorized Python signal evaluation engine that answers one question with institutional rigour:

> **"Is this alpha real, repeatable, and deployable at scale — after all costs, all risks, and all known factors are stripped out?"**

The engine does NOT place orders. It does NOT generate P&L curves. It is a **testing laboratory** — feed it any signal, it outputs a complete Tier C tearsheet. Every number on that tearsheet must be explainable in a Balyasny or Millennium interview without notes.

---

## 2. The 6 Layers

Every engine component belongs to exactly one layer. Nothing is built outside these layers.

```
Layer 1 — Data Integrity          What goes IN
Layer 2 — Signal Construction     How signals are BUILT
Layer 3 — Statistical Validation  Is the alpha REAL?
Layer 4 — Economic Validation     Does it survive COSTS?
Layer 5 — Risk Attribution        What EXPLAINS the return?
Layer 6 — Robustness & Monitoring Does it KEEP working?
```

### Layer 1 — Data Integrity
- Adjusted close prices (splits, dividends corrected)
- Survivorship bias: documented assumption (yfinance gives current constituents — bias is disclosed, not hidden)
- Corporate actions audit: logged in data loader, not silently absorbed
- Stale price detection: forward-fill capped at 3 days (equities) — flagged in tearsheet if breached
- Cross-source: yfinance primary, FRED secondary for macro series
- Point-in-time enforcement: signal at `t` uses only data available before `t`. Enforced by 1-period lag on all signals.

### Layer 2 — Signal Construction
- All signals lagged by 1 period — signal at `t` predicts return at `t+1`. No exceptions.
- Cross-sectional z-score normalisation applied before IC computation
- Adapter pattern: data loading, signal construction, factor models, cost assumptions differ by asset class. Core IC engine never changes.
- Parameter sensitivity: vary each parameter ±20% — signal must remain directionally consistent

### Layer 3 — Statistical Validation
- Spearman rank IC per date
- ICIR = mean(IC) / std(IC)
- Newey-West corrected t-stat (lags=5 for daily data)
- Benjamini-Hochberg multiple testing correction when >1 signal tested simultaneously
- Subsample IC stability: split IS period into thirds — all three must show positive IC
- Rolling IC plot (252-day window): visual signal of decay or drift
- Bootstrap 95% CI on mean IC

Pass gate: IC > 0.03 AND ICIR > 1.0 AND NW t-stat > 2.0 AND subsample IC stable

### Layer 4 — Economic Validation
Full cost model — no partial implementation:

```
Total cost per trade = spread + market impact + borrow cost + stamp duty + financing
Net IC = Gross IC − (total cost × turnover)
```

| Cost component | Default |
|---------------|---------|
| Bid-ask spread | 5 bps (ETFs), 10 bps (equities) |
| Market impact | Almgren square-root model |
| Borrow cost | 0.5%/yr short-side (ETFs) — flagged when higher |
| Stamp duty | 0.1% per trade (Bursa Malaysia) — 0% for US ETFs |
| Financing | SOFR + 150 bps (leveraged positions only) |
| Implementation shortfall | 50% of spread as execution drag estimate |

Malaysia-specific note: 0.1% Bursa stamp duty = 0.2% round-trip. Any short-horizon signal on Bursa stocks must generate >0.2% gross alpha per trade to be economically viable. Engine flags this automatically.

Pass gate: Net IC > 0 after full cost model

### Layer 5 — Risk Attribution
Factor model by asset class (see ADR-001 for full rationale and alternatives):

| Universe | Factor model | Source |
|----------|-------------|--------|
| US equities / ETFs | Fama-French 5 Factor (FF5) | Kenneth French library |
| ASEAN ETFs | MSCI-style regional (Size, Value, Momentum, Quality) | Constructed from regional data |
| Futures | AQR-style (Carry, Momentum, Value, Basis) | Asness et al. / manual |
| Crypto | Custom 4-factor (BTC Beta, Funding, Momentum, Liquidity) | CCXT / Binance |

Outputs:
- Gross alpha (bps/yr)
- Factor betas (static OLS — rolling upgrade path in ADR-001)
- Residual alpha (bps/yr) after factor decomposition
- Residual alpha NW t-stat
- R² (factor-explained variance)

Pass gate: Residual alpha t-stat > 2.0 AND residual alpha positive

### Layer 6 — Robustness & Monitoring
- HMM regime conditioning (3 states: calm-trending, volatile, crisis) — see ADR-002
- IC per regime state: signal must show positive IC in at least 2 of 3 regimes
- Stress periods: compute IC separately for 2008, 2020, 2022 subsamples
- Historical scenario: equity curve if 3 worst months repeat consecutively
- Post-deployment rolling IC tracker: flag if 60-day rolling IC drops below 0.01
- Regime change alarm: flag if P(unknown state) rises above 0.25

---

## 3. Strategy Suite

Five signals run through the same engine. One at a time (Approach C).

| # | Signal | Horizon | Universe | Mechanism |
|---|--------|---------|----------|-----------|
| 1 | **Cross-sectional momentum** | Medium (10–60 day IC) | US SPDR + ASEAN ETFs | Institutional herding, slow information diffusion |
| 2 | **VWAP mean reversion** | Short (1–5 day IC) | US SPDR + ASEAN ETFs | Institutional VWAP anchoring forces price reversion |
| 3 | **Vol Risk Premium (IV rank)** | Medium (weekly rebalance) | ETFs with liquid options | Implied vol systematically exceeds realized vol — premium is harvestable |
| 4 | **Statistical arbitrage** | Short-medium (pair-dependent) | Cointegrated ETF pairs | Structural economic linkage forces spread mean reversion |
| 5 | **Low volatility factor** | Medium (monthly rebalance) | All ETFs | Benchmark-constrained investors overpay for high-vol exposure |

**Signal 1 (momentum) is built first end-to-end before any other signal is touched.**

---

## 4. Universe Design — Single Engine, Dual Universe

One engine. One IC computation method. One tearsheet format.  
What changes per universe: data source, factor model, cost assumptions.

```python
# Same call, different universe
engine.run(signal='momentum', asset_class='equities_us')
engine.run(signal='momentum', asset_class='equities_asean')
```

**US universe:** 11 SPDR sector ETFs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLB, XLU, XLRE, XLC)  
**ASEAN universe:** EWM (Malaysia), EWJ (Japan), EWS (Singapore), EWY (Korea), FXI (China), EWA (Australia)

Portfolio showcase framing: "Same IC methodology, same factor decomp pipeline, same tearsheet — applied to US and ASEAN universes simultaneously. The engine is portable by design."

---

## 5. Multi-Horizon Architecture

The engine handles both short and medium horizon signals in one framework. The IC decay curve is the bridge — it measures IC at every horizon from 1 to 60 days in a single pass.

```
IC decay curve horizons: [1, 5, 10, 20, 60] days

Short-horizon signals (VWAP, IV spike, stat arb):
  → Peak IC expected at day 1–5
  → Rebalance: daily or 2-3x per week
  → Cost drag is proportionally higher — net IC gate is strict

Medium-horizon signals (momentum, low vol, IV cross-section):
  → Peak IC expected at day 10–20
  → Rebalance: weekly or monthly
  → Lower turnover — cost drag more manageable
```

**Decision rule (the "trade the model" principle):**

```
Composite signal = Σ [ ICIR_weighted_signal × P(regime favorable) ]

Momentum        × P(calm-trending regime)      ← medium horizon, up in calm
VWAP reversion  × P(volatile regime)           ← short horizon, up in volatile
IV rank         × P(elevated IV regime)        ← medium horizon
Stat arb        × P(mean-reverting regime)     ← horizon = pair half-life
Low vol         × P(crisis regime)             ← defensive, up in stress

If |composite score| > threshold → deploy
Else → stay flat
```

No human override of the composite score. The model decides.

---

## 6. Signal Combination

**Phase 1 (launch — first 5 signals through engine):** IC-weighted composite.  
Weight each signal proportionally to its ICIR. Higher quality signal gets more weight.

**Phase 2 trigger (see ADR-003):** When all 5 signals are live and running → upgrade to Hierarchical Risk Parity (HRP). HRP does not require inverting a covariance matrix — robust to estimation error.

Signal correlation matrix is computed alongside IC. If any two signals exceed 0.75 correlation — flag it. Combining correlated signals inflates apparent diversification without reducing actual risk.

---

## 7. File Structure

Existing structure — no restructuring needed:

```
workspace/sigma-crypto/alpha_engine/
├── __init__.py                    ← routes asset_class to adapter
├── core/
│   ├── ic_engine.py               ← Layer 3: IC, ICIR, NW t-stat, BH, subsample stability
│   ├── regimes.py                 ← Layer 6: HMM regime detection
│   ├── capacity.py                ← Layer 4: capacity estimate (AUM before alpha decays)
│   └── report.py                  ← Tearsheet generator (all layers → one output)
└── adapters/
    ├── base.py                    ← Abstract interface all adapters implement
    ├── equities/
    │   ├── data.py                ← Layer 1: adjusted close, FRED macro
    │   ├── signals.py             ← Layer 2: momentum, VWAP, low vol, stat arb
    │   ├── factors.py             ← Layer 5: FF5 (US), MSCI regional (ASEAN)
    │   └── costs.py               ← Layer 4: spread + Almgren + borrow + stamp duty
    ├── futures/                   ← Phase 2
    ├── crypto/                    ← Phase 2
    └── options/                   ← Phase 3

Research/architecture/
├── ADR-001-factor-model.md
├── ADR-002-regime-detection.md
├── ADR-003-signal-combination.md
├── ADR-004-ic-method.md
└── ADR-005-cost-model.md
```

---

## 8. Build Sequence — Approach C

One signal end-to-end. Then replicate.

```
Session 1:  data.py — load 11 SPDR ETFs + ASEAN ETFs + FRED macro (VIX, yield curve)
            signals.py — momentum (12-1, 6-1, 3-1), properly lagged
            Test: load → compute signal → verify no look-ahead bias

Session 2:  ic_engine.py — IC, ICIR, NW t-stat, BH correction, subsample stability, rolling IC
            Test: IC and ICIR on momentum signal, verify against literature benchmarks

Session 3:  costs.py — full cost model (spread + Almgren + borrow + stamp duty + IS estimate)
            factors.py — FF5 (US), MSCI regional (ASEAN)
            Test: net IC after costs, residual alpha after factor decomp, dual universe

Session 4:  regimes.py — HMM (3 states), IC per regime, stress period subsamples
            capacity.py — AUM capacity estimate
            Test: IC × regime table, capacity figure

Session 5:  report.py — full Tier C tearsheet
            Test: complete tearsheet for momentum signal, US + ASEAN universe
            Milestone: first portfolio artifact ready

Session 6:  signals.py → add VWAP mean reversion signal
            Test: plug into existing engine → tearsheet (1 session because engine built)

Session 7:  adapters/equities/iv_signals.py → IV rank cross-section (yfinance option chains)
            Test: tearsheet for vol risk premium signal

Session 8:  signals.py → statistical arbitrage (cointegration + z-score)
            Test: pair selection, spread IC, tearsheet

Session 9:  signals.py → low volatility factor
            Test: tearsheet + cross-signal correlation matrix

Session 10: Portfolio construction layer
            Composite IC-weighted signal → HRP upgrade (if all 5 signals pass gates)
            Full multi-signal research memo in Tier C format
```

---

## 9. Deferred Upgrades — ADR Index

Every deliberate deferral is documented. Each ADR defines the exact trigger condition for upgrading.

| ADR | Component | Current | Deferred | Trigger |
|-----|-----------|---------|----------|---------|
| [ADR-001](../../Research/architecture/ADR-001-factor-model.md) | Factor model | FF5 static OLS | Rolling betas, PCA, BARRA | IC unstable across subsamples → rolling betas |
| [ADR-002](../../Research/architecture/ADR-002-regime-detection.md) | Regime detection | HMM 3-state | RS-GARCH, RF classifier | Live signal data >2yrs → RF classifier |
| [ADR-003](../../Research/architecture/ADR-003-signal-combination.md) | Signal combination | IC-weighted | HRP, MVO | All 5 signals live → HRP |
| [ADR-004](../../Research/architecture/ADR-004-ic-method.md) | IC method | Spearman + NW + BH | Partial IC, Mutual Info, Deflated Sharpe | >20 signals tested historically → Deflated Sharpe |
| [ADR-005](../../Research/architecture/ADR-005-cost-model.md) | Cost model | Almgren + spread + stamp duty | Full IS model, Grinold-Kahn | Live execution data available → empirical impact |

---

## 10. Agent Protocol

**Any agent modifying engine components MUST:**

1. Read the relevant ADR before touching the component
2. Check if the trigger condition in the ADR has been met
3. If trigger met → follow the upgrade path documented in the ADR
4. If trigger not met → implement within the current decision, do not deviate from it
5. If proposing a deviation not covered by any ADR → write a new ADR first, get Syafiq approval

No engine component is changed without reading its ADR. This is not optional.

---

## 11. Success Criteria

The engine is operational when:

1. Any signal function → full Tier C tearsheet in < 30 seconds
2. Universe switch via one parameter: `asset_class='equities_us'` vs `asset_class='equities_asean'`
3. Every tearsheet includes: IC, ICIR, NW t-stat, IC decay curve, net IC after costs, residual alpha after factors, IC per HMM regime, capacity estimate
4. All numbers explainable without notes in a Balyasny or Millennium interview
5. `Research/<STRATEGY>/tearsheet_<date>.md` exists as a portfolio artifact for each approved signal
6. Signal correlation matrix computed when ≥2 signals are live

---

## 12. Interview Framing (Tier C Language)

| Never say | Say instead |
|-----------|-------------|
| "I built a backtest" | "I measured the IC and decay profile of this signal" |
| "Sharpe 1.16" | "IC: 0.05, ICIR: 1.2, decay half-life: 12 trading days" |
| "The strategy works" | "61 bps/yr residual alpha survives FF5 decomposition, t-stat 2.4" |
| "OOS degradation 27.5%" | "IC stable IS→OOS, NW t-stat 2.3, subsample IC consistent across all three periods" |
| "I use FF5" | "FF5 for US universe. Custom MSCI-style regional factors for ASEAN — FF5 is US-calibrated and doesn't apply directly to regional ETFs" |
| "We use HMM" | "Probabilistic regime inference via HMM — outputs P(state) continuously, not a binary switch. Momentum runs at full ICIR-weight when P(calm-trending) > 0.6" |

---

*Supersedes: `Braindump/alpha_research_engine_plan.md` (v1) — consolidated into `Research/RESEARCH_FRAMEWORK.md` 2026-05-11*  
*This spec is the implementation blueprint. `Research/RESEARCH_FRAMEWORK.md` is the methodology standard.*
