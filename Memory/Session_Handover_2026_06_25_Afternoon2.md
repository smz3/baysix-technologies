# Handover — June 25, 2026 Afternoon2

## State (FOB-001 — now fully self-contained; visuals need toggle split)
- **FOB_VERSION 1.0.0**, compiles 0 err (only the harmless `#property version "0.21"` warning). All FOB code committed + pushed to master.
- **Compile workflow FIXED this session:** bash-direct `metaeditor64.exe` silently NO-OPS (detaches, writes nothing) — you re-read a stale log and falsely report success. MUST use PowerShell `Start-Process -Wait` AND assert `.ex5` mtime > source mtime. See [[brc_compile_workflow]] (updated) + the verified one-liner there.
- **Detector bug FIXED (v0.7.1):** MT5 reinitializes the EA on every chart-period switch/recompile WITHOUT unloading → globals survived → old `OnInit` only zeroed scalars → re-ingested 64 bars into full buffers → duplicate bars (misplaced dots) + restarted seq on a stale log (stuck "pending VR"). `OnInit` now full-resets `g_events` + every per-TF array. See [[mt5_oninit_full_reset]].
- **FOB independence DONE (v1.0.0):** FOB owns its types ([fob_types.mqh](mt5/Include/fob_system/fob_types.mqh): `FobSwing`/`FobBreak`/`FOB_DIR`/`FOB_SWING_TYPE`) + its own detection ([fob_swings.mqh](mt5/Include/fob_system/fob_swings.mqh), [fob_breakouts.mqh](mt5/Include/fob_system/fob_breakouts.mqh)). ZERO brc code deps (only prose comments mention brc). Label model = ONE JOB PER DOT by precedence (parent VR/CF wins over own PBO); M1 never a PBO; small-caps labels; VR=yellow.
- **BROKEN / user-flagged:** the swing + raw-breakout visuals (`DrawStructure` in [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh)) are drawn **unconditionally** — user wants them removed-as-debug and re-exposed as clean independent toggles. There is also **no toggle to hide the PBO/VR/CF sequence dots**.

## Next
1. **(task 158, P1)** Split FOB visual into 3 independent input toggles under master `InpVisualize`: **(a)** `InpShowSequence` → the PBO/VR/CF classification dots (gate the `RedrawCurrentTF` dot-draw), **(b)** `InpShowSwings` → FOB swing pivots, **(c)** `InpShowRawBreaks` → FOB raw breakouts. Currently `DrawStructure` ([fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh)) draws swings+breaks together with no gate, and the sequence dots are always on. Remove any leftover/debug-framed code. Compile via Start-Process -Wait + verify mtime, then commit.
2. **(task 154, P1)** Eyeball v1.x in Visual Mode once toggles land (still never done).
3. **(task 155, P2)** Python ingester + edge test on `fob_events` CSV (after visuals locked).

## Blockers
None. All compiles. Reload the EA in the JM terminal after each rebuild (MetaEditor → Refresh / re-attach) — the terminal caches the old `.ex5` otherwise.
