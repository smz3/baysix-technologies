# ADR-003: Signal Combination Method

**Date:** 2026-05-13  
**Status:** Active  
**Component:** `core/ic_engine.py` (composite IC computation) + `core/report.py` (portfolio tearsheet)

---

## Decision

**Phase 1 (now — until all 5 signals are live): IC-weighted composite**

Weight each signal proportionally to its ICIR. Signals with higher and more consistent IC get more portfolio weight.

```python
composite_signal = Σ (signal_i × ICIR_i) / Σ ICIR_i
```

**Phase 2 (trigger: all 5 signals running and IC-validated): Hierarchical Risk Parity (HRP)**

HRP clusters signals by correlation, then applies risk parity within and across clusters. Does not require inverting a covariance matrix — robust to estimation error.

**Signal correlation gate (active from day 1):**  
Compute pairwise correlation between all live signals. Flag any pair with correlation > 0.75.  
Do not combine correlated signals without explicit acknowledgement — you are not diversifying, you are doubling down.

---

## Why

**IC-weighting for Phase 1:**
- Simple to implement and explain
- Directly ties portfolio weight to measured signal quality
- No covariance matrix needed — estimation error is irrelevant with 1-2 signals
- Transparent: if momentum ICIR = 1.4 and VWAP ICIR = 0.9, momentum gets 61% weight. Explainable to any PM.

**HRP for Phase 2:**
- Mean-variance optimisation (Markowitz) requires inverting the signal covariance matrix. With 5 signals and limited history, this matrix is poorly estimated — small errors in the matrix produce wildly unstable weights.
- HRP avoids matrix inversion entirely — it uses hierarchical clustering + recursive bisection
- Equal risk contribution from each signal cluster ensures no single signal dominates portfolio risk
- López de Prado (2016) — the method is published, defensible, increasingly industry standard
- HRP weights are stable: a small change in signal IC does not flip the optimal weights

**Signal correlation gate:**
- Momentum (12-1) and low vol are known to have negative correlation in crisis and positive in calm — check this empirically, do not assume
- Momentum and VWAP reversion may be positively correlated at certain horizons — if so, one is redundant
- Stat arb (pairs) is the most likely to be orthogonal to all other signals — verify with data

---

## Alternatives Considered

| Alternative | Description | Why not chosen |
|-------------|-------------|----------------|
| **Equal weight (1/N)** | Each signal gets identical weight regardless of quality | Ignores measured IC differences. Valid if IC estimates are highly uncertain. Upgrade candidate if ICIR estimates prove unstable |
| **Mean-Variance Optimisation (MVO)** | Maximise composite IC subject to signal covariance | Requires stable covariance matrix — with 5 signals and 3-5 years data, estimation error dominates. Produces unstable, extreme weights |
| **Risk parity (equal vol contribution)** | Weight signals so each contributes equal volatility | Simpler than HRP but ignores correlation structure between signals |
| **Black-Litterman** | Combine factor model prior with signal views | Appropriate when combining fundamental views with quant signals. Overkill for a pure quant signal library |
| **Kelly criterion** | Maximise log-expected wealth | Requires precise win/loss estimates. Known to be highly sensitive to estimation error. 1/4 Kelly is valid for sizing, not for signal combination |
| **PCA on signals** | Combine signals via principal components | Removes correlation by construction but destroys interpretability. Each PC is a linear combination of all signals — impossible to attribute |

---

## Deferred Upgrades

### Upgrade 1: IC-weighted → HRP

**Trigger condition:** All 5 signals have passed their individual IC gates (IC > 0.03, ICIR > 1.0, NW t-stat > 2.0). At that point the signal covariance matrix has enough structure to make HRP meaningful.

**How to implement:** `riskfolio-lib` or manual implementation of López de Prado HRP algorithm.  
Steps: (1) compute signal return correlation matrix, (2) hierarchical clustering (Ward linkage), (3) quasi-diagonalise, (4) recursive bisection for weights.

### Upgrade 2: Static weights → Regime-conditioned weights

**Trigger condition:** HMM regime model shows IC per regime is significantly different across states (IC in calm > 2× IC in crisis for at least 2 signals).

**What it means:** Instead of fixed IC-weights, signal weights shift as P(regime) shifts. Already partially implemented via the HMM weighting rule in `core/regimes.py` — this upgrade formalises it as the primary combination method.

---

## Signal Correlation Monitoring

Run this check every time a new signal is added to the engine:

```python
# In core/ic_engine.py
def compute_signal_correlation(signal_matrix: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Spearman correlation between all signal columns."""
    corr = signal_matrix.rank().corr(method='spearman')
    high_corr = [(i, j) for i in corr.columns for j in corr.columns 
                 if i < j and abs(corr.loc[i, j]) > 0.75]
    if high_corr:
        warnings.warn(f"High signal correlation detected: {high_corr}")
    return corr
```

High correlation pairs to watch:
- Momentum(12-1) vs Momentum(6-1) — expected to be highly correlated, treat as one signal family
- Low vol vs stat arb — both are mean-reversion oriented in different forms
- VWAP reversion vs stat arb — both short-horizon, both mean-reverting

---

## Interview Defence

> "We combine signals using ICIR-weighting in Phase 1 — higher quality signals get proportionally more weight, which is transparent and directly tied to measured IC. We're upgrading to Hierarchical Risk Parity when all five signals are live because MVO requires inverting a 5×5 covariance matrix estimated on limited data — the estimation error dominates the optimisation. HRP avoids that entirely. We monitor signal correlation from day one and flag any pair above 0.75 — combining correlated signals isn't diversification, it's concentration in disguise."
