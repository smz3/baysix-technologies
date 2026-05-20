# Regime Engine Architecture
*Sigma Trading System | Syafiq M. Zin | May 2026*

---

## What a Regime Engine Is

The Regime Engine answers one question: **what kind of market are we in right now?** Not direction, not when to trade. Just: which rules have positive expected value in this environment?

It sits between the Context Engine (which scores the environment -1 to +1) and the Signal Layer (SAMTC). It converts a continuous environment score into an actionable regime state with a confidence-weighted position size scalar.

---

## Six First Principles

**1. Markets switch between distinct data-generating processes.**
A trend-following signal generates positive expectation in trending regimes and negative expectation in ranging regimes — same signal, same parameters, different expected value. The Regime Engine identifies which rules have edge right now.

**2. The regime is latent — never directly observable.**
You observe price, yields, GEX, vol. You never see the regime itself. You infer it. HMM was designed precisely for this: hidden states that generate observable outputs.

**3. Regimes persist.**
A trending regime doesn't flip every day. It persists for days to weeks. This autocorrelation is what makes detection valuable. If regimes were random walk, there'd be no edge in detecting them. The HMM transition matrix captures persistence explicitly.

**4. Transitions are the danger zone.**
The worst drawdowns happen not when you're in the wrong regime and you know it — you reduce size. They happen during undetected transitions. This is the gap HMM alone doesn't close. Enter BOCPD.

**5. One regime dimension is not enough.**
Bull/bear/range conflates trend direction, volatility level, and correlation structure into one label. These are independent. Gold can be bearish trending at low vol with safe-haven correlations — completely different from bearish trending at high vol with risk-asset correlations. One label cannot capture both.

**6. Output must be a probability, not a label.**
Discrete "you are in regime X" is pretend certainty. A proper regime engine outputs P(bull), P(bear), P(range) at each timestep. Position size scales continuously with conviction. When probabilities are split, size is cut. Uncertainty becomes actionable, not paralysing.

---

## What's Equivalent or Better Than HMM

HMM has three limitations: assumes Gaussian emissions, strict Markov property (depends only on previous state), and is slow to detect the exact moment of regime transition.

### Bayesian Online Changepoint Detection (BOCPD) — best addition to HMM

BOCPD doesn't identify what regime you're in. It detects the precise moment you're transitioning between regimes. At each new observation it outputs: P(changepoint just occurred).

```python
# Combined use in live trading
regime_probs = hmm_model.predict_proba(new_features)   # WHAT regime
cp_prob = bocpd.update(new_context_score)               # WHEN it's changing

if cp_prob > 0.70:
    size_scalar = 0.50  # immediate size cut, don't wait for HMM
```

### Markov Regime Switching (Hamilton 1989)
Applies regime switching directly to returns with explicit mean and variance per regime. `statsmodels.tsa.regime_switching.MarkovRegression`. More interpretable than hmmlearn, easier to explain in a Tier C interview.

### Regime-Switching GARCH (RS-GARCH)
Each regime has its own GARCH volatility process. The `arch` library in Python implements this. Captures the fact that vol clusters differently in trending gold regimes vs ranging regimes.

### Gradient Boosting Regime Classifier
Train a GBM on historically labeled regimes using context signals as features. Add SHAP for attribution: which signals drove today's regime classification.

### Summary Table

| Method | Best For | Output | Python |
|--------|----------|--------|--------|
| 3-state GaussianHMM | Primary regime detector | P(state) | hmmlearn |
| BOCPD | Transition timing | P(changepoint) | bayesian_changepoint_detection |
| Markov Switching | Academic credibility | P(state) | statsmodels |
| RS-GARCH | Vol-regime precision | Regime + GARCH per state | arch |
| GBM Classifier | Non-linear combination | P(regime) + SHAP | sklearn |
| Particle Filter | Gradual transitions | Continuous state dist | filterpy |

**L4 target: HMM + BOCPD.** L5 upgrade: RS-GARCH + GBM.

---

## Four Regime Dimensions

### RE1 — Trend/Direction Regime (primary signal gate)
Answers: Is gold in a sustained directional move or ranging?
Inputs: Context Score, price autocorrelation (Hurst exponent), real yields momentum, COT trend
Output: TRENDING BULL / TRENDING BEAR / RANGING / TRANSITION
Role: Primary gate on SAMTC breakout signals. Breakouts only fire in TRENDING states.

