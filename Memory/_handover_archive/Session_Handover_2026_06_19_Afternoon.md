# Handover — June 19, 2026 Afternoon

## State (BRC-001 emitter — design decisions locked, zone-identity edit NOT yet applied)
- **Discussed tasks 128 / 127 / zone-identity.** Plan written: [docs/plans/2026-06-18_brc_task128_127_plan.md](../docs/plans/2026-06-18_brc_task128_127_plan.md).
- **Task-122 parity finding LOGGED** (agent_log call_id 79): task-122 was an *algorithmic* port of `CB2BDetector::DetectB2B_5Pointer`, validated by compile + **visual** parity — NOT a numeric windowed run-diff. So there's no empirical "parity window." The live EA's `InpHistoricalBars` (default 5000, [TradingParameters.mqh:47](../mt5/Include/Sigma_System/V5.0/Configuration/TradingParameters.mqh#L47)) is *"Initial bar load"* = a perf knob, NOT a strategy rule.
- **DECISION (locked):** Task 128 = **pure mechanical prune**, NO window cap. Fixes: alive-zone-only advance loop + type-segregated unbroken-swing lists + cursor-bounded freshness scan. Parity gate = reproduce run #2 (1yr smoke) = **12,489 zones byte-identical** (per-TF M5=7791…MN1=1). Any diff = revert.
- **DECISION (locked):** Task 127 = **flag, don't delete** — port Sigma's 50%-overlap rule, mark losers `is_primary`/`consolidated_into`, emit all rows. Follow-up, not this edit.
- **Zone identity:** current `zone_id` is a throwaway global OnDeinit counter ([brc_csv.mqh:53](../mt5/Include/brc_system/brc_csv.mqh#L53)); visualizer keys on `p4_time`, so chart↔CSV share no number. Agreed fix = per-TF `seq` (1-based, p4_time order), written to CSV AND shown as `#seq` on the zone label → chart and data tie out. **This edit was interrupted before any file was changed.**

## Next — apply the `seq` zone-identity edit (6 files, all additive, NO detection change)
1. [brc_types.mqh](../mt5/Include/brc_system/brc_types.mqh) `struct BrcZone`: add `int seq;` (per-TF chronological id).
2. [brc_baysix.mq5](../mt5/Experts/brc_system/brc_baysix.mq5#L138) confirm block: set `z.seq = ArraySize(s.zones) + 1;` BEFORE `s.zones[zi]=z;` (so visual + CSV share it).
3. [brc_csv.mqh](../mt5/Include/brc_system/brc_csv.mqh#L52): add `seq` to header (after `tf`) + write `IntegerToString(z.seq)` in `BrcCsvWriteZone`.
4. [brc_visual.mqh](../mt5/Include/brc_system/brc_visual.mqh#L259) `DrawZoneFull`: prepend `#%d` (z.seq) to the L1 + L2 labels.
5. [tester.py](../research/code/tester.py#L256): add `"seq"` to `_ZONE_COLS` and to `_ZONE_INT_COLS` (DictReader-safe; CSV header name == DB col name).
6. New migration `031_*` : `ALTER TABLE tester_zones ADD COLUMN seq INTEGER;`.
- Then: compile headless (see [[brc_compile_workflow]]), re-emit 1yr smoke (Open prices only, [[brc_emitter_open_prices_model]]), re-ingest, confirm seq populates + still 12,489 zones.
- AFTER identity lands: build task 128 prune (focused pass, byte-identical gate). Then 127.

## Blockers
None. 21h gap was a weekly-limit pause, not a technical block. Task 126 (OOS) stays BLOCKED until IS config frozen ([[is_discipline_guards]]).
