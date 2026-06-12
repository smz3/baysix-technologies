# Handover — June 12, 2026 Afternoon2

## State
🚨 **ORB-001 Gates 0–6 FALSIFIED — look-ahead artifact of time-UNSORTED parquet ticks.** Fork A (Gate-7 re-validation) surfaced the real bug: `data/parquet` `ts_utc` is not time-sorted (~33 gross block inversions/month); `_simulate_day` finds "first breakout" via `np.argmax` (first by **array position, not time**) and trails in array order → hindsight entries on boundary days print +11..+14R that ARE the whole edge. Sorting chronologically collapses it: anchor_oos 09:00/N5 OOS **+7.62 $/t (t=10.74) → −0.18 (t=−1.32)**; full-OOS ideal-fill E[R]=−0.0857. The MT5 tester (chronological) was **correct all along**; margin/spread/fill-model were all symptoms. Logged: **result_id 121**, **strategy_log #23 FALSIFIED**. New code: [fork_a_ea_emulation.py](research/models/orb/orb001/fork_a_ea_emulation.py), [reconcile_cache_vs_parquet.py](research/models/orb/orb001/reconcile_cache_vs_parquet.py). Committed + pushed. Correction: prior +67.4R was NOT a hand-typed phantom — it reproduces from the buggy unsorted pipeline; the lint/enforcement framing (task 50) was a partial misdiagnosis.

## Next
1. **Task 52 (P1) — blast-radius check:** run the 2-month sort-vs-nosort probe on ORB-002 + ORB-003 (same as ORB-001). Almost certainly the same artifact (shared `_simulate_day` + same parquet). If edge collapses → FALSIFY their validations too.
2. **Task 51 (P0) — fix root cause:** globally sort each `data/parquet` partition by `ts_utc` at ingestion + fix the writer; add a sort+`assert is_monotonic` guard in `_simulate_day` / every tick consumer (orb_core, session_cache consumers, trail_oos). `session_cache` inherits source order → equally affected.
3. **Task 53 (P1)** — after the fix, re-run ORB-001 Gates 3–6 on sorted ticks to see if ANY smaller real edge survives (current chronological OOS E[R]=−0.0857 says likely dead).

## Blockers
None. Tasks 35/47/48 (Gate-7 forks), 49 (workflow), 50 (handover lint) are now downstream/secondary — don't work them before 51/52. See [[orb_unsorted_tick_lookahead]] + [[orb001_validated]] (now void).
