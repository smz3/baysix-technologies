"""runs — the code-layer writer for the `runs` registry (task 356, migration 042).

WHAT A RUN ROW IS
One backtest. It answers "what is this folder" for exactly one folder under
`research/outputs/`, and it is the only legal way to write the table — raw SQL on
baysix.db is banned (CLAUDE.md rule 10).

GENERIC BY CONSTRUCTION
`platform` is a column, not a table name. MT5, NinjaTrader and IBKR all file here.
The ledger carries SHAPES, never STRATEGIES (adopted 2026-08-16, strategy_log 125-127):
a new strategy files a row, it does not get a migration.

THE PATH AND THE ROW ARE ONE THING
`open_run()` calls `outputs.run_dir()` and stores the result on `output_dir`, so the
folder is created by the same call that registers it. That is the whole point of doing
tasks 349 and 356 together — a folder that exists without a row, or a row without a
folder, is the state this pair was built to make impossible.

trial_family_id / n_trials
They belong on the SEARCH, which is this row, not on `step4_results`, which is one row
per METRIC and lets the copies disagree. The columns on step4_results are untouched —
whether the 5 existing GRW values get back-filled up here is task 364 call 3 (Syafiq's,
undecided), so nothing back-fills automatically.
"""
from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from research.code.infra.db_path import DB_PATH
from research.code.infra import db_guard
from research.code.infra import outputs

MYT = timezone(timedelta(hours=8))
REPO = Path(__file__).resolve().parents[3]

_VALID_PLATFORM = ("MT5", "NinjaTrader", "IBKR")
_VALID_STAGE = ("IS", "OOS", "WF", "smoke")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    # Declares this a legitimate writer to the spine tables (migration 045).
    # Without it every INSERT/UPDATE/DELETE here fails to compile.
    return db_guard.arm(conn, reason=__name__)


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def _git_sha() -> str:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not sha:
        raise RuntimeError("could not read git HEAD sha")
    return sha


def open_run(platform: str, stage: str, symbol: str, idea_id: str = None,
             version: str = None, data_start: str = None, data_end: str = None,
             git_sha: str = None, trial_family_id: str = None,
             n_trials: int = None, notes: str = None,
             make_dir: bool = True) -> dict:
    """Register a backtest and create its output folder. Returns the row as a dict.

    git_sha defaults to the current HEAD, because a run whose code version is unknown
    cannot be reproduced and is not evidence.
    """
    if platform not in _VALID_PLATFORM:
        raise ValueError(f"platform must be one of {_VALID_PLATFORM} (got {platform!r})")
    if stage not in _VALID_STAGE:
        raise ValueError(f"stage must be one of {_VALID_STAGE} (got {stage!r})")
    if not symbol:
        raise ValueError("symbol is required")
    sha = git_sha or _git_sha()
    now = _now()

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO runs
                (platform, idea_id, stage, symbol, version, data_start, data_end,
                 git_sha, trial_family_id, n_trials, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (platform, idea_id, stage, symbol, version, data_start, data_end,
              sha, trial_family_id, n_trials, notes, now))
        run_id = cur.lastrowid

        out = outputs.run_dir(run_id, idea_id, create=make_dir)
        conn.execute("UPDATE runs SET output_dir=? WHERE run_id=?",
                     (outputs.rel(out), run_id))
        conn.commit()

    print(f"[runs] run_id={run_id} [{platform}|{stage}] {symbol} -> {outputs.rel(out)}")
    return get_run(run_id)


def set_trials(run_id: int, trial_family_id: str, n_trials: int) -> None:
    """Record how many configs the search behind this run has burned."""
    with _conn() as conn:
        conn.execute(
            "UPDATE runs SET trial_family_id=?, n_trials=? WHERE run_id=?",
            (trial_family_id, n_trials, run_id))
        conn.commit()


def attach_results(run_id: int, result_ids: list[int]) -> int:
    """Point existing step4_results rows at the run that produced them (migration 043).

    SQLite could not add the FK constraint to an existing table, so this function IS the
    enforcement: it refuses unknown run_ids rather than writing a dangling reference.
    Returns the number of rows linked.
    """
    if get_run(run_id) is None:
        raise ValueError(f"run_id={run_id} does not exist — refusing a dangling link")
    if not result_ids:
        return 0
    with _conn() as conn:
        marks = ",".join("?" * len(result_ids))
        found = conn.execute(
            f"SELECT COUNT(*) FROM step4_results WHERE result_id IN ({marks})",
            result_ids).fetchone()[0]
        if found != len(result_ids):
            raise ValueError(
                f"{len(result_ids) - found} of the given result_ids do not exist")
        cur = conn.execute(
            f"UPDATE step4_results SET run_id=? WHERE result_id IN ({marks})",
            [run_id, *result_ids])
        conn.commit()
        return cur.rowcount


def get_run(run_id: int) -> dict | None:
    with _conn() as conn:
        r = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(r) if r else None


def get_runs(platform: str = None, idea_id: str = None,
             trial_family_id: str = None) -> list[dict]:
    """Runs, newest first. Filter by platform to keep systems from mixing (rule 5)."""
    q, params = "SELECT * FROM runs WHERE 1=1", []
    for col, val in (("platform", platform), ("idea_id", idea_id),
                     ("trial_family_id", trial_family_id)):
        if val is not None:
            q += f" AND {col}=?"
            params.append(val)
    q += " ORDER BY run_id DESC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
