# Baysix Research Framework — Master Document
**Version**: 3.0  
**Created**: 2026-05-10 | **Consolidated**: 2026-05-11 | **Updated**: 2026-05-13  
**Owner**: Syafiq M. Zin — Quant Researcher (Deployable)  
**Primary Target**: Balyasny Asset Management + Millennium Management (Tier C pod shop QR roles, Singapore)  
**Secondary Target**: Kenanga, Affin Hwang, systematic/prop shops KL (Malaysia private AMs + systematic shops)

> Every signal at Baysix passes through this pipeline. No gate is skipped. No signal reaches capital without clearing all gates. The Alpha Research Engine is the tooling that automates Gates 0–6.

---

## The Full Pipeline (Stage Map)

```
Stage 0   Hypothesis Engine     ← Paper synthesis → derivative hypotheses → your approval
Stage 1   Universe Construction ← adapters/*/data.py
Stage 2   Signal Construction   ← adapters/*/signals.py
Stage 3   IC Screen             ← core/ic_engine.py          ┐
Stage 4   Cost Screen           ← adapters/*/costs.py        │  Alpha Research Engine
Stage 5   Factor Decomposition  ← adapters/*/factors.py      │  (what we're building)
Stage 6   Regime Breakdown      ← core/regimes.py            │
Stage 7   Capacity Estimate     ← core/capacity.py           ┘
Stage 8   IS Validation         ← LEAN CLI (exists)          ┐
Stage 9   OOS Validation        ← LEAN CLI (Test 13A done)   │  LEAN Layer
Stage 10  Monte Carlo           ← LEAN CLI                   ┘
Stage 11  Research Memo         ← core/report.py → Research/<STRATEGY>/tearsheet_<date>.md
Stage 12  Portfolio Construction← planned (after engine done)
Stage 13  Shadow Trading        ← MT5 demo
Stage 14  Live Deployment       ← MT5 live (XAUUSD active)
```

**Gate mapping (legacy 8-gate → stage map):**

| Gate | Stage | Tool |
|------|-------|------|
| Gate 0 — Hypothesis | Stage 0 | Hypothesis Engine |
| Gate 1 — Data Audit | Stage 1 | adapters/*/data.py |
| Gate 2 — Signal Construction | Stage 2 | adapters/*/signals.py |
| Gate 3 — IS Validation | Stage 3–8 | IC Engine + LEAN |
| Gate 4 — OOS Validation | Stage 9 | LEAN CLI |
| Gate 5 — Stress Testing | Stage 10 | LEAN Monte Carlo |
| Gate 6 — Research Memo | Stage 11 | report.py tearsheet |
| Gate 7 — Shadow Trading | Stage 13 | MT5 demo |
| Gate 8 — Live Deployment | Stage 14 | MT5 live |

---

## Part 1: The Gates (Methodology)

### Gate 0 — Hypothesis

**Question:** What market inefficiency does this signal exploit, and why does it exist structurally?

**The synthesis rule:** Papers do the expensive work — proving a mechanism exists on a clean sample over years of data. The Hypothesis Engine extracts the underlying logic and proposes derivative hypotheses adapted to our universe. We are NOT copying signals from papers. We are identifying transferable mechanisms.

**Example of correct synthesis:**
```
Paper proves: VWAP deviation predicts mean-reversion (institutional order flow anchoring)
We derive:    Does daily VWAP deviation in SPDR ETFs predict next-day reversal?
              Does funding-rate-weighted price in BTC perps predict 8h mean-reversion?
These are derivative applications of the mechanism — not replications of the paper's signal.
```

**Hypothesis template (required before Stage 1):**

```markdown
Signal:        [exact function signature]
Universe:      [asset class, instruments, liquidity filter]
Horizon:       [expected holding period]
Mechanism:     [1 sentence — WHY this works structurally]
Source paper:  [title, authors, year — the mechanism evidence]
Kill criteria: [specific IC / t-stat threshold that falsifies this]
```

