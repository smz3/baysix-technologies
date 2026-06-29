"""
Gate 7 — FIDELITY writers for research.db.

The MT5 Strategy-Tester evidence is NOT a separate database: port-fidelity is the
*last research gate* (Gate 7 — FIDELITY), so tester_runs + tester_trades live inside
research.db next to step4_results. This module owns their schema and all writes
(CLAUDE.md rule 10), mirroring pipeline.py conventions (_conn/_now/VALID_* tuples).

Flow:
    ingest_tester_run(...)        -> run_id  (run header + config provenance)
    ingest_tester_trade(run_id, ...) per closed tester round-trip (join key = ticket + entry_ts)
    log_fidelity_diff(run_id, ...) -> writes the diff vs the Python research result,
                                      sets fidelity_verdict, and on 'pass' calls
                                      pipeline.pass_gate(idea_id, 7, ...).

Gate 7 is what execution.register_deployment() / open_deploy_gate('FORWARD') read
before a deployment may touch a broker account.

Spec: docs/reference/execution_schema.md (§research.db — Gate 7 evidence) +
docs/reference/research_protocol.md (Gate 7 — Fidelity).
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root for run-as-script
from research.code.gates import pipeline

DB_PATH = Path(__file__).parents[2] / "db" / "research.db"
MYT     = timezone(timedelta(hours=8))

# Provenance enums — where the ticks came from + how MT5 modelled them.
VALID_DATA_SOURCE    = ("dukascopy", "broker_history", "custom")
VALID_TESTER_MODEL   = ("real_ticks", "every_tick", "1min_ohlc", "open_only")
VALID_DIRECTION      = ("long", "short", "flat")
VALID_FIDELITY       = ("pass", "fail", "pending")


_SCHEMA = """
-- Gate 7 (FIDELITY) evidence — lives in research.db next to step4_results.
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
    rt_count INTEGER, rt_time DATETIME,
    vr_fresh INTEGER,
    confirm_time DATETIME, confirm_price REAL,
    invalidation_time DATETIME, continued INTEGER, alive_at_end INTEGER, bars_alive INTEGER,
    mfe_r REAL, mae_r REAL, realized_r REAL,
    zone_key TEXT, is_primary INTEGER, superseded_by TEXT, zone_valid INTEGER,
    meta TEXT CHECK(meta IS NULL OR json_valid(meta)),
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fob_zones_run     ON fob_zones(run_id);
CREATE INDEX IF NOT EXISTS ix_fob_zones_cycle   ON fob_zones(cycle_id);
CREATE INDEX IF NOT EXISTS ix_fob_zones_confirm ON fob_zones(run_id, confirm_time);

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
"""


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> Path:
    """Create the Gate-7 + BRC tables in research.db. Idempotent (IF NOT EXISTS)."""
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    print(f"[tester] tester schema ready in {DB_PATH.name} (tester_runs/trades/zones)")
    return DB_PATH


# ── Run header ────────────────────────────────────────────────────────────────
def ingest_tester_run(
    idea_id: str,
    symbol: str,
    data_source: str,
    ea_name: str = None,
    ea_version: str = None,
    model_quality: str = None,
    tester_model: str = None,
    timeframe: str = None,
    period_start: str = None,
    period_end: str = None,
    tz_offset_hours: int = None,
    magic_number: int = None,
    initial_deposit: float = None,
    leverage: int = None,
    spread_setting: str = None,
    params: dict = None,
    n_trades: int = None,
    net_profit_usd: float = None,
    profit_factor: float = None,
    max_dd_pct: float = None,
    win_rate: float = None,
    notes: str = None,
) -> int:
    """Open a Strategy-Tester run with its data provenance + run-level summary.
    idea_id is soft-validated against research.db. Returns run_id. The FIDELITY diff
    columns are filled later via log_fidelity_diff()."""
    if not pipeline.get_idea(idea_id):
        raise ValueError(f"idea_id '{idea_id}' not found in research.db — register the idea first")
    if data_source not in VALID_DATA_SOURCE:
        raise ValueError(f"data_source must be one of {VALID_DATA_SOURCE}")
    if tester_model is not None and tester_model not in VALID_TESTER_MODEL:
        raise ValueError(f"tester_model must be one of {VALID_TESTER_MODEL} or None")
    params_json = json.dumps(params) if params is not None else None
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tester_runs
                (idea_id, ea_name, ea_version, symbol, data_source, model_quality,
                 tester_model, timeframe, period_start, period_end, tz_offset_hours,
                 magic_number, initial_deposit, leverage, spread_setting, params,
                 n_trades, net_profit_usd, profit_factor, max_dd_pct, win_rate,
                 notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (idea_id, ea_name, ea_version, symbol, data_source, model_quality,
              tester_model, timeframe, period_start, period_end, tz_offset_hours,
              magic_number, initial_deposit, leverage, spread_setting, params_json,
              n_trades, net_profit_usd, profit_factor, max_dd_pct, win_rate,
              notes, now, now))
        conn.commit()
        run_id = cur.lastrowid
    print(f"[tester] run #{run_id} {idea_id} {symbol} [{data_source}/{tester_model}] n={n_trades}")
    return run_id


def ingest_tester_trade(
    run_id: int,
    session_date: str = None,
    direction: str = None,
    entry_ts: str = None,
    entry_px: float = None,
    exit_ts: str = None,
    exit_px: float = None,
    exit_reason: str = None,
    lots: float = None,
    risk_unit: float = None,
    realized_R: float = None,
    realized_pnl_usd: float = None,
    ticket: int = None,
    meta: dict = None,
) -> int:
    """Record one closed tester round-trip. Cross-system join key = ticket + entry_ts
    (session_date is a nullable convenience for daily strategies). risk_unit is the
    generic 1R denominator (price units); strategy-specific context (ORB: or_high/
    or_low/range_w) goes in `meta` as JSON. Returns tt_id."""
    if direction is not None and direction not in VALID_DIRECTION:
        raise ValueError(f"direction must be one of {VALID_DIRECTION} or None")
    meta_json = json.dumps(meta) if meta is not None else None
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tester_trades
                (run_id, ticket, session_date, direction, entry_ts, entry_px,
                 exit_ts, exit_px, exit_reason, lots, risk_unit, realized_R,
                 realized_pnl_usd, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, ticket, session_date, direction, entry_ts, entry_px,
              exit_ts, exit_px, exit_reason, lots, risk_unit, realized_R,
              realized_pnl_usd, meta_json, now))
        conn.commit()
        tt_id = cur.lastrowid
    return tt_id


# ── BRC zone-lifecycle ingest (task 119) ───────────────────────────────────────
_ZONE_COLS = [
    "csv_zone_id", "tf", "direction",
    "p1_time", "p1_price", "p2_time", "p2_price", "p3_time", "p3_price",
    "p4_time", "p4_price", "p5_time", "p5_price",
    "l1", "l2", "mid", "break_kind",
    "t1_time", "t2_time", "t3_time", "confirm_time", "invalidation_time",
    "alive_at_end", "continued", "mfe_r", "mae_r", "realized_r", "bars_alive",
    "seq", "zone_key", "is_primary", "consolidated_into",
]
_ZONE_TIME_COLS  = {"p1_time", "p2_time", "p3_time", "p4_time", "p5_time",
                    "t1_time", "t2_time", "t3_time", "confirm_time", "invalidation_time"}
_ZONE_INT_COLS   = {"csv_zone_id", "alive_at_end", "continued", "bars_alive",
                    "seq", "is_primary"}
_ZONE_FLOAT_COLS = {"p1_price", "p2_price", "p3_price", "p4_price", "p5_price",
                    "l1", "l2", "mid", "mfe_r", "mae_r", "realized_r"}


def _norm_ts(s: str):
    """'YYYY.MM.DD HH:MM:SS' -> 'YYYY-MM-DD HH:MM:SS'; '' (0-sentinel) -> None.
    Only the date part carries dots (time uses ':'), so a blanket '.'→'-' is safe."""
    s = (s or "").strip()
    return s.replace(".", "-") if s else None


def ingest_brc_zones(run_id: int, csv_path) -> int:
    """Bulk-load a brc_csv.mqh lifecycle CSV (UTF-8, header, comma) into tester_zones
    under an existing tester_runs header. Returns the number of zone rows inserted.
    Re-ingesting the same run_id is blocked (delete the run's rows first to redo)."""
    import csv as _csv
    csv_path = Path(csv_path)
    if not get_tester_run(run_id):
        raise ValueError(f"tester run not found: {run_id} — create the run header first")
    with _conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM tester_zones WHERE run_id=?",
                                (run_id,)).fetchone()[0]
        if existing:
            raise ValueError(f"run #{run_id} already has {existing} zones — "
                             f"delete them before re-ingesting")

    now = _now()
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = _csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        # source header uses 'zone_id'; map it to csv_zone_id
        if "zone_id" not in header:
            raise ValueError(f"unexpected CSV header (no zone_id): {reader.fieldnames}")
        for r in reader:
            rec = {"csv_zone_id": r["zone_id"], "run_id": run_id, "created_at": now}
            for col in _ZONE_COLS:
                if col == "csv_zone_id":
                    continue
                v = r.get(col, "")
                if col in _ZONE_TIME_COLS:
                    rec[col] = _norm_ts(v)
                elif col in _ZONE_INT_COLS:
                    rec[col] = int(v) if str(v).strip() != "" else None
                elif col in _ZONE_FLOAT_COLS:
                    rec[col] = float(v) if str(v).strip() != "" else None
                else:
                    rec[col] = (v.strip() or None)
            rows.append(rec)

    cols = ["run_id"] + _ZONE_COLS + ["created_at"]
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO tester_zones ({', '.join(cols)}) VALUES ({placeholders})"
    with _conn() as conn:
        conn.executemany(sql, [tuple(rec[c] for c in cols) for rec in rows])
        conn.commit()
    print(f"[tester] run #{run_id} ingested {len(rows)} BRC zones from {csv_path.name}")
    return len(rows)


