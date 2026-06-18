# Handover — June 18, 2026 Afternoon

## State (BRC-001 emitter — IS pipeline emit→ingest GREEN)
- **Tester perf fixed.** Root cause: runs were on "Every tick based on real ticks". Switched to **Open prices only** (data-identical for the close-only ledger — touches read off closed-bar high/low, time stored = bar time). 1yr smoke = **23s**. Added `if(MQLInfoInteger(MQL_TESTER)) return;` guard on the live-touch pass ([brc_baysix.mq5](mt5/Experts/brc_system/brc_baysix.mq5#L191)). Compiled clean. See [[brc_emitter_open_prices_model]].
- **Task 119 ingest BUILT** — `tester_zones` schema + `ingest_brc_zones()` in [tester.py](research/code/tester.py); CLI [ingest_brc_zones.py](research/code/ingest_brc_zones.py); migration 030. Each emit = a tester_runs header (provenance) + one tester_zones row/zone/TF. Parses brc_csv.mqh UTF-8/header/comma, time-normalised, 0-sentinel→NULL, re-ingest guard.
- **Task 124 smoke DONE** — run #2, 12,489 zones, 2024 IS year. Per-TF byte-matches CSV; all 8 TFs carry zones + T1/T2/T3 (cascade T1≥T2≥T3); all zones resolved (610 alive + 11,879 invalidated).
- **Task 125 full IS DONE** — run #3, **100,034 zones**, M5 confirm **2016-06-13 → 2024-06-28** (stops before OOS ✓). All resolved (1,392 alive + 98,642 invalidated), continued ~51%, L1-touched ~99.5%. ⚠️ data starts 2016-06 not 2016-01 (Dukascopy M5 depth) — ~5mo short of locked IS window.
- **Broken/slow:** the full 8.5yr run took ~hours w/ climbing ETA — O(n²) close-bar pipeline (unbounded swing/zone/break arrays, `InpMaxAge=0`). Logged **task 128** (P2) with full diagnosis + parity-safe fix plan. Numbers above are row-count verifications from `tester_zones` run #2/#3 (no result_id — pre-Gate-3 observational ledger, not step4_results).

## Next
1. **Task 128 (DISCUSS first):** BRC emitter O(n²) fix — alive-zone-only iteration + bounded swing-lookback prune + bounded dedup. CHECK live Sigma B2B EA's lookback cap and mirror it 1:1. Re-verify vs 1yr smoke (must reproduce run #2 = 12,489 zones, per-TF M5=7791..MN1=1).
2. **Task 127:** ConsolidateOverlappingZones decision (dedup vs keep-all) before parity fully closed.
3. **Task 110:** single-TF atom edge test (E[$/trade] net of cost, H_base vs fade vs single-break) — the first real research, BEFORE russian-doll (task 120). ⚠️ MSM-001 `confluence_2tf_agree_t = -2.1951` (cross-TF agreement already tested negative).

## Blockers
None. Task 126 (OOS emit) intentionally BLOCKED until IS config frozen ([[is_discipline_guards]]). Decide whether to backfill 2016-01→06 IS history (optional).
