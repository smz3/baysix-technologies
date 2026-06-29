# Handover — June 29, 2026 Afternoon

## State
- **CLAUDE.md re-adjusted** — MT5/EA workflow + version-control sections are now **system-agnostic** (FOB = live example, BRC demoted to a one-line parked pointer). Added a **lifecycle rule**: only the ONE active idea gets a baked canonical section; on park it collapses to a pointer.
- **Task 194 DONE — FOB git-sha provenance.** New `gen_version.py <system>` (one parametrized generator; `gen_brc_version.py` = back-compat shim). `fob_version.mqh` auto-generated (gitignored) + `#include`d in [fob_trader.mq5](../mt5/Experts/fob_system/fob_trader.mq5) → prints `v.. | git <sha>-DIRTY(exploratory) | built ..` on init. Drifted `#property version` fixed (baysix 1.19.1→1.20.0). Compiled **0 errors**.
- **Task 193 CSV contract APPROVED** — written into spec [§6.1](../docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md). Grain = one wide CSV/event; ingest derives the 3 fob tables. Columns tiered A (wire now) / B (cheap add) / C (deferred value). **NOT yet coded** — [fob_csv.mqh](../mt5/Include/fob_system/fob_csv.mqh) still emits the old 17-col birth-only row.
- All committed + pushed.

## Next
1. **(task 193, P1)** Build the contract into [fob_csv.mqh](../mt5/Include/fob_system/fob_csv.mqh): emit TIER A+B + the C headers + `htf_state` JSON, causally from the emitter. Lifecycle fields (mid/t1-t3/rt/alive/invalidation) already exist on `FobZone` via `FobReplayZoneLife` — mostly wiring + touch-COUNTS + htf_state snapshot.
2. **(task 191, P1)** Build `ingest_fob` in [tester.py](../research/code/io/tester.py): wide CSV → `fob_cycles`/`fob_events`/`fob_zones`, `idea_id='FOB-001'`, reconstruct cycle linkage by grouping `(setup_tf, seq)`.
3. **(task 190, P1)** Run `fob_baysix` emitter: XAUUSD_dukas, 8 TF, 2016–2024, Open-prices.
4. **(task 192, P1)** Re-screen storyline on FOB OWN zones; pin run_id + assert `idea_id='FOB-001'`.

## Blockers
- None.

## Why
- **Version-stamp was a real gap, not a doc nit** — FOB had only a *manual* `FOB_VERSION` (already drifted) and zero git-sha provenance, so the "DIRTY=exploratory" guarantee CLAUDE.md promised didn't hold for FOB. Fixed before 190/192 so those runs are reproducible-by-construction. One generator (not a dup script) keeps BRC+FOB on the same rail.
- **CLAUDE.md generalized rather than FOB-hardcoded** — the workflow/VC machinery is idea-agnostic; baking FOB names in would just re-rot at the next pivot. Lifecycle rule makes "active=baked, parked=pointer" structural so the BRC-staleness class can't recur.
- **CSV grain = one wide row/event (not 3 files)** — every FOB break already carries its `FobZone` (event↔zone 1:1), so one CSV + ingest-side split is simplest and keeps the EA free of surrogate-key bookkeeping. `fob_cycles` reconstructed at ingest by grouping `(setup_tf, seq)`.

## Ruled-Out
- **R measured to the VR origin (`vr_level`)** — I initially claimed this; it was a **stale code comment**. The live trader actually uses **R = |entry − SL|, SL beyond zone far-edge L2 by `InpSlBufferK`·band** ([fob_trader.mq5:325-339](../mt5/Experts/fob_system/fob_trader.mq5#L325)). Stale comment in [fob_types.mqh:163](../mt5/Include/fob_system/fob_types.mqh#L163) corrected. Do NOT reintroduce vr_level as the R unit.
- **`htf_state` storing the *interpreted* TF direction** — rejected. Store **RAW per-TF live-cycle `{dir,cf}` snapshot** (from `FobSetupState`); apply the awareness mapping (`X ← cycle-on-(X−1)`) in analysis. Baking the derived dir would lose data if the rule sharpens.

## Live-Threads
- **3 FROZEN decisions (Syafiq sign-off, spec §6.1):** (1) `realized_r` sign = good-for-trade always POSITIVE (winning short = +R), value deferred to phase-2 so denominator inherits the trader's real L2-stop rule; (2) `htf_state` = raw per-TF live-cycle snapshot, NOT interpreted; (3) `vr_made_first_tf` + `risk_class` (HR/LR) + `vr_zone_broken` all emitted in round 1.
- **htf_state is a 2-TF object, not single-TF** — Syafiq corrected my loose wording: a cycle needs 2 TFs (PBO on X, VR/CF on X−1), so a TF has no direction in isolation. The snapshot = each TF's *current live cycle* standing, not its isolated breakouts and not full sequence history. Keep this precise when coding the JSON.
- **TIER C values deferred** (mfe_r/mae_r/realized_r compute, confirm linkage, supersede zone_key/is_primary) — headers emit now, values are phase-2. `confirm_time/continued` are ingest-derivable from next-CF linkage when wanted.
- **`instruments` table** still designed-not-created; needed before the first FOB *trader* $ run (not blocking the emitter chain).
