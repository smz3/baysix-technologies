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

-- ── FOB-001 payload: storyline (cycles/events) + zones (FOB owns its shape) ───
-- A cycle = PBO->VR->CF1->CF2... ; a NEW PBO starts a NEW cycle. tester_zones is
-- BRC's 5-pointer table; FOB uses fob_zones (4-pointer). See spec
-- docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md.
CREATE TABLE IF NOT EXISTS fob_cycles (
    cycle_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    setup_tf          TEXT NOT NULL,
    seq               INTEGER NOT NULL,              -- per-setup_tf PBO ordinal = cycle id
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    pbo_time DATETIME, pbo_level REAL, pbo_swing_time DATETIME, pbo_bar_close REAL,
    vr_time DATETIME, vr_level REAL,
    vr_made_first_tf  TEXT,
    n_cf              INTEGER,
    first_cf_time DATETIME, last_cf_time DATETIME,
    status            TEXT CHECK(status IS NULL OR status IN ('alive','invalidated','complete')),
    invalidation_time DATETIME, invalidated_by TEXT,
    start_time DATETIME, end_time DATETIME,
    meta              TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at        DATETIME NOT NULL,
    UNIQUE(run_id, setup_tf, seq)
);
CREATE INDEX IF NOT EXISTS ix_fob_cycles_run    ON fob_cycles(run_id);
CREATE INDEX IF NOT EXISTS ix_fob_cycles_run_tf ON fob_cycles(run_id, setup_tf);

