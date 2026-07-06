# Handover — July 6, 2026 Morning

## State
- **research.db data-plane split SHIPPED (task 229, Lever 2)** — research.db **598.5MB → 0.4MB** (SQLite viewer now opens). Raw FOB payload (cycles/zones/events) moved to Parquet-per-run at `data/fob_payload/run_<id>/` (gitignored, derivable). DB keeps only conclusions: `tester_runs` + `fob_run_stats`.
- New: [fob_payload.py](research/code/io/fob_payload.py) (`export_run` / `read_fob_payload(run_id,table,setup_tf,cols)` / `available_runs`); `tester.clear_fob_payload_run` + `tester.vacuum`; [migration 012](research/migrations/012_fob_payload_to_parquet.py). `ingest_fob.py` now auto-exports+clears at tail (`--keep-raw` opt-out).
- run 19 (766k zones, 8yr clean-VR oracle) verified byte-count-equal in Parquet (~92MB) before clear. Committed + pushed.
- **Entry-testing program is DISCUSS-only** — no code decided. Proposed a screen-first (Phase A/B/C) methodology; awaiting Syafiq's 3 decisions.

## Next
1. **Settle 3 entry-test design decisions** (Blockers below) — gates everything else.
2. **(task 237, P1)** Build Phase A oracle screen on run 19 Parquet — cost-free fill-rate × realized-R surface per `setup_tf × cf_idx × level`, CF & PBO zones. Prioritizer, NOT a verdict. Rank by $/period + survival, never E[R].
3. **(task 233 → then 235, P1)** MT5 arbiter: clean market-on-CF baseline (de-confound), then confirm top 1-2 screened variants on HELD-OUT windows, with cost → G2.

## Blockers
- **3 open design decisions (Syafiq's call, from this session's discussion):**
  1. **Screen-first?** Run cheap Phase A oracle screen on run 19 before MT5 (recommended — data already mined), or go straight to MT5?
  2. **OOS split?** 2022-2023 H4 window is BURNED (we peeked + chose CF_L1_LIMIT on it) — can't be validation. Pick the hold-out before looking.
  3. **Re-baseline market-on-CF?** Its "smooth-negative" was measured on falsified VR — likely void ([[reopen_falsified_on_new_data]]). Re-run clean as baseline, or accept dead?

## Why
- **229 was the fix for "can't open research.db":** the 8yr mine (run 19) dumped 1.8M payload rows into research.db → 598MB. The safeguard was designed (spec 2026-07-03) but never built; this session built Lever 2. Chose staging-through-DB-then-export (not Parquet-native ingest) because the derive functions (`derive_fob_*`) read the DB tables — export+clear at tail reuses all of them, low risk. Tables kept (schema) as transient staging, not dropped, so ingest still works.
- **Entry-test methodology rationale (the core discussion):** the plan is screen-cheap-on-8yr → confirm-few-in-MT5-OOS, because sweeping 6 levels × per-seq-TP × setup-TFs in MT5 real-ticks is dozens of 13h runs AND a forking-paths overfit judged on ~1yr. run 19 already carries per-zone L1/mid/L2 + touch ladder + mfe_r/mae_r/realized_r/continued → the entire entry-depth question is answerable cost-free from Parquet. Phase A is a **prioritizer, not a verdict** (MT5 real-ticks is the HARD arbiter — ORB look-ahead lesson).

## Ruled-Out
- **Clean kills (do NOT retry cold):** full-stack alignment as a trade GATE (result_id 18, REJECTED); setup↔direction as a conditioner (~0, artifact — [[fob_storyline_alignment_finding]]).
- **NOT a clean kill — re-open as baseline:** market-on-CF entry. Its smooth-negative equity was measured with falsified VR timing present (two changes at once) → void under [[reopen_falsified_on_new_data]]. We do NOT actually know market-on-CF fails post-fix.
- **Fragile, not proven:** CF_L1_LIMIT breakeven — 1yr, 1 setup-TF (H4 2022-23), window now burned for validation. Promising signal, not a result.

## Live-Threads
- **CF_L1_LIMIT is entry-mechanic v1.33.0 but only L1 (T1), CF zones only, flat rMultTP** ([fob_entry.mqh:103](mt5/Include/fob_system/fob_entry.mqh#L103) pins `entry=l1`). Task 235 generalizes to CF/PBO × T1/T2/T3 + per-sequence TP — Phase A tells us which cells are worth building.
- **T3=L2 design snag:** entry at L2 with SL at L2±buffer → risk collapses to just `k·band` (razor stop). Decide if T3 is literally L2 or "L2-minus-a-notch" before building the sweep.
- **Nested cycle engine still unbuilt** (carried) — tasks 234/236 need parent-TF direction derivation; brushes against it. Buildable post-mine without re-mining.
- **Google Drive backup:** both emit CSVs copied to `G:\My Drive\baysix_backups\` last session; confirm tray sync is green (cloud upload was async).
