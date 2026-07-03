# FOB payload — data-plane split + rollup-on-ingest

**Date:** 2026-07-03
**Idea:** FOB-001
**Trigger:** research.db hit 707MB (SQLite viewer refused to open) — 100% of it three stale
emit runs (16/17/18) in `fob_zones`/`fob_events`/`fob_cycles` (~2.1M rows). Control-plane
tables (tasks/ideas/gates/results) are <1MB combined.

## Problem
- Raw tick-derived lifecycle payload (millions of rows, machine-only) shares one SQLite file
  with the human-read control plane (tasks/ideas/results). The file balloons, the viewer
  chokes, and any "measure X by setup-TF" answer requires a full-table scan of ~768k rows.
- Two costs from the same root: (a) file too big for the viewer, (b) every analysis /
  agent read scans raw instead of reading a conclusion → slow + token-heavy.

## Principle
> **research.db holds conclusions, never the storyline.**
> Emit → Parquet (raw, disposable) → rollup into research.db (small, permanent) → query the rollup.

## Lever 1 (ship first) — rollup-on-ingest  [task: fob_run_stats]
- In `tester.ingest_fob` (or a new `derive_fob_run_stats(run_id)` called from
  [ingest_fob.py](../../research/code/io/ingest_fob.py) after the Tier-C derivations),
  compute a small **`fob_run_stats`** table: **one row per (run_id × setup_tf)**.
- Columns (round-1): `run_id, setup_tf, n_cycles, n_zones, n_cf,
  mean_rt_count, mean_n_l2_touches, vr_fresh_pct, mean_realized_r, mean_mfe_r, mean_mae_r,
  win_pct, mean_bars_alive`. (~7–60 rows per run.)
- Effect: task 182 (RT edge by setup-TF) and any conditioner screen become a **~10-row read**,
  not a 768k-row scan. This is the bulk of the token/latency win and is independent of storage.
- Rollup lives in research.db (it IS a conclusion). Raw payload can then leave the file.

## Lever 2 — move raw payload out of research.db  [task: fob_parquet_dataplane]
- Write the raw lifecycle payload as **one Parquet file per emit run**, e.g.
  `data/fob_payload/fob_run<NN>.parquet` (gitignored, derivable), **partitioned by `setup_tf`**
  so analysis reads only the needed partition/columns (predicate pushdown).
- research.db keeps only: `tester_runs` (the run manifest) + `fob_run_stats` (the rollup).
  The `fob_zones`/`fob_events`/`fob_cycles` tables are **dropped from research.db** once the
  Parquet path is proven byte-equivalent.
- Analysis / agent reads go through a thin `read_fob_payload(run_id, setup_tf=None, cols=[...])`
  helper (mirrors `arctic_io.py` discipline) — returns a small frame, never dumps raw to context.

### Look-ahead caveat — N/A here
- The "Parquet RETIRED 2026-06-12 (task 51)" rule ([[arctic_tick_store]]) was about the **raw
  tick store**, where unsorted Parquet reads manufactured look-ahead. That risk does **not**
  apply to derived lifecycle payload: it is emitted causally by the EA (single accumulator,
  ≥v1.30.0), already time-stamped, and never re-sorted for analysis. Parquet is safe for the
  data plane. (ArcticDB is the consistent-with-stack alternative if we'd rather one storage
  engine, but 2M rows don't need it.)

## Sequencing
1. Land **Lever 1 (fob_run_stats)** first — pure additive, no data moved, immediate token win.
   Wire it into the task-220 re-emit ingest so the fresh v1.32.0 run gets a rollup for free.
2. Land **Lever 2 (Parquet)** after 220's clean re-emit exists — prove byte-equivalence on the
   fresh run, then drop the three raw tables + VACUUM. research.db stays ~3MB permanently.

## Reversibility
- All current raw payload is re-emittable from the source CSVs (local
  `…/MetaQuotes/…/Common/Files/FOB/` + `G:\My Drive\baysix_backups\fob_emit\`). Run-18's 8yr
  CSV (422MB) is on both. Nothing is lost by dropping DB rows.