**Pass criteria:** Mechanism can be stated without referencing backtest results. If you need the backtest to explain why the signal should work, the hypothesis is post-hoc — FAIL.

**Hypothesis log:** `Research/hypothesis_log.md` — all proposals (approved + rejected). Negative results are logged.

---

### Gate 1 — Data Audit

**Question:** Is the data clean, point-in-time, and free of biases that inflate returns?

**Required:**
- Source documented (yfinance, CCXT, Binance API, FRED, Kenneth French library)
- Survivorship bias check — use point-in-time index constituents, include delisted assets
- Corporate action adjustment confirmed (dividends, splits — adjusted close prices)
- Look-ahead bias check: signal at `t` uses only data available before `t`
- No forward-fill beyond 5 days (equities) | ratio roll adjustment (futures) | UTC daily close alignment (crypto)

**Pass criteria:** All checklist items confirmed. Any unknown bias = automatic FAIL until resolved.

---

### Gate 2 — Signal Construction (IS Only)

**Question:** Does the signal show evidence of alpha in the in-sample period?

**Required:**
- Signal built on IS data only — OOS period sealed, untouched
- All signals lagged by 1 period — signal at `t` predicts return at `t+1`, never `t+0`
- Cross-sectional z-score normalisation applied
- Parameter sensitivity: vary each parameter ±20%, confirm signal remains directionally consistent
- No curve-fitting: parameters chosen on structural logic, not maximum IS Sharpe

**Pass criteria:** IS Sharpe > 0.5 with minimum 30 trades. Parameters are logic-driven, not optimised.

---

### Gate 3 — IS Validation (Statistical Significance)

**Question:** Is the alpha statistically significant in-sample?

**Required (IC Engine outputs):**
- IC > 0.03 (tradeable) | ICIR > 1.0 (consistent) | NW-corrected t-stat > 2.0 (significant)
- IC decay curve — does the signal have a meaningful half-life? Horizons: [1, 5, 10, 20, 60] days
- Benjamini-Hochberg correction applied when testing >1 signal simultaneously
- **Subsample IC stability: split IS into thirds — all three sub-periods must show positive IC**
- **Bootstrap 95% CI on mean IC — point estimate alone is insufficient**
- **Rolling IC plot (252-day window) — visual confirmation of stability, not just aggregate mean**
- Factor attribution: residual alpha positive after factor decomposition

**Pass criteria:** IC > 0.03 AND ICIR > 1.0 AND NW t-stat > 2.0 AND subsample IC positive in all three periods AND residual alpha t-stat > 2.0

---

### Gate 4 — OOS Validation

**Question:** Does the signal hold on data it never touched during construction?

**Required:**
- OOS period strictly separated — no parameter adjustments after seeing OOS results
- IC stable IS→OOS (IC degradation < 30%)
- LEAN CLI enforces IS/OOS separation — no manual override

**Pass criteria:**

| Metric | Pass Threshold |
|--------|---------------|
| OOS Sharpe | > 0.5 (crypto) / > 1.0 (equities) |
| Sharpe degradation IS→OOS | < 30% |
| OOS Calmar | > 1.0 |
| OOS trade count | ≥ 30 trades |
| IC stable IS→OOS | Degradation < 30% |

---

### Gate 5 — Stress Testing

**Question:** Does the signal survive adversarial conditions?

**Required:**
- Monte Carlo (3 methods): Trade Shuffle + Parametric + Block Bootstrap (10,000 paths each)
- Slippage sensitivity: add 0.1%, 0.3%, 0.5% per-trade slippage, record Sharpe at each level
- Worst drawdown scenario: equity curve if 3 worst months repeat consecutively
- Regime break test: performance in the year immediately before IS period

**Pass criteria:** >95% of Monte Carlo paths show positive Sharpe. Strategy profitable at estimated live slippage.

---

### Gate 6 — Research Memo

**Question:** Can I explain this signal, its results, and its risks clearly?

**Output:** Tier C tearsheet from `core/report.py` + written memo in `Research/<STRATEGY>/tearsheet_<date>.md`

