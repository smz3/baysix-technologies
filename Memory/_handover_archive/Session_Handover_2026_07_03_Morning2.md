# Handover — July 3, 2026 Morning2

## State
- **FOB v1.32.0 is the live build** (shipped prior session — visual/causality thread green: tasks 225/226/227 done). No EA code touched this session.
- **research.db purged + compacted: 707MB → 0.4MB** — SQLite viewer was refusing to open it. Cleared the FOB emit payload (`fob_zones`/`fob_events`/`fob_cycles`, ~2.1M rows across the only three runs present: 16/17/18). Control plane intact: `tester_runs`=3 (manifest kept), `log_tasks`=131, ideas/gates/results/lineage untouched.
- **Data-plane-split spec written:** [2026-07-03_fob_payload_dataplane_split.md](docs/specs/2026-07-03_fob_payload_dataplane_split.md).
- **Two new tasks logged:** 228 (P1) rollup-on-ingest `fob_run_stats`; 229 (P2) Parquet data-plane split.
- All three purged runs are **re-emittable from source CSVs** (local `…/MetaQuotes/…/Common/Files/FOB/` + `G:\My Drive\baysix_backups\fob_emit\`; run-18 8yr CSV = 422MB, on both). Nothing lost.
- **Uncommitted:** spec doc is new/unstaged; DB is untracked (local-only) so the purge isn't a git event.

## Next
1. **(task 220, P1)** Re-emit + re-test BOTH modes on v1.32.0 → clean RT-ladder capture (repopulates the now-empty fob tables).
2. **(task 228, P1)** Wire `derive_fob_run_stats(run_id)` into `ingest_fob` so the 220 re-emit gets its rollup for free — ship BEFORE task 229.
3. **(task 222, P1)** VR contamination audit: diff old-CSV VRs vs the fresh v1.32.0 re-emit.
4. **(task 182, P1)** RT statistical study — becomes a ~10-row read off `fob_run_stats` once 228 lands.
5. **(task 229, P2)** Parquet-per-run data plane — AFTER 220's clean re-emit proves byte-equivalence.

## Blockers
- None.

## Why
- **Why purge, not archive:** the whole 707MB was three *stale* emit runs — all pre-v1.30.0, so every VR in them carries the causality bug already fixed (task 221); run 16 is separately KNOWN-BAD ([[fob_emitter_zombie_vr_quadratic]]). Task 220 re-emits fresh regardless, so the rows were about to be overwritten. research.db is untracked + CSVs backed up ⇒ zero-risk delete.
- **Why full truncate, not `delete_run`:** `delete_run`'s `WHERE run_id=?` path is O(rows × indexes) — it was still grinding after 15+ min on run-18's 768k rows (journal crawling 7.6→8.2MB). Since 16/17/18 are the ONLY runs in those tables, a no-WHERE `DELETE FROM t` hits SQLite's **truncate optimization**: cleared all in **9.7s**, VACUUM in 0.07s. Killing the slow delete mid-flight was rollback-safe (SQLite reverted the journal — "before" read the full 885,419 rows intact, then truncated).
- **Why the spec exists (the real lesson):** raw tick-derived payload was living in the same SQLite file as the human-read control plane, so the file bloated AND every "measure X by setup-TF" answer scanned ~768k rows. Fix = (1) rollup-on-ingest (`fob_run_stats`, one row per run×setup_tf) so reads are ~10 scalars not a full scan, and (2) move raw payload to Parquet-per-run out of research.db. Principle: **research.db holds conclusions, never the storyline.**

## Ruled-Out
- **`delete_run` for bulk clears** — do not use it to empty whole tables; it's row-by-row. Full-table truncate (no WHERE) is the tool when clearing ALL runs. (For per-run deletes with other runs present, `delete_run` is still correct, just slow.)
- **Parquet look-ahead objection** — the "Parquet RETIRED, task 51" rule ([[arctic_tick_store]]) is about the RAW TICK store (unsorted reads → look-ahead). It does **not** apply to derived lifecycle payload (emitted causally, never re-sorted). Parquet is safe for the FOB data plane; don't re-litigate this when building 229.

## Live-Threads
- **228 vs 220 sequencing** — task 228 (rollup) ideally lands *before* running the 220 re-emit ingest, so the fresh run gets `fob_run_stats` in one pass. If 220 runs first, just backfill the rollup after. Not a blocker, just cheaper in that order.
- **Uncommitted spec doc** — [2026-07-03_fob_payload_dataplane_split.md](docs/specs/2026-07-03_fob_payload_dataplane_split.md) is unstaged; Syafiq asked to hold the commit decision. Commit it with the next real change.
- **Scratchpad leftovers** — `finish_purge*.py` throwaway scripts live in the session scratchpad only (not the repo); ignore/expire naturally.
