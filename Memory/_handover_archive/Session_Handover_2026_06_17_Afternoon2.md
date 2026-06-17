# Handover — June 17, 2026 Afternoon2

## State
- **BRC-001 — DISCOVERY (Gate 2 passed; Gate 3 deliberately NOT entered).** Syafiq's call: costing a rule that isn't frozen is meaningless — stay descriptive, no cost, until the strategy is shaped. Do NOT open Gate 3.
- **Tasks 116 + 108 DONE + pushed.**
  - [lifecycle.py](research/models/brc/brc001/lifecycle.py) (t116) — invalidation = first candle CLOSING beyond L2 (close>max(L1,L2) SELL / close<min(L1,L2) BUY), EA-mirrored. D1: 245 zones, 196 dead/49 alive, first-death invariant 0/196. strategy_log #49.
  - [retest.py](research/models/brc/brc001/retest.py) (t108) — wick touch ladder T1=L1/T2=mid/T3=L2, **death bar EXCLUDED** (else T3 trivially flags on every kill). deepest_T {T0:31,T1:28,T2:83,T3:103}. strategy_log #50.
  - [continuation.py](research/models/brc/brc001/continuation.py) — fixed-H DEPRECATED (~48% of retests outlive +10 bars). Replaced by `excursion()` (MFE/MAE in R, alive-window) + `barrier_race()` (Ruler B, close-based: WIN=close ≥target·R break-dir first, LOSS=close beyond L2 first, OPEN=alive at end). [dataset.py](research/models/brc/brc001/dataset.py) assembles per-zone table → research/outputs/brc001/ (gitignored).
- **KEY FINDING — directional thesis FALSIFIED vs trend beta (strategy_log #51).** D1, cost-free, Ruler-B 1R race, entry=L1 retest:
  - pooled win 50.5%; by dir BUY 56.5% / SELL 44.2% (n=108/106).
  - trend-beta baseline (random same-dir entry, same per-zone R, ±1R, 2000-boot): BUY 57.7±4.8 (BRC z=−0.25), SELL 41.9±4.7 (z=+0.51). **Retest entry adds NOTHING over beta.** Numbers reproduce from continuation.py `barrier_race` + the inline baseline (no result_id — discovery, pre-Gate, not logged to step4_results by design).
  - deepest_T near-flat (T1/T2 ~54% vs T3 ~47%, T1 n=28 thin). MFE median 2.12R / mean 24.6R (right-skew, rank by median).

## Next
1. **The ONE surviving test (do this first):** payoff/exit asymmetry — does letting winners run to invalidation beat a let-winners-run RANDOM same-dir baseline (matched R, matched entry count)? Winners' MFE ~2R vs 1R stop is the only thread left. If it also ≈ beta → 2nd FALSIFIED → kill BRC (rule 8b needs ≥2). Build alongside `barrier_race` in continuation.py.
2. If (1) survives: re-run the worked-vs-invalidated funnel + which-T conditioner on that exit rule, still cost-free.
3. Only after a D1 edge is shown to beat beta: repeat detection→lifecycle→retest→race per TF (pipeline already TF-agnostic via `detect_zones(tf)`), THEN multi-TF russian-doll combos, THEN plot.

## Blockers
None. Caveat to carry: every BRC number so far is direction-confounded by gold's 2016→2026 3.6× bull run — ALWAYS compare against a direction-matched random baseline before claiming a zone edge (same trap as ORB-001). Gate 3 stays CLOSED until a rule is frozen AND beats beta.
