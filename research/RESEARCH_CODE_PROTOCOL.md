# Research Code Protocol

Rules for writing and modifying code in `research/models/` and `research/code/`.
Each rule exists because a real failure happened. No rule is hypothetical.

---

## Before Touching Any Model File

1. **Read the full file first.** No partial reads. Catch cross-function inconsistencies before writing a single line.
2. **Grep every reference to any parameter you plan to change.** One parameter (e.g. `model="rbf"`) can appear in 3+ functions with different implications.

---

## When Changing an Algorithm or Cost Function

3. **Verify the penalty/hyperparameter scale matches the new algorithm.** Different models have different cost magnitudes — `l2` costs are ~0.0001, `rbf` costs are ~10-1000 on the same signal. Mixing them silently produces garbage output (e.g. K=145).
4. **Keep the same model throughout a pipeline stage.** Elbow sweep and final detection must use the same cost function. If you change one, change both.

---

## Before Any Long Run

5. **Print a sanity block before the main computation:**
   - `n_obs`, `signal_var`, `penalty`, `expected K range`
   - Abort or warn if `K=0` (penalty too high) or `K > 30` (penalty too low / over-segmented)
6. **Adapt hyperparameter ranges to signal scale.** Never hardcode penalty ranges like `logspace(0.3, 3.0)` without verifying they make sense for the signal's variance.

---

## During Any Run

7. **Every loop > 5 iterations must have a `tqdm` progress bar + per-iteration print.** No silent loops. Ever.
8. **Long runs (> 30s) must be launched in a visible PowerShell window**, not background. Use `Start-Process powershell`.

---

## After a Run Completes

9. **Verify results make sense before logging to DB.** Sanity check: does K fall in a reasonable range? Does R² beat random? If not, debug before committing to `pipeline_events`.
10. **Only one canonical run logged per idea per stage.** Clear stale/broken entries before re-running.

---

## Changelog

| Date | Rule Added | Reason |
|---|---|---|
| 2026-05-28 | Rules 3, 4 | l2/rbf mismatch → K=145, 2hr wasted run |
| 2026-05-28 | Rules 7, 8 | Silent elbow sweep with no progress — looked frozen |
| 2026-05-28 | Rule 6 | Hardcoded `logspace(0.3, 3.0)` → all K=0 for l2 model |
