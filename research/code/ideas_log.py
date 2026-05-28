"""
Ideas log interface for ideas_log.db.
All writes go through here — no raw SQL elsewhere.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "ideas_log.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ── Read ──────────────────────────────────────────────────────────────────────

def get_idea(code: str) -> dict:
    """Return a single idea row by code (e.g. 'HMM-001')."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ideas WHERE code = ?", (code,))
        row = cur.fetchone()
        return dict(row) if row else {}


def list_ideas(status: str = None, category: str = None, role: str = None) -> list:
    """Return ideas filtered by status, category, or role."""
    query = "SELECT * FROM ideas WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if role:
        query += " AND role = ?"
        params.append(role)
    query += " ORDER BY sort_order, id"

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


# ── Write ─────────────────────────────────────────────────────────────────────

def add_idea(
    code: str,
    name: str,
    role: str,
    category: str,
    asset_class: str = "XAUUSD",
    signal_type: str = None,
    source: str = "agent",
    parent_idea_id: int = None,
    sort_order: int = None,
    notes: str = None,
) -> int:
    """Insert a new idea. Returns the new idea id."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ideas
                (code, name, role, category, asset_class, signal_type,
                 status, source, parent_idea_id, sort_order, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'inbox', ?, ?, ?, ?, ?)
        """, (code, name, role, category, asset_class, signal_type,
              source, parent_idea_id, sort_order, _now(), notes))
        conn.commit()
        idea_id = cur.lastrowid
        print(f"Added idea {code} (id={idea_id})")
        return idea_id


def update_idea_status(idea_id: int, status: str) -> None:
    """Move idea to: inbox | promoted | parked | dropped."""
    valid = ("inbox", "promoted", "parked", "dropped")
    if status not in valid:
        raise ValueError(f"status must be one of {valid}")

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE ideas SET status = ? WHERE id = ?", (status, idea_id))
        if cur.rowcount == 0:
            raise ValueError(f"idea_id={idea_id} not found")
        conn.commit()
        print(f"idea_id={idea_id}: status -> {status}")


def log_generate_call(
    topic: str,
    question: str,
    output_summary: str,
    outcome: str,
    idea_id: int = None,
) -> int:
    """Log a GENERATE agent call. Returns the new generate_call id."""
    valid_outcomes = ("ranked_families", "dead_end", "needs_more", "framework_mapped")
    if outcome not in valid_outcomes:
        raise ValueError(f"outcome must be one of {valid_outcomes}")

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO generate_calls
                (timestamp, idea_id, topic, question, output_summary, outcome)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (_now(), idea_id, topic, question, output_summary, outcome))
        conn.commit()
        call_id = cur.lastrowid
        print(f"Logged generate_call id={call_id} [{outcome}]")
        return call_id
