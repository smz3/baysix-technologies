# Context Engine Architecture
*Sigma Trading System | Syafiq M. Zin | May 2026*

---

## What a Context Engine Is

A Context Engine transforms raw, heterogeneous data into normalised, comparable, meaningful signals that describe the current state of the market environment. It answers one question: **what is the environment right now?** Not what to trade. Not what regime. Just: what does each data source say, normalised and ready to combine.

---

## Five First Principles

**1. Stationarity**
Raw data lies. Price levels, yield levels, COT absolute positions — all non-stationary. They trend. You cannot model trends as if they're stationary signals. Transform everything: use changes, rates of change, z-scores of changes. The context engine's first job is making every input stationary.

**2. Normalization**
Real yields move in basis points. COT moves in thousands of contracts. GEX moves in billions of notional. You cannot combine these directly. Z-score everything against a rolling window so every signal outputs in σ-units — standard deviations from its own mean. Now they speak the same language.

**3. Temporal Alignment**
Signals update at different frequencies. FRED: daily. COT: weekly (Tuesday positions, Friday release). Polygon: daily. You need a daily snapshot that correctly forward-fills stale data while knowing how old it is. Most beginners ignore this and introduce look-ahead bias.

**4. Signal Decay**
Information has a half-life. A real yields move from 3 months ago carries less predictive weight than last week's. Use exponential weighted mean (EWM) instead of fixed rolling windows. Recent observations count more. This materially improves IC vs static windows.

**5. Redundancy Management**
Real yields and DXY are correlated at ~-0.7. Including both at full weight means 170% exposure to the same underlying factor. Measure correlation between signals and down-weight redundant ones. PCA (Level 4) solves this mathematically.

---

## Kalman Filter — The HMM Equivalent for Context Engine

HMM is used in the Regime Classifier — it models discrete hidden states.

The Kalman Filter is the equivalent upgrade for the Context Engine. It models the **continuous hidden state** — the true underlying signal — and filters out noise from each observation.

**The problem:** Every signal you measure = true signal + noise. Real yields jump around daily. Some of that jumping is real information. Some is market noise. Feed the raw noisy signal into your context engine and noise gets treated as signal. The Regime Classifier misfires.

**What Kalman Filter does:** Maintains a running estimate of the true underlying state and updates it optimally with each new observation. It knows how much to trust the new data vs the prior estimate based on the noise characteristics.

```python
from pykalman import KalmanFilter

kf = KalmanFilter(
    transition_matrices=[1],
    observation_matrices=[1],
    initial_state_mean=0,
    initial_state_covariance=1,
    observation_covariance=0.5,    # how noisy is the observation
    transition_covariance=0.1      # how fast does the true state change
)

filtered_state, _ = kf.filter(real_yields_series)
# filtered_state = clean signal, noise removed
```

Calibrate `observation_covariance` by maximising IC on your training set. Higher = smoother filter = less trust in each new observation.

Apply independently to each input signal before any z-scoring.

---

## The Four Context Engines

One context engine is not enough. You need four, each answering a completely different question.

**CE1 — Macro Context Engine**
Answers: What is the fundamental backdrop for gold?
Inputs: FRED DFII10 (real yields), DXY, 10Y breakeven inflation, FOMC rate expectations
Update frequency: Daily/weekly
Signal horizon: Days to weeks

**CE2 — Options Structure Context Engine**
Answers: What does the derivatives market say about near-term mechanics?
Inputs: GEX (net dealer gamma), IV skew (25Δ risk reversal), term structure (front vs back month IV), put/call ratio, vanna exposure
Update frequency: Daily
Signal horizon: Hours to days

**CE3 — Cross-Asset Correlation Context Engine**
Answers: Is gold behaving consistently with its usual relationships, or is something breaking?
Inputs: Rolling 20-day correlation — gold vs SPX, gold vs TLT, gold vs DXY, gold vs copper, gold vs BTC
When correlations deviate significantly from 1-year norms, regime is shifting.
Update frequency: Daily rolling
Signal horizon: Days to weeks

This engine is underused and powerful. When gold's correlation with TLT breaks (gold rising while bonds sell off), the move is geopolitically driven, not rates-driven. Different regime, different duration, different trade management.

