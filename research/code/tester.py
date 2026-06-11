"""
Gate 7 — FIDELITY writers for research.db.

The MT5 Strategy-Tester evidence is NOT a separate database: port-fidelity is the
*last research gate* (Gate 7 — FIDELITY), so tester_runs + tester_trades live inside
research.db next to step4_results. This module owns their schema and all writes
(CLAUDE.md rule 10), mirroring pipeline.py conventions (_conn/_now/VALID_* tuples).

Flow:
    ingest_tester_run(...)        -> run_id  (run header + config provenance)
    ingest_tester_trade(run_id, ...) per closed tester round-trip (join key = session_date)
    log_fidelity_diff(run_id, ...) -> writes the diff vs the Python research result,
                                      sets fidelity_verdict, and on 'pass' calls
                                      pipeline.pass_gate(idea_id, 7, ...).

Gate 7 is what execution.register_deployment() / open_deploy_gate('FORWARD') read
before a deployment may touch a broker account.

Spec: braindump/execution_schema.md (§research.db — Gate 7 evidence) +
braindump/research_protocol.md (Gate 7 — Fidelity).
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from research.code import pipeline
except ImportError:  # running as a loose script with research/code on sys.path
    import pipeline

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
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
    ea_name         TEXT,                          -- 'baysix_orb_001'
    ea_version      TEXT,
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
    ticket           INTEGER,
    session_date     DATE,                          -- join key to the Python backtest
    direction        TEXT CHECK(direction IS NULL OR direction IN ('long','short','flat')),
    entry_ts         DATETIME,
    entry_px         REAL,
    exit_ts          DATETIME,
    exit_px          REAL,
    exit_reason      TEXT,
    risk_unit        REAL,                          -- range_w (1R)
    realized_R       REAL,
    realized_pnl_usd REAL,
    or_high          REAL,
    or_low           REAL,
    range_w          REAL,
    created_at       DATETIME NOT NULL
);
"""


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> Path:
    """Create the two Gate-7 tables in research.db. Idempotent (IF NOT EXISTS)."""
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    print(f"[tester] Gate-7 schema ready in {DB_PATH.name}")
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
    risk_unit: float = None,
    realized_R: float = None,
    realized_pnl_usd: float = None,
    ticket: int = None,
    or_high: float = None,
    or_low: float = None,
    range_w: float = None,
) -> int:
    """Record one closed tester round-trip. session_date is the join key to the
    Python backtest trade-list. Returns tt_id."""
    if direction is not None and direction not in VALID_DIRECTION:
        raise ValueError(f"direction must be one of {VALID_DIRECTION} or None")
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tester_trades
                (run_id, ticket, session_date, direction, entry_ts, entry_px,
                 exit_ts, exit_px, exit_reason, risk_unit, realized_R,
                 realized_pnl_usd, or_high, or_low, range_w, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, ticket, session_date, direction, entry_ts, entry_px,
              exit_ts, exit_px, exit_reason, risk_unit, realized_R,
              realized_pnl_usd, or_high, or_low, range_w, now))
        conn.commit()
        tt_id = cur.lastrowid
    return tt_id


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


if __name__ == "__main__":
    init_db()
