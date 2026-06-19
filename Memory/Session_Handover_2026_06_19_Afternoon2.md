# Handover — June 19, 2026 Afternoon2

## State (BRC-001 emitter — task 128 SHIPPED, byte-identical, committed `7572bf5`)
- **Task 128 DONE — O(n²) emitter prune, 8.5yr emit hours → 9m30s** (100,034 zones). Three parity-neutral fixes:
  - [brc_zones.mqh](../mt5/Include/brc_system/brc_zones.mqh): `BrcFirstSwingAfter` + `BrcFindP5ForP1` now **binary-search** the chronological swing array (was the real O(n²) hot path — index-0 linear scans per break per candidate). Freshness check pre-bounded via `last_before_p4` (O(1)/candidate).
  - [brc_breakouts.mqh](../mt5/Include/brc_system/brc_breakouts.mqh): `BrcDetectBreaksOnBar` scans only `live_sw`, **order-preserving compaction** (NOT swap-remove — keeps break-append order = CSV row order).
  - [brc_baysix.mq5](../mt5/Experts/brc_system/brc_baysix.mq5): `TfState` gains `live_sw[]`/`alive_idx[]` free-lists.
- **PARITY PROVEN byte-identical.** 2024 1yr rerun (From 2024-01-01→2024-12-31, Open prices only) reproduced the pre-change CSV **exactly: 12,489 zones (M5=7791..MN1=1), sha `e1ed5c3c`** — same as the original-code reference captured before any edit. Detection geometry/levels/dedup/lifecycle untouched. Decision logged: human call_id 80.
- **Two earlier guesses were wrong** (advance-loop prune, then the binary-search confirm path) — neither was the bottleneck. Real cause: unbroken "wrong-side" swings accumulate ~linearly in trends → per-bar break scan = O(bars²). Lesson: the `live_sw` compaction alone can't help (those swings never break/compact); the binary-search of the confirm scans is what mattered.
- **Tasks closed this session:** 128 (perf), 118 (emitter build complete), 117 (DROPPED — Python lifecycle panel not needed; MQL5 `brc_visual.mqh` is the live panel).
- **Compile workflow confirmed working** ([[brc_compile_workflow]]): headless MetaEditor64, `.ex5` junctioned into E7DB terminal, 0err/0warn.

## Next
1. **Identity + Task 127 in one CSV-schema pass** (plan: [docs/plans/2026-06-18_brc_task128_127_plan.md](../docs/plans/2026-06-18_brc_task128_127_plan.md)). Add `seq` (per-TF p4_time chronological — chart `#seq` label + CSV), `zone_key={tf}|{dir}|{p4_time}` +`|{l2}` on collision (stable funnel join key), `is_primary`/`consolidated_into` (50%-overlap flag-don't-delete). Decision LOCKED: seq+zone_key BOTH (call_id 80). 6-file additive edit + migration 031 (tester_zones cols) + tester.py ingest. NO detection change → re-gate: 2024 1yr still 12,489 zones, new cols populate.
2. **Fast full 8.5yr re-emit** (now 9m30s) → freeze IS config (`strategy_log`) → unblocks **OOS task 126** + **funnel task 120**.
3. Then **task 120** (Layer-2 funnel inference, Python on the MT5 ledger) — the actual research payoff. Task 110 (Gate 3 D1 edge) after.

## Blockers
None. Task 126 (OOS) stays BLOCKED until IS config frozen ([[is_discipline_guards]]).
