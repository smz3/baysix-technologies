# Baysix — Quantitative Capability Framework
**Version:** 1.0
**Date:** 2026-04-04
**Purpose:** Complete reference of quant capabilities — fundamentals, differentiators, and institutional-grade additions for Baysix

---

## How to Read This Document

- `[HAVE]` — Already planned/built
- `[ADD]` — Must be added to the build plan
- `[STRETCH]` — Aspirational, Phase 6+ or data-volume dependent
- 🔴 Must-Have | 🟡 Nice to Have | 🟢 Above & Beyond

---

## PILLAR 1 — Backtesting & Validation

### 🔴 Must-Have

| Capability | Description | Status |
|---|---|---|
| In-Sample / Out-of-Sample Split | 70/30 minimum. OOS never touched during development. | `[ADD]` |
| Walk-Forward Optimization (WFO) | Anchored WFO: expanding train window, fixed test period. | `[ADD]` |
| Rolling WFO | Sliding window variant. Detects edge degradation over time. | `[ADD]` |
| Embargo Period | Mandatory gap between IS and OOS. Minimum 5% of window. | `[ADD]` |
| Point-in-Time Data | No lookahead bias. Data only as available at decision time. | `[ADD]` |
| Permutation Test | N=1000 shuffles. Strategy must beat p < 0.05 vs random. | `[HAVE]` |
| Bootstrap Confidence Intervals | Bootstrap Sharpe, Calmar, win rate. Report ranges, not point estimates. | `[ADD]` |

### 🟡 Nice to Have

| Capability | Description | Status |
|---|---|---|
| Monte Carlo Simulation | Resample trade P&L N=10,000 times. Equity curve distribution: median, 5th, 95th percentile. | `[ADD]` |
| Probability of Ruin | % of Monte Carlo sims hitting max drawdown limit. Must be < 1% to deploy. | `[ADD]` |
| Worst-Case Equity Curve | Maximum pessimistic trade ordering — the strategy floor. | `[ADD]` |
| OOS Efficiency Ratio | OOS Sharpe / IS Sharpe. Healthy: 0.5–0.8. Below 0.3 = probable overfit. | `[ADD]` |
| Consecutive Period Analysis | Split OOS into sub-periods. Does performance hold? Detects lucky streaks. | `[ADD]` |
| Regime-Conditioned Backtesting | Re-run backtest by regime. Show Sharpe per regime separately. | `[ADD]` |

### 🟢 Above & Beyond

| Capability | Description | Status |
|---|---|---|
| Deflated Sharpe Ratio (López de Prado) | Adjusts Sharpe for number of trials, skewness, kurtosis. Eliminates multiple testing false positives. | `[STRETCH]` |
| CSCV + PBO | Tests ALL IS/OOS combinations. Outputs Probability of Backtest Overfitting. PBO < 0.5 required. | `[STRETCH]` |
| Minimum Backtest Length Formula | Given Sharpe target and trial count — calculate minimum data needed to reject null. | `[ADD]` |
| Adversarial Backtesting | Worst-case trade ordering for floor estimate. Report [pessimistic, actual, optimistic] Sharpe. | `[STRETCH]` |

---

## PILLAR 2 — Risk Metrics

### 🔴 Must-Have

| Metric | Definition | Status |
|---|---|---|
| Sharpe Ratio | (Rp - Rf) / σp, annualized, risk-free adjusted. | `[HAVE]` |
| Sortino Ratio | (Rp - Rf) / σ_downside. Only penalizes downside variance. | `[ADD]` |
| Calmar Ratio | Annualized CAGR / Max Drawdown. | `[HAVE]` |
| Maximum Drawdown | Largest peak-to-trough. Report $, %, and duration. | `[HAVE]` |
| Recovery Factor | Net Profit / Max Drawdown. > 3 = excellent. | `[HAVE]` |
| Profit Factor | Gross Profit / Gross Loss. > 1.5 acceptable. > 2.0 strong. | `[HAVE]` |
| Win Rate | % profitable trades. Always with confidence interval. | `[HAVE]` |
| Average R-Multiple | (Exit - Entry) / Risk per trade, averaged. > 1.0 required. | `[HAVE]` |
| Expectancy | Win Rate × Avg Win - Loss Rate × Avg Loss. Must be positive. | `[ADD]` |
| Historical VaR (95%, 99%) | Max loss at confidence level from empirical returns. | `[ADD]` |
| Parametric VaR | Assumes normal distribution. Compare to historical VaR. | `[ADD]` |

### 🟡 Nice to Have

