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

CREATE TABLE IF NOT EXISTS tester_trades (
    tt_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           INTEGER NOT NULL REFERENCES tester_runs(run_id),
    zone_id          INTEGER REFERENCES fob_zones(zone_id),  -- triggering zone (nullable)
    ticket           INTEGER,                       -- MT5 position id (unique within a run)
    session_date     DATE,                          -- nullable convenience (daily strategies)
    direction        TEXT CHECK(direction IS NULL OR direction IN ('long','short','flat')),
    entry_ts         DATETIME,                      -- cross-system join key (with ticket)
    entry_px         REAL,
    exit_ts          DATETIME,
    exit_px          REAL,
    exit_reason      TEXT,
    lots             REAL,                          -- position size
    risk_unit        REAL,                          -- generic 1R denominator (price units)
    realized_R       REAL,
    gross_usd        REAL,
    cost_usd         REAL,                          -- spread+commission+swap (TCM-001)
    realized_pnl_usd REAL,
    meta             TEXT CHECK(meta IS NULL OR json_valid(meta)),  -- strategy ctx (ORB: or_high/or_low/range_w)
    created_at       DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tester_trades_run    ON tester_trades(run_id);
CREATE INDEX IF NOT EXISTS ix_tester_trades_run_ts ON tester_trades(run_id, entry_ts);

-- BRC zone-lifecycle ledger (task 119). The BRC emitter is an observational
-- oracle, not a trade strategy, so each emit is a tester_runs header (same
-- provenance: symbol/data_source/tester_model/period) and one tester_zones row
-- per confirmed zone per TF. Source CSV = brc_csv.mqh (UTF-8, header, comma).
-- Times are normalised "YYYY-MM-DD HH:MM:SS"; the 0-sentinel blank -> NULL
-- (level never touched / zone still alive at data-end).
CREATE TABLE IF NOT EXISTS tester_zones (
    tz_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    csv_zone_id       INTEGER,                       -- zone_id within the source CSV (resets per file)
    tf                TEXT NOT NULL,                 -- M5 .. MN1
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    p1_time DATETIME, p1_price REAL,
    p2_time DATETIME, p2_price REAL,
    p3_time DATETIME, p3_price REAL,
    p4_time DATETIME, p4_price REAL,                 -- P4 = 2nd break = confirm bar
    p5_time DATETIME, p5_price REAL,
    l1 REAL, l2 REAL, mid REAL,                      -- zone levels (l1=retest/entry, l2=invalidation, mid)
    break_kind        TEXT CHECK(break_kind IS NULL OR break_kind IN ('sequential','same_bar')),
    t1_time DATETIME, t2_time DATETIME, t3_time DATETIME,   -- L1/mid/L2 touch times (NULL = untouched)
    confirm_time      DATETIME,                      -- == p4_time
    invalidation_time DATETIME,                      -- close beyond L2 (NULL = never invalidated)
    alive_at_end      INTEGER,                       -- 1 = still alive at data-end
    continued         INTEGER,                       -- 1 = continuation past L1 in break direction
    mfe_r REAL, mae_r REAL, realized_r REAL,         -- excursion / realized, in R (1R = entry->stop)
    bars_alive        INTEGER,
    seq               INTEGER,                       -- per-TF, 1-based, p4_time order (task 127 human id)
    zone_key          TEXT,                          -- {tf}|{dir}|{p4_epoch}(+|{l2}) machine join key
    is_primary        INTEGER,                       -- 1 unless consolidated away by a bigger overlapping same-dir zone
    consolidated_into TEXT,                          -- survivor zone_key when is_primary=0 (else NULL)
    created_at        DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tester_zones_run     ON tester_zones(run_id);
CREATE INDEX IF NOT EXISTS ix_tester_zones_run_tf  ON tester_zones(run_id, tf);
CREATE INDEX IF NOT EXISTS ix_tester_zones_confirm ON tester_zones(run_id, confirm_time);

-- ── Shared spine: trader-run scorecard (1:1, trader runs only) ────────────────
CREATE TABLE IF NOT EXISTS tester_run_summary (
    run_id          INTEGER PRIMARY KEY REFERENCES tester_runs(run_id),
    n_trades        INTEGER,
    gross_usd       REAL,
    total_cost_usd  REAL,
    net_profit_usd  REAL,
    profit_factor   REAL,
    max_dd_pct      REAL,
    win_rate        REAL,
    expectancy_r    REAL,
    sharpe          REAL,
    research_result_id   INTEGER,
    trade_overlap_pct    REAL,
    ER_delta_vs_research REAL,
    R_corr               REAL,
    fidelity_verdict     TEXT CHECK(fidelity_verdict IS NULL OR
                            fidelity_verdict IN ('pass','fail','pending')),
    created_at      DATETIME NOT NULL
);

-- FOB payload tables (fob_cycles / fob_zones / fob_events / fob_run_stats) were
-- DROPPED by migration 038 (2026-08-16). The ledger no longer carries strategy-shaped
-- tables: every new strategy used to cost 4 tables + a migration. Raw FOB payload lives
-- as Parquet under research/data/fob_payload/run_<id>/ and is read via fob_payload.py.
-- Do NOT re-add per-strategy DDL here; a new SHAPE may earn a generic table, a new
-- STRATEGY never does.
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