**Tier C memo sections (Balyasny / Millennium standard):**

```
1. Signal Hypothesis        — behavioural or structural reason this alpha exists
2. Universe & Data          — assets, source, survivorship bias handling
3. Raw IC Analysis          — IC per signal horizon, ICIR, IC t-stat (NW-corrected)
4. IC Decay Curve           — IC at lag 1, 5, 10, 20, 60 days
5. Factor Decomposition     — residual alpha (bps/yr), t-stat, R², factor betas
6. Transaction Cost Model   — gross IC, cost drag, net IC
7. Regime Breakdown         — IC by regime (bull/bear, high/low vol, risk-on/off)
8. Capacity Estimate        — AUM at which signal alpha decays to zero
9. Verdict                  — is residual alpha positive, significant, tradeable at scale?
```

**Pass criteria:** Memo readable by a PM with no prior context. If it requires the thesis to understand — rewrite.

---

### Gate 7 — Shadow Trading

**Question:** Does the signal hold under real-time conditions with realistic fills?

**Required:**
- Minimum 6 weeks paper trading on MT5 demo
- Realistic execution: bid-ask spread, slippage, partial fills
- Compare live paper P&L distribution to backtest P&L distribution
- Monitor for: drawdown exceeding Gate 4 OOS Max DD, regime change, execution failures

**Pass criteria:** Paper Sharpe within 30% of OOS Sharpe after 6+ weeks. No structural execution anomalies.

---

### Gate 8 — Live Deployment

**Question:** Is the signal ready for real capital?

**Required:**
- All previous gates PASSED
- Position sizing: 1/4 Kelly derived from live paper results (not backtest)
- Start at 25% of target allocation — scale to 100% over 3 months if live performance holds
- Kill switch pre-configured: drawdown triggers at 50% of OOS Max DD

**Pass criteria:** risk-manager APPROVED + explicit `[LIVE DEPLOYMENT APPROVED]` by Syafiq.

---

## Part 2: The Alpha Research Engine (Tooling)

### The 3-Room Model (Locked 2026-05-16)

ARE is Room 1 of three. Each room asks a different question and uses a different engine.

```
Room 1 — sigma-are    "Does the signal have predictive power?"
          Engine: Python IC measurement (ARE)
          Mode:   vectorized (cross-sectional / time-series) OR event-time for sparse strategies
          Output: IC, ICIR, IC decay, residual alpha, regime breakdown, capacity estimate

Room 2 — sigma-lean   "What does execution look like in simulation?"
          Engine: LEAN CLI (event-driven, bar-by-bar)
          Mode:   ALWAYS event-based — no exceptions, not optional
          Output: P&L curve, drawdown, Sharpe, trade distribution, OOS walk-forward

Room 3 — sigma-mt5    "Does the production code execute correctly?"
          Engine: MT5 Strategy Tester (tick-by-tick)
          Mode:   Event-based, millisecond precision
          Output: Fill quality, broker spread/swap costs, MQL5 logic verification
```

**Rule:** A signal that passes Room 1 (IC gate) MUST go through Room 2 (LEAN) before
capital is allocated. Room 1 IC does not substitute for Room 2 execution simulation.

---

### What It Is

A Python signal quality gate supporting three IC measurement modes. Feed it any signal, it outputs:
- Whether the alpha is real (IC, ICIR, NW t-stat)
- How long it lasts (IC decay curve)
- What survives factor stripping (residual alpha, bps/yr)
- Whether it's tradeable at scale (capacity estimate)
- When it works and when it breaks (regime breakdown)

**This is NOT:** an order execution system, a P&L simulator, or a replacement for LEAN.

**This IS:** the tooling that automates Gates 0–6. The Tier C portfolio piece that replaces "Sharpe 1.16" with "IC 0.047, ICIR 1.31, 61 bps net residual alpha after FF5 decomposition."

**Asset class coverage:**
- Equities ✅ | ETFs ✅ | Futures ✅ | Crypto ✅ | Gold/CFD ✅ | Options ⏳ Phase 2

