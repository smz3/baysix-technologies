# Handover — July 4, 2026 Afternoon

## State
- **8yr EMIT mine COMPLETE → ingested as run_id 19** (FOB-001 emitter, v1.33.0, git 483e365). 766,067 zones / 295,688 cycles, 2016-06-13→2024-06-28, 0 orphans. The clean oracle now lives in `research/db/research.db` (was an empty husk mid-rebuild; run 19 IS the rebuild).
- **Emit CSV**: `Common/Files/FOB/fob_capture_XAUUSD_dukas_v1.33.0_20160614_0000.csv` (430 MB). Also the old v1.25.0 CSV (422 MB, run 18) on disk.
- **Both CSVs backed up to `G:\My Drive\baysix_backups\`** (local copy byte-verified; Drive cloud-upload runs async — confirm tray sync green).
- **VR contamination audit PASSED** (task 222) — run 19 causally clean, zombie signature absent.
- **Run took ~13h** (not the 1.7h preflight extrapolation — real-tick 8yr is far heavier).
- Backlog synced: 220 + 222 resolved; 234/235/236 opened; strategy_log #88 (CF_L1_LIMIT PROPOSED).

## Next
1. **(task 235, P1)** FOB entry-level sweep in TRADE mode (real ticks Model=4): CF **T1/T2/T3** + PBO **T1/T2/T3** pullback limits; TP R-multiple set **per sequence position** (CF1/CF2/CF3 × setup-TF), not flat. A/B each vs CF_MARKET baseline. Build first — entry is the base layer.
2. **(task 234, P1)** Best **setup-TF × direction** combo for the PBO→VR→CF storyline; entry CF T1 (L1 limit), SL L2+buffer. Rank by $/trade + survival (NOT E[R] — [[er_denominator_illusion]]).
3. **(task 236, P1)** Add exit: close on **opposite PBO of the PARENT timeframe** (kill long-held losers). Test on top of the chosen entry. Extends task 179 but keyed to the parent TF, not setup TF.

## Blockers
- None.

## Why
- **CF_L1_LIMIT is the working entry now** (strategy_log #88, PROPOSED): Syafiq's 1yr H4-H1 real-tick A/B (run before the mine) flipped the equity curve from smooth-negative → breakeven/positive vs CF_MARKET. Single-window/exploratory → validated on run 19 before ADOPT, but it's why the whole next program anchors entry at CF T1/L1 with SL at L2+buffer.
- **Program order = entry (235) → TF×dir (234) → exit (236)** because the parent-PBO exit must be tested *on top of* a chosen entry mechanic, not in isolation.
- **run 19 replaced an empty DB husk** — research.db was mid-rebuild (task 203, untracked, payload tables dropped; headers 16/17/18 survived). Ingesting the v1.33.0 CSV was the intended rebuild path, non-destructive (new run_id, 101 MB `research.db.pre40_rebuild` backup already in place).
- **M1 base is mandatory for EMIT** (Syafiq asked): chart Period sets the TF availability floor; the tester doesn't reliably build sub-chart-period TFs. FOB wants M1→MN1, so base must be M1. `InpTfPair` is what EMIT ignores — NOT the chart period.

## Ruled-Out
- **Nothing killed this session.** The exploratory `fob_run_stats` (run_id 19, cost-free mid-price) shows M5 mildly net-positive pre-cost and all higher TFs negative — but that is an oracle geometry screen, **NOT a verdict** (MT5 TRADE-mode is the only arbiter, [[orb_unsorted_tick_lookahead]]). Do not treat those rollup numbers as an edge; spread eats M5. Re-measured properly under tasks 234/235.

## Live-Threads
- **CF invalidation is fully captured** (answered Syafiq's Q): per-zone `alive_at_end` + `invalidation_time` in `fob_zones`. Run 19 split — CF: 96,126 of 278,592 invalidated (survivors 182,466); VR: 66,272 of 191,787; PBO: 83 of 295,688 (anchor ≈ never dies, = cycle-death count). Queryable per setup_tf for the 234/235 screens.
- **Old-vs-new byte diff of VRs was NOT possible** — the contaminated v1.24.0 zombie CSV (run 16) is off disk; on-disk "old" CSV (run 18, v1.25.0) already had the eviction fix. Internal integrity audit stands in as the contamination test (passed). If a true diff is ever wanted, re-ingest run 18 and compare VR sets (~10 min) — but low value.
- **Nested cycle engine still unbuilt** (carried from prior handover) — per-TF state machine + htf_state snapshot exist, but no hierarchical parent-child engine. Assessed buildable post-mine without re-mining. Tasks 234/236 will need parent-TF direction derivation, which brushes against this.
