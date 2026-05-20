# ADR-002: Regime Detection Method

**Date:** 2026-05-13  
**Status:** Active — extension pending (see ENGINE_BLUEPRINT.md §6)  
**Component:** `core/alpha_metrics/regimes.py`

> **Note (2026-05-20):** The HMM 3-state decision below stands. It is to be EXTENDED — not replaced — with
> BOCPD transition detection and four regime dimensions per `engine-architecture/Regime_Engine_Architecture.md`.
> The SPY/VIX/yield-curve `if/else` currently in the `regimes.py` stub docstring is NOT this method and is discarded.

---

## Decision

**Hidden Markov Model (HMM)** — 3 hidden states, Gaussian emission distributions.  
Implementation: `hmmlearn.hmm.GaussianHMM`

**3 states:**
- State 0: Calm-trending (low vol, positive drift, momentum works)
- State 1: Volatile (elevated vol, mean-reverting, VWAP and stat arb work)
- State 2: Crisis (high vol, negative drift, correlation spike, all signals weakened)

**Input features (what the HMM is fit on):**
- Daily return of equal-weight universe
- 21-day rolling realized volatility
- IV rank (VIX percentile vs trailing 252 days)
- 10Y-2Y yield curve slope (from FRED)

**Output per date:** `[P(calm), P(volatile), P(crisis)]` — three probabilities summing to 1.

**Signal weighting rule:**
```
Momentum signal weight    = base_weight × P(calm)
VWAP reversion weight     = base_weight × P(volatile)
IV rank signal weight     = base_weight × (P(calm) + P(volatile)) × 0.5
Stat arb weight           = base_weight × P(volatile)
Low vol signal weight     = base_weight × (1 − P(calm))  ← defensive, rises in stress
```

---

## Why

**Probabilistic output is the core reason.** A binary regime flag ("VIX > 20 = high vol") creates cliff edges. At VIX = 19.9 you are fully invested. At VIX = 20.1 you are out. HMM gives `P(volatile) = 0.68` — the signal weight scales smoothly.

**Temporal structure.** HMM models regime persistence — once in a regime, the model expects it to persist until transition probability tips over. This matches how markets actually behave: crises don't end in a day.

**Unsupervised.** No labels required. The model discovers states from the data. This avoids the look-ahead bias of manually labeling "2008 = crisis" and training on it.

**Interpretable.** 3 discrete states are explainable. `P(crisis) = 0.82` on 15 March 2020 is a claim any PM can evaluate. A 47-dimensional hidden state is not.

---

## Alternatives Considered

| Alternative | Description | Why not chosen |
|-------------|-------------|----------------|
| **Simple threshold (VIX > 20)** | Binary: high vol / low vol | Fast to implement, transparent, but binary — cliff edges at threshold. No temporal persistence. Brittle. Use as sanity check only |
| **Markov Switching Model (Hamilton 1989)** | Explicitly models switching probability in return distribution | Very similar to HMM but harder to extend to multivariate features. HMM is strictly more general |
| **Regime-switching GARCH** | GARCH with regime-dependent vol parameters | Better when vol clustering IS the primary regime driver. Consider if HMM state transitions are driven primarily by vol changes |
| **K-Means / GMM clustering** | Unsupervised clustering of market states | No temporal structure — doesn't model that today's regime predicts tomorrow's regime. Use only if HMM states are unstable |
| **Change-point detection (PELT / CUSUM)** | Detects when return distribution shifts | Identifies WHEN a regime changed, not current probability. Useful supplement for post-hoc analysis but not for real-time conditioning |
| **Random Forest classifier** | Supervised — predicts regime from labeled historical data | Requires labeled training data. Introduces look-ahead if labels are set retrospectively. Valid after 2+ years live signal data |
| **Kalman Filter** | Continuous latent state estimation | Better for continuous states (trend strength score) than discrete regime categories |
| **200-day moving average** | Price above = bull, below = bear | Simple, transparent, used by trend followers. Valid as a sanity check. Too laggy and binary for signal conditioning |

---

## Deferred Upgrades

### Upgrade 1: Gaussian HMM → Regime-Switching GARCH

**Trigger condition:** HMM state transitions are found to be almost entirely predicted by volatility level alone (vol explains >80% of state transitions). If so, GARCH regime-switching is more parsimonious.

**How to implement:** `arch` library, `arch.univariate.MarkovSwitching`. Compare log-likelihood to HMM.

### Upgrade 2: 3-state → 4-state HMM

**Trigger condition:** BIC/AIC comparison shows 4-state model is significantly better fit than 3-state (ΔBIC > 10). The fourth state may represent a "recovery" regime distinct from calm-trending.

**How to implement:** Re-fit `GaussianHMM(n_components=4)` and re-label states by mean return and vol.

### Upgrade 3: HMM → Random Forest Regime Classifier

**Trigger condition:** 3+ years of live signal IC data available with verified regime labels from HMM. Supervised classifier can then predict regime from current features faster and with higher accuracy.

---

## Implementation Notes

- Fit HMM on IS period only. Apply to IS + OOS using `model.predict()` — do not refit on OOS.
- State labels (calm / volatile / crisis) are assigned post-fit by inspecting mean return and mean vol of each state. The HMM assigns arbitrary integer labels.
- State ordering is not guaranteed across refits. Always re-label by characteristics, not by index.
- Minimum 500 observations for stable HMM fit. With daily data, this requires ~2 years minimum.

---

## Interview Defence

> "We use Hidden Markov Models for regime detection because markets move between hidden states we cannot observe directly. HMM infers the probability of each state — calm-trending, volatile, crisis — from observable return and vol data. The output is probabilistic, not binary, so signal weights scale smoothly as regime probabilities shift. We deliberately chose HMM over simple threshold rules to avoid cliff edges, and over supervised classifiers because we don't want to label regimes retrospectively and introduce look-ahead bias."
