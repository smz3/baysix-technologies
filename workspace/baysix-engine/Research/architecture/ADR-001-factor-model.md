# ADR-001: Factor Model Selection

**Date:** 2026-05-13  
**Status:** Active  
**Component:** `adapters/*/factors.py` + `core/ic_engine.py` (residual alpha computation)

---

## Decision

| Universe | Factor Model | Source |
|----------|-------------|--------|
| US equities / ETFs | Fama-French 5 Factor (FF5) | Kenneth French data library — free, point-in-time |
| ASEAN ETFs | MSCI-style regional (Size, Value, Momentum, Quality) | Constructed from regional return data |
| Futures | AQR-style (Carry, Momentum, Value, Basis) | Asness et al. methodology |
| Crypto | Custom 4-factor (BTC Beta, Funding Rate, Momentum, Liquidity) | CCXT / Binance OHLCV |

Beta estimation: **static OLS** over full IS period. One regression. One set of betas.

---

## Why

**FF5 for US equities:**
- Free, publicly available, no vendor dependency
- Point-in-time by construction (Kenneth French updates retroactively)
- Academic and practitioner standard — any PM or QR knows what it means
- Covers ~90% of cross-sectional return variation in US equities
- Residual alpha after FF5 is the most credible "real alpha" claim in any interview

**MSCI-style for ASEAN:**
- FF5 is calibrated on US data — applying it to EWM, EWS, EWJ produces unreliable factor loadings
- MSCI factor definitions (size, value, momentum, quality) are designed for global/regional application
- Cannot use the Kenneth French library directly for ASEAN — must construct regional factor portfolios

**AQR-style for futures:**
- FF5 is equity-specific — no applicability to commodities, rates, FX
- AQR multi-asset factors (carry, momentum, value, defensive) are the published standard for futures
- Carry and momentum are the two most robust futures factors in the literature

**Custom 4F for crypto:**
- No academic consensus on crypto factor model
- BTC beta captures the dominant systematic risk (market factor)
- Funding rate is a crypto-specific carry factor with documented predictive power
- Must construct — no external library

**Static OLS:**
- Simplest defensible implementation
- Sufficient for IS validation where betas are relatively stable
- Rolling upgrade path is documented (see Deferred section)

---

## Alternatives Considered

| Alternative | Description | Why not chosen now |
|-------------|-------------|-------------------|
| **Fama-French 3 Factor (FF3)** | Mkt-RF, SMB, HML | Omits RMW and CMA — FF5 is strictly superior for equity residual alpha |
| **Carhart 4 Factor** | FF3 + Momentum (UMD) | If momentum IS our signal, including UMD mechanically strips our own alpha — do not use when testing momentum signals |
| **BARRA / Axioma** | Commercial 50+ factor models | $50k+/yr. Justified at live AUM > $500k — not now |
| **PCA / Statistical factors** | Data-driven factor discovery from return covariance matrix | No economic interpretation — hard to explain. Valid supplement to FF5, not replacement |
| **APT Macro factors** | Inflation, GDP, yield curve, credit spreads | Better for macro-driven strategies. Not the primary driver for cross-sectional equity signals |
| **Rolling OLS (252-day)** | Re-estimate betas annually on trailing data | More accurate — deliberately deferred. See trigger below |
| **Kalman Filter betas** | Continuous real-time beta estimation | Most accurate — complex. Reserved for post-live-deployment monitoring |

---

## Deferred Upgrades

### Upgrade 1: Static OLS → Rolling 252-day OLS

**What it is:** Re-estimate factor betas every year on the trailing 252 trading days. Betas are not constant — factor exposures change as market structure evolves.

**Trigger condition:** IC is statistically significant overall (NW t-stat > 2.0) but subsample IC is inconsistent — strong in early IS, weak in late IS. This is the symptom of beta instability, not signal decay.

**How to implement:** Replace single `np.linalg.lstsq` with `rolling(252).apply(OLS)` on the return series. Report time-varying betas alongside static betas in the tearsheet.

### Upgrade 2: FF5 → FF5 + PCA Latent Factors

**What it is:** After running FF5 regression, run PCA on the residuals. If the first PCA component explains >15% of residual variance, there is hidden structure FF5 is missing.

**Trigger condition:** FF5 R² < 0.40 on ASEAN universe, OR residual returns show clear cluster structure when plotted against time.

**How to implement:** `sklearn.decomposition.PCA` on the OLS residual matrix. Report first 3 PC eigenvalues alongside FF5 output. If significant → add as additional factors.

### Upgrade 3: Custom ASEAN → BARRA / Axioma

**Trigger condition:** Live AUM > $500k deployed on ASEAN strategies. At that scale, cost of commercial model is justified by risk management value.

---

## Carhart Warning (Important)

If testing a **momentum signal**, do NOT include the momentum factor (UMD / Carhart) in the factor model. UMD is constructed from the same return-ranking procedure as the signal — including it mechanically explains away the alpha you are trying to measure.

Use FF5 only when testing momentum. Use Carhart 4F only when testing non-momentum signals where you want to control for momentum exposure.

---

## Interview Defence

> "We use FF5 for US equities because it's the academic standard, freely available point-in-time, and residual alpha after FF5 is the most credible form of alpha attribution in the literature. For ASEAN, FF5 is US-calibrated and doesn't transfer cleanly — we construct MSCI-style regional factors instead. We're running static betas now, with a documented upgrade path to rolling 252-day estimation triggered by subsample IC instability."