| Metric | Description | Status |
|---|---|---|
| Monte Carlo VaR | VaR from simulation. More robust. | `[ADD]` |
| CVaR / Expected Shortfall | Expected loss conditional on exceeding VaR. Regulator preferred. | `[ADD]` |
| Ulcer Index | Measures drawdown depth AND duration combined. | `[ADD]` |
| Omega Ratio | Probability-weighted gain/loss ratio. No distribution assumption. | `[ADD]` |
| MAE / MFE Analysis | Max Adverse/Favorable Excursion. Informs stop and target placement. | `[ADD]` |
| Rolling Sharpe (30d, 90d, 180d) | Time-varying Sharpe. Real-time degradation detection. | `[ADD]` |
| Drawdown Decomposition | Which trades caused each drawdown? Attribute to instrument/regime/session. | `[ADD]` |

### 🟢 Above & Beyond

| Metric | Description | Status |
|---|---|---|
| Strategy Health Z-Score | Z-score of rolling live Sharpe vs historical distribution. Alert at > -2σ. | `[ADD]` |
| Structural Break Detection | Chow test on rolling performance. Detects if edge has structurally changed. | `[STRETCH]` |
| CUSUM Control Chart | Sequential hypothesis test for sustained degradation. | `[STRETCH]` |
| Tail Risk Ratio | CVaR / VaR. > 1.5 = heavy tails warning. | `[ADD]` |

---

## PILLAR 3 — Regime Detection & Macro Analysis

### 🔴 Must-Have

| Capability | Description | Status |
|---|---|---|
| Rule-Based Regime Classification | VIX, yield curve, DXY, credit spreads → regime label. | `[HAVE]` |
| Regime-Conditional Performance Table | Win rate, Sharpe, avg R per regime × instrument. | `[ADD]` |
| Bull/Bear Debate Pattern | Two agents argue opposite cases. CIO adjudicates. Prevents confirmation bias. | `[HAVE]` |
| Macro Factor Tracking | DXY, VIX, US10Y, 2Y10Y, IG/HY credit spreads, SPX vol term structure. | `[HAVE]` |

### 🟡 Nice to Have

| Capability | Description | Status |
|---|---|---|
| LSTM Regime Classifier | Cross-asset time-series → regime probability distribution. | `[HAVE]` |
| Regime Probability Distribution | [Risk-On: 61%, Risk-Off: 24%, Stagflation: 15%] with p-value. Not just a label. | `[ADD]` |
| Regime Transition Matrix | P(regime_t+1 | regime_t). Which transitions are likely next? | `[ADD]` |
| Yield Curve Shape Classification | Normal, flat, inverted, bear steepener, bull flattener. | `[ADD]` |
| Sector Rotation Model | XLK/XLE/XLF/XLU relative strength per regime. | `[HAVE]` |

### 🟢 Above & Beyond

| Capability | Description | Status |
|---|---|---|
| Hidden Markov Model (HMM) | Unsupervised latent regime detection. Outputs transition probability matrix. | `[STRETCH]` |
| Entropy-Based Market Stress | Shannon entropy of intraday returns. High entropy = low edge conditions. | `[STRETCH]` |
| Cross-Asset Correlation Regime | Detect when correlations break down. Crisis alpha or contagion signal. | `[ADD]` |

---

## PILLAR 4 — Machine Learning & Model Transparency

### 🔴 Must-Have

| Capability | Description | Status |
|---|---|---|
| XGBoost Zone Scorer | Trained on zone outcomes. Scores new zones at detection. | `[HAVE]` |
| Permutation Test Gate | p < 0.05 vs random required to deploy. Hard gate. | `[HAVE]` |
| Feature Importance | Which features drive predictions. Updated each retraining. | `[HAVE]` |
| Model Versioning & Registry | Version, date, samples, accuracy, p-value per model stored. | `[HAVE]` |
| OOS Model Validation | Train on 70%, validate on held-out 30%. OOS accuracy is the metric. | `[ADD]` |

### 🟡 Nice to Have

| Capability | Description | Status |
|---|---|---|
| SHAP Values | Per-prediction directional feature contributions. Waterfall chart in UI. | `[ADD]` |
| Prediction Confidence Intervals | 0.71 ± 0.08 (95% CI) — never a naked point estimate. | `[ADD]` |
| Learning Curve Analysis | Accuracy vs training sample count. Shows if more data will help. | `[ADD]` |
| Model Comparison Panel | v1 vs v2 vs v3 — accuracy, p-value, features side by side. | `[ADD]` |
| Calibration Curve | Does confidence 0.71 actually produce 71% win rate? | `[ADD]` |
| Regime-Conditional Model Accuracy | Does zone scorer work equally across all regimes? | `[ADD]` |

