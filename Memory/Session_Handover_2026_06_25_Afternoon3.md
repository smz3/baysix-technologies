# Handover — June 25, 2026 Afternoon3

## State (FOB-001 — visuals reworked + CF ordinals; two logic changes queued)
- **FOB_VERSION 1.3.0**, compiles 0 err (only the harmless `#property version "0.21"` warning). All committed + pushed to master.
- **Visual toggles (task 158, DONE):** 3 independent layers under master `InpVisualize` — `InpShowSequence` (PBO/VR/CF dots), `InpShowSwings`, `InpShowRawBreaks`. Each gated alone in [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh). (Swings/RawBreaks default off in the user's working copy.)
- **Swing+rawbreak visuals (DONE):** dropped the grey carets + dotted trend-lines; now an exact mirror of [brc_visual.mqh](mt5/Include/brc_system/brc_visual.mqh) — swing = `•` + `High/Low <price>` (tomato/dodgerblue, dimmed when broken); raw break = `•` at the broken swing + `Bob/Bos <swing> (<close>)` (limegreen/orangered, anchor right).
- **CF ordinals (v1.3.0, DONE):** `cf_count` on `FobSetupState` (reset 0 per PBO, +1 per CF emit, [fob_sequence.mqh:96](mt5/Include/fob_system/fob_sequence.mqh#L96)) → `FobEvent.cf_idx`. CSV gained a `cf_idx` column; visual label reads `cf h1 #1.2` (cycle.cfordinal). PBO/VR carry cf_idx=0.
- **Thesis (re-confirmed):** core SOP `CMP→BO→VR→CF`; CF = the entry trigger; manual distinguishes 1st-CF (often a trap) vs 2nd-CF (best, "in the VR zone"). Full dissect: [FOB_breakout_system.dissect.md](research/papers/fob/FOB_breakout_system.dissect.md).

## Next
1. **(task 159, P1)** Fix CF numbering: CF2+ must break a **NEWER structure** formed AFTER CF1 — a break of an OLDER structure already in place before CF1 must NOT count as CF2. Track last-CF structure (swing_time) in `FobClassifyBreak` CF branch and require strictly-newer. ⚠️ Syafiq may send a picture for clarity before coding — ASK.
2. **(task 160, P1)** PBO dot lifecycle states for at-a-glance reading: today only `pending VR` shows. Add `pending CF` (VR locked) → `live CF1` → `live CF2` → … advancing with cf_idx. Render in `RedrawCurrentTF` PBO/anchor branch. Depends on task 159 (corrected cf_idx).
3. **(task 154, P1)** Eyeball v1.x in Visual Mode once 159/160 land.
4. **(task 155, P2)** Python ingester + CF-conditioned edge test on `fob_events` CSV (now has `cf_idx`).

## Blockers
None. All compiles. Reload the EA in the JM terminal after each rebuild (MetaEditor → Refresh / re-attach) — it caches the old `.ex5`. Compile via PowerShell `Start-Process -Wait` + assert `.ex5` mtime > source ([[brc_compile_workflow]]); bash-direct metaeditor64 silently no-ops.
