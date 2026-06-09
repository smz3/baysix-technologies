"""
Agent log interface for research.db (step2_papers + log_agent).
All writes go through here — no raw SQL elsewhere.

Write functions:
  log_agent_call()      — GENERATE or VALIDATE gear (QR agent calls)
  log_dissect_result()  — DISSECT gear (atomic: inserts agent log + updates step2_papers)
  log_human_decision()  — human-Claude architecture/methodology decisions (replaces generate_calls)

Validation:
  validate_dissect_fields() — called automatically inside log_dissect_result().
                              Raises ValueError before any DB write if format is wrong.
"""

import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "research.db"
MYT     = timezone(timedelta(hours=8))

_VALID_MODELS = ("sonnet", "opus")

_CONTEXT_FIT_HEADERS = [
    "**Paper asset:**",
    "**Paper frequency:**",
    "**Target asset:**",
    "**Frequency match:**",
    "**Key deltas:**",
    "**Direct applicability:**",
    "**Reason:**",
    "**Parameters to re-validate:**",
]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_dissect_fields(
    key_equations: str,
    empirical_findings: str,
    context_fit: str,
    limitations: str,
) -> None:
    """
    Validate DISSECT output format before writing to DB.
    Raises ValueError listing every violation found.

    Rules enforced:
      key_equations     : at least one [§X.X] anchor + confidence: tag
      empirical_findings: at least one [§X.X] or [Abstract] anchor + confidence: tag
      context_fit       : all 8 required **Bold header:** lines present
      limitations       : at least one [§X.X] anchor + confidence: tag
    """
    errors = []

    anchor_re         = re.compile(r"\[§\d|\[Abstract\]", re.IGNORECASE)
    section_anchor_re = re.compile(r"\[§\d")
    confidence_re     = re.compile(r"confidence:\s*(full-text|abstract|unavailable)", re.IGNORECASE)

    if not section_anchor_re.search(key_equations):
        errors.append("key_equations: missing [§X.X] anchor — every equation must cite its section")
    if not confidence_re.search(key_equations):
        errors.append("key_equations: missing confidence: tag")

    if not anchor_re.search(empirical_findings):
        errors.append("empirical_findings: missing [§X.X] or [Abstract] anchor")
    if not confidence_re.search(empirical_findings):
        errors.append("empirical_findings: missing confidence: tag")

    missing = [h for h in _CONTEXT_FIT_HEADERS if h not in context_fit]
    if missing:
        errors.append(f"context_fit: missing required headers: {missing}")

    if not section_anchor_re.search(limitations):
        errors.append("limitations: missing [§X.X] anchor")
    if not confidence_re.search(limitations):
        errors.append("limitations: missing confidence: tag")

    if errors:
        raise ValueError(
            "DISSECT format validation failed — DB write blocked.\n"
            + "\n".join(f"  [FAIL] {e}" for e in errors)
        )


# ── Write functions ────────────────────────────────────────────────────────────

def log_agent_call(
    idea_id: str,
    gate_number: int,
    gear: str,
    model: str,
    task_summary: str,
    output_summary: str = "",
    paper_id: int = None,
    result_id: int = None,
) -> int:
    """
    Log a GENERATE or VALIDATE agent call.
    For DISSECT use log_dissect_result() — it atomically updates step2_papers too.

    Returns the new call_id.
    """
    if gear == "DISSECT":
        raise ValueError("Use log_dissect_result() for DISSECT — it atomically updates step2_papers.")
    if gear not in ("GENERATE", "VALIDATE"):
        raise ValueError("gear must be 'GENERATE' or 'VALIDATE'")
    if model not in _VALID_MODELS:
        raise ValueError(f"model must be one of {_VALID_MODELS}")

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_agent
                (idea_id, gate_number, gear, model, source, task_summary,
                 output_summary, paper_id, result_id, created_at)
            VALUES (?, ?, ?, ?, 'agent', ?, ?, ?, ?, ?)
        """, (idea_id, gate_number, gear, model, task_summary,
              output_summary, paper_id, result_id, _now()))
        conn.commit()
        call_id = cur.lastrowid

    print(f"[agent_log] call_id={call_id} [{gear}|{model}] {idea_id} gate={gate_number}")
    return call_id


def log_dissect_result(
    idea_id: str,
    gate_number: int,
    paper_id: int,
    model: str,
    task_summary: str,
    key_equations: str,
    empirical_findings: str,
    context_fit: str,
    limitations: str,
    output_summary: str = "",
) -> int:
    """
    Atomic DISSECT writer.
    Validates fields → updates step2_papers → inserts log_agent.
    All in one transaction.

    Returns the new call_id.
    """
    if model not in _VALID_MODELS:
        raise ValueError(f"model must be one of {_VALID_MODELS}")

    validate_dissect_fields(key_equations, empirical_findings, context_fit, limitations)

    with _conn() as conn:
        cur = conn.cursor()

        cur.execute("SELECT paper_id FROM step2_papers WHERE paper_id=?", (paper_id,))
        if cur.fetchone() is None:
            raise ValueError(f"paper_id={paper_id} not found in step2_papers")

        ts = _now()

        cur.execute("""
            INSERT INTO log_agent
                (idea_id, gate_number, gear, model, source, task_summary,
                 output_summary, paper_id, created_at)
            VALUES (?, ?, 'DISSECT', ?, 'agent', ?, ?, ?, ?)
        """, (idea_id, gate_number, model, task_summary, output_summary, paper_id, ts))
        call_id = cur.lastrowid

        cur.execute("""
            UPDATE step2_papers
            SET dissected=1, key_equations=?, empirical_findings=?,
                context_fit=?, limitations=?, dissected_at=?
            WHERE paper_id=?
        """, (key_equations, empirical_findings, context_fit, limitations, ts, paper_id))

        conn.commit()

    print(f"[agent_log] DISSECT call_id={call_id} [{model}] {idea_id} paper_id={paper_id}")
    return call_id


def log_human_decision(
    idea_id: str,
    gate_number: int,
    task_summary: str,
    output_summary: str = "",
) -> int:
    """
    Log a human-Claude architecture or methodology decision.
    Replaces the old generate_calls table.
    gear='GENERATE', source='human', model=NULL.

    Returns the new call_id.
    """
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_agent
                (idea_id, gate_number, gear, model, source,
                 task_summary, output_summary, created_at)
            VALUES (?, ?, 'GENERATE', NULL, 'human', ?, ?, ?)
        """, (idea_id, gate_number, task_summary, output_summary, _now()))
        conn.commit()
        call_id = cur.lastrowid

    print(f"[agent_log] HUMAN call_id={call_id} {idea_id} gate={gate_number}")
    return call_id


# ── Read functions ─────────────────────────────────────────────────────────────

def get_papers(idea_id: str) -> list[dict]:
    """Return all step2_papers rows for an idea."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM step2_papers WHERE idea_id=? ORDER BY paper_id",
            (idea_id,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_agent_calls(idea_id: str) -> list[dict]:
    """Return all log_agent rows for an idea, ordered by created_at."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM log_agent WHERE idea_id=? ORDER BY created_at",
            (idea_id,)
        )
        return [dict(r) for r in cur.fetchall()]
