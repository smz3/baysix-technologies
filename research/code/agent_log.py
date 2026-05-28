"""
Agent log interface for agent_log.db.
All writes go through here — no raw SQL elsewhere.

Write functions:
  log_agent_call()     — GENERATE or VALIDATE gear
  log_dissect_result() — DISSECT gear (atomic: inserts agent_calls + updates papers_consulted)
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "agent_log.db"
MYT = timezone(timedelta(hours=8))

_VALID_MODELS = ("sonnet", "opus")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d/%H:%M:%S")


def log_agent_call(
    idea_id: int,
    idea_code: str,
    gear: str,
    model: str,
    task: str,
) -> int:
    """
    Log a GENERATE or VALIDATE agent call.
    For DISSECT use log_dissect_result() — it atomically updates papers_consulted too.

    idea_id   : required — links to idea in ideas_log.db
    idea_code : required — e.g. "HMM-001"
    gear      : "GENERATE" or "VALIDATE"
    model     : "sonnet" or "opus"
    task      : one-line description of what was asked

    Returns the new agent_call id.
    """
    if gear == "DISSECT":
        raise ValueError("Use log_dissect_result() for DISSECT — it atomically updates papers_consulted too.")
    if gear not in ("GENERATE", "VALIDATE"):
        raise ValueError("gear must be 'GENERATE' or 'VALIDATE'")
    if model not in _VALID_MODELS:
        raise ValueError(f"model must be one of {_VALID_MODELS}")

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO agent_calls (idea_id, idea_code, gear, model, task, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (idea_id, idea_code, gear, model, task, _now()),
        )
        conn.commit()
        call_id = cur.lastrowid
        print(f"[agent_log] call id={call_id} [{gear}|{model}] {idea_code} — {task}")
        return call_id


def log_dissect_result(
    idea_id: int,
    idea_code: str,
    paper_id: int,
    model: str,
    task: str,
    key_equations: str,
    empirical_findings: str,
    context_fit: str,
    limitations: str,
) -> int:
    """
    Atomic DISSECT writer.
    Inserts one agent_calls row AND updates the matching papers_consulted row in one transaction.
    Raises ValueError immediately if paper_id does not exist.

    idea_id           : required — links to idea in ideas_log.db
    idea_code         : required — e.g. "HMM-001"
    paper_id          : required — papers_consulted.id to mark dissected
    model             : "sonnet" or "opus"
    task              : one-line description, e.g. "Dissect arXiv:2006.08307"
    key_equations     : [§X.X]-anchored equations
    empirical_findings: [§X.X]-anchored numbers and results
    context_fit       : asset/frequency comparison block
    limitations       : [§X.X]-anchored limitations

    Returns the new agent_call id.
    """
    if model not in _VALID_MODELS:
        raise ValueError(f"model must be one of {_VALID_MODELS}")

    with _conn() as conn:
        cur = conn.cursor()

        cur.execute("SELECT id FROM papers_consulted WHERE id=?", (paper_id,))
        if cur.fetchone() is None:
            raise ValueError(f"paper_id={paper_id} not found in papers_consulted")

        ts = _now()
        cur.execute(
            "INSERT INTO agent_calls (idea_id, idea_code, gear, model, task, timestamp) VALUES (?, ?, 'DISSECT', ?, ?, ?)",
            (idea_id, idea_code, model, task, ts),
        )
        call_id = cur.lastrowid

        cur.execute(
            """UPDATE papers_consulted
               SET dissected=1, key_equations=?, empirical_findings=?, context_fit=?, limitations=?, agent_call_id=?
               WHERE id=?""",
            (key_equations, empirical_findings, context_fit, limitations, call_id, paper_id),
        )

        conn.commit()
        print(f"[agent_log] DISSECT id={call_id} [{model}] {idea_code} paper_id={paper_id} — {task}")
        return call_id


def get_papers_for_idea(idea_code: str) -> list:
    """Return all papers_consulted rows linked to a given idea code."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT p.* FROM papers_consulted p
               JOIN agent_calls a ON p.agent_call_id = a.id
               WHERE a.idea_code = ?""",
            (idea_code,),
        )
        return [dict(r) for r in cur.fetchall()]