---

### Architecture Principle

The IC engine core is universal — Spearman rank correlation works identically across all asset classes. What changes per asset class are the **adapters**: data loading, signal construction, factor models, cost assumptions.

```
                    ┌─────────────────────────────────────┐
                    │         IC ENGINE CORE              │
                    │  ic_engine / regimes / capacity /   │
                    │  report  (universal — never changes)│
                    └──────────────┬──────────────────────┘
                                   │  calls adapter interface
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
      ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
      │  Equities /  │   │   Futures    │   │    Crypto    │
      │    ETFs      │   │   Adapter    │   │   Adapter    │
      │ FF5 factors  │   │ AQR factors  │   │ Custom 4F    │
      └──────────────┘   └──────────────┘   └──────────────┘
              (Options adapter — Phase 2)
```

---

### File Structure

```
workspace/baysix-engine/sigma-are/
└── alpha_engine/
    ├── __init__.py              ← routes asset_class param to correct adapter
    ├── core/
    │   ├── ic_engine.py         ← IC Engine (universal — Gates 3, IS portion of 4)
    │   ├── regimes.py           ← Regime Breakdown (universal — Gate 3)
    │   ├── capacity.py          ← Capacity Estimator (universal — Gate 3)
    │   └── report.py            ← Research Report / Tier C Tearsheet (Gate 6)
    └── adapters/
        ├── base.py              ← Abstract interface all adapters implement
        ├── equities/
        │   ├── data.py          ← Adjusted close, dividends, splits (Gate 1)
        │   ├── signals.py       ← Momentum, value, quality (Gate 2)
        │   ├── factors.py       ← Fama-French 5-Factor FF5 (Gate 3)
        │   └── costs.py         ← Spread + Almgren market impact (Gate 3)
        ├── futures/
        │   ├── data.py          ← Continuous contract (ratio adjustment) (Gate 1)
        │   ├── signals.py       ← Carry, momentum, basis, COT (Gate 2)
        │   ├── factors.py       ← AQR-style: carry + momentum + value (Gate 3)
        │   └── costs.py         ← Roll cost + commission + slippage (Gate 3)
        ├── crypto/
        │   ├── data.py          ← CCXT / Binance, funding rate history (Gate 1)
        │   ├── signals.py       ← BTC beta, funding rate, momentum (Gate 2)
        │   ├── factors.py       ← Custom 4-factor crypto model (Gate 3)
        │   └── costs.py         ← Exchange fees + funding drag (Gate 3)
        └── options/             ← PHASE 2 — stubs only
            └── [data / signals / factors / costs].py
```

---

### Component Specifications

#### Adapter Interface (`adapters/base.py`)
```
Methods all adapters must implement:
  load_data(tickers, start, end, freq)  → price_matrix, returns_matrix
  compute_signals(returns, params)      → signal_matrix (z-score normalised, lagged 1 period)
  load_factors(start, end)             → factor_returns (asset-class specific)
  estimate_costs(weights, universe)    → cost_drag_bps
```

#### IC Engine (`core/ic_engine.py`) — THE CORE
```
signal_mode parameter — three modes (locked 2026-05-16):

  cross_sectional  → Spearman IC across instruments at each date (ETFs, equities)
                     Input: signal_matrix [dates × tickers], returns_matrix [dates × tickers]
                     IC per date = Spearman(signal[t], return[t+1]) across tickers

  time_series      → Rolling Spearman IC over time axis (single instrument, dense signal)
                     Input: signal_series [dates], return_series [dates]
                     IC per window = Spearman(signal[t-W:t], return[t-W+1:t+1])

  event_time       → IC measured only at signal activation events (sparse, event-driven)
                     Use for: B2B gold, macro regime-triggered signals
                     Phase 1: sequential event detection loop — state-aware, multi-TF
                              (this loop is intentional — not a vectorization failure)
                     Phase 2: forward return computed for each event timestamp (vectorized)
                     Phase 3: Spearman IC over event subset only (vectorized)
                     Input: events_df [timestamp, signal_score], ohlcv [all bars]

Functions:
  compute_ic(signal, returns, mode='cross_sectional') → pd.Series (IC per date/event)
  compute_icir(ic_series)                             → float
  compute_ic_decay(signal, returns, horizons, mode)   → pd.DataFrame
  ic_tstat(ic_series, lags=5)                         → float  ← Newey-West SE
  multiple_testing_correction(pvalues, method='bh')   → adjusted pvalues  ← BH

Thresholds:   IC > 0.03 | ICIR > 1.0 | NW t-stat > 2.0
```