**CE4 — Microstructure Context Engine**
Answers: What is the intraday market structure saying right now?
Inputs: Volume profile, VWAP deviation, intraday vol patterns, COMEX OI daily change, futures basis
Update frequency: Intraday / end of day
Signal horizon: Hours

CE4 does **not** gate whether you trade. It gates **when and how** you enter once CE1-CE3 have said go. It feeds execution timing only.

```
CE1 Macro Score  →
CE2 Options Score ──→ Regime Classifier → SAMTC Signal → Execution
CE3 Corr Score   →
CE4 Microstructure ───────────────────────────────────── Entry timing only
```

---

## Level Spectrum — Beginner to World Class

### Level 1 — Beginner
Single signal, no normalisation, qualitative judgment. "Real yields went down this week, so I'm bullish." IC: unmeasured, likely 0.02–0.04.

### Level 2 — Structured Beginner
Multiple signals, z-scored, binary gates.

```python
window = 252
ry_zscore = (real_yields - real_yields.rolling(window).mean()) / real_yields.rolling(window).std()
macro_gate = (ry_zscore < -0.5).astype(int)  # binary: 1 or 0
```

Fixed windows, no decay, binary output, no correlation handling. IC: 0.03–0.06.

### Level 3 — Intermediate
Composite scoring, decay-weighted (EWM), IC-validated per signal.

```python
# Decay-weighted z-score
ry_zscore = (real_yields - real_yields.ewm(span=60).mean()) / real_yields.ewm(span=60).std()

# IC calculation per signal
def calculate_ic(signal, forward_returns, horizon=5):
    return signal.corr(forward_returns.shift(-horizon))

# IC-weighted composite
total_ic = ic_macro + ic_options + ic_cot
composite = (ic_macro/total_ic)*zscore_macro + (ic_options/total_ic)*zscore_options + (ic_cot/total_ic)*zscore_cot
```

IC: 0.06–0.10.

### Level 4 — Advanced (Tier C Ready)
Kalman-filtered signals, PCA redundancy removal, dynamic IC weighting, multiple context engines.

**Full L4 Pipeline:**

**Step 1 — Kalman Filter each signal**
```python
from pykalman import KalmanFilter

def kalman_filter_signal(series):
    kf = KalmanFilter(
        transition_matrices=[1], observation_matrices=[1],
        initial_state_mean=series.iloc[0], initial_state_covariance=1,
        observation_covariance=0.5, transition_covariance=0.1
    )
    filtered_state, _ = kf.filter(series.values)
    return pd.Series(filtered_state.flatten(), index=series.index)

filtered_ry  = kalman_filter_signal(real_yields)
filtered_cot = kalman_filter_signal(cot_net_pos)
filtered_gex = kalman_filter_signal(gex_series)
filtered_skew = kalman_filter_signal(iv_skew)
filtered_corr = kalman_filter_signal(cross_asset_corr)
```

**Step 2 — EWM Z-Score**
```python
def ewm_zscore(series, span=60):
    mean = series.ewm(span=span).mean()
    std  = series.ewm(span=span).std()
    return (series - mean) / std

z_ry   = ewm_zscore(filtered_ry)
z_cot  = ewm_zscore(filtered_cot)
z_gex  = ewm_zscore(filtered_gex)
z_skew = ewm_zscore(filtered_skew)
z_corr = ewm_zscore(filtered_corr)
```

**Step 3 — IC Calculation + Dynamic Weighting**
```python
def rolling_ic(signal, forward_returns, horizon=5, window=126):
    lagged_returns = forward_returns.shift(-horizon)
    return signal.rolling(window).corr(lagged_returns)

ic_ry   = rolling_ic(z_ry, gold_returns)
ic_cot  = rolling_ic(z_cot, gold_returns)
ic_gex  = rolling_ic(z_gex, gold_returns)
ic_skew = rolling_ic(z_skew, gold_returns)
ic_corr = rolling_ic(z_corr, gold_returns)

# Normalize weights
total_ic = ic_ry + ic_cot + ic_gex + ic_skew + ic_corr
w_ry = ic_ry / total_ic
# (repeat for each signal)
```

