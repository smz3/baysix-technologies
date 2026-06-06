"""
Pipeline interface for research.db.
All writes go through here — no raw SQL elsewhere.

Idea functions:
  add_idea()          — insert a new idea (status=ideation)

Gate functions:
  open_gate()         — create a gate row (status=open)
  pass_gate()         — mark gate passed
  block_gate()        — mark gate blocked with reason
  kill_idea()         — kill idea at current gate

Result functions:
  log_result()        — log a metric to step4_results

Read functions:
  get_idea()          — fetch idea row
  get_gates()         — fetch all gates for an idea
  get_results()       — fetch all results for an idea
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
MYT     = timezone(timedelta(hours=8))

GATE_QUESTIONS = {
    0: "Do we know the model's mathematical truth from the literature?",
    1: "What is the simple human-readable rule and null hypothesis?",
    2: "Does the simplest possible implementation produce sane output?",
    3: "Does the dumb rule from Gate 1 have any edge, raw and after costs?",
    4: "Does the sophisticated model confirm or challenge the baseline?",
    5: "Is there a tradeable signal with positive net edge?",
    6: "Does the edge survive walk-forward and out-of-sample?",
}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


# ── Idea functions ─────────────────────────────────────────────────────────────

def add_idea(
    idea_id: str,
    name: str,
    description: str,
    category: str,
    parent_idea_id: str | None = None,
) -> str:
    """Insert a new idea into step1_ideas at status='ideation'. Returns idea_id."""
    now = _now()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO step1_ideas
                (idea_id, name, description, category, parent_idea_id,
                 status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'ideation', ?, ?)
        """, (idea_id, name, description, category, parent_idea_id, now, now))
        conn.commit()
    print(f"[pipeline] idea added: {idea_id} ({category})")
    return idea_id


# ── Gate functions ─────────────────────────────────────────────────────────────

def open_gate(
    idea_id: str,
    gate_number: int,
    pass_criteria: str,
    attempt: int = 1,
) -> int:
    """Create a gate row at status=open. Returns gate_id."""
    if gate_number not in range(7):
        raise ValueError(f"gate_number must be 0–6, got {gate_number}")

    _check_previous_gate_passed(idea_id, gate_number)

    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO step3_gates
                (idea_id, gate_number, attempt, gate_question, pass_criteria,
                 status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
        """, (idea_id, gate_number, attempt,
              GATE_QUESTIONS[gate_number], pass_criteria, now, now))
        conn.commit()
        gate_id = cur.lastrowid

    _update_idea_status(idea_id, f"gate_{gate_number}")
    print(f"[pipeline] {idea_id} gate {gate_number} attempt {attempt}: opened")
    return gate_id


def pass_gate(
    idea_id: str,
    gate_number: int,
    gate_answer: str,
    answered_by: str = "human",
    attempt: int = 1,
) -> None:
    """Mark a gate as passed."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE step3_gates
            SET status='passed', gate_answer=?, answered_by=?,
                updated_at=?, answered_at=?
            WHERE idea_id=? AND gate_number=? AND attempt=?
        """, (gate_answer, answered_by, now, now, idea_id, gate_number, attempt))
        if cur.rowcount == 0:
            raise ValueError(f"Gate not found: {idea_id} gate={gate_number} attempt={attempt}")
        conn.commit()
    print(f"[pipeline] {idea_id} gate {gate_number}: PASSED")


def block_gate(
    idea_id: str,
    gate_number: int,
    gate_answer: str,
    answered_by: str = "human",
    attempt: int = 1,
) -> None:
    """Mark a gate as blocked with a reason."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE step3_gates
            SET status='blocked', gate_answer=?, answered_by=?,
                updated_at=?, answered_at=?
            WHERE idea_id=? AND gate_number=? AND attempt=?
        """, (gate_answer, answered_by, now, now, idea_id, gate_number, attempt))
        if cur.rowcount == 0:
            raise ValueError(f"Gate not found: {idea_id} gate={gate_number} attempt={attempt}")
        conn.commit()
    print(f"[pipeline] {idea_id} gate {gate_number}: BLOCKED — {gate_answer[:80]}")


def kill_idea(
    idea_id: str,
    gate_number: int,
    kill_reason: str,
    answered_by: str = "human",
    attempt: int = 1,
) -> None:
    """Kill an idea at a gate. Updates both gate row and idea row."""
    now = _now()
    with _conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            UPDATE step3_gates
            SET status='killed', gate_answer=?, answered_by=?,
                updated_at=?, answered_at=?
            WHERE idea_id=? AND gate_number=? AND attempt=?
        """, (kill_reason, answered_by, now, now, idea_id, gate_number, attempt))

        cur.execute("""
            UPDATE step1_ideas
            SET status='killed', kill_gate=?, kill_reason=?,
                killed_at=?, updated_at=?
            WHERE idea_id=?
        """, (gate_number, kill_reason, now, now, idea_id))

        conn.commit()
    print(f"[pipeline] {idea_id} gate {gate_number}: KILLED — {kill_reason[:80]}")


