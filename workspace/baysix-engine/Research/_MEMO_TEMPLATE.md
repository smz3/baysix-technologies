# Research Memo — [STRATEGY NAME]
**Signal ID**: [e.g. SIG-001]  
**Version**: [e.g. V1.0]  
**Author**: Syafiq M. Zin — Quant Researcher (Deployable)  
**Date**: [YYYY-MM-DD]  
**Universe**: [e.g. US SPDR ETFs / ASEAN ETFs / BTC/USDT Perp]  
**Horizon**: [e.g. Medium — peak IC at day 10–20 / Short — peak IC at day 1–5]  
**Classification**: Proprietary Strategy Research  
**Gate Status**: [e.g. Gate 3 PASSED — Gate 4 pending]

---

## 1. Hypothesis

**Alpha Source:**  
[One sentence — name the market inefficiency being exploited]

**Mechanism:**  
[2–3 sentences — WHY this works structurally. Cite academic paper, observed institutional behaviour, or first-principles logic. Do NOT reference backtest results here. If you need the backtest to explain why the signal works — the hypothesis is post-hoc and FAILS Gate 0.]

**Source paper / evidence:**  
[Title, authors, year. What the paper proved. How our signal differs from theirs — we derive the mechanism, not copy the signal.]

**Kill criteria:**  
[Specific IC / t-stat threshold that falsifies this hypothesis. e.g. "IC < 0.03 after NW correction → signal is economically marginal"]

---

## 2. Universe & Data

| Parameter | Value |
|-----------|-------|
| Universe | [e.g. 11 SPDR sector ETFs + 6 ASEAN regional ETFs] |
| Asset class | [Equities / ETFs / Futures / Crypto] |
| Data source | [yfinance / FRED / CCXT / Kenneth French library] |
| Frequency | [Daily / Weekly] |
| IS period | [YYYY-MM-DD to YYYY-MM-DD] |
| OOS period | [YYYY-MM-DD to YYYY-MM-DD] |
| Survivorship bias | [Documented assumption — yfinance uses current constituents. Disclosed, not hidden.] |
| Look-ahead bias | [Checked — all signals lagged 1 period. Signal at t predicts return at t+1.] |
| Adjusted close | [Yes — splits and dividends adjusted] |
| Stale price | [Forward-fill capped at 3 days — flagged if breached] |

---

## 3. IC Analysis (Gate 3 — The Core)

> This section is the primary output. IC metrics are the Tier C language. Sharpe is secondary.

### 3a. Raw IC

| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| Mean IC | [x.xxx] | > 0.03 | ✅ / ❌ |
| ICIR | [x.xx] | > 1.0 | ✅ / ❌ |
| NW t-stat (lags=5) | [x.xx] | > 2.0 | ✅ / ❌ |
| Bootstrap 95% CI | [[x.xxx, x.xxx]] | Lower bound > 0 | ✅ / ❌ |

### 3b. Subsample IC Stability

| Sub-period | Dates | IC | ICIR | Pass? |
|------------|-------|----|------|-------|
| Period 1 (first third) | [dates] | [x.xxx] | [x.xx] | ✅ / ❌ |
| Period 2 (middle third) | [dates] | [x.xxx] | [x.xx] | ✅ / ❌ |
| Period 3 (final third) | [dates] | [x.xxx] | [x.xx] | ✅ / ❌ |

> All three sub-periods must show positive IC. A signal strong in one period and weak in others is curve-fitted, not structural.

### 3c. IC Decay Curve

| Horizon (days) | IC | Interpretation |
|---------------|-----|----------------|
| 1 | [x.xxx] | [Next-day signal strength] |
| 5 | [x.xxx] | [1-week] |
| 10 | [x.xxx] | [2-week] |
| 20 | [x.xxx] | [1-month] |
| 60 | [x.xxx] | [3-month] |

**Peak IC:** Day [n] — signal is strongest at this horizon  
**Decay half-life:** ~[n] trading days  
**Rebalance implication:** [Daily / Weekly / Monthly — based on where IC materialises]

---

## 4. Transaction Cost Model (Gate 4 — Economic Validation)

