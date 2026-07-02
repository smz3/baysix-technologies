# Handover — July 2, 2026 Afternoon

## State
- **FOB emitter live-chart fixes, v1.27.1 shipped** (`fob_baysix.mq5` + `fob_visual.mqh` + `fob_lifecycle.mqh`; pushed 7aaef30). Both LIVE-only, tester byte-identical.
- **Task 216 (dimming) DONE + confirmed working** by Syafiq: intrabar-dead dimming — a higher-TF zone dims the instant price is beyond L2 (not only at bar close), via `CFobVisual::IntrabarDead` + `curPx` threaded through `StateSignature`/`DrawZones`/`DrawZoneForBreak`. `z.alive` untouched (CSV stays close-only).
- **Task 217 (historical T-touches) STILL BROKEN** — reopened. First attempt (v1.27.0 close-path stamp in `FobAccOnClose`) failed (eviction drops zones from g_watch first); replaced with draw-time fill-only backfill `FobBackfillLadderTimes`/`BackfillChartLadder` (v1.27.1). Syafiq's chart still shows inconsistency.
- **Two EAs compile clean** (0 err, 1 benign version-format warning). `#property version` + `FOB_VERSION` both at 1.27.1.

## Next
1. **(task 217, P1)** Instrument the CF `[Tn]` split BEFORE coding — confirm whether older bull-CF `[T0]` is direction-correct (price rallied away, never pulled back = genuine no-retest) vs a real backfill miss. Print per chart-TF zone: label/dir/brk/t1t2t3/buffer-oldest-bar-time on attach.
2. **(task 217, P1)** Resolve the touch-DEFINITION question with Syafiq: for a continuation CF does "touch" = pullback INTO the zone (current) or price passing THROUGH the band (would show T3)? This decides whether 217 is a bug or a def change.
3. **(task 218 NEW, P1)** Backfill RT retouch count for pre-attach VRs — confirmed gap: `FobBackfillLadderTimes` fills only t1/t2/t3, NOT `rt_count`. Pre-attach VRs always show `[RT0]`. Needs a bar-resolution RT replay (post-invalidation, re-arm hysteresis) live-only.

## Blockers
- **Task 217 blocked on the touch-definition ruling (Next #2)** — can't tell "bug" from "correct behavior" until Syafiq defines CF touch semantics.

## Why
- **217 root cause = v1.24.0 architecture:** the causal tick accumulator (`FobAcc*`) replaced the old draw-time bar-wick replay. Accumulator is BLIND to pre-attach history (only `FobAccOnTick` advances the ladder, and there are no historical ticks on attach). So on attach NO zone gets its ladder from the accumulator — all rely on the backfill.
- **Why 216 worked but 217 didn't (the confusing split):** dimming reads CURRENT price at draw time — independent of history, so it always works. The ladder needs the historical sweep, which the first fix mis-scoped.
- **Leading hypothesis for older=T0 / newer=correct:** newer zones get live-tick refinement (`FobAccOnTick`); older rely on backfill. VR shows T3 (opposite-dir zone, swept by the up-rally); bull CFs show T0 because price rallied away and never pulled back DOWN into them — which by the current pullback-based touch rule is *geometrically correct*. Backfill uses `ev[i].dir` (own-PBO row) + `ev[i].zone`, probing the retest side per break direction.
- **Fill-only, never-reset backfill was chosen** so it can't clobber the causal accumulator's live zones (unlike `UpdateZoneLifecycles`, which recomputes from scratch — the v1.24.0 comment explicitly warns against calling it in the emitter).

## Ruled-Out
- **v1.27.0 close-path ladder stamp (in `FobAccOnClose`, `stamp_ladder=live`)** — REVERTED. Only stamped zones still in `g_watch`, but cycle-end eviction ([fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5#L158-L172)) drops superseded zones before the attach sweep → historical `[Tn]` stayed T0. Do not retry the close-path route.
- **Reviving `UpdateZoneLifecycles`/`FobReplayZoneLife` in the emitter** — rejected: it RESETS the whole ladder + recomputes invalidation/rt, clobbering the causal accumulator's live-zone lifecycle. The non-destructive fill-only variant is the correct replacement.
- **Stamping the ladder on BOTH live+tester** — rejected: breaks the pristine/reproducible OOS re-emit contract. All fixes stay `!MQLInfoInteger(MQL_TESTER)`.

## Live-Threads
- **The core 217 uncertainty is unresolved:** is older-CF `[T0]` a bug or correct? My read leans *correct* (direction-consistent pullback semantics), but Syafiq is experienced and insists there's an inconsistency — needs instrumentation (Next #1) + the definition ruling (Next #2) before any code.
- **RT backfill (task 218)** is the one *definitely-real* hole this session surfaced — separate from the CF `[Tn]` question.
- **`BackfillChartLadder` is chart-TF-gated** (`event_tf == m_idx`) and runs every redraw (early-returns once all 3 stamped). If instrumentation shows cross-TF display zones missing touches, revisit whether the gate is too narrow.
- **Entry-logic phase (prior session) still parked** — task 214 ruling (gate-vs-conditioner) + spec v0.2 (215) untouched today; this session was pure emitter plumbing.
