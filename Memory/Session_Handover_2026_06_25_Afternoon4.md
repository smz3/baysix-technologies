# Handover — June 25, 2026 Afternoon4

## State (FOB-001 — build phase CLOSED at v1.6.0; edge test is all that's left)
- **FOB_VERSION 1.6.0**, compiles 0 err (only the cosmetic MQL5-Market 2-part warning on `#property version "1.6.0"`). All committed + pushed to master (latest `c0b437f`).
- **Version sync (this session):** `#property version` was a stale `0.21` (EA properties dialog) — now matches `FOB_VERSION` (`1.6.0`). Rule: bump BOTH ([fob_types.mqh](mt5/Include/fob_system/fob_types.mqh#L29) + [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5#L24)). Switch to `"1.60"` only if we ever publish to Market.
- **Task 159 (CF newer-structure, v1.4.0):** a CF only fires if its broken swing is newer than `last_conf_swing` (seeded = VR swing on lock, advanced per CF). Kills pre-VR/old reach-backs ([fob_sequence.mqh](mt5/Include/fob_system/fob_sequence.mqh)).
- **Task 162 (PBO CMP-freshness, v1.5.0):** the PBO = the SOURCE nearest CMP. Same-dir break supersedes ONLY if `swt > pbo_swing`; opposite-dir (reversal) always supersedes; same-dir reach-back rejected. Toggle `InpPboNewestOnly` (default ON). Replay-validated on v1.4.0 W1 stream: 20→16 PBOs, rejects #11/#17/#18/#20, live PBO = #19 (swing 2026.05.17, at CMP) — fixed the "far-left Nov-2025 dot" bug.
- **Task 161 (dual-purpose dot) + 160 (PBO lifecycle badge), v1.6.0:** one bar that's PBO(E)+VR/CF(E+1) draws ONE bullet, two fanned labels (PBO anchor-right / parent anchor-left). PBO badge: `pending {E-1} VR → pending {E-1} CF → live {E-1} CF<n>` ([fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh)).
- **Eyeballed working** (Syafiq confirmed v1.6.0 in Visual Mode). Tasks 153/154/159/160/161/162 all `done`.

## Next
1. **(task 155, P2 — the ONLY open FOB task)** FOB Python ingester + edge test — the payoff. Ingest `Common/Files/FOB/fob_events_*.csv` (now has `cf_idx` + `swing_time`) into research.db; test whether VR+CF-conditioned continuation beats BRC's null edge. Fresh session — needs context headroom + MT5-oracle discipline (the EA tester is the arbiter, not a query screen). (Task 152 = dropped, optional figure-render, ignore.)

## Blockers
None. All compiles + pushes clean. Reload the EA in the JM terminal (E7DB) after pulling — MetaEditor → Refresh / re-attach; it caches the old `.ex5`. Re-run to see the PBO dot at the CMP-fresh source + lifecycle badge.