### RE2 — Volatility Regime (sizing engine)
Answers: Is vol expanding or compressing?
Inputs: 10/20/60-day realised vol, VIX level, GEX (negative = vol expansion conditions), RV/IV ratio
Output: HIGH EXPANDING / HIGH STABLE / LOW COMPRESSING / LOW STABLE

| Vol State | Stop Width | Position Size |
|-----------|-----------|---------------|
| HIGH EXPANDING | 2× base stop | 50% base size |
| HIGH STABLE | 1.5× base stop | 75% base size |
| LOW STABLE | 1× base stop | 100% base size |
| LOW COMPRESSING | 0.8× base stop | 100% + anticipate breakout |

### RE3 — Correlation Regime (signal trust calibrator)
Answers: What is gold behaving like — safe haven, inflation hedge, or risk asset?
Inputs: Rolling 20-day correlations: gold/SPX, gold/TLT, gold/DXY, gold/BTC

| Mode | Correlation Pattern | Dominant Driver |
|------|-------------------|-----------------|
| Safe Haven | gold/SPX negative, gold/TLT positive | VIX, geopolitical |
| Inflation Hedge | gold/TLT negative, gold/breakevens positive | Real yields |
| Risk Asset | gold/SPX positive (unusual) | Liquidity, risk appetite |
| Decoupled | Correlations near zero | Idiosyncratic / CB buying |

### RE4 — Liquidity Regime (execution gate)
Answers: Can I execute this trade cleanly right now?
Inputs: COMEX OI vs 30-day average, bid-ask spread, futures basis, intraday vol vs daily average
Output: LIQUID / THIN / CRISIS

### How They Connect

```
RE1 Trend Regime ──────
                       ──── Trade? Yes/No + direction
RE3 Correlation ────────
                             ↓
                       RE2 Vol Regime ─── Stop width + position size
                             ↓
                       RE4 Liquidity ─── Execute now or wait
```

---

## Level Spectrum — Beginner to World Class

### Level 2 — Structured Rules
```python
def classify_regime(ry_zscore, gex, vix_level):
    if gex > 0:
        return "RANGE"
    elif ry_zscore < -0.5 and gex < 0:
        return "BULL_TREND"
    elif ry_zscore > 0.5 and gex < 0:
        return "BEAR_TREND"
    else:
        return "TRANSITION"
```
Regime accuracy: ~63–65%.

### Level 3 — Composite Regime Score
```python
def compute_regime_score(ry_zscore, gex_signal, rv_iv_ratio, cot_zscore):
    score = (
       -0.40 * np.clip(ry_zscore, -2, 2) +
        0.30 * (-1 if gex_signal > 0 else 1) +
        0.20 * np.clip(rv_iv_ratio - 1.0, -1, 1) +
       -0.10 * np.clip(cot_zscore, -2, 2)
    )
    return np.clip(score, -2, 2)
```
Regime accuracy: ~68–72%.

### Level 4 — 3-State HMM + BOCPD (Tier C Target)

```python
from hmmlearn import hmm

model = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=42)
model.fit(features_scaled_train)

regime_probs = model.predict_proba(features_scaled_live)
# Output: [P(bull), P(bear), P(range)] at each timestep

def compute_position_size(regime_probs, cp_prob, base_risk=0.01):
    conviction   = float(np.max(regime_probs))
    trans_scalar = 1.0 - (cp_prob * 0.5)
    return base_risk * conviction * trans_scalar
```
Regime accuracy: ~78–82%.

### Level 5 — World Class
RS-GARCH + multiple independent HMMs per dimension + GBM classifier + SHAP.
Regime accuracy: ~84–88%.

---

## Build Path

| Phase | Timeline | Work |
|-------|----------|------|
| L2 rules-based | Already conceptual | Formalise threshold logic |
| L3 composite score | Weeks 1–2 | Python script, score + sizing |
| L4 HMM + BOCPD | Month 2–3 | Main build, 2–3 weeks |
| L5 RS-GARCH + multi-dim | Month 4+ | Ongoing development |
