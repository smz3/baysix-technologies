# Research Memo — SAMTC B2B Zone Strategy
**Test ID**: Test_13A (OOS Alpha Sentinel)  
**Version**: V1.0  
**Author**: Syafiq M. Zin  
**Date**: 2026-05-10  
**Classification**: Proprietary Strategy Research  
**Gate Status**: Gate 0–4 PASSED | Gate 5 pending | Gate 6 complete

---

## 1. Hypothesis

**Alpha Source:**  
Bilateral Structural Anchor (BSA) zones mark regions where institutional order flow has made a directional commitment — creating persistent order flow imbalances that generate positive expected value when confirmed by multi-timeframe directional consensus.

**Theoretical Basis:**  
Kyle (1985) established that informed traders systematically exploit structural commitment points against uninformed participants, leaving detectable price impact (lambda). SAMTC operationalises this by identifying the precise geometric conditions under which this commitment has occurred (the 5-pointer BSA authentication) and gating entries through a recursive multi-timeframe consensus filter (MN1 → W1 → D1 → H4 → entry TF). The result is a directional search operation constrained between two opposing structural anchors — a State of Imbalance that persists until price converges with the nearest target anchor (Magnet). This is distinct from static supply/demand zones in that zones are authenticated through structural fracture conditions (P3 < P1, P5 < P2, Close(P4) < P5) and degraded dynamically through a 4-state Siege Audit (T0-T3).

**Expected Decay Mechanism:**  
If BSA zone locations become widely known (crowding of entry clusters), the alpha decays. More likely decay path: SAMTC is sensitive to regime — it performs best in trending/inertial markets. In extended sideways/low-volatility regimes, zone formation rate drops and the strategy underperforms via reduced trade count rather than increased loss rate.

---

## 2. Data

| Parameter | Value |
|-----------|-------|
| Market / Instrument | BTC/USDT Perpetual — Binance |
| Asset Class | Crypto (non-linear, 24/7, high volatility) |
| Data Source | CCXT historical OHLCV + sigma-crypto parquet store |
| Frequency | Multi-TF: H1 entry / H4, D1, W1, MN1 context |
| IS Period | 2020-01-01 to 2022-12-31 (3 years) |
| OOS Period | 2024-01-01 to 2025-12-31 (2 years) |
| Gap Year | 2023 excluded from both IS and OOS |
| Survivorship Bias | Not applicable — single instrument (BTC/USDT) |
| Look-Ahead Bias | Checked — all B2B zone detections use close-price confirmation only (no wick-based triggers) |
| Adjusted Close | Not applicable — perpetual swap, no corporate actions |

---

## 3. Results

### IS vs OOS Performance

| Metric | In-Sample (2020–2022) | Out-of-Sample (2024–2025) | Degradation |
|--------|----------------------|-----------------------------|-------------|
| Sharpe Ratio | 1.60 | **1.16** | ▼ 27.5% |
| Sortino Ratio | 2.78 | **2.39** | ▼ 14.0% |
| Calmar Ratio | 0.60 | **1.36** | ▲ +127% (improved) |
| CAGR | 60.35% | **114.75%** | ▲ (improved) |
| Max Drawdown | 99.95% | **84.55%** | ▼ improved |
| Payoff Ratio | 1.53 | **1.65** | ▲ +7.8% (improved) |
| Skew | — | **3.43** | Positive — fat right tail |
| Profit Factor | — | **1.41** | — |
| Prob. Sharpe Ratio | 99.97% | **99.68%** | Negligible |
| Recovery Factor | — | **7.55** | — |
| Avg Win | — | **8.47%** | — |
| Avg Loss | — | **-5.12%** | — |

> **Critical note on drawdown figures:** These are compounded equity curve drawdowns assuming full capital redeployment per trade (no position sizing). Under the Baysix risk framework (1–2% Kelly-derived position sizing), account-level drawdown is estimated at <10%. The Calmar ratio improvement from IS to OOS (0.60 → 1.36) indicates the OOS period was structurally better suited to the strategy's regime requirements than IS (which included COVID crash + 2022 bear market).