#### Factor Models per Asset Class
```
| Asset Class | Model         | Factors                              | Source                    |
|-------------|---------------|--------------------------------------|---------------------------|
| Equities    | Fama-French 5 | Mkt-RF, SMB, HML, RMW, CMA           | Kenneth French library    |
| ETFs        | FF5           | Same as equities                     | Kenneth French library    |
| Futures     | AQR Multi-asset| Carry, Momentum, Value, Basis       | Asness et al. / manual    |
| Crypto      | Custom 4F     | BTC beta, Funding, Momentum, Liquidity| Constructed from CCXT    |
| Options     | Vol premium   | Vega, Skew, Term structure           | Phase 2                   |
```

#### Transaction Cost Defaults
```
Equities:  10 bps linear + Almgren square-root market impact
ETFs:       5 bps linear + Almgren market impact
Futures:   Roll cost + ~$2 RT commission + slippage
Crypto:     5 bps taker fee + 8h funding drag + market impact
```

#### Regime Detection (`core/regimes.py`)

**Method: Hidden Markov Model (HMM) — 3 probabilistic states**

```
State 0: Calm-trending     — low vol, positive drift → momentum works
State 1: Volatile          — elevated vol, mean-reverting → VWAP + stat arb work
State 2: Crisis            — high vol, negative drift, correlation spike → all signals weaken

Output per date: [P(calm), P(volatile), P(crisis)] — three probabilities summing to 1

Signal weighting:
  Momentum        × P(calm)
  VWAP reversion  × P(volatile)
  Stat arb        × P(volatile)
  IV rank         × (P(calm) + P(volatile)) × 0.5
  Low vol         × (1 − P(calm))   ← defensive, rises in stress
```

HMM inputs: daily return, 21-day realised vol, IV rank (VIX percentile), 10Y-2Y yield curve slope.

Simple threshold rules (VIX > 20) are used only as sanity checks — HMM is the primary method.
See `Research/architecture/ADR-002-regime-detection.md` for full rationale and alternatives.

Asset-class additions (supplemental):
```
  Futures:  Contango / Backwardation (basis signal)
  Crypto:   BTC dominance + funding rate regime inputs to HMM
```

#### Tearsheet Output (`core/report.py`)
```
  ┌─────────────────────────────────────────────────────────────┐
  │ SIGNAL: [name]     ASSET CLASS: [Equities/Futures/Crypto]  │
  │ UNIVERSE: [n] assets    PERIOD: [start]–[end]   FREQ: [D]  │
  ├─────────────────────────────────────────────────────────────┤
  │ IC: 0.047          ICIR: 1.31                               │
  │ IC t-stat: 2.8 ✅  (Newey-West corrected)                   │
  │ IC decay peak: day 5    Decay half-life: 12 days            │
  ├─────────────────────────────────────────────────────────────┤
  │ Gross alpha: 89 bps/yr   Turnover: 42%/yr                  │
  │ Cost drag:  28 bps/yr    Net alpha: 61 bps/yr              │
  ├─────────────────────────────────────────────────────────────┤
  │ Factor model: [FF5 / AQR / Crypto 4F]                      │
  │ Residual α: 54 bps/yr    t-stat: 2.41 ✅                   │
  │ R²: 0.18                 Factor-explained: 82%             │
  ├─────────────────────────────────────────────────────────────┤
  │ Capacity: ~$45M                                             │
  │ Works in: all regimes (weak in risk-off)                    │
  └─────────────────────────────────────────────────────────────┘
  Saves to: Research/<STRATEGY>/tearsheet_<date>.md
```