### 🟢 Above & Beyond

| Capability | Description | Status |
|---|---|---|
| Information Coefficient (IC) | Correlation between zone score and actual R-multiple. ICIR = IC / σ(IC). | `[ADD]` |
| Bayesian Win Rate Updating | Update posterior as outcomes arrive. Credible intervals replace frequentist CIs. | `[STRETCH]` |
| Gemma LoRA Fine-Tuning | Agents reason about B2B zones with domain knowledge. Phase 9. | `[HAVE]` |

---

## PILLAR 5 — Statistical Research Process

### 🔴 Must-Have

| Capability | Description | Status |
|---|---|---|
| Hypothesis Board | Hypothesis → Test → Result (p-value, n) → Conclusion. Archive of all. | `[ADD]` |
| t-Test on Returns | Is mean return significantly different from zero? Automated per backtest. | `[ADD]` |
| Minimum Sample Size Enforcement | n < 30 = rejected. n < 100 = warning. n > 200 for deployment decisions. | `[ADD]` |
| Statistical Claims with Citations | Every output number: source, date, n, confidence level. No naked statistics. | `[ADD]` |

### 🟡 Nice to Have

| Capability | Description | Status |
|---|---|---|
| Multiple Hypothesis Correction | Bonferroni / Benjamini-Hochberg. Testing 20 hypotheses at p<0.05 expects 1 false positive. | `[ADD]` |
| Effect Size Reporting | Cohen's d alongside p-value. Significant ≠ practically meaningful. | `[ADD]` |
| Statistical Power Analysis | Plan sample collection before testing. Calculate n required for given effect size and α. | `[ADD]` |
| Regime × Instrument × Session Hit Rate Table | The full edge map of Sigma. Complete cross-table. | `[ADD]` |

---

## PILLAR 6 — Trade Analytics & P&L Attribution

### 🔴 Must-Have

| Capability | Description | Status |
|---|---|---|
| Equity Curve | Cumulative P&L vs benchmark. | `[HAVE]` |
| Monthly Returns Heatmap | Calendar heatmap. Spots seasonality and consistency. | `[HAVE]` |
| Drawdown (Underwater) Chart | Time below previous peak. Duration as important as depth. | `[ADD]` |
| R-Multiple Distribution | Histogram. Right skew = good system. | `[HAVE]` |
| Full Trade Log with Attribution | Entry, exit, regime at entry, session, zone score, sizing reason. | `[ADD]` |
| P&L by Instrument | Which instruments contribute profit vs drag? | `[ADD]` |
| P&L by Session | London vs NY vs Asian performance split. | `[ADD]` |
| P&L by Regime | Does the strategy work in all regimes or just some? | `[ADD]` |

### 🟡 Nice to Have

| Capability | Description | Status |
|---|---|---|
| MAE/MFE Scatterplot | Informs stop and target placement decisions. | `[ADD]` |
| Slippage Analysis | Actual fill vs intended per instrument, broker, session. | `[ADD]` |
| Transaction Cost Impact | How much does slippage reduce Sharpe vs theoretical clean? | `[ADD]` |
| Logic Trace per Trade | Why was zone scored X? Regime? Agent recommendation? Explainability per trade. | `[HAVE]` |

### 🟢 Above & Beyond

| Capability | Description | Status |
|---|---|---|
| Live vs Backtest Drift Monitor | Z-score of live rolling Sharpe vs backtest expectation. Alert at > 2σ divergence. | `[ADD]` |
| Concentration Risk | What % of P&L comes from top 10% of trades? High = fragile. | `[ADD]` |
| Time-of-Day Edge Heatmap | 15-min bucket P&L. Where intraday does Sigma edge concentrate? | `[ADD]` |

---

## PILLAR 7 — Sigma Strategy-Specific Analytics

### 🔴 Must-Have

| Capability | Description | Status |
|---|---|---|
| Zone Quality Score | XGBoost confidence per zone at detection. | `[HAVE]` |
| Zone Age vs Hit Rate | Correlation between zone age and hold probability. Statistically validated. | `[ADD]` |
| Touch Count vs Hit Rate | First touch vs re-test — which has better statistics? | `[ADD]` |
| ATR Ratio Analysis | Zone size / ATR ranges with best hit rates. | `[ADD]` |
| Session-Conditioned Zone Stats | London vs NY vs Asian zone outcomes separately. | `[ADD]` |
| Timeframe Confluence | Higher-TF zones vs lower-TF — quantified edge difference. | `[ADD]` |