**Step 4 — PCA Decomposition**
```python
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import numpy as np

# Stack all z-scored signals
signal_matrix = np.column_stack([z_ry, z_cot, z_gex, z_skew, z_corr])

# Remove NaNs for fitting
clean_matrix = signal_matrix[~np.isnan(signal_matrix).any(axis=1)]

scaler = StandardScaler()
scaled = scaler.fit_transform(clean_matrix)

pca = PCA(n_components=3)
independent_components = pca.fit_transform(scaled)
# 5 correlated signals → 3 orthogonal components
# Explained variance ratio tells you how much information each component carries
print(pca.explained_variance_ratio_)
```

**Step 5 — IC-Weighted Composite Score**
```python
# Calculate IC for each PCA component against forward returns
ic_pc1 = rolling_ic(pd.Series(independent_components[:,0]), gold_returns)
ic_pc2 = rolling_ic(pd.Series(independent_components[:,1]), gold_returns)
ic_pc3 = rolling_ic(pd.Series(independent_components[:,2]), gold_returns)

total_ic_pca = ic_pc1 + ic_pc2 + ic_pc3
context_score = (
    (ic_pc1/total_ic_pca) * independent_components[:,0] +
    (ic_pc2/total_ic_pca) * independent_components[:,1] +
    (ic_pc3/total_ic_pca) * independent_components[:,2]
)
# Output: context_score, continuous, feeds Regime Classifier
```

IC: 0.08–0.14.

### Level 5 — World Class
What changes from Level 4:

**ADD — Alternative Data + Real-Time Feeds**
NLP sentiment on gold news headlines, satellite mine output data, physical gold flow data, real-time streaming feeds (not daily batch). Expands the information set beyond what's publicly available on standard schedules.

**REPLACE — ML Ensemble replaces PCA + IC Weighting**
```python
from sklearn.ensemble import GradientBoostingRegressor

gbm = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05)
gbm.fit(signal_matrix_train, forward_returns_train)

context_score = gbm.predict(signal_matrix_live)
```

Learns non-linear combinations. Discovers patterns like: "real yields falling AND GEX negative AND pre-FOMC week = 3× stronger signal than any factor individually."

**ADD — Ledoit-Wolf Covariance**
```python
from sklearn.covariance import LedoitWolf

lw = LedoitWolf()
lw.fit(signal_matrix)
covariance_matrix = lw.covariance_
```

**ADD — Continuous IC Monitoring + Auto-Retire**
```python
rolling_60d_ic = signal.rolling(60).corr(forward_returns.shift(-5))

if rolling_60d_ic.iloc[-1] < 0.01:
    signal_active[signal_name] = False
    alert("Signal decaying — review required")
```

**UPGRADE — Output: Distribution + SHAP Attribution**
```python
import shap

explainer = shap.TreeExplainer(gbm)
shap_values = explainer.shap_values(signal_matrix_today)
# L4 output: single number
# L5 output: score + confidence interval + per-signal attribution
```

IC: 0.12–0.20+.

---

## Build Path for Sigma Gold

| Phase | Timeline | Work | Target |
|-------|----------|------|--------|
| L2 → L3 | Weeks 1–3 | IC calculation per signal, EWM z-scores, composite scoring | Validated IC numbers per signal |
| L3 → L4 | Month 2 | Kalman filter, PCA, build CE2 + CE3 | Full L4 pipeline with IC 0.08+ |
| L4 → L5 (partial) | Month 4+ | GBM signal combiner, IC auto-monitoring | Ongoing development |

L4 is the Tier C interview target. It requires demonstrating: IC per signal, ICIR, how signals combine, what PCA components represent, and what the composite context score predicts on OOS data.

---

## Python Library Stack

| Library | Use |
|---------|-----|
| `pykalman` | Kalman Filter for noise removal |
| `pandas.ewm()` | Decay-weighted normalization |
| `sklearn.decomposition.PCA` | Redundancy removal |
| `sklearn.covariance.LedoitWolf` | Stable covariance (L5) |
| `sklearn.ensemble.GradientBoostingRegressor` | ML signal combiner (L5) |
| `shap` | Signal attribution (L5) |
| `fredapi` | FRED data pull |
| `polygon` | GLD options chain |