---

### Known Gaps (to address in build sessions)

| Gap | File | Fix |
|-----|------|-----|
| IC autocorrelation inflates t-stat | core/ic_engine.py | Newey-West SE (lags=5) |
| Multiple testing false positives | core/ic_engine.py | Benjamini-Hochberg correction |
| FF5 doesn't apply to crypto | adapters/crypto/factors.py | Custom 4-factor crypto model |
| Futures price continuity | adapters/futures/data.py | Ratio adjustment roll |
| Options complexity | adapters/options/ | Deferred Phase 2 |

---

### Build Sequence — Approach C (10 sessions, locked 2026-05-13)

One signal end-to-end first. All subsequent signals plug into the same engine.

**Universe: Dual (single engine, one parameter swap)**
- US: 11 SPDR sector ETFs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLB, XLU, XLRE, XLC)
- ASEAN: EWM, EWJ, EWS, EWY, FXI, EWA

```
Session 1:  data.py — load SPDR ETFs + ASEAN ETFs + FRED macro (VIX, yield curve)
            signals.py — momentum (12-1, 6-1, 3-1), properly lagged
            → test: load → compute → verify no look-ahead bias

Session 2:  ic_engine.py — IC, ICIR, NW t-stat, BH correction, subsample stability, rolling IC
            → test: IC on momentum signal, verify against literature benchmarks

Session 3:  costs.py — full cost model (spread + Almgren + borrow + stamp duty)
            factors.py — FF5 (US) + MSCI regional (ASEAN)
            → test: net IC after costs, residual alpha, dual universe comparison

Session 4:  regimes.py — HMM (3 states), IC per regime, stress subsamples (2008/2020/2022)
            capacity.py — AUM capacity estimate
            → test: IC × regime table, capacity figure

Session 5:  report.py — full Tier C tearsheet ← FIRST PORTFOLIO ARTIFACT
            → test: complete tearsheet, US + ASEAN, momentum signal

Session 6:  signals.py → VWAP mean reversion (Almgren & Chriss mechanism)
            → plug into existing engine → tearsheet (1 session)

Session 7:  adapters/equities/iv_signals.py → IV rank cross-section (yfinance option chains)
            → tearsheet for vol risk premium signal

Session 8:  signals.py → statistical arbitrage (cointegration screen + z-score)
            → pair selection, spread IC, tearsheet

Session 9:  signals.py → low volatility factor (60-day realised vol ranking)
            → tearsheet + cross-signal correlation matrix

Session 10: Portfolio construction layer
            → IC-weighted composite → HRP upgrade (when all 5 signals pass gates)
            → full multi-signal research memo in Tier C format
```

---

### Dependencies

```python
pandas >= 2.0          # Core data manipulation
numpy >= 1.24          # Numerical operations
scipy                  # Spearman correlation, OLS
statsmodels            # Factor regression, Newey-West SE
yfinance               # Equities, ETFs, macro data
pandas-datareader      # FRED + Kenneth French FF5 factors
ccxt                   # Crypto exchange data (Binance, Bybit)
matplotlib             # IC decay plots, regime charts
tabulate               # Console tearsheet formatting
```

---

## Part 3: Stage 0 — Hypothesis Engine

### Design Principle

Academic papers prove that mechanisms exist. We synthesize the underlying logic and derive our own application. The paper is the proof of concept, not the recipe.

```
Without papers: discover mechanism + test application  ← full research cost
With synthesis: mechanism already proven + test our application ← 50% of cost
```

### What the Dissector Agent Produces

Two layers per paper:

**Layer 1 — What the paper proved:**
- Core mechanism (1 sentence)
- Evidence quality (sample size, period, citations)
- Post-publication decay risk (publication date, post-pub subsample)