def log_fidelity_diff(
    run_id: int,
    research_result_id: int,
    trade_overlap_pct: float,
    ER_delta_vs_research: float,
    R_corr: float,
    verdict: str,
    gate_answer: str = None,
    answered_by: str = "human",
    allow_incomplete: bool = False,
) -> None:
    """Write the FIDELITY diff against the Python research result and set the verdict.

    On verdict='pass' this calls pipeline.pass_gate(idea_id, 7, ...) — the precondition
    execution.register_deployment() / open_deploy_gate('FORWARD') read. On 'fail' it
    blocks Gate 7 (the port is not the validated strategy). Pre-commit the equivalence
    thresholds before computing the diff (gate_answer should record them + the numbers)."""
    if verdict not in VALID_FIDELITY:
        raise ValueError(f"verdict must be one of {VALID_FIDELITY}")
    run = get_tester_run(run_id)
    if not run:
        raise ValueError(f"tester run not found: {run_id}")
    idea_id = run["idea_id"]
    now = _now()
    with _conn() as conn:
        conn.execute("""
            UPDATE tester_runs
            SET research_result_id=?, trade_overlap_pct=?, ER_delta_vs_research=?,
                R_corr=?, fidelity_verdict=?, updated_at=?
            WHERE run_id=?
        """, (research_result_id, trade_overlap_pct, ER_delta_vs_research, R_corr,
              verdict, now, run_id))
        conn.commit()
    answer = gate_answer or (
        f"FIDELITY {verdict}: overlap={trade_overlap_pct}%, "
        f"ER_delta={ER_delta_vs_research}, R_corr={R_corr} (run #{run_id})"
    )
    print(f"[tester] run #{run_id} FIDELITY diff: {verdict} "
          f"(overlap={trade_overlap_pct}%, ER_delta={ER_delta_vs_research}, R_corr={R_corr})")
    # Drive the research gate from the verdict.
    if verdict == "pass":
        if not _gate7_open(idea_id):
            pipeline.open_gate(idea_id, 7,
                               pass_criteria="overlap>=95%, E[R]/win/$per-t in research 95% CI, high R_corr")
        pipeline.pass_gate(idea_id, 7, answer, answered_by=answered_by,
                           allow_incomplete=allow_incomplete)
    elif verdict == "fail":
        if not _gate7_open(idea_id):
            pipeline.open_gate(idea_id, 7,
                               pass_criteria="overlap>=95%, E[R]/win/$per-t in research 95% CI, high R_corr")
        pipeline.block_gate(idea_id, 7, answer, answered_by=answered_by)


