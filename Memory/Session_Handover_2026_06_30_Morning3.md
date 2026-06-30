# Handover — June 30, 2026 Morning3

## State
- **FOB emitter v1.25.0 — cycle-end eviction SHIPPED + all gates green, committed `3e09256`.** New PBO on a setup_TF retires the prior cycle's VR/CF from `g_watch` ([fob_baysix.mq5:152-172](../mt5/Experts/fob_system/fob_baysix.mq5#L152)) — event-driven, NO bar cap.
- **Bug fixed = O(T²) zombie-VR.** Old v1.24.0 never evicted VRs → per-tick scan grew unbounded. 1yr ran 26min+ and *never finished*; now **11min COMPLETED** (run_id 17), 8yr extrapolates ~90min linear / ~390MB.
- **`rt_count` de-zombied:** run_id 17 (12mo) rt_count p50 330→0, p99 1212→58, RT total 2.29M→87k despite 4× the VRs (raw counts off `fob_zones`, run_id 17 vs 16).
- **DETERMINISM PASS** — byte-identical double-run (run_determinism.ps1 exit 0) → eviction is causal, not look-ahead.
- run_id 17 = 1yr preflight (2016-06→2017-05): 36000 cycles / 92952 zones / 0 orphans.
- Task 201 added+resolved. **run_id 16 `rt_count`/`rt_time` KNOWN-BAD** (zombie-inflated) — superseded.

## Next
1. **(task 190, P1)** Full 8yr emit: [fob_preflight_1yr.ini](../mt5/tester/fob_preflight_1yr.ini) → set ToDate=2024+ (or full range), real ticks Model=4, all 9 TFs M1→MN1. ~90min via [run_preflight.ps1](../mt5/tester/run_preflight.ps1) (Start-Process window). Then `ingest_fob` → run_id 18.
2. **(task 192, P1)** Storyline-alignment screen on the **full-history run** (not run_id 16/17), assert `idea_id='FOB-001'`, filter `zone_valid=1`, **W1/MN1 warm-up tag** (exclude pre-cutoff high-TF cycles — derive cutoff from first valid MN1 VR in data). EXPLORATORY mid-price, NOT a tester gate.
3. **(task 200, P2)** ingest_fob phase-2: Tier-C (continued/confirm via next-CF linkage; mfe/mae/realized_r; supersede/is_primary).

## Blockers
- None. Emitter validated + committed; full emit is a known-good ~90min run.

## Why
- **Bar-cap eviction REJECTED by Syafiq (hard rule):** FOB is event-driven — lifecycle/RT confirmed off tick-touches + bar-closes + storyline events, NEVER a numerical bar count. A bar-cap would wrongly cut a legitimately-long high-TF cycle (an MN1 cycle alive for months SHOULD keep counting RT) while a dead M1 cycle should stop the instant its next PBO prints. Cycle-end is the only correct trigger. ([[fob_event_driven_no_bar_caps]])
- **Eviction lives emitter-side** (`g_watch` is emitter-only state), NOT in trader-shared `FobClassifyBreak` → trader parity untouched. Hooked to the newly-appended PBO event in OnTick; matches on `FobEvent.setup_tf`+`seq` (both already on the struct → zero schema change).
- **1yr-before-8yr probe was the right call** — it exposed the quadratic (would've been ~64× not 8× full-scale) and the data-corruption (zombie rt_count) before committing an 8yr run. ([[fob_emitter_zombie_vr_quadratic]])
- **Keep-all-and-tag** chosen for W1/MN1 warm-up (vs starting measurement at 2018): keep all data, exclude high-TF cycles at *screen* time via a data-derived cutoff. The ladder is mutually dependent (M1 = VR-provider for M5; MN1 = top bias anchor) so the emit can't drop either end or chunk by year (would sever multi-year cycles).

## Ruled-Out
- **Bar-cap RT eviction (~150 bars/TF)** — proposed from the empirical RT-latency (p50≈1.5 / p90≈30-50 bars off run_id 16), then REJECTED: conceptually wrong for FOB (see Why). Cycle-end eviction replaces it entirely.
- **Removing only the `bool live` gate** (earlier task-197 framing) — cosmetic, already shipped in v1.24.0; not revisited.

## Live-Threads
- **run_id 17 is a 1yr PREFLIGHT, not the screen dataset** — task 192 must run on the full-history emit (run_id 18), not 17. 17 exists only to prove the fix.
- **W1/MN1 warm-up cutoff is unset** — 1yr slice had only 1 MN1 cycle (too few). Derive the cutoff (first valid MN1 VR) from the full 8yr run before screening.
- **Trader still v1.23.0, bar-coarse** — its internal touch/RT lifecycle doesn't consume the emitter's tick-resolution zones. Out of scope until the edge is measured (execution = G3/G4, downstream).
- `research.db` has the task-201 resolve uncommitted from this session — gets committed with this handover.
- `gen_version` leaves fob_version.mqh DIRTY between commits (gitignored, expected).
