"""035 — FOB-001 payload schema + shared-spine cleanup.

Additive rebuild agreed 2026-06-29 (spec: docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md).

Shared spine:
  - tester_runs   += run_role ('emitter'|'trader'), git_sha, git_dirty
  - tester_trades += zone_id (link to fob_zones), gross_usd, cost_usd
  - tester_run_summary  (NEW, 1:1, trader runs only — the MT5 scorecard)

FOB-owned payload (the storyline — FOB no longer borrows BRC's tester_zones):
  - fob_cycles    (PBO->VR->CF chain; NEW PBO = NEW cycle; identity (run_id,setup_tf,seq))
  - fob_events    (chronological PBO/VR/CF ledger + per-TF awareness snapshot htf_state)
  - fob_zones     (4-pointer + touches/RT + vr_fresh + lifecycle)

tester_zones is KEPT (it is BRC's 5-pointer table; FOB uses fob_zones). Purely additive
-> no existing reader/writer breaks. Idempotent: ALTERs guarded, CREATEs use IF NOT EXISTS.
"""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "research.db"
MYT = timezone(timedelta(hours=8))


def _add_col(conn, table, coldef):
    col = coldef.split()[0]
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if col not in have:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")
        print(f"  + {table}.{col}")
    else:
        print(f"  = {table}.{col} (exists)")


SPINE_DDL = """
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
"""

FOB_DDL = """
-- A cycle = PBO -> VR -> CF1 -> CF2 ...  ; a NEW PBO starts a NEW cycle.
-- Identity (run_id, setup_tf, seq); seq = per-setup_tf PBO ordinal.
CREATE TABLE IF NOT EXISTS fob_cycles (
    cycle_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    setup_tf          TEXT NOT NULL,                 -- governing PBO TF
    seq               INTEGER NOT NULL,              -- per-setup_tf PBO ordinal = cycle id
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    pbo_time DATETIME, pbo_level REAL, pbo_swing_time DATETIME, pbo_bar_close REAL,
    vr_time DATETIME, vr_level REAL,
    vr_made_first_tf  TEXT,                           -- which TF made the VR first (double-BO tiebreak)
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

-- The tradeable 4-pointer zone + touches (T) + retests (RT) + vr_fresh + lifecycle.
CREATE TABLE IF NOT EXISTS fob_zones (
    zone_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    cycle_id          INTEGER REFERENCES fob_cycles(cycle_id),
    source_label      TEXT CHECK(source_label IS NULL OR source_label IN ('PBO','VR','CF')),
    event_tf          TEXT NOT NULL,
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    l1 REAL, l2 REAL, mid REAL,                      -- entry / stop / 50%
    p1_time DATETIME, p1_price REAL,
    p3_time DATETIME, p3_price REAL,
    -- touches (T) --
    t1_time DATETIME, t2_time DATETIME, t3_time DATETIME,   -- first touch of L1/mid/L2
    n_l1_touches INTEGER, n_mid_touches INTEGER, n_l2_touches INTEGER,
    -- retests (RT) --
    rt_count INTEGER, rt_time DATETIME,
    -- fresh vs structured --
    vr_fresh INTEGER,                                -- 1 = no close back into zone; 0 = not-fresh/structured
    -- lifecycle (R = entry->stop, asset-agnostic) --
    confirm_time DATETIME, confirm_price REAL,
    invalidation_time DATETIME, continued INTEGER, alive_at_end INTEGER, bars_alive INTEGER,
    mfe_r REAL, mae_r REAL, realized_r REAL,
    zone_key TEXT, is_primary INTEGER, superseded_by TEXT, zone_valid INTEGER,
    meta TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fob_zones_run      ON fob_zones(run_id);
CREATE INDEX IF NOT EXISTS ix_fob_zones_cycle    ON fob_zones(cycle_id);
CREATE INDEX IF NOT EXISTS ix_fob_zones_confirm  ON fob_zones(run_id, confirm_time);

-- Chronological PBO/VR/CF ledger. htf_state = per-TF live-cycle AWARENESS snapshot at bar_time
-- (causal; emitter walks all TFs in one pass). NOT an all-agree filter.
CREATE TABLE IF NOT EXISTS fob_events (
    event_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES tester_runs(run_id),
    cycle_id          INTEGER REFERENCES fob_cycles(cycle_id),
    zone_id           INTEGER REFERENCES fob_zones(zone_id),
    event_tf          TEXT NOT NULL,
    label             TEXT CHECK(label IN ('PBO','VR','HRCF','CF')),
    cf_idx            INTEGER,                        -- CF ordinal within cycle (0 for PBO/VR)
    risk_class        TEXT CHECK(risk_class IS NULL OR risk_class IN ('LOW','HIGH')),  -- LR vs HRCF
    direction         TEXT CHECK(direction IN ('BUY','SELL')),
    swing_time DATETIME, bar_time DATETIME NOT NULL,
    level REAL, bar_close REAL,
    body_clears       INTEGER,                        -- 1 = close cleared level by body (wick != count)
    vr_zone_broken    INTEGER,                        -- 1 = strong close through VR zone (reversal/FM trigger)
    htf_state         TEXT CHECK(htf_state IS NULL OR json_valid(htf_state)),  -- {MN1:{dir,cf},W1:..,D1:..,H4:..,H1:..}
    meta              TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at        DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fob_events_run     ON fob_events(run_id);
CREATE INDEX IF NOT EXISTS ix_fob_events_cycle   ON fob_events(cycle_id);
CREATE INDEX IF NOT EXISTS ix_fob_events_run_bar ON fob_events(run_id, bar_time);
"""


def main():
    now = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")  # forward FK refs during create
        print("tester_runs:")
        _add_col(conn, "tester_runs", "run_role TEXT CHECK(run_role IS NULL OR run_role IN ('emitter','trader'))")
        _add_col(conn, "tester_runs", "git_sha TEXT")
        _add_col(conn, "tester_runs", "git_dirty INTEGER")
        print("tester_trades:")
        _add_col(conn, "tester_trades", "zone_id INTEGER REFERENCES fob_zones(zone_id)")
        _add_col(conn, "tester_trades", "gross_usd REAL")
        _add_col(conn, "tester_trades", "cost_usd REAL")
        print("spine + FOB payload tables:")
        conn.executescript(SPINE_DDL)
        conn.executescript(FOB_DDL)
        conn.commit()
        # verify
        tbls = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ("tester_run_summary", "fob_cycles", "fob_zones", "fob_events"):
            assert t in tbls, f"missing {t}"
        print(f"[035] OK ({now}) — FOB payload + spine ready. tables present:",
              sorted(t for t in tbls if t.startswith(("fob_", "tester_"))))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