**Layer 2 — What we could build:**
- 2–3 derivative hypotheses for our asset classes
- Explicit statement of how each differs from the paper
- Kill criteria per hypothesis

**Example:**
```
Paper: Almgren & Chriss (2000) — VWAP as optimal execution benchmark
Mechanism: Institutional traders anchor to VWAP → price reverts toward it

Derivative hypotheses:
  H-A: XAUUSD 15min VWAP deviation → 1h mean-reversion (futures adapter)
  H-B: Daily VWAP deviation in SPDR ETFs → next-day reversal (equities adapter)
  H-C: Funding-weighted price vs spot → 8h mean-reversion in BTC perps (crypto adapter)

NOT copies: paper tested execution quality. We test predictive IC of the mechanism.
```

### Paper Sources and Priority

```
Tier A — strongest priors, test first:
  Academic papers (AQR, Asness, Novy-Marx, Jegadeesh-Titman, Fama-French)
  ArXiv q-fin.PM, q-fin.TR, q-fin.ST (last 3 years — decay risk filter)
  SSRN finance working papers

Tier B — market-observed:
  Cross-asset lead-lag relationships
  COT data, options flow, funding rate behaviour

Tier C — exploratory, test last:
  Macro regime shifts, news/sentiment signals
```

**Paper type vs synthesis potential:**

| Paper type | Synthesis potential | Why |
|------------|-------------------|-----|
| Market microstructure / execution | High | Mechanism applies anywhere |
| Behavioural finance (anchoring, herding) | High | Human behaviour is universal |
| Risk premia / factor papers | Medium | Mechanism documented, but crowded |
| Specific signal papers ("momentum in X") | Low | Signal IS the paper, nothing to cook |

### Hypothesis Pipeline

```
ArXiv / SSRN APIs
     ↓
Paper Scraper Agent (weekly)
     ↓
Paper Dissector Agent (Claude — mechanism extraction + derivative hypotheses)
     ↓
Research/hypothesis_queue/   ← pending approval
     ↓
Your approval gate (Approve / Reject / Modify)
     ↓
Research/hypothesis_log.md   ← approved only
     ↓
Alpha Research Engine (Stage 1+)
```

### Hypothesis Log Format (`Research/hypothesis_log.md`)

```markdown
| ID   | Date       | Source                  | Signal            | Universe     | Mechanism                       | Kill Criteria    | Status  |
|------|------------|------------------------|-------------------|--------------|----------------------------------|------------------|---------|
| H001 | —          | [pending approval]     | momentum(252, 21) | 11 SPDR ETFs | Institutional rebalancing flows  | IC < 0.03        | Queued  |
```

No hypothesis enters the log without your explicit approval. Rejected hypotheses are logged with the rejection reason.

---

## Part 4: Signal Registry

**Engine signals (Alpha Research Engine — Approach C build):**

| # | Signal | Universe | Horizon | Mechanism | Gate Status | IC Target | Memo |
|---|--------|----------|---------|-----------|-------------|-----------|------|
| 1 | **Cross-sectional momentum** | US SPDR + ASEAN ETFs | Medium (10–60d) | Institutional herding, slow info diffusion | Gate 0 🔲 | IC > 0.03 | — |
| 2 | **VWAP mean reversion** | US SPDR + ASEAN ETFs | Short (1–5d) | VWAP anchoring — institutional order flow (Almgren & Chriss) | Gate 0 🔲 | IC > 0.02 | — |
| 3 | **Vol Risk Premium / IV rank** | ETFs with liquid options | Medium (weekly) | IV > RV premium harvestable cross-sectionally | Gate 0 🔲 | IC > 0.03 | — |
| 4 | **Statistical arbitrage** | Cointegrated ETF pairs | Short-medium | Structural economic linkage → spread mean reversion | Gate 0 🔲 | IC > 0.04 | — |
| 5 | **Low volatility factor** | All ETFs | Medium (monthly) | Benchmark-constrained overpay for high vol | Gate 0 🔲 | IC > 0.02 | — |

