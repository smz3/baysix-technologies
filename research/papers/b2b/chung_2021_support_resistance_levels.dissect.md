# Dissection — Evidence and Behaviour of Support and Resistance Levels in Financial Time Series

- **Authors:** Chung, K.; Bellotti, A.
- **Year:** 2021
- **paper_id:** 29  ·  **idea:** B2B-001
- **Model:** opus  ·  **Dissected:** 2026-06-16 09:59:32
- **Source:** arxiv  ·  **DOI:** n/a

> Reconstructed from research.db (step2_papers + DISSECT log_agent) by backfill_dissect_md.py. The DB is the source of truth.

## Summary

ACTIONABLE WITH TRANSLATION + REPLICATION. Confirms two B2B priors quantitatively: zone strength RISES with retest-holds (touch count) and zone edge DECAYS with age, and the effect is genuine memory (beats shuffled returns + AR(1)), not mean-reversion. Provides a ready Bayesian estimator E[p(b|bprev)]=(n+1)/(N+2) for a per-touch retest hit-rate prior and a logistic age-slope spec for a freshness/invalidation model. BUT their level = rolling min/max, NOT our swing double-break; decay constants are 2018-FX-specific; gold untested; no costs -- so do NOT inherit the ~350/900min windows; replicate the framework on XAUUSD ticks. Opens Gate-0/1 framing for B2B-001: (a) min-touch threshold, (b) freshness/age cutoff, (c) penetration=invalidation.

## Key Equations

[§2.1 Def 2.1] confidence: full-text
Support level = interval [a,b]: if x_t in [a,b] then P(x_{t+d}>b) > P(x_{t+d}<a) for all d in 1..omega. Resistance is the mirror (Def 2.2). omega = level lifetime (temporary by construction).

[§2.1] confidence: full-text
Bounce = price enters interval from one boundary and exits through the SAME boundary; penetration = enters one boundary, exits the OTHER. Strength p(b) = P(exit on bounce side)/P(any exit), conditional on exit; >0.5 = predictive.

[§2.2 Eq.1] confidence: full-text
Level discovery: rolling window of i minutes; support=min(X_t)-gamma, resistance=max(X_t)+gamma; gamma = avg abs price increment Delta = (1/(T-1)) sum |x_t - x_{t-1}|. Calibrated so a random walk yields p(b)=0.5 (higher gamma inflates p(b), lower deflates).

[§2.2] confidence: full-text
Bounce count S_b = floor(0.5 * sum of upper-boundary crossings) over the window.

[§2.3] confidence: full-text
Strength-vs-touches estimator: Bayesian binomial-Beta, uniform prior U[0,1], posterior Beta(n+1, N-n+1). E[p(b|bprev)] = (n_bprev+1)/(N_bprev+2); Var = (n+1)(N-n+1)/((N+3)(N+2)^2).

[§3.2 Eq.2] confidence: full-text
Significance: permutation test Lambda = E[1(p_orig > p_shuffled)] via Monte Carlo, 1000 shuffled-return series.

[§4.2] confidence: full-text
Micro-decay logistic: log(Y/(1-Y)) = a + bX, Y=1 bounce / 0 penetration, X=time since last bounce; a=baseline (>0 => p>0.5), b=age slope (negative => decay).

## Empirical Findings

[§3 / §3.1] confidence: full-text
Data: 2018 minute intraday, 3 assets -- EURUSD (FX, 372,607 obs), LLOY (LSE equity, 127,606), BRENT crude (commodity, 307,678).

[§3.1 Fig 3.1-3.6] confidence: full-text
STRENGTH-RISES-WITH-TOUCHES: p(b|bprev) positively correlated with #prior bounces across all 3 assets and both 60/240min windows; original series >> shuffled-returns; no discernible support-vs-resistance difference.

[§3.2 Table 3.1] confidence: full-text
Permutation Lambda mostly >0.95 (EURUSD 60min ~1.000 for bprev 1-6); effect significant vs shuffle up to bprev=5. LLOY high-bprev weak -- smallest Lambda 0.226 (short series).

[§4.1 Fig 4.1] confidence: full-text
MACRO-DECAY (age via lag window, EURUSD): p(b) falls toward 0.5 as window lengthens; bprev=1 decays to 0.5 by ~350min, bprev=4 holds to ~900min -- MORE touches = SLOWER decay.