# ── Result logging ─────────────────────────────────────────────────────────────

def log_result(
    idea_id: str,
    gate_number: int,
    stage: str,
    metric_key: str,
    metric_value: float,
    cost_adjusted: int,
    period: str,
    n_obs: int,
    data_start: str,
    data_end: str,
    git_sha: str,
    code_path: str,
    n_trials: int = None,
    trial_family_id: str = None,
    instrument: str = "XAUUSD",
    parameters: str = None,
    data_hash: str = None,
    seed: int = None,
    notes: str = None,
) -> int:
    """Log a metric result. Returns result_id."""
    valid_stages  = ("IS", "walkforward", "montecarlo", "OOS")
    valid_periods = ("per_trade", "daily", "annualised")

    if stage not in valid_stages:
        raise ValueError(f"stage must be one of {valid_stages}")
    if period not in valid_periods:
        raise ValueError(f"period must be one of {valid_periods}")
    if cost_adjusted not in (0, 1):
        raise ValueError("cost_adjusted must be 0 (raw) or 1 (net)")
    if not git_sha:
        raise ValueError("git_sha is required — run `git rev-parse --short HEAD`")
    if not n_obs:
        raise ValueError("n_obs is required")

    now = _now()
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO step4_results
                (idea_id, gate_number, stage, metric_key, metric_value,
                 cost_adjusted, period, n_obs, n_trials, trial_family_id,
                 instrument, data_start, data_end, parameters,
                 git_sha, data_hash, seed, code_path, notes, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idea_id, gate_number, stage, metric_key, metric_value,
            cost_adjusted, period, n_obs, n_trials, trial_family_id,
            instrument, data_start, data_end, parameters,
            git_sha, data_hash, seed, code_path, notes, now,
        ))
        conn.commit()
        result_id = cur.lastrowid

    label = "net" if cost_adjusted else "raw"
    print(f"[pipeline] {idea_id} gate={gate_number} {stage} {metric_key}={metric_value} [{label}|{period}]")
    return result_id


# ── Read functions ─────────────────────────────────────────────────────────────

def get_idea(idea_id: str) -> dict:
    """Return the idea row as a dict. Empty dict if not found."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM step1_ideas WHERE idea_id=?", (idea_id,))
        row = cur.fetchone()
        return dict(row) if row else {}


def get_gates(idea_id: str) -> list[dict]:
    """Return all gate rows for an idea, ordered by gate_number then attempt."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM step3_gates WHERE idea_id=? ORDER BY gate_number, attempt",
            (idea_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_results(idea_id: str) -> list[dict]:
    """Return all result rows for an idea, ordered by gate_number then logged_at."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM step4_results WHERE idea_id=? ORDER BY gate_number, logged_at",
            (idea_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_lifecycle() -> list[dict]:
    """Return the idea_lifecycle view — one row per idea."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM idea_lifecycle ORDER BY idea_id")
        return [dict(r) for r in cur.fetchall()]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _check_previous_gate_passed(idea_id: str, gate_number: int) -> None:
    """Raise if gate N-1 is not passed (skip check for gate 0)."""
    if gate_number == 0:
        return
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT status FROM step3_gates
            WHERE idea_id=? AND gate_number=?
            ORDER BY attempt DESC LIMIT 1
        """, (idea_id, gate_number - 1))
        row = cur.fetchone()
        if not row or row["status"] != "passed":
            raise ValueError(
                f"Cannot open gate {gate_number}: gate {gate_number - 1} is not passed"
            )


def _update_idea_status(idea_id: str, new_status: str) -> None:
    now = _now()
    with _conn() as conn:
        conn.execute(
            "UPDATE step1_ideas SET status=?, updated_at=? WHERE idea_id=?",
            (new_status, now, idea_id)
        )
        conn.commit()
