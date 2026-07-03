# Handover — July 3, 2026 Morning3

## State
- **FOB v1.32.0 live, recompiled + pushed twice this session** (`501d725` groups/labels, then const-hide). No logic touched — CSV/lifecycle byte-identical, `.set` presets preserved.
- **Tester Inputs tab cleaned up** (task 230 done): MQL5 `input group` headers (MODE / TRADE-STUDY / TRADE / STUDY / LIVE / VISUAL), comments now lead with mode tag, visual `#include` moved below the input block so MODE renders first. The 3 frozen DETECT knobs (`InpSwingWindow`/`InpMaxAge`/`InpPboNewestOnly`) converted `input`→`const` (hidden from tab, reversible).
- **Tick cache confirmed WARM** — 121 monthly `.tkc`, full 201606→202606, `bases/Custom/ticks/XAUUSD_dukas` (2.0 GB). Re-run does NOT re-download.
- fob emit tables still EMPTY (purged prior session) — task 220 repopulates.
- Nothing running. Fresh `.ex5` at 11:14:33 visible in JM terminal (E7DB) via junction.

## Next
1. **(task 228, P1)** Wire `derive_fob_run_stats(run_id)` into `ingest_fob` (rollup one row per run×setup_tf) — land BEFORE 220 so the re-emit rolls up in one pass.
2. **(task 231, P1)** Preflight: short-window EMIT (e.g. 2026-01..06) in tester **Visual Mode, real ticks** → Syafiq eyeballs zones/T-touches/RT-dots + we extrapolate true 8yr time. **GATE** before the full mine.
3. **(task 220, P1)** Full 8yr EMIT overnight (both modes) once preflight passes → repopulates fob tables.
4. **(task 222, P1)** VR contamination audit: diff old-CSV VRs vs fresh v1.32.0 re-emit.
5. **(task 232, P2)** Relabel modes EMIT→CAPTURE, STUDY→MEASURE(parked). **(task 202, P2)** excursion as derived layer.

## Blockers
- None.

## Why
- **Input cleanup (230):** Syafiq kept getting lost — MT5 shows the `//comment` as the on-screen label, not the `InpXXX` name I speak in, and the visual toggles rendered *before* the mode switch. Groups + tag-leading labels + reordered include fix the mapping; hiding frozen DETECT knobs cuts clutter. No renames = `.set` presets stay valid.
- **DON'T merge STUDY into EMIT (settled this session):** merging wouldn't corrupt the storyline data, but it injects measurement params (horizon "170"/cap-bars/setup-TF choice) into EMIT's output → kills its defining property: a **parameter-free, byte-identical, re-emittable oracle**. You'd re-mine 8yr per horizon. Also forward-excursion can only finalize N bars *after* an event, so it can't ride EMIT's write-at-bar-close path. Excursion belongs DOWNSTREAM = derived layer (task 202), re-computable at any horizon off the oracle + sorted ticks, no re-mine.
- **Sharding the 8yr mine by TF-pair = rejected (see Ruled-Out).** One all-9 pass already emits all 8 pairs.
- **12h benchmark is quadratic-era.** Run 18 was pre-eviction (O(T²) zombie-VR). Current build has cycle-end eviction ([fob_baysix.mq5:377-391](../mt5/Experts/fob_system/fob_baysix.mq5#L377-L391)) → ~linear + already decimates repeated ticks ([line 435](../mt5/Experts/fob_system/fob_baysix.mq5#L435)). Expect materially faster — but MEASURE via preflight, don't assume.

## Ruled-Out
- **Shard the 8yr EMIT into 8 separate TF-pair runs (Syafiq's speed idea).** One all-9 pass already emits every one of the 8 pairs (a pair's events = adjacent-TF breaks). Splitting *re-replays* the 8yr tick stream N times = MORE total work; only helps wall-clock if parallelized, and MT5 runs one continuous backtest on ONE core ([[brc_headless_tester_fires]] blocks concurrent headless too). Net loss.
- **"Warm-cache re-run halves the 12h."** Disproven — cache is already warm (`ticks synchronized already`), so no download time to reclaim. The 12h was genuine compute (and quadratic-era).
- **numba port of the accumulator** for a 10-100× mine — rejected: re-introduces the exact dual-engine drift the v1.28.0 merge killed (two accumulators that must stay byte-identical forever). Not worth it for a rare one-off cost.

## Live-Threads
- **Mode relabel (232) not yet applied** — decided but not coded (deferred to save context). One-line enum-comment change: EMIT→CAPTURE, STUDY→MEASURE(parked). Do it next session with the 228 work.
- **Preflight window unpicked** — Syafiq to choose the short QA window (I suggested Jan–Jun 2026, freshest in memory + densest ticks). Configs already exist: [fob_preflight_1yr.ini](../mt5/tester/fob_preflight_1yr.ini), [fob_emit_8yr.ini](../mt5/tester/fob_emit_8yr.ini).
- **Stray `resolve_task(0)`** fired once during task sync (no task 0 exists → harmless no-op); ignore.
