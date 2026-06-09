"""
ORB-001 anchor/OR-window OOS + fill re-validation (backlog task 22).

Task 15 IS sweep flagged three anchor candidates that beat incumbent 08:00/N=5
on IS dollar/trade. This script tests all four cells OOS (post-2024-05-02)
with the full trail_oos.py fill-realism gauntlet, then applies the decision rule:

    Switch ONLY if candidate OOS dol/trade > incumbent OOS dol/trade by > 1 SE
    AND the candidate retains a comparable share of edge post fill-stress
    (slip-2x and gap-through) to the incumbent.

Cells tested (trail_1R arm only):
    08:00 / N=5  -- incumbent / control
    08:30 / N=3  -- IS rank 1  (+53pct IS dol/trade vs incumbent)
    08:30 / N=5  -- IS rank 2  (+41pct)
    09:00 / N=5  -- IS rank 3  (+38pct)

IS control gate: incumbent 08:00/N=5 must reproduce IS trail_1R E[R]=+0.7910
within tolerance before the OOS scan runs. Halt on mismatch.

    python research/models/orb/anchor_oos.py
    python research/models/orb/anchor_oos.py --smoke  # 2 files only

Outputs -> research/outputs/orb/anchor_oos/
    anchor_oos_main.csv  anchor_oos_fill.csv  anchor_oos_summary.json
"""