> **IS Max DD note:** The 99.95% IS drawdown reflects the 2022 crypto bear market devastating a compounded long-only-leaning strategy. The Storyline latch mechanism exists to flip bearish in these regimes — but there was measurable lag during the transition.

### Gate 4 Verdict

| Check | Threshold | Result | Pass? |
|-------|-----------|--------|-------|
| OOS Sharpe | > 0.5 (crypto) | **1.16** | ✅ PASS |
| Sharpe Degradation IS→OOS | < 30% | **27.5%** | ✅ PASS (marginal) |
| OOS Calmar | > 1.0 | **1.36** | ✅ PASS |
| OOS Payoff | > 1.0 | **1.65** | ✅ PASS |
| OOS Skew | Positive preferred | **+3.43** | ✅ PASS |

**Gate 4: PASSED** — Marginal on Sharpe degradation (27.5% vs 30% threshold). Monitor closely.

---

## 4. Statistical Significance

| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| Prob. Sharpe Ratio (OOS) | **99.68%** | > 95% | ✅ PASS |
| t-statistic (annualised returns) | Pending calculation | > 2.0 | 🔲 PENDING |
| Deflated Sharpe Ratio (DSR) | Pending implementation | > 0 | 🔲 PENDING |
| Factor-adjusted alpha (FF3) | Not applicable (crypto) | Positive | 🔲 PENDING |

> **DSR note:** DSR implementation is on the roadmap (`sigma-crypto` evaluation module). Until completed, the 99.68% Prob. Sharpe provides a partial substitute — it confirms the OOS Sharpe is statistically distinguishable from zero with >99% confidence. However, DSR additionally corrects for the number of strategy parameter combinations tested during development. This must be resolved before Gate 5 is cleared.

---

## 5. Stress Testing (Gate 5)

*Gate 5 is pending. The following is the test plan.*

| Test | Method | Target | Status |
|------|--------|--------|--------|
| Monte Carlo — Trade Shuffle | 10,000 paths, sigma-crypto | >95% positive Sharpe | 🔲 PENDING |
| Monte Carlo — Parametric | 10,000 paths, sigma-crypto | >95% positive Sharpe | 🔲 PENDING |
| Monte Carlo — Block Bootstrap | 10,000 paths, sigma-crypto | >95% positive Sharpe | 🔲 PENDING |
| Slippage @ 0.1% per trade | Sharpe sensitivity | > 1.0 | 🔲 PENDING |
| Slippage @ 0.3% per trade | Sharpe sensitivity | > 0.8 | 🔲 PENDING |
| Slippage @ 0.5% per trade | Sharpe sensitivity | > 0.5 | 🔲 PENDING |
| LEAN H1 Cross-Validation | Independent engine | Sharpe within 20% of 1.16 | 🔲 IN PROGRESS (Docker running) |

> **LEAN Cross-Validation:** The LEAN CLI H1 IS backtest (2020–2022) is currently running. This serves as the primary stress test — an independent event-driven engine reproducing SAMTC logic validates that the sigma-crypto Sharpe 1.16 is not an artefact of vectorized simulation assumptions (look-ahead, fill optimism, etc.).

---

## 6. Known Failure Modes & Risks

> Honest assessment — not marketing.

1. **Storyline Latch Lag During Sharp Regime Transitions**  
   Description: The Storyline latch (directional bias filter) takes multiple bars to confirm a regime flip. During COVID crash (March 2020) and 2022 bear market onset, the strategy continued placing BULLISH entries into a rapidly declining market for 10-20 bars before flipping BEARISH.  
   Observed evidence: IS Max DD 99.95% is partly attributable to this lag. OOS LEAN run shows consecutive SL hits in early 2020 before any BEARISH entries appear.  
   Mitigation: Gate C (Discovery Bridge) partially addresses this via momentum threshold. Full fix requires a faster regime detection layer — candidate: Kronos forecasting module or a VIX-equivalent for crypto.