**Existing validated signal (needs IC reframe):**

| Signal | Market | Gate Status | Tier C Metrics | Memo |
|--------|--------|-------------|----------------|------|
| B2B Zone | XAUUSD (CFD, OTC) | Gate 4 ✅ Gate 5 🔲 | IC/ICIR: TBD — event_time mode, macro factor model (DXY/yields/VIX/oil) | [memo_test13a.md](SAMTC/memo_test13a.md) |

**Regime model (not a standalone signal — conditions all signals above):**

| Component | Method | Status |
|-----------|--------|--------|
| Market regime detector | HMM 3-state (calm / volatile / crisis) | Gate 0 🔲 — built in Session 4 |

---

## Part 5: QR Language Standards

Every strategy discussion uses Tier C pod shop framing. No exceptions.

| Avoid | Use instead |
|-------|-------------|
| "I built a backtest" | "I measured the IC and decay profile of this signal" |
| "Sharpe 1.16" | "IC: 0.05, ICIR: 1.2, decay half-life: 12 trading days" |
| "The strategy works" | "60 bps/yr residual alpha survives FF5 decomposition" |
| "OOS degradation 27.5%" | "IC stable IS→OOS, NW t-stat 2.3, Prob Sharpe 96%" |
| "A trading system" | "A systematic alpha signal with factor-decomposed attribution" |
| "A dashboard" | "A live alpha research platform showing IC-validated signals" |
| "The signal works in crypto" | "Signal capacity estimated at $X before market impact exceeds net IC" |

---

## Part 6: Architecture Decision Records (ADR Governance)

Every major engine component decision is documented in a dedicated ADR. No agent modifies an engine component without reading the relevant ADR first.

**Rule:** If the trigger condition in the ADR is not met → implement within the current decision. If met → follow the upgrade path. If proposing something not in any ADR → write a new ADR and get Syafiq approval first.

| ADR | Component | Current choice | Upgrade trigger |
|-----|-----------|---------------|----------------|
| [ADR-001](architecture/ADR-001-factor-model.md) | Factor model | FF5 static OLS | IC unstable across subsamples → rolling betas |
| [ADR-002](architecture/ADR-002-regime-detection.md) | Regime detection | HMM 3-state | Live signal data >2yr → RF classifier |
| [ADR-003](architecture/ADR-003-signal-combination.md) | Signal combination | IC-weighted | All 5 signals live → HRP |
| [ADR-004](architecture/ADR-004-ic-method.md) | IC method | Spearman + NW + BH | >20 signals tested → Deflated Sharpe |
| [ADR-005](architecture/ADR-005-cost-model.md) | Cost model | Almgren + stamp duty | Live execution data → empirical impact |

Full implementation spec: [`architecture/engine-design-v1.md`](architecture/engine-design-v1.md)

---

## Part 7: Agent Responsibilities

| Gate | Primary Agent | Quality Gate |
|------|--------------|--------------|
| 0–2 | `quant-researcher` | Chief of Staff review |
| 3–5 | `quant-researcher` | Chief of Staff review |
| 6 | Chief of Staff (Syafiq + Claude) | Syafiq signs off |
| 7 | `quant-trader` (monitor only) | `risk-manager` APPROVED |
| 8 | `risk-manager` | `[LIVE DEPLOYMENT APPROVED]` by Syafiq |

---

## Success Criteria

The full system is operational when:
1. Any signal function → full Tier C tearsheet in < 30 seconds
2. Asset class switch via one parameter: `asset_class='equities'|'futures'|'crypto'`
3. Hypothesis queue populated by paper synthesis agent, approved by Syafiq
4. IC, ICIR, decay curve, residual alpha, regime breakdown, capacity — all in one output
5. Every number explainable in a Balyasny/Millennium interview without notes
6. `Research/<STRATEGY>/tearsheet_<date>.md` exists as a portfolio artifact for each approved signal

---

*Supersedes: `Braindump/alpha_research_engine_plan.md` (v1 build plan) — consolidated into this document 2026-05-11*
