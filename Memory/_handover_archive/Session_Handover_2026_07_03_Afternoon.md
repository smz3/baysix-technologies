# Handover — July 3, 2026 Afternoon

## State
- **Task 228 SHIPPED + pushed** — rollup-on-ingest. New `fob_run_stats` table (one row per run_id×setup_tf) + `derive_fob_run_stats(run_id)` wired into [ingest_fob.py](../research/code/io/ingest_fob.py) after Tier-C, with a per-TF rollup verify-print. Columns per the 2026-07-03 data-plane spec.
- **Stale-husk bug caught + fixed** — live `fob_zones` was on the OLD single-retouch schema (`rt_count`/`rt_time`); current EA + code use 3-level `rt1/rt2/rt3_time`. Would have crashed task-220 ingest on column mismatch. Added `reset_fob_payload_tables()` (empty-guard) in [tester.py](../research/code/io/tester.py); dropped+recreated the 3 EMPTY payload tables from current schema. Verified: rt1/2/3 present, old cols gone, 0 rows lost.
- **231 preflight GATE PASSED** (both halves): visual QA done by Syafiq (H1 EMIT, real ticks); timing done — 2022-06→2023-06 (1 dense yr) ran **12:25 (745s)**.
- **fob_cycles/fob_events/fob_zones now EMPTY + correct-schema** — ready target for 220. NO current EMIT CSV exists (only stale v1.25.0 422MB on G: backup — quadratic-era, KNOWN-BAD rt).
- Nothing running (unless Syafiq launched 220).

## Next
1. **(task 220, P1)** Launch full 8yr EMIT mine: `InpMode=EMIT`, window **2016-06-01 → 2024-06-01**, real ticks (Model=4), no visuals, H1 timeframe. Only Mode+window are load-bearing (setup/TF are no-ops in EMIT — captures all 9 TFs regardless). Expect ~1.7h (see Why).
2. **(task 220 cont.)** When done → run [ingest_fob.py](../research/code/io/ingest_fob.py) on the fresh v1.32.0 capture CSV → fills 3 tables + auto-builds `fob_run_stats` rollup (prints per-TF summary).
3. **(task 222, P1)** VR contamination audit: diff old-CSV VRs vs fresh v1.32.0 re-emit.

## Blockers
- None.

## Why
- **8yr ≈ 1.7h (not 12h):** 745s for one DENSE year (2022-23, high-vol) × 8 ≈ 99 min. Conservative upper bound — sparse early years (2016-19) run faster. vs the old 12h → ~7× faster = eviction fix confirmed (O(T²) zombie-VR era dead). Even a 3× super-linear penalty still lands ~5h = overnight-safe.
- **Dense year chosen for timing, not sparse:** measuring 2016 (fewest ticks) then ×8 would under-shoot real wall-clock. 2022-23 keeps the probe in-sample (seal ~2024-05, so 2025-26 = OOS, kept pristine even for a timing probe — Syafiq's call).
- **Window 2016-06→2024-06 = IS block** (just past seal). Emitting OOS is safe later (EMIT is a read-only re-emittable oracle) but held back per Syafiq's OOS-hygiene instinct.
- **Keep the 3 raw fob tables for now:** they're the SOURCE the rollup reads from during ingest. They only leave research.db at task 229 (Parquet/Arctic split), and only after byte-equivalence is proven. Today's rollup (Lever 1) already captured most of the token/latency win; Lever 2 is deferred + optional.

## Ruled-Out
- **ArcticDB already has the FOB payload → skip task 229 storage.** FALSE conflation (Syafiq raised it): ArcticDB holds raw TICKS (input, 511M prints); the 229 Parquet is the DERIVED lifecycle payload (zones/cycles/events, output). Different layer — ArcticDB does not contain FOB zones. 229 storage-location decision (Parquet vs ArcticDB) still stands, just deferred.
- **Reuse the existing v1.25.0 422MB CSV for 220.** Stale — quadratic-era, old schema (rt_count/rt_time), run-18 vintage with KNOWN-BAD rt_count. Must re-emit fresh on v1.32.0.

## Live-Threads
- **Task 229 (Parquet/Arctic data-plane split) — storage engine undecided.** Spec names Parquet-per-run OR ArcticDB ("one-engine" alt, matches Syafiq's preference). Decide at 229, after 220's clean re-emit exists. Not needed for tonight.
- **Mode relabel (task 232) still not applied** — EMIT→CAPTURE, STUDY→MEASURE(parked). One-line enum-comment change, deferred again. Current dropdown still says EMIT.
- **Excursion as derived layer (task 202)** — still parked downstream; STUDY mode captures only the setup pair (confirmed from code this session), not all 9 TFs.
