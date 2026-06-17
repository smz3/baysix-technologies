# Handover — June 17, 2026 Afternoon3

## State
- **METHODOLOGY PIVOT (Syafiq's call, this session): BRC moves to MT5-first.** Build/simulate BRC in MQL5 (Strategy Tester = chronological oracle, event-driven OnTick, no look-ahead/fixed-H class of bug). Python is DEMOTED to inference-only on the exported trade ledger. This is the Gate-7 FIDELITY pattern ([deployment_dgate_sequence.md]) applied earlier. NOT yet logged as a decision / NOT yet tasked.
  - **Split:** MT5 = signal + event-accurate fills/spread/swap → exports trades. Python = ONLY the trend-beta matched-random baseline + t-stat/DSR on those rows. MT5 *cannot* do the 2000-rep baseline — that handoff is MANDATORY (gold's 3.6× run confounds every long-biased rule).
  - BRC detection already lives in the EA (B2BDetector / B2BZoneStatus.mqh); the Python was a port. Going to MT5 = back to the source.
- **BRC-001 — 3 FALSIFICATIONS, but Syafiq chose REFRAME over kill.** Still `gate_2`, falsified 3/2 (kill unblocked, NOT executed). All event-based (race/let_run), NO fixed-H.
  - #52 (strategy_log): D1 let-run payoff ≈ trend beta. E[R] +13.67R vs beta +12.74±4.65, z=+0.21. Artifact: research/outputs/brc001/brc001_gate3_dataset_D1.csv + [payoff_asymmetry.py].
  - #53 (strategy_log): H4 reframe = outlier MIRAGE. Uncapped E[R] +29.65R z=+3.50 BUT top-1 trade=4832R, top-10=60% of sum (tiny-R zones never invalidate → multi-yr hold / huge R). Winsorized: cap10R z=+2.31 but E[R] −1.15R (LOSES); cap50R z=+1.02. No tradeable edge clears z≥2. Artifact: research/outputs/brc001/brc001_gate3_dataset_H4.csv.
- **Cleanup done + pushed:** fixed-H continuation fully removed (Syafiq flagged it as wrong for an event-based strat). Deleted Continuation/label_continuation/_signed/contH cols/--H. Verdicts reproduce identically (they never used H-10). [continuation.py], [dataset.py] now event-based only.

## Next
1. **Log the MT5-first methodology decision** — `agent_log.log_human_decision(idea_id='BRC-001', ...)` + `backlog.add_task` for the EA build. (Not done yet — do this first.)
2. **Build the BRC test EA in MT5** — wire existing B2BDetector into an EA that logs each confirmed zone + the L1-retest entry trade (stop=L2, exit on invalidation), run Strategy Tester on XAUUSD, export trade ledger (QUANT_ZONES-style CSV → research.db tester_trades).
3. **Python inference on the ledger ONLY:** trend-beta matched-random same-dir baseline (reuse [payoff_asymmetry.py] `_boot_numba`) + t-stat. Edge must beat beta at z≥2 or BRC is dead on a 4th falsification.

## Blockers
None. Carry-forward caveat: every BRC number is direction-confounded by gold's 2016→2026 bull run — ALWAYS compare vs a direction-matched random baseline before claiming edge. MT5 fixes mechanics bugs, NOT the trend illusion. Gate 3 stays CLOSED until a frozen rule beats beta.