| Cost component | Assumption | bps/yr |
|---------------|-----------|--------|
| Bid-ask spread | [x bps per trade × annual turnover] | [x] |
| Market impact | Almgren √(participation rate) | [x] |
| Borrow cost (short side) | [x %/yr on short positions] | [x] |
| Stamp duty | [0% US ETFs / 0.1% Bursa per trade] | [x] |
| Implementation shortfall | 50% of spread as execution drag | [x] |
| **Total cost drag** | | **[x] bps/yr** |

| Metric | Value |
|--------|-------|
| Annual turnover | [x%/yr] |
| Gross IC | [x.xxx] |
| Gross alpha (est.) | [x bps/yr] |
| Cost drag | [x bps/yr] |
| **Net IC** | **[x.xxx]** |
| **Net alpha** | **[x bps/yr]** |

**Pass gate:** Net IC > 0 ✅ / ❌

> Malaysia note: If universe includes Bursa stocks, 0.1% stamp duty = 0.2% round-trip. Signal must generate >0.2% gross alpha per trade to be viable at any rebalance frequency.

---

## 5. Factor Decomposition (Gate 5 — Risk Attribution)

**Factor model used:** [FF5 (US) / MSCI regional (ASEAN) / Custom 4F (crypto)]  
**Beta estimation:** [Static OLS / Rolling 252-day OLS]  
**See:** [ADR-001](../architecture/ADR-001-factor-model.md) for model selection rationale

| Factor | Beta | t-stat |
|--------|------|--------|
| Market (Mkt-RF) | [x.xx] | [x.xx] |
| Size (SMB) | [x.xx] | [x.xx] |
| Value (HML) | [x.xx] | [x.xx] |
| Profitability (RMW) | [x.xx] | [x.xx] |
| Investment (CMA) | [x.xx] | [x.xx] |

| Attribution metric | Value | Pass? |
|-------------------|-------|-------|
| R² (factor-explained) | [x%] | — |
| Factor-explained alpha | [x bps/yr] | — |
| **Residual alpha** | **[x bps/yr]** | — |
| **Residual alpha t-stat (NW)** | **[x.xx]** | **> 2.0** ✅ / ❌ |

> Residual alpha is what survives factor stripping. This is the number that matters to a pod shop PM.

---

## 6. Regime Breakdown (Gate 6 — Robustness)

**Regime method:** HMM 3-state probabilistic — see [ADR-002](../architecture/ADR-002-regime-detection.md)

| Regime | Mean P(state) | Signal IC in regime | ICIR | Works? |
|--------|--------------|---------------------|------|--------|
| Calm-trending | [x%] | [x.xxx] | [x.xx] | ✅ / ❌ |
| Volatile | [x%] | [x.xxx] | [x.xx] | ✅ / ❌ |
| Crisis | [x%] | [x.xxx] | [x.xx] | ✅ / ❌ |

**Signal must show positive IC in at least 2 of 3 regimes.**

**Stress period breakdown:**

| Period | Dates | IC | Notes |
|--------|-------|----|-------|
| GFC 2008 | 2008-01 to 2009-03 | [x.xxx] | [What happened] |
| COVID crash | 2020-02 to 2020-04 | [x.xxx] | [What happened] |
| Rate shock 2022 | 2022-01 to 2022-12 | [x.xxx] | [What happened] |

---

## 7. Capacity Estimate

| Metric | Value |
|--------|-------|
| Estimated AUM at which market impact = net IC | ~$[X]M |
| Max position size (% of ADV) | [x%] |
| Liquidity-adjusted universe size | [n assets × avg ADV] |

**Capacity framing:** "Signal alpha decays to zero at approximately $[X]M AUM. At $[Y]M — a realistic pod shop allocation — the strategy retains [Z]% of gross IC after market impact."

---

## 8. IS/OOS Validation (LEAN Layer — Gates 8–9)

> This section covers the LEAN CLI validation layer — separate from the IC engine above.

| Metric | In-Sample | Out-of-Sample | Degradation |
|--------|-----------|---------------|-------------|
| Period | [dates] | [dates] | — |
| Sharpe Ratio | [x.xx] | [x.xx] | [x%] |
| Calmar Ratio | [x.xx] | [x.xx] | — |
| Max Drawdown | [x%] | [x%] | — |
| CAGR | [x%] | [x%] | — |
| Total Trades | [n] | [n] | — |

