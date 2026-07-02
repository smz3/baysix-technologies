# Handover — July 2, 2026 Afternoon2

## State
- **FOB is now ONE EA — merge shipped v1.28.0** ([fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5); pushed 8795dfe + cleanup 85f32e5). `InpMode = EMIT | TRADE | STUDY`.
- **One lifecycle engine:** the causal tick accumulator (`FobAcc*`/`g_watch`) drives touches/RT for every mode. The trader's old stateless bar-replay path is GONE — this is the root fix for the emitter-vs-trader touch-ladder disagreement.
- **EMIT** = all 9 TFs + `htf_state` + CSV, no orders (order path never runs → pristine + OOS-re-emittable; CSV byte-identical to old emitter). **TRADE/STUDY** = setup pair `{n-1,n}` only.
- **Compile clean:** 0 err, 1 benign MQL5-Market version-format warning. `fob_trader.mq5` deleted; all `fob_trader` artifacts purged (repo+terminal = 0).
- **RT still L2-only in code** — the RT-ladder redefine is NOT done yet (deliberately staged).

## Next
1. **(task 219, P1)** RT-ladder redefine: replace single L2-only `rt_count`/`rt_time` with mirror ladder **RT1/RT2/RT3** (L2→mid→L1, armed at close-invalidation), stamped OnTick like T1/T2/T3. Touches [fob_types.mqh](../mt5/Include/fob_system/fob_types.mqh) (add rt1/rt2/rt3_time) → [fob_lifecycle.mqh](../mt5/Include/fob_system/fob_lifecycle.mqh) (FobAccInit/OnTick/OnClose + FobReplayZoneLife) → [fob_csv.mqh](../mt5/Include/fob_system/fob_csv.mqh) (serialize) → [fob_visual.mqh](../mt5/Include/fob_system/fob_visual.mqh) (`[RTn]` label). Human ruling call_id 93.
2. After RT-ladder: gen_version fob → headless compile → verify 0 err → commit.
3. Then re-emit + re-test both modes on real ticks (EMIT CSV changes once RT schema changes).

## Blockers
- None.

## Why
- **Root cause of the touch-ladder drift = two EAs, two engines** (emitter=causal tick accumulator, trader=stateless bar replay). Verified per-EA: emitter live path already OnTick (`FobAccOnTick`), trader was bar-close (`FobReplayZoneLife` over closed bars + forming-bar `LiveTouchForming`). Merging = strongest enforcement of "both behave the same" (there's no "both" left). Syafiq authorized overriding the two-EA HARD rule 2026-07-02.
- **Separation-of-concerns preserved via `InpMode`, not two binaries:** EMIT never runs the order path → still pristine for OOS re-emit (the old emitter's whole reason). `tester_runs.run_role` now set by mode.
- **RT = full mirror ladder** (Syafiq, call_id 93): after a VR invalidates (CLOSE beyond L2), price returns and re-touches L2→mid→L1 (mirror order of the T-ladder). Same 3 levels, opposite side/sequence.
- **Pre-attach history is bar-resolution, unavoidable:** MT5 gives a freshly-attached live EA bars, not historical ticks — so past zones can only be bar-wick backfilled (loses intrabar order). The tester replays every real tick from run start → no gap → CSV always exact. Documented in CLAUDE.md tester-model section.

## Ruled-Out
- **Keeping two EAs / two engines** — rejected; it was the bug source. (See [[fob_single_ea_merge.md]].)
- **Making touches close-only** — no; touches are tick-based by design. The trader was the laggard, now unified onto the accumulator.
- **Tick-accurate pre-attach history on a live chart** — impossible (no historical ticks); bar-resolution seed is the ceiling, live-only.
- **Deleting fob_parity_trader.ini** — kept, repointed to `fob_baysix.ex5` + `InpMode=1` (valid trade-mode config; only the name says "trader").

## Live-Threads
- **RT-ladder schema ripples:** changing `rt_count`→rt1/rt2/rt3 shifts the fob CSV column layout → the ingest_fob loader + `fob_zones` schema likely need matching columns. Check the loader before/after task 219 so the CSV↔DB contract stays aligned.
- **`.set` presets:** the 3 stale trader presets were deleted; any future TRADE preset must set `InpMode=1` (defaults to EMIT, silent no-orders). Emitter presets work unchanged (InpMode defaults EMIT).
- **Entry-logic spec phase still parked** — spec v0.2 ([docs/specs/2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md](../docs/specs/2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md)) + tasks 214/215 untouched; this session was pure EA architecture.