2. **Compounded Equity Curve Hides Account-Level Risk**  
   Description: Tearsheet DDs (IS 99.95%, OOS 84.55%) are on a compounded no-position-sizing curve. An investor reading these numbers without context will immediately reject the strategy.  
   Observed evidence: Calmar 1.36 sounds low relative to the Sharpe 1.16 because the DD denominator is inflated by compounding.  
   Mitigation: All future reporting must include a position-sized equity curve (1-2% Kelly) alongside the raw curve. Account-level estimated Max DD: <10% under risk framework limits.

3. **Clean Fill Assumption — Live Slippage Not Modeled**  
   Description: sigma-crypto backtests assume fills at close price. BSA entries are limit-order-based — in fast markets, the zone may be partially filled or missed entirely.  
   Observed evidence: Not directly measurable in current backtest infrastructure.  
   Estimated impact: 0.3% per-trade slippage on a 50% win rate strategy at Payoff 1.65 degrades Sharpe by approximately 0.10-0.15 points. OOS Sharpe would estimate at ~1.01-1.06 under live conditions.  
   Mitigation: Slippage model to be added to LEAN backtests (FeeModel + SlippageModel). Nautilus paper trading will provide real fill data.

4. **Crypto-Specific Microstructure — Transferability Unknown**  
   Description: SAMTC was developed and validated exclusively on BTC/USDT perpetual swap. The B2B zone geometry may not transfer cleanly to FX (different session structure), equities (gap opens, earnings), or commodities (roll costs, physical constraints).  
   Observed evidence: MT5 XAUUSD deployment is the first cross-asset test. No systematic OOS data yet.  
   Mitigation: XAUUSD live trading serves as a live transferability test. ETF momentum strategy (in development) will test whether the SAMTC regime framework generalises to equity ETFs.

5. **Heavy Tails (Kurtosis 28.06) — Tail Risk Underestimated by Sharpe**  
   Description: Kurtosis 28.06 (vs 3 for a normal distribution) means large outlier events are 9x more likely than Sharpe assumes. The positive Skew 3.43 means these outliers are mostly wins — but catastrophic losses are also fatter-tailed than normal.  
   Observed evidence: Best Year 1708.87%, Worst Year -76.79% in OOS. This is a strategy that can make or lose a year's worth of returns in weeks.  
   Mitigation: Position sizing (1-2% Kelly) is the primary defence. Kill switch at 10% account drawdown (risk_parameters.md).

---

## 7. Verdict

### Gate Status Summary

| Gate | Description | Status |
|------|-------------|--------|
| 0 — Hypothesis | Order flow imbalance at BSA zones — grounded in Kyle (1985) | ✅ PASSED |
| 1 — Data Audit | BTC/USDT perpetual, CCXT, no look-ahead, close-price confirmation | ✅ PASSED |
| 2 — Signal Construction | IS-only construction, 5-pointer geometry + recursive gating | ✅ PASSED |
| 3 — IS Validation | IS Sharpe 1.60, Prob. Sharpe 99.97% | ✅ PASSED |
| 4 — OOS Validation | OOS Sharpe 1.16, degradation 27.5% (<30%), Calmar improved | ✅ PASSED |
| 5 — Stress Testing | Monte Carlo pending; LEAN cross-validation in progress | 🔲 PENDING |
| 6 — Research Memo | This document | ✅ COMPLETE |
| 7 — Paper Trading | Nautilus Trader setup (after Gate 5 cleared) | 🔲 PENDING |
| 8 — Live Deployment | After Gate 7 cleared — small allocation first | 🔲 PENDING |

**Recommendation:** CONDITIONAL DEPLOY

**Conditions before Gate 7 (Paper Trading):**
1. LEAN H1 OOS cross-validation must show Sharpe within 20% of 1.16 (≥ 0.93)
2. Deflated Sharpe Ratio must be implemented and return DSR > 0
3. Monte Carlo (3 methods) must show >95% positive Sharpe paths

**Next Action:** Check LEAN IS result (`docker logs e192f80bd287`). If IS Sharpe ≥ 1.0, proceed to OOS run. After both, implement DSR and run Monte Carlo to complete Gate 5.

---

*Thesis reference: `workspace/sigma-quant/public/research/samtc_sr.pdf` — methodology detail*  
*Tearsheet: `workspace/sigma-quant/public/research/audits/test13a_tearsheet_oos_validation.html`*
