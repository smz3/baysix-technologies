# Handover — May 27, 2026 Evening

## State
ideas_log.db now at 62 ideas. New columns added: `category` (alpha/regime/guard/signal_processing/execution/cost_utility/diagnostic) and `sort_order` (controls display, families grouped under parents). `build_order` table complete — 13 infrastructure tools across 3 phases (research/deployment/scale). LIQ-001 spawned 5 children (LIQ-002..006), ALT-001 spawned 6 children (ALT-002..007). RISK-001 design decisions locked (sigma_trade=TCM-001 dynamic, lot sizing=% equity formula, min_lot_override retired → min_tradeable_equity gate). Research pipeline schema fully designed but NOT YET BUILT in research_log.db — current schema is stale and needs rebuilding.

## Next
1. Rebuild research_log.db pipeline + pipeline_events tables with the locked schema (see below)
2. Fix HMM-001 pipeline row: confirm idea_id=1 FK is valid, add missing columns, enable `PRAGMA foreign_keys = ON` on every connection
3. Lock metric_key controlled vocabulary as CHECK constraint before any new VALIDATE calls

## Pipeline Schema — Locked (build this next session)

**Stage flow:**
`EXPLORING → HYPOTHESIS_SET → IS_SIGNAL → IS_BUILD → WALK_FORWARD → MONTE_CARLO → OOS → LIVE`

**MC order within MONTE_CARLO stage:** Bootstrap → Trade Shuffle → Synthetic Paths

**pipeline table columns to add:**
- `asset_class`, `venue` (broker — e.g. just_markets_mt5), `approach` (statistical/ml/hybrid/rule_based)
- `stage_status` (active/killed/parked), `kill_reason`
- `gross_metric` (REAL), `net_metric` (REAL)
- `data_fingerprint` (TEXT — dataset hash/label)
- `cost_model_version` (TEXT — TCM version used)
- `idea_id` as explicit PRIMARY KEY

**pipeline_events columns to add:**
- `metric_unit` (TEXT), `test_type` (TEXT — t_test/PSR/KS/permutation)
- `n_simulations` (INTEGER — for MC events)
- `metric_key` needs CHECK constraint with controlled vocabulary:
  `IS_gross_tstat, IS_net_edge, WF_sharpe, OOS_tstat, MC_bootstrap_percentile, MC_shuffle_pvalue, MC_synthetic_percentile`

## Blockers
None.