| OOS Check | Threshold | Result | Pass? |
|-----------|-----------|--------|-------|
| OOS Sharpe | > 0.5 (crypto) / > 1.0 (equities) | [x.xx] | ✅ / ❌ |
| Sharpe degradation IS→OOS | < 30% | [x%] | ✅ / ❌ |
| OOS Calmar | > 1.0 | [x.xx] | ✅ / ❌ |
| OOS Trades | ≥ 30 | [n] | ✅ / ❌ |
| IC stable IS→OOS | Degradation < 30% | [x%] | ✅ / ❌ |

---

## 9. Stress Testing (Gate 10 — Monte Carlo)

| Test | Method | Result | Pass? |
|------|--------|--------|-------|
| Monte Carlo — Trade Shuffle | 10,000 paths | [x% paths positive Sharpe] | ✅ / ❌ |
| Monte Carlo — Parametric | 10,000 paths | [x% paths positive Sharpe] | ✅ / ❌ |
| Monte Carlo — Block Bootstrap | 10,000 paths | [x% paths positive Sharpe] | ✅ / ❌ |
| Slippage @ 0.1% per trade | Sharpe | [x.xx] | ✅ / ❌ |
| Slippage @ 0.3% per trade | Sharpe | [x.xx] | ✅ / ❌ |
| Slippage @ 0.5% per trade | Sharpe | [x.xx] | ✅ / ❌ |
| Worst 3-month repeat | Equity curve | [describe outcome] | ✅ / ❌ |

**Pass criteria:** >95% of Monte Carlo paths show positive Sharpe. Strategy profitable at estimated live slippage.

---

## 10. Known Failure Modes & Risks

> A memo with no failure modes signals a researcher who hasn't looked hard enough.

1. **[Failure Mode 1]**  
   Condition: [When does this happen]  
   Evidence: [Where in the data it appeared]  
   Mitigation: [How position sizing, gates, or HMM conditioning addresses this]

2. **[Failure Mode 2]**  
   Condition: ...

3. **[Crowding risk]**  
   Condition: [Is this a published/well-known signal? Crowding risk post-publication]  
   Monitoring: [How to detect crowding — factor ETF AUM, short interest, IC decay acceleration]

---

## 11. Tier C Verdict

**Gate Status:**

| Gate | Description | Status |
|------|-------------|--------|
| 0 — Hypothesis | Mechanism stated without referencing backtest | ✅ / ❌ |
| 1 — Data Audit | Point-in-time, biases documented | ✅ / ❌ |
| 2 — Signal Construction | Lagged, z-scored, parameter sensitivity checked | ✅ / ❌ |
| 3 — IC Screen | IC > 0.03, ICIR > 1.0, NW t-stat > 2.0, subsample stable | ✅ / ❌ |
| 4 — Cost Screen | Net IC > 0 after full cost model | ✅ / ❌ |
| 5 — Factor Decomp | Residual alpha t-stat > 2.0 | ✅ / ❌ |
| 6 — Regime Breakdown | IC positive in ≥2 of 3 HMM regimes | ✅ / ❌ |
| 7 — Capacity | AUM capacity documented | ✅ / ❌ |
| 8 — IS Validation (LEAN) | Sharpe > threshold | ✅ / 🔲 |
| 9 — OOS Validation (LEAN) | IC stable IS→OOS, degradation < 30% | ✅ / 🔲 |
| 10 — Monte Carlo | >95% paths positive Sharpe | ✅ / 🔲 |
| 11 — Research Memo | This document | ✅ |
| 12 — Shadow Trading | Paper Sharpe within 30% of OOS after 6 weeks | 🔲 |
| 13 — Live Deployment | risk-manager APPROVED + Syafiq sign-off | 🔲 |

**Tier C Summary (lead with this in any interview):**

> "[Signal name] shows IC of [x.xxx] (ICIR [x.xx], NW t-stat [x.xx]) on [universe]. IC peaks at day [n] and decays with half-life ~[n] days. After full transaction cost model ([x bps/yr drag], [x%] annual turnover), net IC is [x.xxx]. FF5 factor decomposition leaves [x bps/yr] residual alpha (t-stat [x.xx]). IC is stable IS→OOS (degradation [x%]) and positive across all three IS sub-periods. HMM regime analysis shows IC of [x.xxx] in calm-trending regime, [x.xxx] in volatile. Capacity estimated at ~$[X]M."

**Recommendation:** [DEPLOY / CONDITIONAL DEPLOY / REJECT]  
**Conditions (if conditional):** [What must be resolved]  
**Next Action:** [Specific next step]
