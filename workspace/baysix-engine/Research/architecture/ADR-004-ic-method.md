# ADR-004: IC Computation and Statistical Testing

**Date:** 2026-05-13  
**Status:** Active  
**Component:** `core/ic_engine.py`

---

## Decision

**IC method:** Spearman rank correlation (cross-sectional, per date)  
**Standard errors:** Newey-West with lags=5 (daily data standard)  
**Multiple testing:** Benjamini-Hochberg (BH) False Discovery Rate correction  
**Subsample validation:** IC computed over full IS + three equal sub-periods (all must be positive)  
**IC decay:** Computed at horizons [1, 5, 10, 20, 60] days  

```python
# The core IC computation
IC_t = spearmanr(signal[t], forward_return[t+h]).correlation

# ICIR
ICIR = IC_series.mean() / IC_series.std()

# Newey-West t-stat
t_stat = IC_series.mean() / newey_west_se(IC_series, lags=5)

# BH correction (when testing multiple signals simultaneously)
adjusted_pvalues = BH_correction(raw_pvalues, alpha=0.05)
```

**Pass gate:** IC > 0.03 AND ICIR > 1.0 AND NW t-stat > 2.0 AND subsample IC positive in all three periods

---

## Why

**Spearman over Pearson:**
Financial returns are fat-tailed and non-normal. Pearson correlation assumes normality and is sensitive to outliers — one extreme return date can dominate the correlation estimate. Spearman converts both signal and return to ranks first, then correlates the ranks. Outliers become rank 1 or rank N — their magnitude no longer matters. Non-parametric and robust by construction. This is the industry standard for IC computation.

**Newey-West over naive t-stat:**
IC values are autocorrelated — yesterday's IC predicts today's IC because signals persist. Naive t-stat = mean(IC) / std(IC) / sqrt(T) assumes IC values are independent draws. They are not. Autocorrelation inflates the effective sample size and makes the naive t-stat too optimistic. Newey-West standard errors correct for autocorrelation with lags=5 (the standard for daily financial data) and heteroskedasticity. Without this correction, signals fail in live deployment despite passing the backtest significance test.

**BH over Bonferroni:**
Bonferroni controls the Family-Wise Error Rate (no false positives at all). For medical trials where one false positive has catastrophic consequences — correct. For alpha research where we want to discover real signals without rejecting everything — too conservative. BH controls the False Discovery Rate: among all signals declared significant, at most 5% are false. This is the appropriate criterion for a signal library. Bonferroni would eliminate signals that are genuinely real.

**Subsample IC stability:**
A signal with IC = 0.05 over 10 years is meaningless if IC = 0.12 in 2015-2018 and IC = -0.01 in 2019-2024. The 10-year average masks a dead signal. Three-sub-period decomposition forces the signal to demonstrate consistency across time, not just aggregate average. A signal that passes aggregate IC but fails subsample stability is curve-fitted, not structural.

---

## Alternatives Considered

| Alternative | Description | Why not chosen now |
|-------------|-------------|-------------------|
| **Pearson correlation** | Parametric, assumes normality, sensitive to outliers | Financial returns are non-normal and fat-tailed. Pearson is unreliable. Never use for IC |
| **Kendall's Tau** | Another rank correlation, more robust in very small samples | Spearman and Kendall produce nearly identical results on samples > 30. Spearman is faster |
| **Partial IC** | IC computed after partialling out factor returns first | Measures pure alpha IC excluding factor contamination — more rigorous. Triggers: if factor betas are high and time-varying |
| **Mutual Information** | Captures non-linear signal-return relationships | Required when signal is ML-derived or relationship is non-linear. Harder to interpret and compare across signals |
| **Deflated Sharpe Ratio (DSR)** | Bailey & López de Prado — penalises Sharpe for number of trials, skewness, kurtosis | More rigorous for large signal libraries. Trigger: >20 signals tested historically. Add alongside NW t-stat, not instead of it |
| **Haircut Sharpe (Harvey & Liu)** | Discount Sharpe for number of strategies ever tested in the field | Useful for reviewing published strategies to account for publication bias. Not for internal signal testing |
| **Block bootstrap SE** | Resample time blocks to estimate SE without distributional assumptions | More robust than NW but slower and harder to explain. Valid alternative — consider if NW gives counterintuitive results |

---

## Deferred Upgrades

### Upgrade 1: Add Partial IC

**What it is:** Regress signal on factor returns, compute IC on the residual signal. Measures alpha IC after removing factor exposure from the signal itself (not just from returns).

**Trigger condition:** Factor betas are high (>0.5) and time-varying (rolling betas differ significantly from static). High factor exposure in the signal itself inflates IC by picking up factor returns.

**How to implement:** `signal_residual = signal − β × factors`. Compute Spearman IC on `signal_residual` vs forward return.

### Upgrade 2: Add Deflated Sharpe Ratio

**What it is:** DSR = Sharpe × (1 − γ × ln(N)) where N is number of strategies tested. Penalises Sharpe for the multiple testing implicit in testing many strategies over time.

**Trigger condition:** Total number of signals ever tested (including rejected ones) exceeds 20. At that point, the cumulative multiple testing burden is material.

**How to implement:** Maintain a counter in `Research/hypothesis_log.md` of all signals ever tested. Pass this N to DSR computation.

### Upgrade 3: Add Mutual Information IC

**Trigger condition:** Any ML-derived signal is added to the engine. Mutual information captures non-linear relationships that Spearman misses — necessary when the signal is a tree model output or neural network score.

---

## On IC Thresholds — Why 0.03 and 1.0

**IC > 0.03:** Academic consensus. Below 0.03 the signal is economically marginal — any realistic cost model will consume the alpha. The threshold appears across Grinold & Kahn (1999), Qian & Hua (2004), and multiple AQR papers. This is not arbitrary.

**ICIR > 1.0:** IC consistency threshold. An ICIR of 1.0 means IC mean equals IC standard deviation — the signal delivers alpha at least as reliably as it varies. Below 1.0 the signal is too noisy to build a stable position around. At ICIR = 2.0 the signal is strong enough to trade with meaningful conviction.

**NW t-stat > 2.0:** Standard 5% significance threshold after autocorrelation correction. Note: NW t-stat is almost always lower than naive t-stat. If your NW t-stat > 2.0, your naive t-stat may show 3.5+. Always report NW t-stat — never the naive one.

---

## Interview Defence

> "We use Spearman rank IC because financial returns are fat-tailed and non-normal — Pearson is unreliable in that environment. We correct t-statistics with Newey-West because IC values are autocorrelated — naive t-stats inflate significance. We use BH multiple testing correction rather than Bonferroni because Bonferroni is appropriate when one false positive is catastrophic; in signal research, it's too conservative and kills real signals. Finally, we decompose IC into three sub-periods — a signal must show positive IC in all three, not just in aggregate. Aggregate IC can mask a dead signal hiding behind a strong early period."
