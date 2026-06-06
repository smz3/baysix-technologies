# Handover — May 29, 2026 Evening2

## State
HMM-001: Gate 0 + Gate 1 passed. Gate 2 BLOCKED (attempt 1, result_id=1) — old features [r_t, |r_t|] and [r_t, rolling_vol] both failed persistence (min A_jj < 0.85) and occupancy checks. Gate 2 objective criteria are now locked in research_protocol.md (4 hard checks: convergence, occupancy 5–90%, persistence A_jj > 0.85, vol_ratio > 2.0). research/models/hmm/ has gaussian_hmm.py (formal Gate 2 runner, attempt 1 done) and gaussian_hmm_sweep.py (exploratory sweep, all 6 windows blocked).

## Next
1. Read hedge_fund_method_10_steps.md — this is the full spec. Steps 1–9 = rule-based Markov chain baseline. Step 10 = HMM (HMM-001). Follow it 1:1 on XAUUSD.
2. Gate 2 attempt 2: rewrite gaussian_hmm.py feature to 20d rolling cumulative return (matches Step 1 of the spec). Run via `python research/models/hmm/gaussian_hmm.py`. Log as attempt=2 in DB.

## Blockers
None — clear path forward.
