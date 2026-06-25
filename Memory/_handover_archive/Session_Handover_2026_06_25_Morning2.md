# Handover — June 25, 2026 Morning2

## State
- **FOB-001 visuals reworked + M1 added. All compiles 0 err (headless), strategy_log log_id 69.** Sibling of BRC under STRUCT-001. G1 still open. See [[fob001_foundation]].
- **M1 → 9 TFs:** ladder now M1·M5·M15·M30·H1·H4·D1·W1·MN1 (`FOB_N_TF 9`, M1 at idx 0). n−1/n−2 rule is index-relative so M1 slotted in cleanly. [fob_types.mqh](mt5/Include/fob_system/fob_types.mqh) + [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5). FOB_VERSION 0.2.1.
- **Visuals (locked this session):** arrows → BRC `"•"` dot idiom (no arrows); draw gate flipped `event_tf → setup_tf` so each chart = one setup-TF lens (full chains, lower-TF VR/CF/HRCF projected up + joined by a per-`(setup,seq)` connector). Colours unchanged (PBO blue/VR purple/HRCF orange/CF green). [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh).
- **Dot-placement bug FIXED:** `swing_time` now threaded through `FobEvent`/sequence/emitter/CSV; every role draws its dot + connector AT the broken swingpoint (like BRC raw breakouts), not the breakout-bar time.
- **Decided, NOT yet built (Syafiq picked, then called handover):** the `#N` repeat is NOT a bug — `#N`=chain id, stamped on all 4 roles of a chain by design. Fix = show `#N` on **PBO only**; VR/CF/HRCF show `role+eventTF`, bound by the connector. PLUS encode direction as `BUY/SELL` word on the PBO label + tint connector by direction (NO triangles — tester font renders unicode as `?`).
- FOB reuses brc_swings/brc_breakouts (STRUCT primitives) by design — no own detection mqh (tech-debt: promote to shared `struct_system`).

## Next
1. **(task 154)** Build the chosen visual change in [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh): `#N` on PBO label only; VR/CF/HRCF = `role+eventTF` (no `#`); add `BUY/SELL` to PBO label + direction-tint the connector. Recompile headless, then Syafiq eyeballs in Visual Mode.
2. **(task 155)** After visuals locked: Python ingester for `Common/Files/FOB/fob_events_*.csv` (now has `swing_time` col) + edge test — does VR+CF-conditioned continuation beat BRC's null?

## Blockers
None. Foundation compiles + runs; next change is scoped + agreed, just needs building then an eyeball pass.
