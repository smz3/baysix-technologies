"""Trial-family ledger for research.db (trial_family + step4_results trial rows).

The N_trials ledger (López de Prado). When you SWEEP configs and SELECT a winner,
every config you tried is a researcher degree of freedom that inflates the
in-sample Sharpe of the winner. The Deflated Sharpe Ratio (Bailey & López de
Prado) penalises this: it needs N = number of configs tried and V[SR_n] =
variance of the per-config Sharpe across the family. This module is where that
ledger lives so gate5_report can run a TRUE DSR instead of silently degrading to
PSR(sr_benchmark=0). (ADR 2026-06-15 §24/§52; tasks 87/88.)

Each swept config logs a step4_results row (metric_key='trial_sharpe',
trial_family_id=<family>, config_hash=<cfg>) — the immutable per-config record.
The trial_family row CACHES the derived N (n_configs) and V[SR_n] (var_sr),
recomputed from those rows on every log_trial.

Write:
  open_family()     — create/upsert a trial family for one selection decision
  log_trial()       — record one tried config's per-period Sharpe (+ step4_results row)
  select_config()   — mark the winning config_hash
Read:
  read_family()     — full family row as dict, or None
  deflation_inputs()— (n_trials, var_sr) for gate5_report; (0, None) if no family

All writes go through here / pipeline.log_result — no raw SQL elsewhere (rule 10).
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
MYT     = timezone(timedelta(hours=8))

TRIAL_METRIC = "trial_sharpe"  # metric_key for a swept config's per-period Sharpe


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def _pipeline():
    """Lazy handle on pipeline (dual path: package vs own-dir script)."""
    try:
        from research.code import pipeline
    except ImportError:
        import pipeline
    return pipeline


# ── Write ────────────────────────────────────────────────────────────────────

def open_family(
    family_id: str,
    idea_id: str,
    description: str = None,
    data_start: str = None,
    data_end: str = None,
) -> str:
    """Create (or update metadata of) a trial family. One row per selection
    decision — the family of configs you compared before picking one."""
    now = _now()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO trial_family
                (family_id, idea_id, description, n_configs, var_sr,
                 selected_config_hash, data_start, data_end, created_at, updated_at)
            VALUES (?, ?, ?, 0, NULL, NULL, ?, ?, ?, ?)
            ON CONFLICT(family_id) DO UPDATE SET
                description = COALESCE(excluded.description, trial_family.description),
                data_start  = COALESCE(excluded.data_start,  trial_family.data_start),
                data_end    = COALESCE(excluded.data_end,    trial_family.data_end),
                updated_at  = excluded.updated_at
            """,
            (family_id, idea_id, description, data_start, data_end, now, now),
        )
        conn.commit()
    print(f"[trial_family] open {family_id} (idea={idea_id})")
    return family_id


def log_trial(
    family_id: str,
    idea_id: str,
    config_hash: str,
    sharpe: float,
    n_obs: int,
    git_sha: str,
    code_path: str,
    *,
    gate_number: int = 5,
    stage: str = "IS",
    cost_adjusted: int = 1,
    period: str = "per_trade",
    parameters: str = None,
    instrument: str = "XAUUSD",
    data_start: str = None,
    data_end: str = None,
    seed: int = None,
    notes: str = None,
) -> int:
    """Record ONE tried config's per-period Sharpe. Writes an immutable
    step4_results trial row (metric_key='trial_sharpe') then recomputes the
    family's n_configs + var_sr. cost_adjusted defaults to 1 (net) — keep all
    configs in a family on the SAME cost basis so V[SR] is meaningful.
    Returns result_id."""
    result_id = _pipeline().log_result(
        idea_id=idea_id,
        gate_number=gate_number,
        stage=stage,
        metric_key=TRIAL_METRIC,
        metric_value=float(sharpe),
        cost_adjusted=cost_adjusted,
        period=period,
        n_obs=n_obs,
        data_start=data_start,
        data_end=data_end,
        git_sha=git_sha,
        code_path=code_path,
        trial_family_id=family_id,
        config_hash=config_hash,
        instrument=instrument,
        parameters=parameters,
        seed=seed,
        notes=notes,
    )
    recompute_family(family_id)
    return result_id


def recompute_family(family_id: str) -> dict:
    """Recompute n_configs (N) and var_sr (V[SR_n], sample variance ddof=1) from
    the family's logged trial rows. Upserts the cache on trial_family."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT metric_value FROM step4_results "
            "WHERE trial_family_id=? AND metric_key=?",
            (family_id, TRIAL_METRIC),
        ).fetchall()
        sharpes = [r[0] for r in rows if r[0] is not None]
        n = len(sharpes)
        var = float(np.var(sharpes, ddof=1)) if n >= 2 else None
        cur = conn.execute(
            "UPDATE trial_family SET n_configs=?, var_sr=?, updated_at=? WHERE family_id=?",
            (n, var, _now(), family_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"no trial_family {family_id!r} — call open_family first")
    return {"n_configs": n, "var_sr": var}


def select_config(family_id: str, config_hash: str) -> None:
    """Mark the winning config_hash (the one promoted out of the sweep)."""
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE trial_family SET selected_config_hash=?, updated_at=? WHERE family_id=?",
            (config_hash, _now(), family_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"no trial_family {family_id!r} — call open_family first")


# ── Read ─────────────────────────────────────────────────────────────────────

def read_family(family_id: str) -> dict | None:
    """Full family row as a dict, or None if it does not exist."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM trial_family WHERE family_id=?", (family_id,)
        ).fetchone()
        return dict(row) if row else None


def deflation_inputs(family_id: str) -> tuple:
    """(n_trials, var_sr) for gate5_report.evaluate_pnl. Returns (0, None) when
    the family is absent or has fewer than 2 configs — the caller then runs PSR,
    not DSR, and the report says so honestly."""
    fam = read_family(family_id)
    if not fam:
        return (0, None)
    return (fam["n_configs"] or 0, fam["var_sr"])
