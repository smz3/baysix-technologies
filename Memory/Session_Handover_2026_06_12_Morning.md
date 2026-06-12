# Handover — June 12, 2026 Morning

## State
**Gate-7 FIDELITY root cause SOLVED — it was DATA, not the EA.** ORB-001 tester win 33% vs Python 57% because the MT5 tester symbol `XAUUSD_dukas` (a fresh QDM Dukascopy download, 2-digit) is a **different price series** than the research parquet `data/parquet` (3-digit). Proven by an instrumented EA diag run (added `InpDiag`/`DiagOR` → `Common/Files/orb001_diag.csv`): EA tick@09:05 vs true parquet bid only 2.3% within 0.3pt, 89% off >2pt; no consistent offset. EA strategy logic EXONERATED. Falsified en route (all by data, no wasted EA edits): trail port bug, entry price-basis (emulations agree 95.6%), time-base offset. Diagnostics: [research/models/orb/orb001/](research/models/orb/orb001/) `fidelity_{diff,emulate,offset,timecheck,diagoffset}.py` + [outputs](research/outputs/orb/fidelity/). Gate 7 OPENED+BLOCKED (tester_runs run #1, verdict=fail vs result #54).

**Fix tooling BUILT + committed:** [export_ticks_mt5.py](research/code/export_ticks_mt5.py) (parquet→binary in Common/Files; 2024-05 = 5.0M ticks exported, round-trip PASS) + [import_custom_ticks.mq5](mt5/Scripts/orb_system/import_custom_ticks.mq5) (creates `XAUUSD_pq` 3-digit via CustomTicksReplace; compiled 0/0 in JM terminal). Task 45 = the active blocker.

**Discrepencies between xauusd.pq and xauusd.s broker:** pq. script import symbol uses 3 point data. broker xauusd.s uses 2 point data. Ask Syafiq for images between those two. 

## Next
1. **Syafiq runs the validation** (handed off, awaiting): Navigator→Refresh → drag `Scripts/orb_system/import_custom_ticks` onto a chart (builds `XAUUSD_pq` from the 5M parquet ticks) → Strategy Tester `baysix_orb_001` on `XAUUSD_pq`, M1, real ticks, 2024-05, $10k, offset 0. Report the **win rate**.
2. **Claude verifies (3 ways)** once done: win-rate jump 33%→~57%; `orb001_diag.csv` 09:00 bars now match parquet; bridge `mt5.copy_ticks_range('XAUUSD_pq')` == parquet. Re-diff via [fidelity_diff.py](research/models/orb/orb001/fidelity_diff.py) (repoint REPORT to the new run).
3. **If validated → scale:** `python research/code/export_ticks_mt5.py 2024-05 2026-05` → re-import → full-OOS tester run → real Gate-7 diff → if pass, `pass_gate(7)` unblocks FORWARD (task 35).
4. Build the headless tester automation (task 46) for the re-run loop.

## Blockers
Validation tester run needs Syafiq (single-instance JM terminal — Claude can't drive the tester/GUI script, only read the resulting CSV/report/bridge).
