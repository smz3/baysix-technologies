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
SCHEMA_MT5 = """
-- G4 (Live/FIDELITY) evidence — lives in research.db next to step4_results.
CREATE TABLE IF NOT EXISTS tester_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id         TEXT NOT NULL,                 -- soft FK into step1_ideas (same DB)
    run_role        TEXT CHECK(run_role IS NULL OR run_role IN ('emitter','trader')),
    ea_name         TEXT,                          -- 'baysix_orb_001'
    ea_version      TEXT,
    git_sha         TEXT,                          -- provenance (DIRTY tree = exploratory only)
    git_dirty       INTEGER,
    symbol          TEXT NOT NULL,                 -- e.g. 'XAUUSD_dukas'
    data_source     TEXT NOT NULL CHECK(data_source IN
                       ('dukascopy','broker_history','custom')),
    model_quality   TEXT,                          -- MT5 history quality, e.g. '100% real ticks'
    tester_model    TEXT CHECK(tester_model IS NULL OR tester_model IN
                       ('real_ticks','every_tick','1min_ohlc','open_only')),
    timeframe       TEXT,                          -- 'M1'
    period_start    DATE,
    period_end      DATE,
    tz_offset_hours INTEGER,                        -- tester server->UTC offset (0 = UTC dukas)
    magic_number    INTEGER,
    initial_deposit REAL,                           -- fair deposit (cap non-binding)
    leverage        INTEGER,
    spread_setting  TEXT,                           -- 'real' | 'fixed:N'
    params          TEXT CHECK(params IS NULL OR json_valid(params)),  -- EA inputs snapshot
    -- run-level summary --
    n_trades        INTEGER,
    net_profit_usd  REAL,
    profit_factor   REAL,
    max_dd_pct      REAL,
    win_rate        REAL,
    -- FIDELITY diff vs Python research (filled by log_fidelity_diff) --
    research_result_id   INTEGER,                   -- soft ref to step4_results
    trade_overlap_pct    REAL,                      -- same session_date+direction
    ER_delta_vs_research REAL,
    R_corr               REAL,
    fidelity_verdict     TEXT CHECK(fidelity_verdict IS NULL OR
                            fidelity_verdict IN ('pass','fail','pending')),
    notes           TEXT,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);


-- tester_trades / tester_zones / tester_run_summary were DROPPED by migration 039
-- (2026-08-16). They were bulk per-run PAYLOAD; payload lives in files keyed by the
-- run_id in the path, not in the ledger.
--
-- tester_runs above is deliberately KEPT: it is the run REGISTRY, the row that makes
-- research/data/fob_payload/run_<id>/ identifiable instead of anonymous. Rename it to
-- `runs` + add a `platform` column when the DB moves to baysix.db.
"""


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