### 🟡 Nice to Have

| Capability | Description | Status |
|---|---|---|
| Cascade Score Impact | Does sigma_core cascade score correlate with actual outcomes? | `[ADD]` |
| Zone Density Analysis | Clustering detection. Dense clusters may signal congestion, lower quality. | `[ADD]` |
| Regime × Zone Type Cross-Table | Which zone types work best in each regime? Full statistical cross-table. | `[ADD]` |

### 🟢 Above & Beyond

| Capability | Description | Status |
|---|---|---|
| Zone Invalidation Classifier | What does a zone look like right before invalidation? Early exit signal. | `[STRETCH]` |

---

## PILLAR 8 — System & Engineering

### 🔴 Must-Have

| Capability | Status |
|---|---|
| Automated data pipeline (no manual downloads) | `[ADD]` |
| Data quality checks (missing, outliers, freshness) | `[ADD]` |
| Event-driven research triggers | `[HAVE]` |
| LangGraph PostgresSaver checkpointing | `[HAVE]` |
| Dual kill switch (EA + Supabase) | `[HAVE]` |
| Model versioning and registry | `[HAVE]` |
| Dead Man's Switch (context > 24h → 0.5x sizing) | `[HAVE]` |
| .env security (keys never in code or logs) | `[HAVE]` |

### 🟡 Nice to Have

| Capability | Status |
|---|---|
| Broker adapter heartbeat monitoring | `[ADD]` |
| System latency monitoring (FastAPI, agents, LLMs) | `[ADD]` |
| Automated regression tests on model updates | `[ADD]` |
| Data lineage tracking | `[ADD]` |

### 🟢 Above & Beyond

| Capability | Status |
|---|---|
| SHAP explanation API (per-prediction via FastAPI) | `[ADD]` |
| Execution benchmarking vs VWAP/TWAP | `[ADD]` |

---

## PILLAR 9 — Quantitative Morning Report

**Generated daily by CIO agent. Published publicly at `/daily`. This is the showcase.**

```
BAYSIX QUANTITATIVE MORNING REPORT — [DATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGIME CLASSIFICATION
  Risk-Off:     61%  (p=0.003, n=47 cross-asset obs)
  Risk-On:      24%
  Stagflation:  15%
  Yield Curve:  Bear steepener (2Y10Y: -18bp)
  Persistence:  Day 7 in current regime

SIGMA EDGE — REGIME-MATCHED STATISTICS (not all-time)
  Instrument    Win Rate [95% CI]    Avg R   Sharpe   n
  XAUUSD        71.3% [63–79%]      1.43R   3.21     312
  BTC-PERP      64.8% [58–72%]      1.28R   2.14     187
  SPY            58.2% [50–66%]      1.12R   1.67      94

HYPOTHESIS BOARD SUMMARY
  Confirmed: H-043 BTC edge in Risk-Off regime (p=0.002)
  Testing:   H-047 NFP week edge degradation (p=0.14, n=34)
  Rejected:  H-039 London vs NY session edge (p=0.31)

RISK POSTURE
  Kelly fraction:  0.71x  (capped 0.5x conservative)
  Current DD:      -2.1%  (limit: -8.0%)
  Rolling 30d Sharpe: 1.43  (hist avg: 1.16)  Z: +0.8σ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated by Baysix Research Engine | Powered by Sigma
```

---

## Build Priority Matrix

| Priority | Capability Group | Phase |
|---|---|---|
| P0 | Core risk metrics (Sharpe, Sortino, Calmar, VaR, CVaR) | 0–2 |
| P0 | Data flywheel (zone_outcomes) | 2 |
| P0 | IS/OOS + WFO + embargo framework | 2 |
| P1 | Monte Carlo + probability of ruin | 3 |
| P1 | Regime-conditional performance tables | 3 |
| P1 | Hypothesis Board | 3 |
| P1 | SHAP values on zone scorer | 5 |
| P1 | MAE/MFE, trade attribution, logic trace | 7 |
| P2 | Multiple hypothesis correction | 6 |
| P2 | Rolling Sharpe z-score | 6 |
| P2 | Live vs backtest drift detection | 6 |
| P2 | IC / ICIR | 6 |
| P3 | Deflated Sharpe Ratio | 8 |
| P3 | HMM regime detection | 8 |
| P3 | CSCV / PBO | 9 |
| P3 | Bayesian win rate updating | 9 |

---

**Total: ~100 capabilities across 9 pillars**
**`[HAVE]`:** ~15 | **`[ADD]`:** ~65 | **`[STRETCH]`:** ~20
