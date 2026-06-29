# Handover — June 29, 2026 Morning2

## State
- **FOB data-capture schema DESIGNED + DB REBUILT** (additive migration 035, verified). Spec: [docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md](../docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md).
- **Shared spine:** `tester_runs` += `run_role`(emitter|trader)/`git_sha`/`git_dirty`; new `tester_run_summary` (trader scorecard); `tester_trades` += `zone_id`/`gross_usd`/`cost_usd`.
- **FOB-owned payload (new):** `fob_cycles` (PBO-anchored storyline), `fob_events` (PBO/VR/CF ledger + `htf_state` awareness snapshot), `fob_zones` (4-pointer + touches/RT/`vr_fresh`/lifecycle). All 0 rows.
- **`tester_zones` KEPT as BRC's 5-pointer table** — FOB no longer borrows it (kills the P5 confusion); 6 live BRC/seed readers untouched.
- Code-layer synced: [tester.py](../research/code/io/tester.py) `_SCHEMA` + `delete_run` updated; `init_db()` idempotent ✓. Logged strategy_log id80, human_decision call_id90, task 193. Committed + pushed.
- **Nothing emits/ingests into the new tables yet** — the EA CSV + ingest are the build queue.

## Next
1. **(task 193, P1)** Extend [fob_csv.mqh](../mt5/Include/fob_system/fob_csv.mqh) (path A) to emit lifecycle (touches t1/t2/t3+counts, rt_count/rt_time, vr_fresh, confirm/invalidation/continued/realized_r) **+ per-TF `htf_state` snapshot**, causally from the tester.
2. **(task 191, P1)** Build `ingest_fob` in [tester.py](../research/code/io/tester.py): rich CSV → `fob_cycles`/`fob_events`/`fob_zones`, tagged `idea_id='FOB-001'`.
3. **(task 190, P1)** Run `fob_baysix` emitter: XAUUSD_dukas, 8 TF, 2016–2024, Open-prices.
4. **(task 192, P1)** Re-screen storyline on FOB OWN zones; pin run_id + assert `idea_id='FOB-001'`.

## Blockers
- None.

## Why
- **FOB is a sequence/cycle model, not a flat zone bag** — Syafiq pushed back on a universal zone table because it flattens the storyline (PBO→VR→CF chain) that FOB's edge depends on. Resolution: shared spine (provenance/asset/trades — genuinely identical across strategies) + strategy-OWNED payload (each strategy models its own storyline). Best of both; avoids the BRC-contamination class of bug.
- **Migration went ADDITIVE, not destructive** — dropping `tester_zones` would break 6 live BRC/seed files; keeping it (as BRC's table) gives the same clean outcome with zero breakage. FOB simply uses `fob_*` now.
- **Multi-asset is handled by an `instruments` dimension + R-units** — edges measured in R are asset-agnostic; $ lives only on trader runs tied to an instrument row. New asset = one new row, never a schema change. (`instruments` table itself NOT yet created — mirrors execution.db `d1_instruments`; create when first trader run needs it.)
- **`component='data_schema'` is NOT a valid strategy_log component** — used `config` (valid set: exit/anchor/sizing/entry/filter/config/conditioning/management).

## Ruled-Out
- **Universal/model-agnostic single zone table for FOB** — rejected (would JSON-blob the cycle/CF/RT structure → un-queryable storyline). Strategy-owned payload chosen instead.
- **Path B (Python re-derives lifecycle from price after the fact)** — rejected for any gate-grade number; it re-creates the [[orb_unsorted_tick_lookahead]] trap. Path A (EA emits causally) is the contract. B allowed only if explicitly labelled exploratory.
- **Full-stack TF-alignment as a trade GATE** — already banked REJECTED (id18); reconfirmed this session it's conceptually wrong, not just flat. Alignment = AWARENESS snapshot (`htf_state`), never an all-agree filter.

## Live-Threads
- **CORRECTIONS to FOB model (Syafiq, this session) — saved to [[fob_cmp_storyline_model]]:** (1) cycle = PBO-anchored, **new PBO = new cycle** (NOT "repeats when VR breaks"); (2) alignment = awareness, trade direction depends on which setup-TF you pick. A TF's current dir = the live cycle one TF below it (gold now: MN1 bull/W1 CF5, but W1 dir = D1 CF1 bear → Bias bearish).
- **Phase-2 nuances deferred (real edge, noted not lost):** distance of CF from VR + zone edges; setup-TYPE per TF (in-zone/above/before, HR vs LR, fresh vs structured); regime features; outcome labels at multiple horizons. Layer on after round-1 basics feed sims.
- **`realized_r` SELL-sign convention (task 189)** — still unverified; must be frozen into the path-A CSV contract before any FOB screen is trusted.
- **`instruments` table** designed in spec but not created; needed before the first FOB *trader* run logs $.
- **`htf_state` JSON shape** proposed as `{MN1:{dir,cf}, W1:.., D1:.., H4:.., H1:..}` — finalize keys/values when building the emitter (task 193).
