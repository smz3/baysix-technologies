# Handover — July 1, 2026 Morning4

## State
- **FOB awareness spec at v3** — [docs/specs/2026-07-01_fob_awareness_conditioner_spec.md](docs/specs/2026-07-01_fob_awareness_conditioner_spec.md). Storyline Sequence (2.1.1–2.1.9) folded into **Layer 1b** (control-chain + patterns S1–S10) + **locked decision 6** (VR/cycle event vocab).
- **VR event vocab LOCKED:** cycle birth = new PBO (`seq`); **VR detected** = zone birth (retires "confirmation"); **VR break** = continuation-dir clear → arms `[RT0]`; **RT** = broken-VR retouch. Grounded in [fob_visual.mqh:444-450](mt5/Include/fob_system/fob_visual.mqh#L444-L450).
- **Conditioner screen BUILT + first run** — [research/models/fob/alignment/setup_direction_screen.py](research/models/fob/alignment/setup_direction_screen.py): cohort-separated (M15-M5 / M5-M1), independence-guarded (D1 own-cycle dir).
- **Two findings logged (run_id 18, EXPLORATORY mid):** Setup↔Direction REJECTED (results 20/21); M5-M1 scalp lead KILLED (result 22).
- research.db local-only (untracked, task 203). Code/specs pushed to master.

## Next
1. **(task 207 P1)** Screen next conditioner **`vr_fresh`** (fresh vs structured) on both cohorts — HAVE field, reuse `setup_direction_screen.py` pattern. Report cont-lift + realized $/oz + BUY/SELL + per-year.
2. Because **both baselines are dead at cost** (result_id 22), judge every conditioner by whether it lifts a DEAD baseline into **net-positive $/oz**, not just a pp shift — else pivot to payoff-asymmetry (task 167, THE lever).
3. **(task 202 P2)** ingest_fob phase-2b — `mfe_r`/`mae_r` came back **NULL/nan** in the $/oz check → excursion fields incomplete; prereq for any payoff-magnitude screen.

## Blockers
- None.

## Why
- **−33.8pp "aligned=reversal" ghost = confirmed CIRCULARITY ARTIFACT** (result_id 19 void as signal). Guarded single-D1 Setup↔Direction gives +0.1pp (M15-M5, z=+0.28) / −1.1pp (M5-M1, z=−4.74 but non-durable) — dissolves it. See result_id 20/21, strategy_log 83. The saga's lesson is the **independence guard**, not any alignment edge. [[fob_storyline_alignment_finding]] rewritten to RESOLVED-AS-ARTIFACT.
- **VR "confirmation" term retired** per Syafiq: his manual typo ("break VR creates new cycle") = a new VR *confirms* the PBO-started cycle; PBO leads, VR-break lags. Kept two VR events only (detected/break) so the emitter can't double-count a cycle-id.
- **Sequence routed, not dumped:** S1–S3/S9 = Layer-1b state · S4 → L2 · S5(Setaman)/S8(scalp-risk)/S10(cycle-VR-BO) = new conditioner states · S6 → L3 barrier-TP · S7 = counter/fade state.

## Ruled-Out
- **Setup↔Direction (D1) as a conditioner** — REJECTED, strategy_log 84/83, results 20/21. No durable, economically-meaningful shift in either cohort. Stays out (spec decision 2).
- **M5-M1 as a scalp band** — KILLED, result_id 22 / strategy_log 84. "+0.157R baseline" = only **+$0.013/oz gross** on median $0.32/oz zones, **median trade −$0.14**, NET **−$0.19/oz** at a $0.20 spread; and BUY-only (+$0.033) vs SELL flat (−$0.007) = gold long-bias/trend-beta, not edge. Same shape as [[ib001_reversion_finding]].

## Live-Threads
- **Baseline is dead at cost in BOTH cohorts** (result_id 22: M5-M1 −$0.19/oz, M15-M5 −$0.25/oz gross-spread). Reframes the whole conditioner hunt: we're now hunting a state that flips a dead baseline positive, OR the real lever is payoff-asymmetry (task 167), not hit-rate. Carry this lens into task 207.
- **`mfe_r`/`mae_r` NULL/incomplete** on run_id 18 zones (MFE came back nan) — blocks payoff/excursion screens; ties to task 202. Fix before any payoff-magnitude work.
- **Long-bias confound live** — baseline positivity is BUY-only over a 2016-24 gold bull. Task 189 (genuine-bear / other-asset re-screen) is the clean control; not yet run.
