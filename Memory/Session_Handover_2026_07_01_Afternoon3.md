# Handover — July 1, 2026 Afternoon3

## State
- **Task 210 SHIPPED — FOB zone always draws (v1.26.0, commit b173bbd).** [FobComputeBreakZone](mt5/Include/fob_system/fob_breakouts.mqh) rewritten: **P3 = deepest opposite-direction CLOSE in (P2, break)** (raw retrace extreme, no fractal lag), **P1 optional**, **freshness + gap-val REJECTS deleted** (they were BRC trade-quality filters, not geometry). `valid` = "≥1 far-edge anchor exists". Threaded `times[]` through `FobDetectBreaksOnBar`→`FobComputeBreakZone` so P3 gets a timestamp. L1=P2 (always), L2=extreme(P1,P3) (always) → box always draws.
- **Version lockstep fixed (7d5486b):** both `#property version` bumped 1.25.0/1.23.0 → **1.26.0** to match `FOB_VERSION`. Was cosmetic drift; the terminal Navigator showed stale labels.
- **Trader chart-hiding removed (46cafd1):** deleted the OnInit block that force-hid bid/ask lines + trade levels + OHLC "for focus". Trader now inherits the user's own chart settings.
- **All three compile 0 errors** (only the benign MQL5-Market `xxx.yyy` version warning). `.ex5` rebuilt. fob_version.mqh stamped at 46cafd1@master (clean, not DIRTY).
- **Lineage:** strategy_log `log_id 85` (ADOPTED, config, zone always-draw).

## Next
1. **(task 211, P1)** Re-emit `fob_baysix` v1.26.0 on the run_id-18 window (real ticks Model=4, 2016–2024) so `fob_zones` carries the new deepest-close L2. run_id 18 zones are PRE-fix (many `zone_valid=0`).
2. **(task 212, P1)** Re-test `fob_trader` on the re-emitted zones — new L2 moves SL/1R AND makes previously-skipped (invalid-zone) setups tradeable; compare trade count + net vs pre-fix.
3. **(task 209, P1)** CF break-state A/B/C entry screen — DERIVE off the RE-EMITTED run (not run_id 18), cont-lift + net $/oz per bucket.

## Blockers
- **None.** 211/212 just need the emitter/trader tester runs; nothing gated on an answer.

## Why
- **The "no box" bug root cause (task 210):** P2 (broken level) + P4 (break bar) always exist; only P1/P3 can go missing. The old P3 = FIRST fractal-confirmed opposite swing, which needs a confirming bar AFTER it — on a sharp V-pullback the break fires before P3 confirms, so P3 wasn't in the array yet → hard bail → no box. Worst on M1 (noisiest, ~4%). Fix = use the raw deepest pullback CLOSE (the real low, past-only, no look-ahead) instead of a lagging fractal. Syafiq explicitly rejected any "synthetic far-edge" / "messy flag" — the deepest close is a REAL printed price, not synthesized, so it satisfies "legit full box".
- **Why delete freshness + gap-val (not just P3):** both `return`ed on a COMPLETE 4-pointer. They're BRC *trade*-quality filters mis-placed in the geometry/draw path. Re-home to the trader (fob_entry gates on `zone.valid`) if ever wanted — not the box builder.
- **Window size is the WRONG lever (Syafiq asked):** window must be odd ≥3; 4 is illegal, 5 (radius 2) makes confirmation lag WORSE + pivots coarser → more bails. We're already at the least-lagging legal setting (3). Fractal requirement itself was the problem; extreme-close removes it.
- **Two-EA split is intentional (Syafiq vented but it's his locked rule):** emitter = pristine all-9-TF read-only oracle (re-emittable for OOS); trader = orders, scoped to setup-TF pair (`g_ingest = [setup_tf-1, setup_tf]`, [fob_trader.mq5:108-109](mt5/Experts/fob_system/fob_trader.mq5#L108-L109)). Merging them would risk corrupting the detection oracle on every trade tweak.

## Ruled-Out
- **"Trader is running old code" (v1.23.0 in Navigator) — FALSE ALARM.** That was the un-bumped `#property version` label; the v1.26.0 zone logic was already compiled in via shared includes. Truth = the init PRINT line (`[FOB TRADER] v1.26.0 | git 46cafd1`), not the Navigator number. Fixed in 7d5486b.
- **"Bid/ask lines gone + only some TFs draw = your zone change broke the trader" — FALSE ALARM.** Bid/ask hiding was pre-existing OnInit code (ff62e95); "only some TFs" is by-design trader scoping (2 TFs only). My change can only ADD valid zones, never remove a TF or touch chart lines. Both now addressed (46cafd1 restores lines).
- **Synthetic far-edge / "messy" flag fix — REJECTED by Syafiq** (from Afternoon2). Superseded by the deepest-close approach (real price, always draws).

## Live-Threads
- **L2 is now WIDER on some zones** — deepest close over the whole (P2,break) window can sit further from L1 than the old "first pullback pivot" → bigger 1R → smaller lots (possibly min-lot rounding). Watch this in the 212 re-test; it's the main behavioral risk of v1.26.0, not a crash.
- **research.db is LOCAL-ONLY** (675MB > GitHub cap, task 203) — run_id 18 / result_id 19-22 / log_id 85 / tasks 210-212 live only on this disk. Rebuildable from emit CSV (G:\My Drive\baysix_backups).
- **mfe_r/mae_r NULL on run_id 18** (task 202) — still blocks payoff-magnitude buckets in 209; the re-emit (211) is the chance to capture them.
- **`#property version` xxx.yyy warning is benign** — Market layer deferred; 1.26.0 (3-part) will always warn until a 2-part Market build is cut.
