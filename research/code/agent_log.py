"""
Agent log interface for agent_log.db.
All writes go through here — no raw SQL elsewhere.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "db" / "agent_log.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log_agent_call(
    gear: str,
    model: str,
    task: str,
    papers: list = None,
    idea_id: int = None,
    idea_code: str = None,
) -> int:
    """
    Log a QR agent call to agent_log.db.

    gear    : "GENERATE" or "VALIDATE"
    model   : "sonnet" or "opus"
    task    : one-line description of what was asked
    papers  : list of dicts [{title, url, source, relevance}] or None
    idea_id : optional — link to idea in ideas_log.db
    idea_code: optional — e.g. "HMM-001" (denormalized for readability)

    Returns the new agent_call id.
    """
    valid_gears  = ("GENERATE", "VALIDATE")
    valid_models = ("sonnet", "opus")

    if gear not in valid_gears:
        raise ValueError(f"gear must be one of {valid_gears}")
    if model not in valid_models:
        raise ValueError(f"model must be one of {valid_models}")

    papers_json = json.dumps(papers or [])

    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agent_calls
                (idea_id, idea_code, gear, model, task, papers, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (idea_id, idea_code, gear, model, task, papers_json, _now()))
        conn.commit()
        call_id = cur.lastrowid
        print(f"Logged agent_call id={call_id} [{gear} | {model}] — {task}")
        return call_id


def get_papers_for_idea(idea_code: str) -> list:
    """Return all papers pulled for a given idea across all agent calls."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT papers FROM agent_calls WHERE idea_code = ? AND papers != '[]'",
            (idea_code,)
        )
        rows = cur.fetchall()

    all_papers = []
    for row in rows:
        all_papers.extend(json.loads(row["papers"]))
    return all_papers
