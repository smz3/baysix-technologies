"""
Canonical DDL for the run-ledger half of research.db — the SINGLE SOURCE OF TRUTH.

Why this file exists (task 287): the MT5 tester DDL was duplicated in
[db_init.py](db_init.py) and [tester.py](../io/tester.py). The two copies drifted —
db_init's copy was missing `tester_runs.run_role/git_sha/git_dirty`,
`tester_trades.zone_id/gross_usd/cost_usd`, plus `tester_run_summary` and the whole
`fob_*` payload block. A rebuild from db_init would therefore have SILENTLY produced a
narrower schema than the one every writer expects. Hand-syncing two copies is what
caused the drift, so the fix is to have exactly one copy and import it.

Ownership after this change:
  - schema_ledger.py  -> tester_* (shared spine), fob_* (FOB payload), grw_* (GRW factory)
  - db_init.py        -> step1..step4 / log_* protocol core + views; imports both constants
  - tester.py         -> imports SCHEMA_MT5 (was its private _SCHEMA)

Everything is CREATE ... IF NOT EXISTS, so executing either constant is idempotent.
"""

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA_MT5 — the MT5 run ledger: shared spine + FOB payload.
# Verbatim carry-over of tester.py's former _SCHEMA (which matched the live DB).
# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA_MT5 is intentionally empty. tester_runs was DROPPED by migration 040
# (2026-08-16), completing 038/039: research.db is now a pure spine — ideas, papers,
# gates, results, three logs, four views. Nothing named after a strategy OR a platform.
# The constant is kept so existing imports (db_init.py) keep resolving.
#
# When the DB moves to baysix.db, a GENERIC `runs` registry (one row per backtest, with
# a `platform` column) is still the right thing to build — it is what makes an output
# folder identifiable. It just starts empty rather than carrying superseded FOB history.
SCHEMA_MT5 = ""


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA_GRW — the GRW-001 compounding-factory ledger (task 289).
# Spec: docs/reference/grw_autonomous_workflow.md §2 (promotion ladder) + §4 (storage).
#
# Design notes that are load-bearing, not decoration:
#   - grw_passes rows are RAW MATERIAL, never findings. Only an S3-adjudicated
#     survivor is copied into step4_results (spec §2.3). The `verdict` column is the
#     boundary between the two.
#   - The multiplicity ledger is `trial_family_id`. It accumulates ACROSS batches, so
#     the bar rises as the search widens — this is the entire reason GRW shares
#     research.db instead of getting its own file (two DBs = two denominators).
#   - `prereg_sha` is copied onto every pass row. A pass whose prereg hash does not
#     match the committed prereg.json was adjudicated under a moved goalpost, and the
#     row itself carries the evidence.
#   - Protocol 4.0 deliberately dropped n_trials/trial_family_id as DSR/PSR *deflators*
#     (db_init.py header). They come back here as a BOOKKEEPING ledger only — nothing
#     auto-kills on them; see [[simplicity_first_protocol]] and CLAUDE.md rule 8.
# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA_GRW is intentionally empty. grw_batches / grw_passes and their two views were
# DROPPED by migration 038 (2026-08-16) under the same no-per-strategy-tables rule; both
# were empty (GRW-001 had never run). The constant is kept so existing imports
# (db_init.py, migration 037) keep resolving — it now creates nothing.
#
# STILL OWED before GRW-001 starts: grw_passes carried `trial_family_id`, the multiplicity
# ledger that raises the bar as the search widens. It needs a GENERIC home in the spine —
# trial counting is a spine concern (how much did we search), not strategy data.
SCHEMA_GRW = ""