def _gate7_open(idea_id: str) -> bool:
    """True if a Gate-7 row already exists for this idea (any status)."""
    return any(g["gate_number"] == 7 for g in pipeline.get_gates(idea_id))


def get_tester_run(run_id: int) -> dict:
    """Return the tester_runs row as a dict (empty if not found)."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tester_runs WHERE run_id=?", (run_id,)).fetchone()
    return dict(row) if row else {}


def gate7_passed(idea_id: str) -> bool:
    """True iff Gate 7 (FIDELITY) is 'passed' for this idea — the live-side gate that
    execution.py checks before a deployment may exist."""
    gates = pipeline.get_gates(idea_id)
    return any(g["gate_number"] == 7 and g["status"] == "passed" for g in gates)


def delete_run(run_id: int, drop_run_row: bool = True) -> dict:
    """Hard-delete one emitter/trader run's data from research.db: its payload
    (tester_zones [BRC] + fob_cycles/fob_events/fob_zones [FOB]), tester_trades,
    tester_run_summary, and (optionally) the tester_runs row itself. Returns the
    deleted-row counts. Destructive + irreversible — caller must have explicit human
    authorization (CLAUDE.md rule 2). Re-emit + re-ingest to restore."""
    with _conn() as conn:
        meta = conn.execute(
            "SELECT idea_id, ea_name FROM tester_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        # FOB payload: events/zones reference cycles -> delete children first
        fe = conn.execute("DELETE FROM fob_events WHERE run_id=?", (run_id,)).rowcount
        fz = conn.execute("DELETE FROM fob_zones  WHERE run_id=?", (run_id,)).rowcount
        fc = conn.execute("DELETE FROM fob_cycles WHERE run_id=?", (run_id,)).rowcount
        z = conn.execute("DELETE FROM tester_zones WHERE run_id=?", (run_id,)).rowcount
        t = conn.execute("DELETE FROM tester_trades WHERE run_id=?", (run_id,)).rowcount
        conn.execute("DELETE FROM tester_run_summary WHERE run_id=?", (run_id,))
        r = 0
        if drop_run_row:
            r = conn.execute("DELETE FROM tester_runs WHERE run_id=?", (run_id,)).rowcount
        conn.commit()
    out = {"run_id": run_id, "idea_id": meta["idea_id"] if meta else None,
           "ea_name": meta["ea_name"] if meta else None,
           "zones_deleted": z, "fob_zones_deleted": fz, "fob_events_deleted": fe,
           "fob_cycles_deleted": fc, "trades_deleted": t, "run_rows_deleted": r}
    print(f"[tester] delete_run {run_id} ({out['idea_id']}/{out['ea_name']}): "
          f"brc_zones={z} fob(c/z/e)={fc}/{fz}/{fe} trades={t} run_row={r}")
    return out


if __name__ == "__main__":
    init_db()
