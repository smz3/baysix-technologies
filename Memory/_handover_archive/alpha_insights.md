# Alpha Insights
Last Updated: 2026-03-11
Owner: Memory Curator (synthesized from Quant Researcher + CIO outputs)

## Validated Edges

### [2026-03-11] — Structural B2B Zones as Liquidity Anchors
**Insight**: Break-to-Break zones on higher timeframes (D1/H4) act as durable liquidity anchors that price repeatedly returns to with predictable behavior.
**Evidence**: 7 years of BTCUSDT backtesting, 10,000 Monte Carlo iterations (Test 10C: Calmar 3.90, Recovery Factor 13.21)
**Instruments**: BTCUSDT perps, EURUSD (MT5)
**Status**: Validated — production baseline
**Source**: sigma-crypto Test 10C, sigma-mt5 V5.0

---

### [2026-03-11] — Multi-Timeframe Consensus Amplifies Signal Quality
**Insight**: SAMTC's multi-temporal consensus (MN1 → W1 → D1 → H4 → H1 aligned) produces trades with significantly better payoff ratios than single-timeframe signals.
**Evidence**: Test 13A OOS: Payoff 1.65, Skew 3.43 — positive skew means winners significantly larger than losers
**Status**: Validated OOS (2024-2025)
**Source**: sigma-crypto Test 13A

---

### [2026-03-11] — 5-Point Swing Geometry Filters Noise
**Insight**: Requiring a valid 5-point fractal swing structure (sigma-crypto/core/filters/fractal_geometry.py) as a filter eliminates the majority of false B2B zone activations.
**Evidence**: Documented in Master_Research_Paper_Fractal_Liquidity_Anchors.md
**Status**: Validated — incorporated into SAMTC core
**Source**: sigma-crypto research papers

---

## Hypotheses Under Investigation

### [2026-03-11] — B2B Cluster Detection Edge Case (MT5)
**Hypothesis**: The current V5.0 cluster detection algorithm picks older L1/L2 levels than intended in clustered breakout scenarios, reducing trade quality.
**Evidence**: Documented in sigma-mt5/Documentation/B2B_CLUSTER_FIX_PLAN.md (3 proposed solutions)
**Status**: Hypothesis — fix options A/B/C under evaluation
**Next Step**: Quant Researcher to evaluate options, Quant Developer to implement and test

---

## Invalidated Ideas (Learn From These)

*[No invalidated ideas documented yet — update as research progresses]*

---

## Open Questions
1. Does SAMTC edge survive under realistic live slippage assumptions vs clean backtest fills?
2. Does the B2B zone edge transfer across instruments (ETH, SOL perps)?
3. What is the optimal timeframe for SAMTC on intraday (M15/M30)?