[§4.2 Table 4.1] confidence: full-text
MICRO-DECAY EURUSD (600min window): intercept a rises with bprev (0.005 -> 0.40*** @bprev4 -> 0.72* @8); age slope b negative throughout, significant only at bprev=4 (b=-0.00179*, N=505) and bprev=5 (b=-0.00273*, N=258). High-bprev N too small.

[§4.2 Table 4.3] confidence: full-text
BRENT micro-decay b sign inconsistent except bprev=4 (b=-0.00195**, N=467); bprev=1 BRENT decays BELOW 0.5 (predicts penetration) in 2018 bear quarter.

[§4.1 Table 4.2] confidence: full-text
LLOY persistent -- macro-decay inconclusive (most p(b) stay above 0.5); attributed to equity market structure.

[§5 Fig 5.1-5.3] confidence: full-text
AR(1) simulation (length 1M; rho=1/0.95/0.9): bprev NEGATIVELY correlated with p(b) -- effect CANNOT be reproduced by stationary AR(1). Confirms genuine memory, not a mean-reversion artifact.

## Context Fit

**Paper asset:** EURUSD (FX), LLOY (LSE equity), BRENT crude (commodity); gold NOT tested. BRENT is the closest analog to XAUUSD.
**Paper frequency:** 1-minute intraday bars, year 2018.
**Target asset:** XAUUSD - tick/intraday on MT5 (Just Markets); IS sealed 2024-05-02, OOS 2024-05-02 -> 2026.
**Frequency match:** Partial
**Key deltas:**
1. Level definition: paper = rolling-window min/max +/- gamma (recent extreme); B2B = structural swing double-break origin. bprev semantics do NOT transfer 1:1 -- must be re-defined as post-formation retest-holds on our ticks.
2. Asset: gold has round-number clustering + 24h session structure unlike EURUSD/BRENT; decay windows are FX-2018-specific, not transferable constants.
3. Resolution: gamma is resolution-dependent; on XAUUSD ticks gamma must be re-derived or p(b) is biased.
4. Regime: authors attribute several sub-0.5 decays to 2018 bear market -- single-year, regime-contaminated.
**Direct applicability:** MEDIUM
**Reason:** The framework (touch-count strength + age-decay + Bayesian hit-rate estimator + penetration=invalidation) maps cleanly onto B2B zone lifecycle, but the level definition and decay constants must be replicated on XAUUSD ticks before trusting any number.
**Parameters to re-validate:** (a) min-touch threshold -- p(b) by bprev bucket on our zones (b) freshness/age cutoff -- macro+micro decay on XAUUSD (c) gamma / zone width on ticks (d) penetration-as-invalidation rule (e) per-touch retest hit-rate prior E[p]=(n+1)/(N+2).

## Limitations

[§2.2] confidence: full-text
Level = rolling-window min/max +/- gamma -- mechanically different from B2B swing/double-break formation; their level is a recent extreme, ours is a breakout origin, so bprev does not transfer 1:1.

[§3 / §4.1] confidence: full-text
Only 2018, single year, 3 assets; decay shapes admittedly asset-AND-regime specific (BRENT/EURUSD support sub-0.5 decay blamed on 2018 bear market). Numbers are not stable constants.

[§2.2] confidence: full-text
gamma = avg-increment width is resolution-dependent; higher gamma inflates p(b), lower deflates. On XAUUSD ticks gamma must be re-derived.

[§4.2 Table 4.1] confidence: full-text
Micro-decay statistically significant only at bprev=4-5 (EURUSD) and isolated cells elsewhere; high-touch buckets small-N (N=41-151), underpowered -- decay slope suggestive, not robustly proven.

[§3.1] confidence: full-text
No transaction costs, no spread/slippage modelled; p(b)>0.5 is signal EXISTENCE, not tradeable edge.

[§2.2] confidence: full-text
Discovery freezes while price is inside a level and assumes one level pair at a time -- ignores overlapping/nested zones (relevant to Russian-doll B2B).

[§3] confidence: full-text
Gold never tested; round-number clustering and 24h session structure differ from EURUSD/BRENT.