CREATE TABLE IF NOT EXISTS fob_zones (
    zone_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    cycle_id          INTEGER REFERENCES fob_cycles(cycle_id),
    source_label      TEXT CHECK(source_label IS NULL OR source_label IN ('PBO','VR','CF')),
    event_tf          TEXT NOT NULL,
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    l1 REAL, l2 REAL, mid REAL,
    p1_time DATETIME, p1_price REAL,
    p3_time DATETIME, p3_price REAL,
    t1_time DATETIME, t2_time DATETIME, t3_time DATETIME,
    n_l1_touches INTEGER, n_mid_touches INTEGER, n_l2_touches INTEGER,
    rt1_time DATETIME, rt2_time DATETIME, rt3_time DATETIME,
    vr_fresh INTEGER,
    -- FORWARD POINTER to the next same-cycle CF. Non-null iff a later CF exists, so it can
    -- never anchor an entry or gate a filter (task 261). Anchor on fob_events.bar_time.
    next_cf_time DATETIME, next_cf_price REAL,
    invalidation_time DATETIME, continued INTEGER, alive_at_end INTEGER, bars_alive INTEGER,
    mfe_r REAL, mae_r REAL, realized_r REAL,
    zone_key TEXT, is_primary INTEGER, superseded_by TEXT, zone_valid INTEGER,
    meta TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fob_zones_run     ON fob_zones(run_id);
CREATE INDEX IF NOT EXISTS ix_fob_zones_cycle   ON fob_zones(cycle_id);
CREATE INDEX IF NOT EXISTS ix_fob_zones_next_cf ON fob_zones(run_id, next_cf_time);

CREATE TABLE IF NOT EXISTS fob_events (
    event_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    cycle_id          INTEGER REFERENCES fob_cycles(cycle_id),
    zone_id           INTEGER REFERENCES fob_zones(zone_id),
    event_tf          TEXT NOT NULL,
    label             TEXT CHECK(label IN ('PBO','VR','HRCF','CF')),
    cf_idx            INTEGER,
    risk_class        TEXT CHECK(risk_class IS NULL OR risk_class IN ('LOW','HIGH')),
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    swing_time DATETIME, bar_time DATETIME NOT NULL,
    level REAL, bar_close REAL,
    body_clears       INTEGER,
    vr_zone_broken    INTEGER,
    htf_state         TEXT CHECK(htf_state IS NULL OR json_valid(htf_state)),
    meta              TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at        DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fob_events_run     ON fob_events(run_id);
CREATE INDEX IF NOT EXISTS ix_fob_events_cycle   ON fob_events(cycle_id);
CREATE INDEX IF NOT EXISTS ix_fob_events_run_bar ON fob_events(run_id, bar_time);

-- ── FOB-001 rollup (task 228): one CONCLUSION row per (run_id, setup_tf) so
-- downstream screens read ~10 rows, not a ~768k raw-payload scan. Round-1 columns
-- per docs/specs/2026-07-03_fob_payload_dataplane_split.md. Derived by
-- derive_fob_run_stats() after the Tier-C derivations. research.db keeps this even
-- once the raw fob_* tables move to Parquet (Lever 2).
CREATE TABLE IF NOT EXISTS fob_run_stats (
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    setup_tf          TEXT NOT NULL,
    n_cycles          INTEGER,
    n_zones           INTEGER,
    n_cf              INTEGER,
    mean_rt_count     REAL,      -- mean # of non-null rt{1,2,3}_time per zone (0-3)
    mean_n_l2_touches REAL,
    vr_fresh_pct      REAL,      -- 100 * AVG(vr_fresh) over zones where vr_fresh NOT NULL
    mean_realized_r   REAL,
    mean_mfe_r        REAL,
    mean_mae_r        REAL,
    win_pct           REAL,      -- 100 * AVG(continued) over resolved CF zones
    mean_bars_alive   REAL,
    created_at        DATETIME NOT NULL,
    PRIMARY KEY (run_id, setup_tf)
);
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
SCHEMA_GRW = """
-- One row per pre-registered batch. prereg.json on disk stays the source of truth
-- (hashed + git-committed BEFORE the batch runs); this table is the queryable index
-- so the adjudicator and the "3 batches with no promotion" hard stop can read it.
CREATE TABLE IF NOT EXISTS grw_batches (
    batch_id        TEXT PRIMARY KEY,               -- 'grw-2026-08-04-001'
    idea_id         TEXT NOT NULL,                  -- soft FK into step1_ideas
    trial_family_id TEXT NOT NULL,                  -- multiplicity key; spans batches
    hypothesis      TEXT NOT NULL,                  -- one sentence, falsifiable
    mechanism       TEXT NOT NULL,                  -- WHY the edge should exist (spec 3.0:
                                                    -- no mechanism = no slot in the batch)
    fitness_ref     TEXT,                           -- 'grw_fitness.json@<sha>'
    is_start DATE, is_end DATE,                     -- in-sample window
    oos_start DATE, oos_end DATE,                   -- HELD OUT — never passed to the optimizer
    n_trials_budget INTEGER,                        -- declared BEFORE the run
    promote_if      TEXT NOT NULL,                  -- mechanical rule, applied at S3
    kill_if         TEXT,
    prereg_path     TEXT,                           -- data/grw_runs/<batch_id>/prereg.json
    prereg_sha      TEXT NOT NULL,                  -- sha256 of prereg.json minus this field
    prereg_git_sha  TEXT,                           -- commit that froze the prereg
    stage           TEXT CHECK(stage IS NULL OR stage IN
                       ('S0','S1','S2','S3','S4','S5')),
    oos_spent       INTEGER NOT NULL DEFAULT 0,     -- 1 once OOS has been looked at (spec 2.2:
                                                    -- "looking is spending it")
    n_promoted      INTEGER,                        -- filled at S4
    notes           TEXT,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_grw_batches_family ON grw_batches(trial_family_id, created_at);

-- One row per optimizer pass (S0). NOT a result — see the verdict column.
CREATE TABLE IF NOT EXISTS grw_passes (
    pass_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL REFERENCES grw_batches(batch_id),
    trial_family_id TEXT NOT NULL,                  -- denormalised for cheap family rollups
    idea_id         TEXT NOT NULL,
    prereg_sha      TEXT NOT NULL,                  -- goalpost the pass was judged against
    config_hash     TEXT,                           -- hash of params; dedupes repeat configs
    params          TEXT CHECK(params IS NULL OR json_valid(params)),  -- EA inputs snapshot
    -- S0/S1: in-sample --
    is_run_id       INTEGER REFERENCES tester_runs(run_id),
    is_fitness      REAL,                           -- OnTester() custom fitness. v2.0.0 =
                                                    -- barrier outcome: 1.0 target / 0.0 floor
                                                    -- / -1e9 CENSORED (grw_fitness.json)
    is_growth       REAL,                           -- log-growth over the IS window. PARKED
                                                    -- objective, kept as a diagnostic only —
                                                    -- never rank on it (fitness v2.0.0)
    is_n_trades     INTEGER,
    is_net_usd      REAL,
    is_max_dd_pct   REAL,                           -- REPORTED, never a constraint (spec 0/§2)
    rank            INTEGER,                        -- S1 rank by fitness within the batch
    -- S2: held-out --
    oos_run_id      INTEGER REFERENCES tester_runs(run_id),
    oos_fitness     REAL,
    oos_growth      REAL,
    oos_n_trades    INTEGER,
    oos_net_usd     REAL,
    oos_max_dd_pct  REAL,
    -- S3/S4: adjudication (mechanical — the agent gets no vote) --
    stage           TEXT CHECK(stage IS NULL OR stage IN ('S0','S1','S2','S3','S4')),
    verdict         TEXT CHECK(verdict IS NULL OR verdict IN
                       ('PENDING','PROMOTED','FALSIFIED','KILLED')),
    verdict_reason  TEXT,                           -- which clause of promote_if/kill_if fired
    adjudicated_at  DATETIME,
    result_id       INTEGER,                        -- soft ref to step4_results once promoted
    git_sha         TEXT,
    git_dirty       INTEGER,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_grw_passes_batch   ON grw_passes(batch_id, rank);
CREATE INDEX IF NOT EXISTS ix_grw_passes_family  ON grw_passes(trial_family_id);
CREATE INDEX IF NOT EXISTS ix_grw_passes_verdict ON grw_passes(verdict);

-- The multiplicity ledger, as a view so it can never fall out of sync with the passes.
-- "A growth rate without its trial count is not a finding" (spec 2.3).
DROP VIEW IF EXISTS grw_family_trials;
CREATE VIEW grw_family_trials AS
SELECT p.trial_family_id,
       COUNT(*)                                             AS n_trials_cum,
       COUNT(DISTINCT p.batch_id)                           AS n_batches,
       COUNT(DISTINCT p.config_hash)                        AS n_distinct_configs,
       SUM(CASE WHEN p.verdict = 'PROMOTED'  THEN 1 ELSE 0 END) AS n_promoted,
       SUM(CASE WHEN p.verdict = 'FALSIFIED' THEN 1 ELSE 0 END) AS n_falsified,
       MIN(p.created_at)                                    AS first_pass_at,
       MAX(p.created_at)                                    AS last_pass_at
FROM grw_passes p
GROUP BY p.trial_family_id;

-- Batch scoreboard: drives the spec-3.3 hard stop (3 consecutive no-promotion batches).
DROP VIEW IF EXISTS grw_batch_scoreboard;
CREATE VIEW grw_batch_scoreboard AS
SELECT b.batch_id, b.idea_id, b.trial_family_id, b.stage, b.oos_spent,
       b.hypothesis, b.n_trials_budget,
       COUNT(p.pass_id)                                         AS n_passes_run,
       SUM(CASE WHEN p.verdict = 'PROMOTED'  THEN 1 ELSE 0 END) AS n_promoted,
       SUM(CASE WHEN p.verdict = 'FALSIFIED' THEN 1 ELSE 0 END) AS n_falsified,
       SUM(CASE WHEN p.verdict IS NULL OR p.verdict = 'PENDING'
                THEN 1 ELSE 0 END)                              AS n_pending,
       MAX(p.is_growth)                                         AS best_is_growth,
       MAX(p.oos_growth)                                        AS best_oos_growth,
       b.created_at
FROM grw_batches b
LEFT JOIN grw_passes p ON p.batch_id = b.batch_id
GROUP BY b.batch_id
ORDER BY b.created_at DESC;
"""
